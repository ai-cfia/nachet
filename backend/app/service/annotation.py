"""
Annotation service using generic BaseCRUDService.

Provides service layer for Annotation operations with RBAC, logging, and error handling.
"""

from typing import Dict, Any, Type

from app.service.base_crud import BaseCRUDService
from app.db.model import Annotation
from app.exceptions import (
    AnnotationNotFoundError,
    AnnotationCreationError,
    AnnotationUpdateError,
    AnnotationDeletionError,
)


class AnnotationService(BaseCRUDService[Annotation]):
    """
    Service layer for Annotation operations.

    Uses the generic BaseCRUDService for standard CRUD operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Each annotation must be associated with a user, picture, and organization
    - Annotations contain raw ML inference data in JSON format
    - Pipeline reference indicates which ML pipeline was used (or "human" for manual)
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "Annotation"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class."""
        from app.datastore.annotation import AnnotationDataService

        return AnnotationDataService

    @classmethod
    def serialize_entity(cls, entity: Annotation) -> Dict[str, Any]:
        """
        Convert Annotation entity to dictionary for API response.

        This handles all the field serialization for Annotation.
        """
        return {
            "id": str(entity.id),
            "user_id": str(entity.user_id),
            "user_email": entity.user.email if entity.user else None,
            "org_admin_id": str(entity.org_admin_id),
            "org_user_role_id": str(entity.org_user_role_id) if entity.org_user_role_id else None,
            "picture_id": str(entity.picture_id),
            "pipeline_id": str(entity.pipeline_id) if entity.pipeline_id else None,
            "pipeline_name": entity.pipeline.name if entity.pipeline else None,
            "date_created": entity.date_created.isoformat(),
            "raw_data": entity.raw_data,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return Annotation-specific NotFoundError exception class."""
        return AnnotationNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return Annotation-specific CreationError exception class."""
        return AnnotationCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return Annotation-specific UpdateError exception class."""
        return AnnotationUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return Annotation-specific DeletionError exception class."""
        return AnnotationDeletionError
