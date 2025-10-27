"""
Generic base CRUD service providing reusable patterns for all entity services.

This module implements a generic CRUD service using Python's typing.Generic to
eliminate code duplication across service classes. All entity-specific services
should inherit from BaseCRUDService and BaseCRUDDataService.
"""

from beartype.typing import TypeVar, Generic, List, Optional, Dict, Any, Type, Protocol, cast
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped


class CRUDModel(Protocol):
    """Protocol defining the required attributes for CRUD operations."""
    id: Mapped[UUID]
    active: Mapped[bool]
    date_created: Mapped[datetime]


# Generic type variable for database models
T = TypeVar("T", bound=DeclarativeBase)
# Type variable for model classes
ModelClass = TypeVar("ModelClass", bound=Type[DeclarativeBase])


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
        # Type assertion: All model classes used with CRUD must have these attributes
        model_class_typed = cast(Type[CRUDModel], model_class)

        # Enforce limit bounds
        limit = min(max(1, limit), 1000)
        offset = max(0, offset)

        # Base query
        query = select(model_class).where(model_class_typed.active.is_(True))

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
        total_count = count_result.scalar() or 0

        # Apply sorting
        if order_by and hasattr(model_class, order_by):
            order_field = getattr(model_class, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field.asc())
        else:
            # Default sort by date_created descending (newest first)
            query = query.order_by(model_class_typed.date_created.desc())

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
        # Type assertion: All model classes used with CRUD must have these attributes
        model_class_typed = cast(Type[CRUDModel], model_class)
        query = (
            select(model_class)
            .where(model_class_typed.id == entity_id)
            .where(model_class_typed.active.is_(True))
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
            The created entity object with relationships loaded
        """
        model_class = self.get_model_class()
        # Type assertion: All model classes used with CRUD must have these attributes
        model_class_typed = cast(Type[CRUDModel], model_class)
        kwargs["active"] = True  # Ensure active is set
        entity = model_class(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)

        # Re-fetch with relationships loaded if query options are defined
        query_options = self.get_query_options()
        if query_options:
            # Cast entity to access id attribute for type checker
            entity_typed = cast(CRUDModel, entity)
            query = (
                select(model_class)
                .where(model_class_typed.id == entity_typed.id)
                .options(*query_options)
            )
            result = await self.session.execute(query)
            entity = result.scalar_one()

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
        # Type assertion: All model classes used with CRUD must have these attributes
        model_class_typed = cast(Type[CRUDModel], model_class)
        query = select(model_class).where(model_class_typed.id == entity_id)
        result = await self.session.execute(query)
        entity = result.scalar_one_or_none()

        if not entity:
            return None

        # Cast entity to access active attribute for type checker
        entity_typed = cast(CRUDModel, entity)
        entity_typed.active = False
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
