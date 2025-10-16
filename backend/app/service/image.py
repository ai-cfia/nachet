"""
Business logic layer for Picture (Image) entities.
"""

from typing import Any, Dict, Type
from uuid import UUID

from app.db.model import Picture
from app.exceptions import (
    ImageCreationError,
    ImageDeletionError,
    ImageNotFoundError,
    ImageUpdateError,
)
from app.service.base_crud import AuthorizedBaseCRUDService


class ImageService(AuthorizedBaseCRUDService[Picture]):
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
        Convert Picture entity to dictionary for API response.

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
            "org_admin_role_id": str(entity.org_admin_role_id),
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

    @classmethod
    async def verify_create_access(cls, _user_id: UUID, **kwargs) -> None:
        """
        Verify user can create images.

        Authorization: Any authenticated user

        Based on the business requirements, pictures can be created by any
        authenticated user within their organization. This provides basic
        authentication while allowing users to upload images.

        Args:
            _user_id: UUID of the requesting user
            **kwargs: Image creation parameters

        Raises:
            HTTPException: 403 if user is not authenticated or not associated with an organization
        """
        from app.service.rbac import RbacService
        # Verify user is authenticated and associated with an organization
        await RbacService.get_user_organization_id(_user_id)

    @classmethod
    async def create(cls, _user_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Override create to ensure user_id is included and relationships are loaded.

        This method implements the full create logic with proper relationship loading
        to avoid the greenlet error when accessing entity.folder.name in serialization.

        Args:
            _user_id: UUID of the requesting user
            **kwargs: Picture attributes including folder_id, org_user_role_id, etc.

        Returns:
            Dictionary representation of the created picture with loaded relationships
        """
        from app.service.rbac import RbacService
        from app.db.utils import sessionmanager
        from fastapi import HTTPException, status
        
        entity_name = cls.get_entity_name()
        entity_name_lower = entity_name.lower()
        creation_exc = cls.get_creation_exception()

        try:
            # Basic authentication check
            await RbacService.get_user_organization_id(_user_id)

            # Authorization check
            await cls.verify_create_access(_user_id, **kwargs)

            # Ensure user_id is included in kwargs for Picture model
            kwargs["user_id"] = _user_id

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)
                
                # Create the entity
                entity = await data_service.create(**kwargs)
                
                # Reload the entity with relationships using get_by_id
                # This will use get_query_options() to load relationships
                entity_with_relationships = await data_service.get_by_id(entity.id)
                
                if not entity_with_relationships:
                    raise creation_exc(f"Failed to reload created {entity_name_lower}")

                result = cls.serialize_entity(entity_with_relationships)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"{entity_name} created successfully",
                    user_id=str(_user_id),
                    entity_id=str(entity.id),
                )

                return result

        except HTTPException:
            raise
        except creation_exc as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}",
                user_id=str(_user_id),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {entity_name_lower}: {cls._sanitize_error_message(e)}",
                user_id=str(_user_id),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity_name_lower}",
            )
