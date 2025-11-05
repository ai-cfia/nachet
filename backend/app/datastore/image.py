"""
Data access layer for Picture (Image) entities.
"""

from uuid import UUID

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

    def get_query_options(self) -> list:
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

    async def check_sha256_exists(self, sha256: str, user_role_id: UUID):
        """
        Check if a picture with the given SHA256 hash exists within the user's organization.

        Image duplication is allowed across organizations but not within an organization.
        This is enforced by filtering on org_user_role_id, which is scoped to the organization.

        Args:
            sha256: The SHA256 hash to check
            user_role_id: The user's role ID (scoped to their organization)

        Returns:
            UUID | None: The UUID of the picture if it exists in the same organization, None otherwise
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug(
            "Checking SHA256 existence",
            sha256=sha256[:16] + "...",  # Log first 16 chars for privacy
            user_role_id=str(user_role_id),
        )

        start_time = time.time()

        query = (
            select(Picture.id)
            .where(Picture.sha256 == sha256)
            .where(Picture.org_user_role_id == user_role_id)
            .limit(1)
        )
        result = await self.session.execute(query)
        picture_id = result.scalar_one_or_none()

        elapsed_ms = (time.time() - start_time) * 1000

        if picture_id:
            logger.debug(
                "SHA256 exists (duplicate detected)",
                sha256=sha256[:16] + "...",
                existing_picture_id=str(picture_id),
                duration_ms=round(elapsed_ms, 2),
            )
        else:
            logger.debug(
                "SHA256 not found (no duplicate)",
                sha256=sha256[:16] + "...",
                duration_ms=round(elapsed_ms, 2),
            )

        return picture_id
