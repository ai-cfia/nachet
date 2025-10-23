"""
User data service using generic BaseCRUDDataService.

Provides data access layer for Users operations with minimal code duplication.
"""

from typing import Type
from sqlalchemy.orm import selectinload

from app.db.model import Users
from app.datastore.base_crud import BaseCRUDDataService


class UserDataService(BaseCRUDDataService[Users]):
    """Data access layer for Users database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Users]:
        """Return the Users ORM class."""
        return Users

    def get_query_options(self) -> list:
        """
        Load the organization relationship for all queries.

        Returns:
            List of SQLAlchemy query options for loading the organization_ref relationship
        """
        return [selectinload(Users.organization_ref)]
