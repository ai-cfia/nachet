"""
Annotation service using generic BaseCRUDService.

Provides service layer for Annotation operations with RBAC, logging, and error handling.
"""

from typing import Dict, Any, Type
from uuid import UUID

from app.service.base_crud import AuthorizedBaseCRUDService
from app.db.model import Annotation
from app.exceptions import (
    AnnotationNotFoundError,
    AnnotationCreationError,
    AnnotationUpdateError,
    AnnotationDeletionError,
)


class AnnotationService(AuthorizedBaseCRUDService[Annotation]):
    """
    Service layer for Annotation operations.

    Uses the generic AuthorizedBaseCRUDService for standard CRUD operations with RBAC.

    Access Control:
    - CREATE operations: Any authenticated user within their organization
    - READ operations: Organization users and admins (filtered by organization)
    - UPDATE operations: Organization users and admins with access to the entity
    - DELETE operations: Organization admins only (admin-level permission required)

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
            "org_admin_role_id": str(entity.org_admin_role_id),
            "org_user_role_id": str(entity.org_user_role_id)
            if entity.org_user_role_id
            else None,
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

    @classmethod
    async def verify_create_access(cls, _user_id: UUID, **kwargs) -> None:
        """
        Verify user can create annotations.

        Authorization: Any authenticated user

        Based on the business requirements, annotations can be created by any
        authenticated user within their organization. This allows users to create
        annotation data for ML inference results.

        Args:
            _user_id: UUID of the requesting user
            **kwargs: Additional parameters (not used for annotations)

        Raises:
            HTTPException: 403 if user is not authenticated or not associated with an organization
        """
        from app.service.rbac import RbacService

        # Verify user is authenticated and associated with an organization
        await RbacService.get_user_organization_id(_user_id)
