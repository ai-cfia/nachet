"""
Data access layer for Picture (Image) entities.
"""

from typing import Sequence

from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.db.model import Picture
from app.datastore.base_crud import BaseCRUDDataService


class ImageDataService(BaseCRUDDataService[Picture]):
    """Data service for Picture (Image) entity operations."""

    @classmethod
    def get_model_class(cls) -> type[Picture]:
        """Return the Picture model class."""
        return Picture

    @classmethod
    def get_query_options(cls) -> Sequence:
        """
        Return query options for eager loading relationships.

        Loads:
        - folder: The folder containing this picture
        - org_admin_role: The organization admin role
        - org_user_role: The organization user role
        """
        return [
            selectinload(Picture.folder),
            selectinload(Picture.org_admin_role),
            selectinload(Picture.org_user_role),
        ]

    async def check_sha256_exists(self, sha256: str):
        """
        Check if a picture with the given SHA256 hash exists in the database.

        Args:
            sha256: The SHA256 hash to check

        Returns:
            UUID | None: The UUID of the picture if it exists, None otherwise
        """
        query = select(Picture.id).where(Picture.sha256 == sha256).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
