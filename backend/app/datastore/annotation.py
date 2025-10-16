"""
Annotation data service using generic BaseCRUDDataService.

Provides data access layer for Annotation operations with minimal code duplication.
Note: Annotation model doesn't have 'active' field, so we override methods that assume it exists.
"""

from typing import Type, Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import Annotation
from app.datastore.base_crud import BaseCRUDDataService


class AnnotationDataService(BaseCRUDDataService[Annotation]):
    """Data access layer for Annotation database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Annotation]:
        """Return the Annotation ORM class."""
        return Annotation

    def get_query_options(self) -> list:
        """
        Load relationships for all Annotation queries.
        
        Returns:
            List of SQLAlchemy query options for loading relationships:
            - picture: The associated picture
            - user: The user who created the annotation
            - pipeline: The pipeline used for annotation
            - org_admin_role: The organization admin role
            - org_user_role: The organization user role
        """
        return [
            selectinload(Annotation.picture),
            selectinload(Annotation.user),
            selectinload(Annotation.pipeline),
            selectinload(Annotation.org_admin_role),
            selectinload(Annotation.org_user_role),
        ]

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> tuple[List[Annotation], int]:
        """
        Retrieve annotations with pagination, filtering, and sorting.
        
        Override parent method since Annotation model doesn't have 'active' field.
        
        Returns:
            Tuple of (list of annotations, total count)
        """
        from sqlalchemy import func, select as sa_select
        
        model_class = self.get_model_class()
        
        # Start with base query - no active filter for Annotation
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
        count_query = sa_select(func.count()).select_from(query.alias())
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
        query_options = self.get_query_options()
        if query_options:
            query = query.options(*query_options)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.session.execute(query)
        entities = result.scalars().all()
        
        return list(entities), total_count

    async def get_by_id(self, entity_id: UUID) -> Optional[Annotation]:
        """
        Retrieve an annotation by ID.
        
        Override parent method since Annotation model doesn't have 'active' field.
        """
        model_class = self.get_model_class()
        
        query = (
            select(model_class)
            .where(model_class.id == entity_id)
        )
        
        # Apply relationships loading
        query_options = self.get_query_options()
        if query_options:
            query = query.options(*query_options)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Annotation:
        """
        Create a new annotation.
        
        Override parent method since Annotation model doesn't have 'active' field.
        """
        # Don't add 'active' field for Annotation model
        model_class = self.get_model_class()
        entity = model_class(**kwargs)
        
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        
        # Re-fetch with relationships loaded
        query = (
            select(model_class)
            .where(model_class.id == entity.id)
            .options(*self.get_query_options())
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    # TODO: Add 'active' field to Annotation model in database to support soft delete
    # Currently Annotation model lacks 'active' field, preventing proper soft delete functionality.
    # Once the field is added, remove these overrides and use the base class soft_delete implementation.
    
    async def delete(self, entity_id: UUID) -> bool:
        """
        DEPRECATED: Hard delete not allowed - waiting for 'active' field addition.
        
        Override parent method since Annotation model doesn't have 'active' field.
        This method should not be used until the model is updated.
        """
        raise NotImplementedError(
            "Delete operation not supported for Annotation. "
            "TODO: Add 'active' field to Annotation model to enable soft delete."
        )

    async def soft_delete(self, entity_id: UUID) -> Optional[Annotation]:
        """
        NOT IMPLEMENTED: Waiting for 'active' field addition to Annotation model.
        
        Annotation model currently lacks 'active' field required for soft delete.
        This method cannot function until the database schema is updated.
        """
        raise NotImplementedError(
            "Soft delete not supported for Annotation - missing 'active' field. "
            "TODO: Add 'active' field to Annotation model in database schema."
        )
