from typing import Dict, Any, Type
from uuid import UUID
from loguru import logger

from app.db.utils import sessionmanager
from app.db.model import Folder
from app.datastore import DirectoryDataService
from app.service.base_crud import BaseCRUDService
from app.service.rbac import RbacService
from app.exceptions import (
    DirectoryNotFoundError,
    DirectoryCreationError,
    DirectoryUpdateError,
    DirectoryDeletionError,
)
from fastapi import HTTPException


class DirectoryService(BaseCRUDService[Folder]):
    """
    Service layer for Directory (Folder) operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active directories are returned by default
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "Directory"

    @classmethod
    def get_data_service_class(cls) -> Type[DirectoryDataService]:
        """Return the data service class."""
        return DirectoryDataService

    @classmethod
    def serialize_entity(cls, entity: Folder) -> Dict[str, Any]:
        """Convert Folder entity to dictionary."""
        return {
            "id": str(entity.id),
            "user_id": str(entity.user_id),
            "org_admin_id": str(entity.org_admin_id),
            "name": entity.name,
            "folder_prefix": entity.folder_prefix,
            "description": entity.description,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
            "date_updated": entity.date_updated.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return Directory NotFoundError exception class."""
        return DirectoryNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return Directory CreationError exception class."""
        return DirectoryCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return Directory UpdateError exception class."""
        return DirectoryUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return Directory DeletionError exception class."""
        return DirectoryDeletionError

    # Custom methods for directory-specific operations
    @staticmethod
    async def get_user_directories(user_id: UUID) -> Dict[str, Any]:
        """
        Get all directories for a specific user with picture counts.

        This is a custom method that provides additional aggregated data
        beyond the standard get_all() CRUD operation.

        Args:
            user_id: UUID of the user

        Returns:
            Dictionary containing list of directories with picture counts

        Raises:
            HTTPException: If user is not authorized or operation fails
        """
        try:
            # Verify user authentication
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DirectoryDataService(session)
                directories = await data_service.get_user_directories_count(str(user_id))

                logger.info(
                    f"Retrieved {len(directories)} directories for user {user_id}"
                )

                return {
                    "directories": [directory._asdict() for directory in directories]
                    if directories
                    else []
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to retrieve directories for user {user_id}: {str(e)}"
            )
            raise DirectoryNotFoundError(
                f"Failed to retrieve directories for user {user_id}"
            )

    @staticmethod
    async def create_directory(
        user_id: UUID,
        org_admin_id: UUID,
        name: str,
        folder_prefix: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new directory for a user.

        This is a custom method that handles directory creation with specific
        business logic beyond the standard create() CRUD operation.

        Args:
            user_id: UUID of the user creating the directory
            org_admin_id: UUID of the organization admin role
            name: Name of the directory
            folder_prefix: Folder prefix (path) for the directory
            description: Optional description of the directory

        Returns:
            Dictionary representation of the created directory

        Raises:
            HTTPException: If user is not authorized or creation fails
        """
        try:
            # Verify user is CFIA admin for create operations
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DirectoryDataService(session)
                new_directory_id = await data_service.create_directory(
                    str(user_id), str(org_admin_id), name, folder_prefix, description
                )
                await session.commit()

                logger.info(
                    f"Created directory '{name}' (ID: {new_directory_id}) for user {user_id}"
                )

                return {"id": new_directory_id, "message": "Directory created successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to create directory '{name}' for user {user_id}: {str(e)}"
            )
            raise DirectoryCreationError(f"Failed to create directory '{name}'")

    @staticmethod
    async def rename_directory(user_id: UUID, directory_id: UUID, new_name: str) -> Dict[str, Any]:
        """
        Rename an existing directory.

        This is a custom method for the specific rename operation,
        which is a subset of the standard update() CRUD operation.

        Args:
            user_id: UUID of the user performing the rename
            directory_id: UUID of the directory to rename
            new_name: New name for the directory

        Returns:
            Dictionary with the directory ID and success message

        Raises:
            HTTPException: If user is not authorized or rename fails
        """
        try:
            # Verify user is CFIA admin for update operations
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DirectoryDataService(session)
                updated_directory_id = await data_service.rename_directory(
                    str(directory_id), new_name
                )
                await session.commit()

                logger.info(
                    f"Renamed directory {directory_id} to '{new_name}' by user {user_id}"
                )

                return {
                    "id": updated_directory_id,
                    "message": f"Directory renamed to '{new_name}' successfully",
                }
        except HTTPException:
            raise
        except ValueError as e:
            logger.error(f"Directory {directory_id} not found: {str(e)}")
            raise DirectoryNotFoundError(f"Directory {directory_id} not found")
        except Exception as e:
            logger.error(
                f"Failed to rename directory {directory_id} to '{new_name}': {str(e)}"
            )
            raise DirectoryUpdateError(
                f"Failed to rename directory {directory_id} to '{new_name}'"
            )

