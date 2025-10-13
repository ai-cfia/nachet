"""
Generic base CRUD service providing reusable patterns for all entity services.

This module implements a generic CRUD service using Python's typing.Generic to
eliminate code duplication across service classes. All entity-specific services
should inherit from BaseCRUDService and BaseCRUDDataService.
"""

import traceback
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.service.rbac import RbacService
from app.service.logs import LogService
from app.db.data.data_constants import ROLE_CFIA_ADMIN

# Generic type variable for database models
T = TypeVar("T", bound=DeclarativeBase)


class BaseCRUDDataService(Generic[T]):
    """
    Generic data access layer for CRUD operations.

    Type parameter T should be a SQLAlchemy ORM model class.
    Subclasses must override get_model_class() to specify the entity type.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    def get_model_class(cls) -> Type[T]:
        """
        Return the SQLAlchemy model class for this data service.
        Must be overridden by subclasses.

        Example:
            @classmethod
            def get_model_class(cls) -> Type[Model]:
                return Model
        """
        raise NotImplementedError("Subclasses must implement get_model_class()")

    def get_query_options(self) -> list:
        """
        Return SQLAlchemy query options (e.g., joinedload, selectinload).
        Override this to customize eager loading of relationships.

        Returns:
            List of query options to apply to SELECT statements
        """
        return []

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> tuple[List[T], int]:
        """
        Retrieve active entities with pagination, filtering, and sorting.

        Args:
            offset: Number of records to skip (default: 0)
            limit: Maximum number of records to return (default: 100, max: 1000)
            filters: Dictionary of field_name: value pairs for filtering (optional)
            order_by: Field name to sort by (optional, defaults to date_created)
            order_direction: Sort direction 'asc' or 'desc' (default: 'asc')

        Returns:
            Tuple of (list of entity objects, total count before pagination)
        """
        model_class = self.get_model_class()

        # Enforce limit bounds
        limit = min(max(1, limit), 1000)
        offset = max(0, offset)

        # Base query
        query = select(model_class).where(model_class.active.is_(True))

        # Apply filters
        if filters:
            for field_name, value in filters.items():
                if hasattr(model_class, field_name):
                    field = getattr(model_class, field_name)
                    query = query.where(field == value)

        # Count total before pagination
        from sqlalchemy import func, select as sa_select
        count_query = sa_select(func.count()).select_from(query.alias())
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar()

        # Apply sorting
        if order_by and hasattr(model_class, order_by):
            order_field = getattr(model_class, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field.asc())
        elif hasattr(model_class, "date_created"):
            # Default sort by date_created descending (newest first)
            query = query.order_by(model_class.date_created.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Apply relationship loading
        query = query.options(*self.get_query_options())

        result = await self.session.execute(query)
        return list(result.scalars().all()), total_count

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Retrieve an entity by ID.

        Args:
            entity_id: The entity UUID

        Returns:
            Entity object if found and active, None otherwise
        """
        model_class = self.get_model_class()
        query = (
            select(model_class)
            .where(model_class.id == entity_id)
            .where(model_class.active.is_(True))
            .options(*self.get_query_options())
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> T:
        """
        Create a new entity with provided attributes.

        Args:
            **kwargs: Attributes to set on the new entity

        Returns:
            The created entity object
        """
        model_class = self.get_model_class()
        kwargs["active"] = True  # Ensure active is set
        entity = model_class(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity_id: UUID, **kwargs) -> Optional[T]:
        """
        Update an entity with provided attributes.

        Args:
            entity_id: The entity UUID
            **kwargs: Attributes to update (only non-None values are updated)

        Returns:
            Updated entity object if found, None otherwise
        """
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        # Update only provided fields (non-None values)
        for key, value in kwargs.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)

        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def soft_delete(self, entity_id: UUID) -> Optional[T]:
        """
        Soft delete an entity by setting active to False.

        Args:
            entity_id: The entity UUID

        Returns:
            The soft-deleted entity object if found, None otherwise
        """
        model_class = self.get_model_class()
        query = select(model_class).where(model_class.id == entity_id)
        result = await self.session.execute(query)
        entity = result.scalar_one_or_none()

        if not entity:
            return None

        entity.active = False
        await self.session.flush()
        await self.session.refresh(entity)
        return entity


