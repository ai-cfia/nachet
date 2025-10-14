"""
Business logic layer for ChangeLog entities.
"""

from typing import Any, Dict, Type

from app.db.model import ChangeLog
from app.exceptions import (
    ChangeLogCreationError,
    ChangeLogDeletionError,
    ChangeLogNotFoundError,
    ChangeLogUpdateError,
)
from app.service.base_crud import BaseCRUDService


class ChangeLogService(BaseCRUDService[ChangeLog]):
    """Service for managing ChangeLog CRUD operations."""

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "ChangeLog"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class for ChangeLog operations."""
        # Lazy import to avoid circular dependency
        from app.datastore.change_log import ChangeLogDataService

        return ChangeLogDataService

    @classmethod
    def serialize_entity(cls, entity: ChangeLog) -> Dict[str, Any]:
        """
        Serialize a ChangeLog entity to a dictionary.

        Args:
            entity: ChangeLog entity to serialize

        Returns:
            Dictionary representation of the change log with all fields
        """
        return {
            "id": str(entity.id),
            "date_created": entity.date_created.isoformat() if entity.date_created else None,
            "user_id": str(entity.user_id),
            "user_email": entity.user.email if entity.user else None,
            "table": entity.table,
            "entry_id": str(entity.entry_id) if entity.entry_id else None,
            "action_id": str(entity.action_id) if entity.action_id else None,
            "value_prev": entity.value_prev,
            "value_new": entity.value_new,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return the exception to raise when a change log is not found."""
        return ChangeLogNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return the exception to raise when change log creation fails."""
        return ChangeLogCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return the exception to raise when change log update fails."""
        return ChangeLogUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return the exception to raise when change log deletion fails."""
        return ChangeLogDeletionError
