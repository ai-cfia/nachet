from beartype.typing import Dict, Any, Type, cast
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
      EXCEPTION: Cannot update a user's default folder if the user is still active
    - DELETE operations:
      Folder creator (user_id matches) OR org_admin_role_id OR CFIA admin
      EXCEPTION: Cannot delete a user's default folder if the user is still active
      EXCEPTION: Cannot delete a folder containing active pictures
    - CREATE operations: Any user belonging to an organization (see verify_create_access)

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active directories are returned by default
    - Default folders cannot be deleted while the associated user is active
    - Default folders cannot be updated while the associated user is active
    - Folders containing active pictures cannot be deleted
    - Users can delete folders they created (unless constraints prevent it)
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
    async def verify_create_access(cls, requester_id: UUID, **_kwargs) -> None:
        """
        Verify user can create directories.

        Authorization: Any user belonging to an organization

        Users can create directories within their organization. This allows
        all organization members to create folders for their work.

        Args:
            requester_id: UUID of the requesting user

        Raises:
            HTTPException: 403 if user does not belong to an organization
        """
        # Verify user has organization membership by getting their org roles
        # This will raise an exception if the user doesn't have proper org access
        await RbacService.get_user_org_roles(requester_id)

    @classmethod
    async def verify_delete_access(cls, requester_id: UUID, entity: Folder) -> None:
        """
        Verify user can delete the folder.

        Authorization Rules:
        1. User created the folder (user_id matches), OR
        2. User is org admin for the folder's organization, OR
        3. User is CFIA admin
        4. CANNOT delete a user's default folder if that user is still active
        5. CANNOT delete a folder containing active pictures

        This allows users to delete their own folders while preventing deletion
        of default folders which would break user workflows and preventing accidental
        deletion of folders containing active pictures.

        Args:
            requester_id: UUID of the requesting user
            entity: The Folder entity to delete

        Raises:
            HTTPException: 403 if access denied, folder is a default folder for active user,
                          or folder contains active pictures
        """
        from app.db.utils import sessionmanager
        from app.db.model import Users
        from sqlalchemy import select
        from fastapi import status

        # Check if user created this folder
        is_creator = entity.user_id == requester_id

        # If not the creator, check admin access (org admin or CFIA admin)
        if not is_creator:
            try:
                await super().verify_delete_access(requester_id, entity)
            except HTTPException:
                # User is neither creator nor admin
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to delete folder - must be folder creator, organization admin, or CFIA admin",
                )

        # Additional check: Prevent deletion of default folders for active users
        async with sessionmanager.get_session() as session:
            # Check if this folder is set as default_folder_id for any active user
            stmt = (
                select(Users)
                .where(Users.default_folder_id == entity.id)
                .where(Users.active.is_(True))
            )
            result = await session.execute(stmt)
            user_with_default_folder = result.scalar_one_or_none()

            if user_with_default_folder:
                logger.warning(
                    f"Attempted to delete default folder {entity.id} for active user {user_with_default_folder.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete folder: it is the default folder for an active user. "
                    "Deactivate the user first or change their default folder.",
                )

        # Additional check: Prevent deletion if folder contains active pictures
        has_active_pictures = await cls._has_active_pictures(cast(UUID, entity.id))
        if has_active_pictures:
            logger.warning(
                f"Attempted to delete folder {entity.id} containing active pictures"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete folder: it contains active picture(s). "
                "Please delete or move all pictures before deleting the folder.",
            )

    @staticmethod
    async def _has_active_pictures(folder_id: UUID) -> bool:
        """
        Check if a folder contains any active pictures.

        This method performs an efficient existence check to determine if at least
        one active picture exists in the folder without counting all pictures.

        Args:
            folder_id: UUID of the folder to check

        Returns:
            True if the folder contains at least one active picture, False otherwise
        """
        from app.db.utils import sessionmanager
        from app.db.model import Picture
        from sqlalchemy import select

        async with sessionmanager.get_session() as session:
            stmt = (
                select(Picture.id)
                .where(Picture.folder_id == folder_id)
                .where(Picture.active.is_(True))
                .limit(1)
            )
            result = await session.execute(stmt)
            first_picture = result.scalar_one_or_none()
            return first_picture is not None

    @classmethod
    async def verify_update_access(cls, requester_id: UUID, entity: Folder) -> None:
        """
        Verify user can update the folder.

        Authorization Rules:
        1. User must have org_user_role_id OR org_admin_role_id OR be CFIA admin (base class check)
        2. CANNOT update a user's default folder if that user is still active

        This prevents accidental modifications to default folders which could break
        user workflows. Default folders can only be updated after the user is
        deactivated.

        Args:
            requester_id: UUID of the requesting user
            entity: The Folder entity to update

        Raises:
            HTTPException: 403 if access denied or folder is a default folder for active user
        """
        from app.db.utils import sessionmanager
        from app.db.model import Users
        from sqlalchemy import select
        from fastapi import status

        # First, perform standard authorization check
        await super().verify_update_access(requester_id, entity)

        # Additional check: Prevent updates to default folders for active users
        async with sessionmanager.get_session() as session:
            # Check if this folder is set as default_folder_id for any active user
            stmt = (
                select(Users)
                .where(Users.default_folder_id == entity.id)
                .where(Users.active.is_(True))
            )
            result = await session.execute(stmt)
            user_with_default_folder = result.scalar_one_or_none()

            if user_with_default_folder:
                logger.warning(
                    f"Attempted to update default folder {entity.id} for active user {user_with_default_folder.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update folder: it is the default folder for an active user. "
                    "Deactivate the user first or change their default folder.",
                )

    @classmethod
    async def create(cls, requester_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Override create to handle folder-specific parameters.

        The base create() method expects the requesting user's UUID as the first
        positional argument and forwards ``**kwargs`` directly to the data
        service. Folder creation sometimes needs to pass a different
        ``folder_user_id`` to indicate ownership of the folder while still using
        the authenticated ``requester_id`` for RBAC.

        This override keeps backward compatibility with existing call sites that
        pass ``user_id=`` while also supporting an optional ``folder_user_id``
        keyword which will be mapped to the model's ``user_id`` column.

        Args:
            requester_id: UUID of the requesting user (for RBAC checks)
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
            kwargs["user_id"] = requester_id

        # Call parent create method with the authenticated user context.
        return await super().create(requester_id, **kwargs)

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

            # Convert UUID id to string for API response
            serialized_directories = [{**d, "id": str(d["id"])} for d in directories]

            logger.info(f"Retrieved {len(directories)} directories for user {user_id}")

            return {
                "directories": serialized_directories if serialized_directories else []
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
            if user_org_id is None:
                raise DirectoryNotFoundError(
                    f"User {user_id} is not associated with an organization"
                )

            # Get the organization's user role ID
            org_user_role_id = await RbacService.get_org_user_role_id(user_org_id)

            # Call data service static method (manages its own session)
            directories = await DirectoryDataService.get_org_directories_with_count(
                str(org_user_role_id)
            )

            # Convert UUID fields to strings for API response
            serialized_directories = [
                {**d, "id": str(d["id"]), "user_id": str(d["user_id"])}
                for d in directories
            ]

            logger.info(
                f"Retrieved {len(directories)} directories for organization (org_id: {user_org_id})"
            )

            return {
                "directories": serialized_directories if serialized_directories else []
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

        The organization prefix is automatically prepended to the provided path.

        Path Validation Rules:
        - Must not start with / (provide relative path)
        - Can only contain alphanumeric, slash, underscore, dash, and period
        - Must end with alphanumeric character (not _, -, or .)
        - Cannot have consecutive slashes
        - Folder name (characters after last slash) cannot contain slashes

        Args:
            user_id: UUID of the user creating the directory
            fullpath: Relative path for the directory (e.g., "org/team/project")
            description: Optional description of the directory

        Returns:
            Dictionary representation of the created directory

        Raises:
            HTTPException: If user is not authorized, path is invalid, or creation fails
        """
        # Get user's organization and role information
        user_org_roles = await RbacService.get_user_org_roles(user_id)

        # Validate and parse fullpath
        folder_name, folder_prefix = cls._validate_and_parse_fullpath(
            f"/{user_org_roles.org_prefix}/{fullpath}"
        )

        # Use the standard create() method which handles authorization
        # Note: user_id parameter is for RBAC, must also pass it as folder field
        folder_fields = {
            "org_admin_role_id": user_org_roles.org_admin_role_id,
            "org_user_role_id": user_org_roles.org_user_role_id,
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
    async def get_or_create_folder(
        cls,
        user_id: UUID,
        normalized_path: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Get or create a folder using the get-or-create pattern (idempotent).

        This method checks if a folder exists at the given path. If it exists,
        returns the existing folder_id. If not, creates a new folder and returns
        the new folder_id.

        The organization prefix is automatically prepended to the normalized_path.

        Authorization: Any user belonging to an organization

        Args:
            user_id: UUID of the user creating/retrieving the folder
            normalized_path: Relative path (e.g., "avena-fatua" or "mycology/avena-fatua")
            description: Optional description for the folder (defaults to empty string)

        Returns:
            Dictionary with folder_id

        Raises:
            HTTPException: If user is not authorized, path is invalid, or operation fails

        Example:
            normalized_path="avena-fatua" -> fullpath="/cfia/avena-fatua"
            folder_name="avena-fatua", folder_prefix="/cfia/"
        """
        from app.db.utils import sessionmanager

        # Get user's organization and role information
        user_org_roles = await RbacService.get_user_org_roles(user_id)

        # Validate and parse fullpath (prepend org prefix)
        fullpath = f"/{user_org_roles.org_prefix}/{normalized_path}"
        folder_name, folder_prefix = cls._validate_and_parse_fullpath(fullpath)

        # Check if folder exists
        async with sessionmanager.get_session() as session:
            data_service = DirectoryDataService(session)
            existing_folder_id = await data_service.find_folder_by_path(
                str(user_org_roles.org_user_role_id),
                folder_name,
                folder_prefix,
            )

            if existing_folder_id:
                logger.info(
                    f"Folder already exists: '{folder_name}' at '{folder_prefix}' (ID: {existing_folder_id})"
                )
                return {"folder_id": str(existing_folder_id)}

        # Folder doesn't exist, create it
        logger.info(
            f"Folder not found, creating: '{folder_name}' at '{folder_prefix}' for user {user_id}"
        )

        # Use create_directory which handles authorization
        result = await cls.create_directory(
            user_id=user_id,
            fullpath=normalized_path,
            description=description,
        )

        return {"folder_id": result["id"]}

    @classmethod
    async def update_folder(
        cls,
        user_id: UUID,
        folder_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> Dict[str, Any]:
        """
        Update a folder's name and/or description.

        Authorization: Same as AuthorizedBaseCRUDService.update() - users with folder's
        org_user_role_id OR org_admin_role_id OR CFIA admin

        Validation:
        - Cannot update default folders (blocked in verify_update_access)
        - If name is provided, validates it doesn't conflict with existing folders
        - Name must follow path validation rules

        Args:
            user_id: UUID of the user performing the update
            folder_id: UUID of the folder to update
            name: Optional new folder name (just the name, not the full path)
            description: Optional new description

        Returns:
            Dictionary with updated folder id and success message

        Raises:
            HTTPException: If folder is default folder, name conflicts, or validation fails
            DirectoryNotFoundError: If folder doesn't exist
            DirectoryUpdateError: If update operation fails
        """
        from app.db.utils import sessionmanager

        if name is None and description is None:
            raise HTTPException(
                status_code=400,
                detail="At least one field (name or description) must be provided for update",
            )

        # Get user's organization and role information
        user_org_roles = await RbacService.get_user_org_roles(user_id)

        # Fetch the folder entity to verify it exists and check permissions
        folder_entity = await cls.get_by_id(user_id, folder_id)

        # Build update parameters
        update_params = {}

        # If name is being updated, validate it
        if name is not None:
            # Validate the new name follows path rules
            # We'll use the existing folder's prefix with the new name
            new_fullpath = f"{folder_entity['folder_prefix']}{name}"
            new_name, new_prefix = cls._validate_and_parse_fullpath(new_fullpath)

            # Check if a folder with this name already exists at the same prefix
            async with sessionmanager.get_session() as session:
                data_service = DirectoryDataService(session)
                existing_folder_id = await data_service.find_folder_by_path(
                    str(user_org_roles.org_user_role_id),
                    new_name,
                    new_prefix,
                )

                if existing_folder_id and str(existing_folder_id) != str(folder_id):
                    logger.warning(
                        f"Attempted to rename folder {folder_id} to '{new_name}' but name already exists (ID: {existing_folder_id})"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"A folder with the name '{new_name}' already exists at this location. "
                        "Please choose a different name.",
                    )

            update_params["name"] = new_name

        # Add description to update if provided
        if description is not None:
            update_params["description"] = description

        # Perform the update using base class method (includes authorization check)
        await cls.update(user_id, folder_id, **update_params)

        logger.info(f"Folder {folder_id} updated successfully by user {user_id}")
        return {
            "id": str(folder_id),
            "message": "Folder updated successfully",
        }

    @staticmethod
    async def check_folder_exists(
        folder_id: UUID,
        user_role_id: UUID,
    ) -> str:
        """
        Check if a folder exists and belongs to the given user role.

        This verifies that:
        1. The folder exists
        2. The folder is active
        3. The folder belongs to the specified organization (via user_role_id)

        Manages its own database session internally.

        Args:
            folder_id: UUID of the folder to check
            user_role_id: UUID of the organization's user role

        Returns:
            The folder_prefix if folder exists

        Raises:
            FolderNotFoundError: If folder doesn't exist or doesn't belong to the user role
        """
        from app.db.utils import sessionmanager

        try:
            async with sessionmanager.get_session() as session:
                data_service = DirectoryDataService(session)
                folder_prefix = await data_service.check_folder_exists(
                    str(folder_id), str(user_role_id)
                )

                if not folder_prefix:
                    logger.warning(
                        f"Folder check failed: folder_id={folder_id}, user_role_id={user_role_id}"
                    )
                    raise DirectoryNotFoundError(
                        f"Folder {folder_id} not found or access denied"
                    )

                logger.debug(
                    f"Folder exists: folder_id={folder_id}, user_role_id={user_role_id}, prefix={folder_prefix}"
                )

                return folder_prefix

        except DirectoryNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to check folder existence: {str(e)}",
                folder_id=str(folder_id),
                user_role_id=str(user_role_id),
                error_type=type(e).__name__,
            )
            raise DirectoryNotFoundError(
                f"Failed to verify folder {folder_id}: {str(e)}"
            )

    @classmethod
    async def rename_directory(
        cls, user_id: UUID, directory_id: UUID, fullpath: str
    ) -> Dict[str, Any]:
        """
        Rename an existing directory by providing a new fullpath.

        This is a convenience method that validates the fullpath and calls the
        standard update() CRUD operation with role-based authorization.

        The organization prefix is automatically prepended to the provided path.

        Path Validation Rules:
        - Must not start with / (provide relative path)
        - Can only contain alphanumeric, slash, underscore, dash, and period
        - Must end with alphanumeric character (not _, -, or .)
        - Cannot have consecutive slashes

        Authorization: Same as update() - users with org_user_role_id OR org_admin_role_id OR CFIA admin

        Args:
            user_id: UUID of the user performing the rename
            directory_id: UUID of the directory to rename
            fullpath: New relative path for the directory (e.g., "org/team/new_name")

        Returns:
            Dictionary with the directory ID and success message

        Raises:
            HTTPException: If user is not authorized, path is invalid, or rename fails
        """
        # Get user's organization and role information
        user_org_roles = await RbacService.get_user_org_roles(user_id)

        # Validate and parse fullpath
        folder_name, folder_prefix = cls._validate_and_parse_fullpath(
            f"/{user_org_roles.org_prefix}/{fullpath}"
        )

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