class BaseCRUDService(Generic[T]):
    """
    Generic service layer for CRUD operations with RBAC and logging.

    Provides standard CRUD methods with:
    - RBAC validation (GET operations for any user, CUD for admin only)
    - Structured error handling
    - Comprehensive logging
    - Consistent response formats

    Subclasses must implement:
    - get_entity_name(): Return entity name for error messages
    - get_data_service_class(): Return the data service class
    - serialize_entity(): Convert entity to dictionary
    - get_not_found_exception(): Return entity-specific NotFoundError
    - get_creation_exception(): Return entity-specific CreationError
    - get_update_exception(): Return entity-specific UpdateError
    - get_deletion_exception(): Return entity-specific DeletionError
    """

    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger instance."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages (e.g., 'Model', 'Pipeline')."""
        raise NotImplementedError("Subclasses must implement get_entity_name()")

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[T]]:
        """Return the data service class for this entity."""
        raise NotImplementedError("Subclasses must implement get_data_service_class()")

    @classmethod
    def serialize_entity(cls, entity: T) -> Dict[str, Any]:
        """
        Convert entity to dictionary for API response.
        Override this to customize serialization.

        Args:
            entity: The entity object to serialize

        Returns:
            Dictionary representation of the entity
        """
        raise NotImplementedError("Subclasses must implement serialize_entity()")

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return entity-specific NotFoundError exception class."""
        raise NotImplementedError("Subclasses must implement get_not_found_exception()")

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return entity-specific CreationError exception class."""
        raise NotImplementedError("Subclasses must implement get_creation_exception()")

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return entity-specific UpdateError exception class."""
        raise NotImplementedError("Subclasses must implement get_update_exception()")

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return entity-specific DeletionError exception class."""
        raise NotImplementedError("Subclasses must implement get_deletion_exception()")

    @classmethod
    async def get_all(
        cls,
        user_id: UUID,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> Dict[str, Any]:
        """
        Retrieve entities with pagination, filtering, and sorting.

        Args:
            user_id: UUID of the requesting user
            offset: Number of records to skip (default: 0)
            limit: Maximum records to return (default: 100, max: 1000)
            filters: Dictionary of field_name: value pairs for filtering (optional)
            order_by: Field name to sort by (optional)
            order_direction: Sort direction 'asc' or 'desc' (default: 'asc')

        Returns:
            Dictionary with pagination metadata and items:
            {
                "items": [...],
                "total": 150,
                "offset": 0,
                "limit": 100,
                "has_more": true
            }

        Raises:
            HTTPException: 401 if user not authenticated, 500 on other errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        entity_name_plural = f"{entity_name_lower}s"

        try:
            # RBAC: Any authenticated user can view
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                entities, total_count = await data_service.get_all(
                    offset=offset,
                    limit=limit,
                    filters=filters,
                    order_by=order_by,
                    order_direction=order_direction,
                )

                result = {
                    "items": [
                        cls.serialize_entity(entity) for entity in entities
                    ],
                    "total": total_count,
                    "offset": offset,
                    "limit": limit,
                    "has_more": (offset + limit) < total_count,
                }

                await session.commit()
                return result

        except HTTPException:
            raise
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to retrieve {entity_name_plural}: {str(e)}",
                user_id=str(user_id),
                offset=offset,
                limit=limit,
            )
            logger.debug(
                f"Traceback for failed retrieve {entity_name_plural}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity_name_plural}",
            )

    @classmethod
    async def get_by_id(cls, user_id: UUID, entity_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a single entity by ID (requires any authenticated user).

        Args:
            user_id: UUID of the requesting user
            entity_id: UUID of the entity to retrieve

        Returns:
            Dictionary representation of the entity

        Raises:
            HTTPException: 401 if not authenticated, 404 if not found, 500 on errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()

        try:
            # RBAC: Any authenticated user can view
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.get_by_id(entity_id)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                result = cls.serialize_entity(entity)
                await session.commit()
                return result

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            logger.warning(
                f"{entity_name} not found: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to retrieve {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed retrieve {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity_name_lower}",
            )

    @classmethod
    async def create(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Create a new entity (requires CFIA admin).

        Args:
            user_id: UUID of the requesting user
            **kwargs: Entity attributes

        Returns:
            Dictionary representation of the created entity

        Raises:
            HTTPException: 401 if not authenticated, 403 if not admin, 500 on errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        creation_exc = cls.get_creation_exception()

        try:
            # RBAC: Only CFIA admin can create
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(user_id, ROLE_CFIA_ADMIN, user_org_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.create(**kwargs)

                result = cls.serialize_entity(entity)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} created successfully",
                    user_id=str(user_id),
                    entity_id=str(entity.id),
                )

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
            )
            logger.debug(
                f"Traceback for failed create {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
            )
            logger.debug(
                f"Traceback for failed create {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )

    @classmethod
    async def update(cls, user_id: UUID, entity_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Update an existing entity (requires CFIA admin).

        Args:
            user_id: UUID of the requesting user
            entity_id: UUID of the entity to update
            **kwargs: Fields to update (only non-None values)

        Returns:
            Dictionary representation of the updated entity

        Raises:
            HTTPException: 401 if not authenticated, 403 if not admin,
                          404 if not found, 500 on errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()
        update_exc = cls.get_update_exception()

        try:
            # RBAC: Only CFIA admin can update
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(user_id, ROLE_CFIA_ADMIN, user_org_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.update(entity_id, **kwargs)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                result = cls.serialize_entity(entity)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} updated successfully",
                    user_id=str(user_id),
                    entity_id=str(entity_id),
                )

                return result

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            logger.warning(
                f"{entity_name} not found for update: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except update_exc as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to update {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed update {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to update {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed update {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )

    @classmethod
    async def delete(cls, user_id: UUID, entity_id: UUID) -> Dict[str, str]:
        """
        Soft delete an entity (requires CFIA admin).

        Args:
            user_id: UUID of the requesting user
            entity_id: UUID of the entity to delete

        Returns:
            Success message with entity ID

        Raises:
            HTTPException: 401 if not authenticated, 403 if not admin,
                          404 if not found, 500 on errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()
        deletion_exc = cls.get_deletion_exception()

        try:
            # RBAC: Only CFIA admin can delete
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(user_id, ROLE_CFIA_ADMIN, user_org_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.soft_delete(entity_id)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} soft deleted successfully",
                    user_id=str(user_id),
                    entity_id=str(entity_id),
                )

                return {
                    "message": f"{entity_name} soft deleted successfully",
                    "id": str(entity_id),
                }

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            logger.warning(
                f"{entity_name} not found for deletion: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except deletion_exc as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to delete {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed delete {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to delete {entity_name_lower}: {str(e)}",
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed delete {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )
