from __future__ import annotations

from beartype.typing import Type, Optional, TypedDict
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.model import Folder, Picture, Users
from app.datastore.base_crud import BaseCRUDDataService


class UserDirectoryRow(TypedDict):
    """Row type for user directory with count query results."""

    id: UUID
    name: str
    folder_prefix: str
    description: str
    picture_count: int
    is_default_folder: bool


class OrgDirectoryRow(TypedDict):
    """Row type for organization directory with count query results."""

    id: UUID
    user_id: UUID
    name: str
    folder_prefix: str
    description: str
    picture_count: int


class DirectoryDataService(BaseCRUDDataService[Folder]):
    """Data access layer for Directory (Folder) database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Folder]:
        """Return the Folder model class."""
        return Folder

    def get_query_options(self) -> list:
        """
        Load relationships for all Folder queries.

        Returns:
            List of SQLAlchemy query options for loading relationships:
            - pictures: The pictures in this folder
            - org_admin_role: The organization admin role
            - org_user_role: The organization user role
        """
        return [
            selectinload(Folder.pictures),
            selectinload(Folder.org_admin_role),
            selectinload(Folder.org_user_role),
        ]

    # Custom methods for directory-specific operations

    @classmethod
    async def get_user_directories_with_count(
        cls, user_id: str
    ) -> list[UserDirectoryRow]:
        """
        Retrieve all directories for a user with picture counts.

        This is a standalone method that manages its own session lifecycle.

        Args:
            user_id: The ID of the user whose directories are to be fetched.

        Returns:
            List of dictionaries with directory data and picture counts
        """
        from app.db.utils import sessionmanager

        async with sessionmanager.get_session() as session:
            data_service = cls(session)
            return await data_service.get_user_directories_count(user_id)

    @classmethod
    async def get_org_directories_with_count(
        cls, org_user_role_id: str
    ) -> list[OrgDirectoryRow]:
        """
        Retrieve all directories for an organization with picture counts.

        This is a standalone method that manages its own session lifecycle.

        Args:
            org_user_role_id: The organization's user role ID to filter by.

        Returns:
            List of dictionaries with directory data and picture counts
        """
        from app.db.utils import sessionmanager

        async with sessionmanager.get_session() as session:
            data_service = cls(session)
            return await data_service.get_org_directories_count(org_user_role_id)

    async def get_user_directories_count(self, user_id: str) -> list[UserDirectoryRow]:
        """
        Retrieve all directories for a given user and number of pictures from the database.
        Includes is_default_folder flag to indicate if folder is a default folder for any active user.

        Args:
            user_id: The ID of the user whose directories are to be fetched.
        Returns:
            List of dictionaries with directory data and picture counts
        """
        # Subquery to check if folder is default for any active user
        is_default_subquery = (
            select(Users.id)
            .where(Users.default_folder_id == Folder.id)
            .where(Users.active.is_(True))
            .limit(1)
            .scalar_subquery()
        )

        stmt = (
            select(
                Folder.id,
                Folder.name,
                Folder.folder_prefix,
                Folder.description,
                func.count(Picture.id).label("picture_count"),
                (is_default_subquery.is_not(None)).label("is_default_folder"),
            )
            .join(Picture, isouter=True)
            .where(Folder.user_id == user_id)
            .where(Folder.active.is_(True))
            .group_by(Folder.id, Folder.name, Folder.folder_prefix, Folder.description)
        )
        # print(stmt.compile(dialect=postgresql.dialect()))
        result = await self.session.execute(stmt)  # type: ignore[attr-defined]
        return [row._asdict() for row in result.all()]  # type: ignore[misc]

    async def get_org_directories_count(
        self, org_user_role_id: str
    ) -> list[OrgDirectoryRow]:
        """
        Retrieve all directories for an organization and number of pictures from the database.

        Args:
            org_user_role_id: The organization's user role ID to filter by.
        Returns:
            List of dictionaries with directory data and picture counts
        """
        stmt = (
            select(
                Folder.id,
                Folder.user_id,
                Folder.name,
                Folder.folder_prefix,
                Folder.description,
                func.count(Picture.id).label("picture_count"),
            )
            .join(Picture, isouter=True)
            .where(Folder.org_user_role_id == org_user_role_id)
            .where(Folder.active.is_(True))
            .group_by(
                Folder.id,
                Folder.user_id,
                Folder.name,
                Folder.folder_prefix,
                Folder.description,
            )
        )
        result = await self.session.execute(stmt)  # type: ignore[attr-defined]
        return [row._asdict() for row in result.all()]  # type: ignore[misc]

    async def create_directory(
        self,
        user_id: str,
        org_admin_id: str,
        org_user_role_id: str,
        name: str,
        folder_prefix: str,
        description: str = "",
    ) -> str:
        """
        Create a new directory in the database.

        Args:
            user_id: The ID of the user creating the directory.
            org_admin_id: The ID of the organization admin role.
            org_user_role_id: The ID of the organization user role.
            name: The name of the directory.
            folder_prefix: The folder prefix (path) for the directory.
            description: Optional description of the directory.

        Returns:
            The created Folder object.
        """
        new_directory = Folder(
            user_id=user_id,
            org_admin_id=org_admin_id,
            org_user_role_id=org_user_role_id,
            name=name,
            folder_prefix=folder_prefix,
            description=description,
            active=True,
        )
        self.session.add(new_directory)  # type: ignore[attr-defined]
        await self.session.flush()  # type: ignore[attr-defined]  # Ensure the new directory gets an ID
        return str(new_directory.id)

    async def rename_directory(self, directory_id: str, new_name: str) -> str:
        """
        Rename an existing directory in the database.

        Args:
            directory_id: The ID of the directory to be renamed.
            new_name: The new name for the directory.

        Returns:
            None
        """
        stmt = (
            select(Folder)
            .where(Folder.id == directory_id)
            .where(Folder.active.is_(True))
        )
        result = await self.session.execute(stmt)  # type: ignore[attr-defined]
        directory = result.scalar_one_or_none()

        if directory:
            directory.name = new_name
            self.session.add(directory)  # type: ignore[attr-defined]
            await self.session.flush()  # type: ignore[attr-defined]  # Ensure changes are applied
        else:
            raise ValueError(f"Directory with ID {directory_id} not found or inactive.")
        return str(directory.id)

    async def check_folder_exists(
        self, folder_id: str, user_role_id: str
    ) -> Optional[str]:
        """
        Check if a folder exists and belongs to the given user role.

        Args:
            folder_id: The ID of the folder to check.
            user_role_id: The organization user role ID.

        Returns:
            The folder_prefix if folder exists and belongs to the user role, None otherwise
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug(
            "Checking folder exists",
            folder_id=folder_id,
            user_role_id=user_role_id,
        )

        start_time = time.time()

        stmt = (
            select(Folder.folder_prefix)
            .where(Folder.id == folder_id)
            .where(Folder.org_user_role_id == user_role_id)
            .where(Folder.active.is_(True))
        )
        result = await self.session.execute(stmt)  # type: ignore[attr-defined]
        folder_prefix = result.scalar_one_or_none()

        elapsed_ms = (time.time() - start_time) * 1000

        if folder_prefix:
            logger.debug(
                "Folder exists",
                folder_id=folder_id,
                folder_prefix=folder_prefix,
                duration_ms=round(elapsed_ms, 2),
            )
        else:
            logger.debug(
                "Folder not found",
                folder_id=folder_id,
                duration_ms=round(elapsed_ms, 2),
            )

        return folder_prefix

    async def find_folder_by_path(
        self, org_user_role_id: str, folder_name: str, folder_prefix: str
    ) -> Optional[UUID]:
        """
        Find a folder by its path components (org_user_role_id, name, folder_prefix).

        Args:
            org_user_role_id: The organization user role ID.
            folder_name: The name of the folder (e.g., "avena-fatua").
            folder_prefix: The folder prefix (e.g., "/cfia/mycology/").

        Returns:
            The folder ID (UUID) if found, None otherwise.
        """
        stmt = (
            select(Folder.id)
            .where(Folder.org_user_role_id == org_user_role_id)
            .where(Folder.name == folder_name)
            .where(Folder.folder_prefix == folder_prefix)
            .where(Folder.active.is_(True))
        )
        result = await self.session.execute(stmt)  # type: ignore[attr-defined]
        folder_id = result.scalar_one_or_none()
        return folder_id  # type: ignore[return-value]
