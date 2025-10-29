"""
User service using generic BaseCRUDService.

Provides service layer for Users operations with RBAC, logging, and error handling.
"""

from beartype.typing import Dict, Any, Type, Protocol, Optional
from uuid import UUID
import traceback

from fastapi import HTTPException, status
from sqlalchemy import select

from app.service.base_crud import BaseCRUDService
from app.db.model import Users
from app.db.utils import sessionmanager
from app.exceptions import (
    UserNotFoundError,
    UserCreationError,
    UserUpdateError,
    UserDeletionError,
)


class UserProtocol(Protocol):
    """Protocol defining the interface for User objects from JWT tokens."""

    oid: Optional[str]
    email: Optional[str]
    preferred_username: Optional[str]


class UserService(BaseCRUDService[Users]):
    """
    Service layer for Users operations.

    Uses the generic BaseCRUDService for standard CRUD operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active users are returned by default
    - Each user must be associated with an organization
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "User"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class."""
        from app.datastore.user import UserDataService

        return UserDataService

    @classmethod
    def serialize_entity(cls, entity: Users) -> Dict[str, Any]:
        """
        Convert Users entity to dictionary for API response.

        This handles all the field serialization for Users.
        """
        return {
            "id": str(entity.id),
            "email": entity.email,
            "organization_id": str(entity.organization),
            "organization_name": entity.organization_ref.name
            if entity.organization_ref
            else None,
            "default_folder_id": str(entity.default_folder_id)
            if entity.default_folder_id
            else None,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
            "date_updated": entity.date_updated.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return User-specific NotFoundError exception class."""
        return UserNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return User-specific CreationError exception class."""
        return UserCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return User-specific UpdateError exception class."""
        return UserUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return User-specific DeletionError exception class."""
        return UserDeletionError

    @classmethod
    async def _create_default_folder(cls, session, user: Users, email: str) -> None:
        """
        Create a default folder for a user.

        This is a private helper method shared by create() and register_user()
        to avoid code duplication.

        Args:
            session: Active database session
            user: User entity (must have organization_ref loaded)
            email: User's email address

        Raises:
            Exception: Logs warning but doesn't raise (folder creation is non-critical)
        """
        try:
            from app.db.model import RbacRole, Folder

            # Extract username from email
            username = email.split("@")[0] if email and "@" in email else "user"

            # Get organization folder prefix
            org_folder_prefix = user.organization_ref.folder_prefix or "default-org"

            # Construct folder prefix: organization/username
            folder_prefix = f"/{org_folder_prefix}/{username}"

            # Get the admin role for this organization
            stmt = select(RbacRole).where(
                RbacRole.organization_id == user.organization,
                RbacRole.name == "admin",
                RbacRole.active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            org_admin_role = result.scalar_one()

            # Get the organization user role for this organization
            stmt = select(RbacRole).where(
                RbacRole.organization_id == user.organization,
                RbacRole.name == "user",
                RbacRole.active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            org_user_role = result.scalar_one()

            # Create the default folder
            default_folder = Folder(
                user_id=user.id,
                org_user_role_id=org_user_role.id,
                org_admin_role_id=org_admin_role.id,
                name=username,
                folder_prefix=folder_prefix,
                description=f"Default folder for {email}",
                active=True,
            )
            session.add(default_folder)
            await session.flush()

            # Link the folder to the user
            user.default_folder_id = default_folder.id

            logger = cls._get_logger()
            logger.info(
                "Created default folder for user",
                user_id=str(user.id),
                folder_id=str(default_folder.id),
                folder_prefix=folder_prefix,
            )
        except Exception as folder_error:
            logger = cls._get_logger()
            logger.warning(
                f"Failed to create default folder for user, continuing without folder: {str(folder_error)}",
                user_id=str(user.id),
            )

    @classmethod
    async def _assign_user_role(
        cls, session, user: Users, role_name: str = "user"
    ) -> None:
        """
        Assign a role to a user in their organization.

        This is a private helper method used by register_user() to automatically
        assign the default "user" role to newly registered users.

        Args:
            session: Active database session
            user: User entity (must have organization set)
            role_name: Name of the role to assign (default: "user")

        Raises:
            Exception: Logs warning but doesn't raise (role assignment is non-critical)
        """
        try:
            from app.db.model import RbacRole, RbacUserRole

            # Find the role for this organization
            stmt = select(RbacRole).where(
                RbacRole.organization_id == user.organization,
                RbacRole.name == role_name,
                RbacRole.active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            role = result.scalar_one_or_none()

            if not role:
                logger = cls._get_logger()
                logger.warning(
                    f"Role '{role_name}' not found for organization",
                    user_id=str(user.id),
                    organization_id=str(user.organization),
                )
                return

            # Check if user already has this role
            stmt = select(RbacUserRole).where(
                RbacUserRole.user_id == user.id,
                RbacUserRole.role_id == role.id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger = cls._get_logger()
                logger.info(
                    f"User already has '{role_name}' role",
                    user_id=str(user.id),
                    role_id=str(role.id),
                )
                return

            # Assign the role
            user_role = RbacUserRole(user_id=user.id, role_id=role.id, active=True)
            session.add(user_role)
            await session.flush()

            logger = cls._get_logger()
            logger.info(
                f"Assigned '{role_name}' role to user",
                user_id=str(user.id),
                role_id=str(role.id),
                organization_id=str(user.organization),
            )

        except Exception as role_error:
            logger = cls._get_logger()
            logger.warning(
                f"Failed to assign '{role_name}' role to user, continuing without role: {str(role_error)}",
                user_id=str(user.id),
            )

    @classmethod
    async def create(cls, requester_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Create a new user (requires CFIA admin).

        This override eagerly loads the organization_ref relationship to prevent
        greenlet errors when serializing the entity outside the session context.

        Automatically creates a default folder for the user using the email username
        (the string before @ symbol) as part of the folder prefix.

        Args:
            requester_id: UUID of the requesting user
            **kwargs: User attributes (email, organization, etc.)

        Returns:
            Dictionary representation of the created user

        Raises:
            HTTPException: 401 if not authenticated, 403 if not admin, 500 on errors
        """
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        creation_exc = cls.get_creation_exception()

        try:
            # RBAC: Only CFIA admin can create
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(requester_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                user = await data_service.create(**kwargs)

                # Eagerly load organization_ref to avoid greenlet errors in serialize_entity
                await session.refresh(user, attribute_names=["organization_ref"])

                # Create default folder for the new user
                email = kwargs.get("email", "")
                await cls._create_default_folder(session, user, email)

                result = cls.serialize_entity(user)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} created successfully",
                    user_id=str(requester_id),
                    entity_id=str(user.id),
                )

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            error_msg = f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.error(
                error_msg,
                user_id=str(requester_id),
            )
            logger.debug(
                f"Traceback for failed create {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.error(
                error_msg,
                user_id=str(requester_id),
            )
            logger.debug(
                f"Traceback for failed create {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )

    @classmethod
    async def check_user_registration(cls, user: UserProtocol) -> bool:
        """
        Check if a user is registered in the system.

        If the user is not registered and not already in pending_registration,
        automatically creates a pending registration entry.

        Args:
            user: User object from JWT token (contains oid and email)

        Returns:
            True if user is registered, False otherwise
        """
        try:
            async with sessionmanager.get_session() as session:
                # Check if user exists in users table
                query = select(Users).where(Users.id == UUID(user.oid))
                result = await session.execute(query)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    return True

                # User not registered - check if already in pending_registration
                # Validate that user.oid is not None before proceeding
                if not user.oid:
                    logger = cls._get_logger()
                    logger.error("User oid is None, cannot check pending registration")
                    return False

                from app.datastore.pending_registration import (
                    PendingRegistrationDataService,
                )

                pending_service = PendingRegistrationDataService(session)
                pending_registration = await pending_service.get_by_azure_oid(user.oid)

                if not pending_registration:
                    # Create pending registration entry to prevent abuse
                    await pending_service.create(
                        azure_ad_oid=user.oid, email=user.preferred_username
                    )
                    await session.commit()

                    logger = cls._get_logger()
                    logger.info(
                        "Created pending registration for user",
                        azure_ad_oid=user.oid,
                        email=user.email,
                    )

                return False

        except Exception as e:
            logger = cls._get_logger()
            error_msg = (
                f"Error checking user registration: {cls._sanitize_error_message(e)}"
            )
            logger.error(
                error_msg,
                azure_ad_oid=user.oid,
            )
            logger.debug(
                "Traceback for check_user_registration error",
                traceback=traceback.format_exc(),
            )
            # Don't expose internal errors, just return False
            return False

    @classmethod
    async def register_user(
        cls, admin_user_id: UUID, azure_ad_oid: str, organization_id: UUID, email: str
    ) -> Dict[str, Any]:
        """
        Register a user by assigning them to an organization (CFIA admin only).

        This method:
        1. Verifies the admin has permission
        2. Creates a full user record with organization
        3. Creates a default folder for the user
        4. Assigns the default "user" role to the user
        5. Deletes the pending registration entry

        Args:
            admin_user_id: UUID of the admin performing the registration
            azure_ad_oid: Azure AD object ID of the user to register
            organization_id: Organization to assign the user to
            email: User's email address

        Returns:
            Dictionary representation of the created user

        Raises:
            HTTPException: 401 if not authenticated, 403 if not admin, 500 on errors
        """
        if not admin_user_id or not azure_ad_oid or not organization_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters for user registration",
            )

        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()

        try:
            # RBAC: Only CFIA admin can register users
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(admin_user_id)

            async with sessionmanager.get_session() as session:
                # Create the user using the existing create method
                # Note: We need to pass id explicitly as azure_ad_oid
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                user = await data_service.create(
                    id=UUID(azure_ad_oid),
                    email=email,
                    organization=organization_id,
                    registered_by=admin_user_id,
                )

                # Eagerly load organization_ref to avoid greenlet errors
                await session.refresh(user, attribute_names=["organization_ref"])

                # Create default folder for the new user
                await cls._create_default_folder(session, user, email)

                # Assign default "user" role to the newly registered user
                await cls._assign_user_role(session, user, role_name="user")

                # Delete from pending_registration table
                from app.datastore.pending_registration import (
                    PendingRegistrationDataService,
                )

                pending_service = PendingRegistrationDataService(session)
                await pending_service.delete(azure_ad_oid)

                result = cls.serialize_entity(user)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} registered successfully",
                    admin_user_id=str(admin_user_id),
                    user_id=str(user.id),
                    organization_id=str(organization_id),
                )

                return result

        except HTTPException:
            raise
        except Exception as e:
            logger = cls._get_logger()
            error_msg = f"Failed to register {entity_name_lower}: {cls._sanitize_error_message(e)}"
            logger.error(
                error_msg,
                admin_user_id=str(admin_user_id),
                azure_ad_oid=azure_ad_oid,
            )
            logger.debug(
                f"Traceback for failed register {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register {entity_name_lower}",
            )
