"""
Data access layer for Picture (Image) entities.
"""

from typing import Sequence

from sqlalchemy.orm import selectinload

from app.db.model import Picture
from app.service.base_crud import BaseCRUDDataService


class ImageDataService(BaseCRUDDataService[Picture]):
    """Data service for Picture (Image) entity operations."""

    @classmethod
    def get_model_class(cls) -> type[Picture]:
        """Return the Picture model class."""
        return Picture

    @classmethod
    async def get_query_options(cls) -> Sequence:
        """
        Return query options for eager loading relationships.

        Loads:
        - folder: The folder containing this picture
        - org_admin_role: The organization admin role
        """
        return [
            selectinload(Picture.folder),
            selectinload(Picture.org_admin_role),
        ]
