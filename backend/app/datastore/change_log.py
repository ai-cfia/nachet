"""
Data access layer for ChangeLog entities.
"""

from typing import Sequence

from sqlalchemy.orm import selectinload

from app.db.model import ChangeLog
from app.datastore.base_crud import BaseCRUDDataService


class ChangeLogDataService(BaseCRUDDataService[ChangeLog]):
    """Data service for ChangeLog entity operations."""

    @classmethod
    def get_model_class(cls) -> type[ChangeLog]:
        """Return the ChangeLog model class."""
        return ChangeLog

    def get_query_options(self) -> list:
        """
        Return query options for eager loading relationships.

        Loads:
        - user: The user who made the change
        """
        return [
            selectinload(ChangeLog.user),
        ]
