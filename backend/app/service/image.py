"""
Business logic layer for Picture (Image) entities.
"""

from typing import Any, Dict, Type

from app.db.model import Picture
from app.exceptions import (
    ImageCreationError,
    ImageDeletionError,
    ImageNotFoundError,
    ImageUpdateError,
)
from app.service.base_crud import BaseCRUDService


class ImageService(BaseCRUDService[Picture]):
    """Service for managing Picture (Image) CRUD operations."""

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "Image"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class for Picture operations."""
        # Lazy import to avoid circular dependency
        from app.datastore.image import ImageDataService

        return ImageDataService

    @classmethod
    def serialize_entity(cls, entity: Picture) -> Dict[str, Any]:
        """
        Serialize a Picture entity to a dictionary.

        Args:
            entity: Picture entity to serialize

        Returns:
            Dictionary representation of the picture with all fields
        """
        return {
            "id": str(entity.id),
            "folder_id": str(entity.folder_id),
            "folder_name": entity.folder.name if entity.folder else None,
            "user_id": str(entity.user_id),
            "org_admin_id": str(entity.org_admin_id),
            "org_user_role_id": str(entity.org_user_role_id) if entity.org_user_role_id else None,
            "active": entity.active,
            "date_created": entity.date_created.isoformat() if entity.date_created else None,
            "width": entity.width,
            "height": entity.height,
            "sha256": entity.sha256,
            "name": entity.name,
            "blob_url_original": entity.blob_url_original,
            "format": entity.format,
            "size_on_disk_original": entity.size_on_disk_original,
            "size_on_disk_sanitized": entity.size_on_disk_sanitized,
            "magnification": entity.magnification,
            "blob_url_sanitized": entity.blob_url_sanitized,
            "device_model_id": str(entity.device_model_id) if entity.device_model_id else None,
            "device_lens_id": str(entity.device_lens_id) if entity.device_lens_id else None,
            "single_species_image": str(entity.single_species_image) if entity.single_species_image else None,
            "description": entity.description,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return the exception to raise when an image is not found."""
        return ImageNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image creation fails."""
        return ImageCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image update fails."""
        return ImageUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return the exception to raise when image deletion fails."""
        return ImageDeletionError
