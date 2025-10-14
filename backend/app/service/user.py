"""
User service using generic BaseCRUDService.

Provides service layer for Users operations with RBAC, logging, and error handling.
"""

from typing import Dict, Any, Type

from app.service.base_crud import BaseCRUDService
from app.db.model import Users
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
