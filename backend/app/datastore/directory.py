from typing import List, Type
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.model import Folder, Picture
from app.datastore.base_crud import BaseCRUDDataService


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
    async def get_user_directories_count(self, user_id: str) -> List[Folder]:
        """
        Retrieve all directories for a given user and number of pictures from the database.

        Args:
            user_id: The ID of the user whose directories are to be fetched.
        Returns:
            List of Folder objects.
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
        return result.all()

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
        return new_directory._asdict()["id"]

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
        return directory._asdict()["id"]
