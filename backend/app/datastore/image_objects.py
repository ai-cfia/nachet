"""
Data access layer for Object (ImageObjects) entities.

Note: Object model doesn't have 'active' field, so we override methods that assume it exists.
"""

from typing import Sequence, List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.model import Object
from app.datastore.base_crud import BaseCRUDDataService


class ImageObjectsDataService(BaseCRUDDataService[Object]):
    """Data service for Object (ImageObjects) entity operations."""

    @classmethod
    def get_model_class(cls) -> type[Object]:
        """Return the Object model class."""
        return Object

    @classmethod
    async def get_query_options(cls) -> Sequence:
        """
        Return query options for eager loading relationships.

        Loads:
        - annotation: The inference/annotation this object belongs to
        - seed_top_1: The top seed prediction
        - seed_top_2: The second seed prediction
        - seed_top_3: The third seed prediction
        - user: The user who created the object
        - picture: The picture this object is from
        - feedback_user: The user who provided feedback
        - verifier_user: The user who verified the object
        - pipeline: The pipeline used for inference
        - org_admin_role: The organization admin role
        - org_user_role: The organization user role
        """
        return [
            selectinload(Object.annotation),
            selectinload(Object.seed_top_1),
            selectinload(Object.seed_top_2),
            selectinload(Object.seed_top_3),
            selectinload(Object.user),
            selectinload(Object.picture),
            selectinload(Object.feedback_user),
            selectinload(Object.verifier_user),
            selectinload(Object.pipeline),
            selectinload(Object.org_admin_role),
            selectinload(Object.org_user_role),
        ]

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> tuple[List[Object], int]:
        """
        Retrieve objects with pagination, filtering, and sorting.

        Override parent method since Object model doesn't have 'active' field.

        Returns:
            Tuple of (list of objects, total count)
        """
        model_class = self.get_model_class()

        # Start with base query - no active filter for Object
        query = select(model_class)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(model_class, key):
                    column = getattr(model_class, key)
                    if isinstance(value, list):
                        query = query.where(column.in_(value))
                    else:
                        query = query.where(column == value)

        # Count total before pagination
        count_query = select(func.count()).select_from(query.alias())
        count_result = await self.session.execute(count_query)
        total_count = count_result.scalar()

        # Apply ordering
        if order_by and hasattr(model_class, order_by):
            column = getattr(model_class, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())

        # Apply relationships loading
        query_options = await self.get_query_options()
        if query_options:
            query = query.options(*query_options)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        # Execute query
        result = await self.session.execute(query)
        entities = result.scalars().all()

        return list(entities), total_count

    async def get_by_id(self, entity_id: UUID) -> Optional[Object]:
        """
        Retrieve an object by ID.

        Override parent method since Object model doesn't have 'active' field.
        """
        model_class = self.get_model_class()

        query = select(model_class).where(model_class.id == entity_id)

        # Apply relationships loading
        query_options = await self.get_query_options()
        if query_options:
            query = query.options(*query_options)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Object:
        """
        Create a new object.

        Override parent method since Object model doesn't have 'active' field.
        """
        model_class = self.get_model_class()
        entity = model_class(**kwargs)

        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)

        # Re-fetch with relationships loaded
        query = (
            select(model_class)
            .where(model_class.id == entity.id)
            .options(*await self.get_query_options())
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    # TODO: Add 'active' field to Object model in database to support soft delete
    # Currently Object model lacks 'active' field, preventing proper soft delete functionality.
    # Once the field is added, remove these overrides and use the base class soft_delete implementation.

    async def delete(self, entity_id: UUID) -> bool:
        """
        DEPRECATED: Hard delete not allowed - waiting for 'active' field addition.

        Override parent method since Object model doesn't have 'active' field.
        This method should not be used until the model is updated.
        """
        raise NotImplementedError(
            "Delete operation not supported for Object. "
            "TODO: Add 'active' field to Object model to enable soft delete."
        )

    async def soft_delete(self, entity_id: UUID) -> Optional[Object]:
        """
        NOT IMPLEMENTED: Waiting for 'active' field addition to Object model.

        Object model currently lacks 'active' field required for soft delete.
        This method cannot function until the database schema is updated.
        """
        raise NotImplementedError(
            "Soft delete not supported for Object - missing 'active' field. "
            "TODO: Add 'active' field to Object model in database schema."
        )
