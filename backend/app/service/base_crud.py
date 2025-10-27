"""
Generic base CRUD service providing reusable patterns for all entity services.

This module implements a generic CRUD service using Python's typing.Generic to
eliminate code duplication across service classes. All entity-specific services
should inherit from BaseCRUDService and BaseCRUDDataService.

AUTHORIZATION FRAMEWORK:

This module provides two CRUD service base classes:

1. BaseCRUDService - Original implementation with basic RBAC:
   - GET operations: Any authenticated user
   - CUD operations: CFIA admin only

2. AuthorizedBaseCRUDService - Enhanced implementation with role-based access:
   - retrieve: org_user_role_id OR org_admin_role_id OR cfia_admin_role_id
   - update: org_user_role_id OR org_admin_role_id OR cfia_admin_role_id
   - delete: org_admin_role_id OR cfia_admin_role_id (admin-only)
   - create: Must override verify_create_access() in implementing classes

MIGRATION GUIDE:

To migrate from BaseCRUDService to AuthorizedBaseCRUDService:

1. Change inheritance:
   class MyService(BaseCRUDService[MyEntity]):  # OLD
   class MyService(AuthorizedBaseCRUDService[MyEntity]):  # NEW

2. Implement create authorization:
   @classmethod
   async def verify_create_access(cls, user_id: UUID, **kwargs) -> None:
       # Choose one of these patterns:

       # Pattern 1: Only org admins can create
       await RbacService.verify_user_is_org_admin(user_id)

       # Pattern 2: Any authenticated user can create
       await RbacService.get_user_organization_id(user_id)

       # Pattern 3: Custom logic based on creation parameters
       if kwargs.get('restricted_field'):
           await RbacService.verify_user_is_cfia_admin(user_id)
       else:
           await RbacService.verify_user_is_org_admin(user_id)

3. Ensure entities have role fields:
   - org_user_role_id: UUID field linking to user role
   - org_admin_role_id: UUID field linking to admin role

ROLE-BASED ACCESS PATTERNS:

The authorization system uses three levels of access:
- org_user_role_id: Basic user access within organization
- org_admin_role_id: Admin access within organization
- cfia_admin_role_id: Cross-organization admin access

Access is granted if user has ANY of the matching roles for the operation.
"""

import traceback
from beartype.typing import (
    TypeVar,
    Generic,
    Optional,
    Dict,
    Any,
    Type,
    Protocol,
    cast,
    runtime_checkable,
)
from uuid import UUID
from sqlalchemy.orm import DeclarativeBase
from fastapi import HTTPException, status
from abc import ABC, abstractmethod

from app.db.utils import sessionmanager
from app.service.logs import LogService
from app.datastore.base_crud import BaseCRUDDataService


# Protocol for entities with an id attribute
@runtime_checkable
class HasId(Protocol):
    """Protocol for database entities that have an id field."""

    id: UUID


