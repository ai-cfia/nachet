from typing import Type, Optional, Sequence, TypedDict
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.model import Folder, Picture
from app.datastore.base_crud import BaseCRUDDataService


class UserDirectoryRow(TypedDict):
    """Row type for user directory with count query results."""
    id: UUID
    name: str
    folder_prefix: str
    description: str
    picture_count: int


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

    async def get_user_directories_count(
        self, user_id: str
    ) -> list[UserDirectoryRow]:
        """
        Retrieve all directories for a given user and number of pictures from the database.

        Args:
            user_id: The ID of the user whose directories are to be fetched.
        Returns:
            List of dictionaries with directory data and picture counts
        """
        stmt = (
            select(
                Folder.id,
                Folder.name,
                Folder.folder_prefix,
                Folder.description,
                func.count(Picture.id).label("picture_count"),
            )
            .join(Picture, isouter=True)
            .where(Folder.user_id == user_id)
            .where(Folder.active.is_(True))
            .group_by(Folder.id, Folder.name, Folder.folder_prefix, Folder.description)
        )
        # print(stmt.compile(dialect=postgresql.dialect()))
        result = await self.session.execute(stmt)
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
        result = await self.session.execute(stmt)
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
        self.session.add(new_directory)
        await self.session.flush()  # Ensure the new directory gets an ID
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
        result = await self.session.execute(stmt)
        directory = result.scalar_one_or_none()

        if directory:
            directory.name = new_name
            self.session.add(directory)
            await self.session.flush()  # Ensure changes are applied
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
        stmt = (
            select(Folder.folder_prefix)
            .where(Folder.id == folder_id)
            .where(Folder.org_user_role_id == user_role_id)
            .where(Folder.active.is_(True))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
