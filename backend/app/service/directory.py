from typing import Dict, Any, Type
from uuid import UUID
from loguru import logger

from app.db.model import Folder
from app.datastore import DirectoryDataService
from app.service.base_crud import AuthorizedBaseCRUDService
from app.service.rbac import RbacService
from app.exceptions import (
    DirectoryNotFoundError,
    DirectoryCreationError,
    DirectoryUpdateError,
    DirectoryDeletionError,
)
from fastapi import HTTPException


class DirectoryService(AuthorizedBaseCRUDService[Folder]):
    """
    Service layer for Directory (Folder) operations.

    Access Control (AuthorizedBaseCRUDService):
    - GET operations (get_all, get_by_id):
      Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
    - UPDATE operations:
      Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
    - DELETE operations:
      Users with folder's org_admin_role_id OR CFIA admin (admin-only)
    - CREATE operations: CFIA admin only (see verify_create_access)

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
            "org_admin_role_id": str(entity.org_admin_role_id),
            "org_user_role_id": str(entity.org_user_role_id)
            if entity.org_user_role_id
            else None,
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

    @classmethod
    async def verify_create_access(cls, _user_id: UUID, **kwargs) -> None:
        """
        Verify user can create directories.

        Authorization: CFIA admin only

        This ensures only CFIA admins can create directories, maintaining
        the current authorization model while enabling role-based access
        for other operations.

        Args:
            user_id: UUID of the requesting user
            **kwargs: Directory creation parameters

        Raises:
            HTTPException: 403 if user is not CFIA admin
        """
        await RbacService.verify_user_is_cfia_admin(_user_id)

    @classmethod
    async def create(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Override create to handle folder-specific parameters.

        The base create() method expects the requesting user's UUID as the first
        positional argument and forwards ``**kwargs`` directly to the data
        service. Folder creation sometimes needs to pass a different
        ``folder_user_id`` to indicate ownership of the folder while still using
        the authenticated ``user_id`` for RBAC.

        This override keeps backward compatibility with existing call sites that
        pass ``user_id=`` while also supporting an optional ``folder_user_id``
        keyword which will be mapped to the model's ``user_id`` column.

        Args:
            user_id: UUID of the requesting user (for RBAC checks)
            **kwargs: Folder fields, optionally including ``folder_user_id``

        Returns:
            Dictionary representation of the created folder
        """

        folder_user_id = kwargs.pop("folder_user_id", None)

        # If the caller provided a dedicated folder_user_id, prefer it. Otherwise
        # default to the requesting user when no user_id was supplied in kwargs.
        if folder_user_id is not None:
            kwargs.setdefault("user_id", folder_user_id)
        elif "user_id" not in kwargs:
            kwargs["user_id"] = user_id

        # Call parent create method with the authenticated user context.
        return await super().create(user_id, **kwargs)

    # Custom methods for directory-specific operations

    @staticmethod
    def _validate_and_parse_fullpath(fullpath: str) -> tuple[str, str]:
        """
        Validate fullpath format and extract folder name and prefix.

        Path Validation Rules:
        - Must start with /
        - Can only contain alphanumeric, slash, underscore, dash, and period
        - Must end with alphanumeric character (not _, -, or .)
        - Cannot have consecutive slashes

        Args:
            fullpath: Full path for the directory (e.g., /org/team/project)

        Returns:
            Tuple of (folder_name, folder_prefix)
            - folder_name: The directory name (after last slash)
            - folder_prefix: The path before the name (always starts and ends with /)

        Raises:
            HTTPException: 400 if path validation fails

        Examples:
            "/org/team/project" -> ("project", "/org/team/")
            "/project" -> ("project", "/")
            "/org/my_file-v2" -> ("my_file-v2", "/org/")
        """
        import re
        from fastapi import status

        # Validate fullpath format
        if not fullpath:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fullpath cannot be empty",
            )

        if not fullpath.startswith("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fullpath must start with /",
            )

        # Cannot have consecutive slashes (check this first)
        if "//" in fullpath:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fullpath cannot contain consecutive slashes",
            )

        # Check for valid characters: alphanumeric, /, _, -, .
        # AND must end with alphanumeric character
        if not re.match(r"^[a-zA-Z0-9/_.\-]+[a-zA-Z0-9]$", fullpath):
            # Determine which rule was violated for better error message
            if not re.match(r"^[a-zA-Z0-9/_.\-]+$", fullpath):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fullpath can only contain alphanumeric characters, slash, underscore, dash, and period",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fullpath must end with an alphanumeric character",
                )

        # Extract folder name (after last slash) and folder_prefix (path before last slash)
        last_slash_index = fullpath.rfind("/")
        folder_name = fullpath[last_slash_index + 1 :]

        # For fullpath like "/project", folder_prefix should be "/"
        # For fullpath like "/org/team/project", folder_prefix should be "/org/team/"
        if last_slash_index == 0:
            # Root-level folder like "/project"
            folder_prefix = "/"
        else:
            # Nested folder like "/org/team/project"
            folder_prefix = fullpath[: last_slash_index + 1]  # Include trailing slash

        if not folder_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fullpath must contain a folder name after the last slash",
            )

        # Folder name cannot contain slashes (already guaranteed by extraction logic)
        if "/" in folder_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="folder name cannot contain slashes",
            )

        return folder_name, folder_prefix

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

            # Call data service static method (manages its own session)
            directories = await DirectoryDataService.get_user_directories_with_count(
                str(user_id)
            )

            logger.info(f"Retrieved {len(directories)} directories for user {user_id}")

            return {
                "directories": [directory._asdict() for directory in directories]
                if directories
                else []
            }
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Failed to retrieve directories for user {user_id}: {DirectoryService._sanitize_error_message(e)}"
            logger.error(error_msg)
            raise DirectoryNotFoundError(
                f"Failed to retrieve directories for user {user_id}"
            )

    @staticmethod
    async def get_org_directories(user_id: UUID) -> Dict[str, Any]:
        """
        Get all directories for a user's organization with picture counts.

        This retrieves all directories that belong to the same organization as the user,
        filtered by the organization's user role ID.

        Args:
            user_id: UUID of the user (used to determine organization)

        Returns:
            Dictionary containing list of organization directories with picture counts

        Raises:
            HTTPException: If user is not authorized or operation fails
        """
        try:
            # Verify user authentication and get their organization
            user_org_id = await RbacService.get_user_organization_id(user_id)

            # Get the organization's user role ID
            org_user_role_id = await RbacService.get_org_user_role_id(user_org_id)

            # Call data service static method (manages its own session)
            directories = await DirectoryDataService.get_org_directories_with_count(
                str(org_user_role_id)
            )

            logger.info(
                f"Retrieved {len(directories)} directories for organization (org_id: {user_org_id})"
            )

            return {
                "directories": [directory._asdict() for directory in directories]
                if directories
                else []
            }
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Failed to retrieve org directories for user {user_id}: {DirectoryService._sanitize_error_message(e)}"
            logger.error(error_msg)
            raise DirectoryNotFoundError(
                f"Failed to retrieve organization directories for user {user_id}"
            )

    @classmethod
    async def create_directory(
        cls,
        user_id: UUID,
        fullpath: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new directory for a user.

        This is a convenience method that validates the fullpath and calls the
        standard create() CRUD operation with role-based authorization.

        Path Validation Rules:
        - Must start with /
        - Can only contain alphanumeric, slash, underscore, dash, and period
        - Must end with alphanumeric character (not _, -, or .)
        - Cannot have consecutive slashes
        - Folder name (characters after last slash) cannot contain slashes

        Args:
            user_id: UUID of the user creating the directory
            fullpath: Full path for the directory (e.g., /org/team/project)
            description: Optional description of the directory

        Returns:
            Dictionary representation of the created directory

        Raises:
            HTTPException: If user is not authorized, path is invalid, or creation fails
        """
        # Validate and parse fullpath
        folder_name, folder_prefix = cls._validate_and_parse_fullpath(fullpath)

        # Fetch required parameters: org_admin_role_id and org_user_role_id
        user_org_id = await RbacService.get_user_organization_id(user_id)

        # Get the admin role for the user's organization
        org_admin_role_id = await RbacService.get_org_admin_role_id(user_org_id)
        org_user_role_id = await RbacService.get_org_user_role_id(user_org_id)

        # Use the standard create() method which handles authorization
        # Note: user_id parameter is for RBAC, must also pass it as folder field
        folder_fields = {
            "org_admin_role_id": org_admin_role_id,
            "org_user_role_id": org_user_role_id,
            "name": folder_name,
            "folder_prefix": folder_prefix,
            "description": description,
            "active": True,
        }
        result = await cls.create(
            user_id,
            folder_user_id=user_id,
            **folder_fields,
        )

        logger.info(
            f"Created directory '{folder_name}' at '{folder_prefix}' (ID: {result['id']}) for user {user_id}"
        )

        return {
            "id": result["id"],
            "message": f"Directory '{folder_name}' created successfully at {fullpath}",
        }

    @classmethod
    async def rename_directory(
        cls, user_id: UUID, directory_id: UUID, fullpath: str
    ) -> Dict[str, Any]:
        """
        Rename an existing directory by providing a new fullpath.

        This is a convenience method that validates the fullpath and calls the
        standard update() CRUD operation with role-based authorization.

        Path Validation Rules:
        - Must start with /
        - Can only contain alphanumeric, slash, underscore, dash, and period
        - Must end with alphanumeric character (not _, -, or .)
        - Cannot have consecutive slashes

        Authorization: Same as update() - users with org_user_role_id OR org_admin_role_id OR CFIA admin

        Args:
            user_id: UUID of the user performing the rename
            directory_id: UUID of the directory to rename
            fullpath: New full path for the directory (e.g., /org/team/new_name)

        Returns:
            Dictionary with the directory ID and success message

        Raises:
            HTTPException: If user is not authorized, path is invalid, or rename fails
        """
        # Validate and parse the new fullpath
        folder_name, folder_prefix = cls._validate_and_parse_fullpath(fullpath)

        # Use the standard update() method which handles authorization
        result = await cls.update(
            user_id, directory_id, name=folder_name, folder_prefix=folder_prefix
        )

        logger.info(
            f"Renamed directory {directory_id} to '{folder_name}' at '{folder_prefix}' by user {user_id}"
        )

        return {
            "id": result["id"],
            "message": f"Directory renamed to '{folder_name}' successfully at {fullpath}",
        }