# Generic type variable for database models
T = TypeVar("T", bound=DeclarativeBase)


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

    @staticmethod
    def _sanitize_error_message(error: Exception) -> str:
        """
        Sanitize exception message for safe logging.

        SQLAlchemy error messages often contain SQL with parameter placeholders
        like %(param_name)s which can be misinterpreted as format strings by
        loggers, causing KeyError when the logger tries to format them.

        This method escapes % characters to prevent format string interpretation.

        Args:
            error: The exception to sanitize

        Returns:
            Sanitized error message safe for logging
        """
        error_str = str(error)
        # Escape % to prevent format string interpretation
        # %(param)s becomes %%(param)s which is treated as literal %(param)s
        return error_str.replace("%", "%%")

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
        requester_id: UUID,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> Dict[str, Any]:
        """
        Retrieve entities with pagination, filtering, and sorting.

        Args:
            requester_id: UUID of the requesting user
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
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

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
                    "items": [cls.serialize_entity(entity) for entity in entities],
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
            error_msg = f"Failed to retrieve {entity_name_plural}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                offset=offset,
                limit=limit,
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed retrieve {entity_name_plural}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity_name_plural}",
            )

    @classmethod
    async def get_by_id(cls, requester_id: UUID, entity_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a single entity by ID (requires any authenticated user).

        Args:
            requester_id: UUID of the requesting user
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
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

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
            warning_msg = f"{entity_name} not found: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to retrieve {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed retrieve {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity_name_lower}",
            )

    @classmethod
    async def create(cls, requester_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Create a new entity (requires CFIA admin).

        Args:
            requester_id: UUID of the requesting user
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
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.create(**kwargs)

                result = cls.serialize_entity(entity)
                await session.commit()

                logger = cls._get_logger()
                # Type assertion: entity conforms to HasId protocol
                # All database entities should have an id field
                entity_with_id = cast(HasId, entity)
                logger.bind(
                    user_id=str(requester_id),
                    entity_id=str(entity_with_id.id),
                ).info(f"{entity_name} created successfully")

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(user_id=str(requester_id)).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed create {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.bind(user_id=str(requester_id)).error(
                f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            )
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed create {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )

    @classmethod
    async def update(
        cls, requester_id: UUID, entity_id: UUID, **kwargs
    ) -> Dict[str, Any]:
        """
        Update an existing entity (requires CFIA admin).

        Args:
            requester_id: UUID of the requesting user
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
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.update(entity_id, **kwargs)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                result = cls.serialize_entity(entity)
                await session.commit()

                logger = cls._get_logger()
                logger.bind(
                    user_id=str(requester_id),
                    entity_id=str(entity_id),
                ).info(f"{entity_name} updated successfully")

                return result

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            warning_msg = (
                f"{entity_name} not found for update: {cls._sanitize_error_message(e)}"
            )
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except update_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to update {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed update {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to update {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed update {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )

    @classmethod
    async def delete(cls, requester_id: UUID, entity_id: UUID) -> Dict[str, str]:
        """
        Soft delete an entity (requires CFIA admin).

        Args:
            requester_id: UUID of the requesting user
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
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.soft_delete(entity_id)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                await session.commit()

                logger = cls._get_logger()
                logger.bind(
                    user_id=str(requester_id),
                    entity_id=str(entity_id),
                ).info(f"{entity_name} soft deleted successfully")

                return {
                    "message": f"{entity_name} soft deleted successfully",
                    "id": str(entity_id),
                }

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            warning_msg = f"{entity_name} not found for deletion: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except deletion_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to delete {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed delete {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to delete {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                user_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed delete {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )


# ============================================================================
# Authorization-Enhanced CRUD Service
# ============================================================================


class AuthorizationMixin(ABC, Generic[T]):
    """
    Abstract mixin defining authorization methods for entity operations.

    Implementing classes must define how to verify user access for each operation
    based on entity role fields (org_user_role_id, org_admin_role_id).
    """

    @classmethod
    @abstractmethod
    async def verify_retrieve_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can retrieve/view the entity.

        Args:
            requester_id: UUID of the requesting user
            entity: The entity being accessed

        Raises:
            HTTPException: 403 if access denied
        """
        pass

    @classmethod
    @abstractmethod
    async def verify_update_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can update the entity.

        Args:
            requester_id: UUID of the requesting user
            entity: The entity being updated

        Raises:
            HTTPException: 403 if access denied
        """
        pass

    @classmethod
    @abstractmethod
    async def verify_delete_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can delete the entity.

        Args:
            requester_id: UUID of the requesting user
            entity: The entity being deleted

        Raises:
            HTTPException: 403 if access denied
        """
        pass

    @classmethod
    @abstractmethod
    async def verify_create_access(cls, requester_id: UUID, **kwargs) -> None:
        """
        Verify user can create entities.

        Must be implemented by subclasses as creation rules vary by entity type.

        Args:
            requester_id: UUID of the requesting user
            **kwargs: Entity creation parameters

        Raises:
            HTTPException: 403 if access denied
        """
        pass


class AuthorizedBaseCRUDService(BaseCRUDService[T], AuthorizationMixin[T]):
    """
    Enhanced CRUD service with role-based authorization.

    Implements fine-grained access control based on entity role fields:
    - retrieve: org_user_role_id OR org_admin_role_id OR cfia_admin_role_id
    - update: org_user_role_id OR org_admin_role_id OR cfia_admin_role_id
    - delete: org_admin_role_id OR cfia_admin_role_id (admin-only)
    - create: Must override verify_create_access() in implementing classes

    Entities must have org_user_role_id and org_admin_role_id fields.

    Example usage:
        class MyEntityService(AuthorizedBaseCRUDService[MyEntity]):
            @classmethod
            async def verify_create_access(cls, user_id: UUID, **kwargs) -> None:
                # Custom creation authorization logic
                await RbacService.verify_user_is_org_admin(user_id)
    """

    @classmethod
    async def verify_retrieve_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can retrieve/view the entity.

        Access granted if user has:
        - org_user_role_id matching entity.org_user_role_id, OR
        - org_admin_role_id matching entity.org_admin_role_id, OR
        - cfia_admin_role_id (cross-organization authority)
        """
        from app.service.rbac import RbacService

        # Get entity role fields
        org_user_role_id = getattr(entity, "org_user_role_id", None)
        org_admin_role_id = getattr(entity, "org_admin_role_id", None)

        # Check access using RbacService utility
        has_access = await RbacService.verify_user_has_entity_access(
            requester_id, org_user_role_id, org_admin_role_id
        )

        if not has_access:
            entity_name = cls.get_entity_name()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to retrieve {entity_name}",
            )

    @classmethod
    async def verify_update_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can update the entity.

        Access granted if user has:
        - org_user_role_id matching entity.org_user_role_id, OR
        - org_admin_role_id matching entity.org_admin_role_id, OR
        - cfia_admin_role_id (cross-organization authority)
        """
        from app.service.rbac import RbacService

        # Get entity role fields
        org_user_role_id = getattr(entity, "org_user_role_id", None)
        org_admin_role_id = getattr(entity, "org_admin_role_id", None)

        # Check access using RbacService utility
        has_access = await RbacService.verify_user_has_entity_access(
            requester_id, org_user_role_id, org_admin_role_id
        )

        if not has_access:
            entity_name = cls.get_entity_name()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to update {entity_name}",
            )

    @classmethod
    async def verify_delete_access(cls, requester_id: UUID, entity: T) -> None:
        """
        Verify user can delete the entity.

        Access granted if user has:
        - org_admin_role_id matching entity.org_admin_role_id, OR
        - cfia_admin_role_id (cross-organization authority)

        Note: org_user_role_id is NOT sufficient for deletion (admin-only operation)
        """
        from app.service.rbac import RbacService

        # Get entity admin role field
        org_admin_role_id = getattr(entity, "org_admin_role_id", None)

        # Check admin access using RbacService utility
        has_admin_access = await RbacService.verify_user_has_entity_admin_access(
            requester_id, org_admin_role_id
        )

        if not has_admin_access:
            entity_name = cls.get_entity_name()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to delete {entity_name} - admin role required",
            )

    @classmethod
    async def verify_create_access(cls, requester_id: UUID, **kwargs) -> None:
        """
        Verify user can create entities.

        MUST BE OVERRIDDEN in implementing classes.
        Creation authorization varies by entity type and business rules.

        Raises:
            NotImplementedError: If not overridden by subclass
        """
        entity_name = cls.get_entity_name()
        raise NotImplementedError(
            f"{cls.__name__} must implement verify_create_access() for {entity_name} creation. "
            f"Example: async def verify_create_access(cls, user_id: UUID, **kwargs) -> None: "
            f"await RbacService.verify_user_is_org_admin(user_id)"
        )

    # Override CRUD methods to include authorization checks

    @classmethod
    async def get_by_id(cls, requester_id: UUID, entity_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a single entity by ID with authorization check.

        Overrides BaseCRUDService.get_by_id() to add authorization verification.
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()

        try:
            # Basic authentication check
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.get_by_id(entity_id)

                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                # Authorization check
                await cls.verify_retrieve_access(requester_id, entity)

                result = cls.serialize_entity(entity)
                await session.commit()
                return result

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            warning_msg = f"{entity_name} not found: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to retrieve {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed retrieve {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity_name_lower}",
            )

    @classmethod
    async def update(
        cls, requester_id: UUID, entity_id: UUID, **kwargs
    ) -> Dict[str, Any]:
        """
        Update an existing entity with authorization check.

        Overrides BaseCRUDService.update() to add authorization verification.
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()
        update_exc = cls.get_update_exception()

        try:
            # Basic authentication check
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                # Get entity first for authorization check
                entity = await data_service.get_by_id(entity_id)
                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                # Authorization check
                await cls.verify_update_access(requester_id, entity)

                # Perform update
                updated_entity = await data_service.update(entity_id, **kwargs)
                if not updated_entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                result = cls.serialize_entity(updated_entity)
                await session.commit()

                logger = cls._get_logger()
                logger.bind(
                    requester_id=str(requester_id),
                    entity_id=str(entity_id),
                ).info(f"{entity_name} updated successfully")

                return result

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            warning_msg = (
                f"{entity_name} not found for update: {cls._sanitize_error_message(e)}"
            )
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except update_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to update {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed update {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to update {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed update {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity_name_lower}",
            )

    @classmethod
    async def delete(cls, requester_id: UUID, entity_id: UUID) -> Dict[str, str]:
        """
        Soft delete an entity with authorization check.

        Overrides BaseCRUDService.delete() to add authorization verification.
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        not_found_exc = cls.get_not_found_exception()
        deletion_exc = cls.get_deletion_exception()

        try:
            # Basic authentication check
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                # Get entity first for authorization check
                entity = await data_service.get_by_id(entity_id)
                if not entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                # Authorization check
                await cls.verify_delete_access(requester_id, entity)

                # Perform soft delete
                deleted_entity = await data_service.soft_delete(entity_id)
                if not deleted_entity:
                    raise not_found_exc(f"{entity_name} {entity_id} not found")

                await session.commit()

                logger = cls._get_logger()
                logger.bind(
                    requester_id=str(requester_id),
                    entity_id=str(entity_id),
                ).info(f"{entity_name} soft deleted successfully")

                return {
                    "message": f"{entity_name} soft deleted successfully",
                    "id": str(entity_id),
                }

        except HTTPException:
            raise
        except not_found_exc as e:
            logger = cls._get_logger()
            warning_msg = f"{entity_name} not found for deletion: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).warning(warning_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except deletion_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to delete {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed delete {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to delete {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(
                requester_id=str(requester_id),
                entity_id=str(entity_id),
            ).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed delete {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity_name_lower}",
            )

    @classmethod
    async def create(cls, requester_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Create a new entity with authorization check.

        Overrides BaseCRUDService.create() to add authorization verification.
        Subclasses MUST implement verify_create_access().
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        creation_exc = cls.get_creation_exception()

        try:
            # Basic authentication check
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requester_id)

            # Authorization check (must be implemented by subclass)
            await cls.verify_create_access(requester_id, **kwargs)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                entity = await data_service.create(**kwargs)

                result = cls.serialize_entity(entity)
                await session.commit()

                logger = cls._get_logger()
                # Type assertion: entity conforms to HasId protocol
                # All database entities should have an id field
                entity_with_id = cast(HasId, entity)
                logger.bind(
                    requester_id=str(requester_id),
                    entity_id=str(entity_with_id.id),
                ).info(f"{entity_name} created successfully")

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(requester_id=str(requester_id)).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed create {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.bind(requester_id=str(requester_id)).error(error_msg)
            logger.bind(traceback=traceback.format_exc()).debug(
                f"Traceback for failed create {entity_name_lower}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
