"""
User service using generic BaseCRUDService.

Provides service layer for Users operations with RBAC, logging, and error handling.
"""

from typing import Dict, Any, Type
from uuid import UUID
import traceback

from fastapi import HTTPException, status

from app.service.base_crud import BaseCRUDService
from app.db.model import Users
from app.db.utils import sessionmanager
from app.exceptions import (
    UserNotFoundError,
    UserCreationError,
    UserUpdateError,
    UserDeletionError,
)


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
    async def create(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Create a new user (requires CFIA admin).

        This override eagerly loads the organization_ref relationship to prevent
        greenlet errors when serializing the entity outside the session context.

        Args:
            user_id: UUID of the requesting user
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

            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                user = await data_service.create(**kwargs)

                # Eagerly load organization_ref to avoid greenlet errors in serialize_entity
                await session.refresh(user, attribute_names=["organization_ref"])

                result = cls.serialize_entity(user)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} created successfully",
                    user_id=str(user_id),
                    entity_id=str(user.id),
                )

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}",
                user_id=str(user_id),
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
            logger.error(
                f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}",
                user_id=str(user_id),
            )
            logger.debug(
                f"Traceback for failed create {entity_name_lower}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
