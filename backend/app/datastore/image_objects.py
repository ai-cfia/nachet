"""
Data access layer for Object (ImageObjects) entities.
"""

from typing import Sequence

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
