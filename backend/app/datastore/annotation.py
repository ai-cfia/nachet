"""
Annotation data service using generic BaseCRUDDataService.

Provides data access layer for Annotation operations with minimal code duplication.
"""

from typing import Type
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
