"""
Business logic layer for Object (ImageObjects) entities.
"""

from typing import Any, Dict, Type

from app.db.model import Object
from app.exceptions import (
    ImageObjectsCreationError,
    ImageObjectsDeletionError,
    ImageObjectsNotFoundError,
    ImageObjectsUpdateError,
)
from app.service.base_crud import BaseCRUDService


class ImageObjectsService(BaseCRUDService[Object]):
    """Service for managing Object (ImageObjects) CRUD operations."""

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "ImageObject"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class for Object operations."""
        # Lazy import to avoid circular dependency
        from app.datastore.image_objects import ImageObjectsDataService

        return ImageObjectsDataService

    @classmethod
    def serialize_entity(cls, entity: Object) -> Dict[str, Any]:
        """
        Serialize an Object entity to a dictionary.

        Args:
            entity: Object entity to serialize

        Returns:
            Dictionary representation of the object with all fields
        """
        return {
            "id": str(entity.id),
            "user_id": str(entity.user_id),
            "user_email": entity.user.email if entity.user else None,
            "org_admin_id": str(entity.org_admin_id),
            "inference_id": str(entity.inference_id),
            "picture_id": str(entity.picture_id),
            "pipeline_id": str(entity.pipeline_id),
            "pipeline_name": entity.pipeline.name if entity.pipeline else None,
            "valid": entity.valid,
            # Bounding box coordinates
            "box": {
                "top_x": entity.top_x_abs,
                "top_y": entity.top_y_abs,
                "bottom_x": entity.bot_x_abs,
                "bottom_y": entity.bot_y_abs,
            },
            # Top predictions
            "top_id": str(entity.top_id),
            "top_seed_name": entity.seed_top_1.name if entity.seed_top_1 else None,
            "top_score": entity.top_score,
            "top_id_2": str(entity.top_id_2) if entity.top_id_2 else None,
            "top_seed_name_2": entity.seed_top_2.name if entity.seed_top_2 else None,
            "top_score_2": entity.top_score_2,
            "top_id_3": str(entity.top_id_3) if entity.top_id_3 else None,
            "top_seed_name_3": entity.seed_top_3.name if entity.seed_top_3 else None,
            "top_score_3": entity.top_score_3,
            # Dates
            "date_created": entity.date_created.isoformat() if entity.date_created else None,
            "date_verified": entity.date_verified.isoformat() if entity.date_verified else None,
            "date_feedback": entity.date_feedback.isoformat() if entity.date_feedback else None,
            # Update flags
            "box_update": entity.box_update,
            "species_update": entity.species_update,
            # Feedback and verification
            "feedback_user_id": str(entity.feedback_user_id) if entity.feedback_user_id else None,
            "feedback_user_email": entity.feedback_user.email if entity.feedback_user else None,
            "verifier_user_id": str(entity.verifier_user_id) if entity.verifier_user_id else None,
            "verifier_user_email": entity.verifier_user.email if entity.verifier_user else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return the exception to raise when an image object is not found."""
        return ImageObjectsNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image object creation fails."""
        return ImageObjectsCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image object update fails."""
        return ImageObjectsUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image object deletion fails."""
        return ImageObjectsDeletionError
