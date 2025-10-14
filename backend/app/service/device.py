from typing import Dict, Any, Type
from uuid import UUID

from app.db.utils import sessionmanager
from app.db.model import DeviceBrand, DeviceModel, DeviceLens
from app.datastore import (
    DeviceBrandDataService,
    DeviceModelDataService,
    DeviceLensDataService,
)
from app.service.base_crud import BaseCRUDService
from app.service.rbac import RbacService
from app.exceptions import (
    DeviceBrandNotFoundError,
    DeviceBrandCreationError,
    DeviceBrandUpdateError,
    DeviceBrandDeletionError,
    DeviceModelNotFoundError,
    DeviceModelCreationError,
    DeviceModelUpdateError,
    DeviceModelDeletionError,
    DeviceLensNotFoundError,
    DeviceLensCreationError,
    DeviceLensUpdateError,
    DeviceLensDeletionError,
)


class DeviceBrandService(BaseCRUDService[DeviceBrand]):
    """
    Service layer for DeviceBrand operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active brands are returned by default
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "DeviceBrand"

    @classmethod
    def get_data_service_class(cls) -> Type[DeviceBrandDataService]:
        """Return the data service class."""
        return DeviceBrandDataService

    @classmethod
    def serialize_entity(cls, entity: DeviceBrand) -> Dict[str, Any]:
        """Convert DeviceBrand entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "active": entity.active,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return DeviceBrand NotFoundError exception class."""
        return DeviceBrandNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return DeviceBrand CreationError exception class."""
        return DeviceBrandCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return DeviceBrand UpdateError exception class."""
        return DeviceBrandUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return DeviceBrand DeletionError exception class."""
        return DeviceBrandDeletionError


class DeviceModelService(BaseCRUDService[DeviceModel]):
    """
    Service layer for DeviceModel operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active models are returned by default
    - Each model must be associated with a brand
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "DeviceModel"

    @classmethod
    def get_data_service_class(cls) -> Type[DeviceModelDataService]:
        """Return the data service class."""
        return DeviceModelDataService

    @classmethod
    def serialize_entity(cls, entity: DeviceModel) -> Dict[str, Any]:
        """Convert DeviceModel entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "device_brand_id": str(entity.device_brand_id),
            "active": entity.active,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return DeviceModel NotFoundError exception class."""
        return DeviceModelNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return DeviceModel CreationError exception class."""
        return DeviceModelCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return DeviceModel UpdateError exception class."""
        return DeviceModelUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return DeviceModel DeletionError exception class."""
        return DeviceModelDeletionError


class DeviceLensService(BaseCRUDService[DeviceLens]):
    """
    Service layer for DeviceLens operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active lenses are returned by default
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "DeviceLens"

    @classmethod
    def get_data_service_class(cls) -> Type[DeviceLensDataService]:
        """Return the data service class."""
        return DeviceLensDataService

    @classmethod
    def serialize_entity(cls, entity: DeviceLens) -> Dict[str, Any]:
        """Convert DeviceLens entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "device_brand_id": str(entity.device_brand_id),
            "active": entity.active,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return DeviceLens NotFoundError exception class."""
        return DeviceLensNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return DeviceLens CreationError exception class."""
        return DeviceLensCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return DeviceLens UpdateError exception class."""
        return DeviceLensUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return DeviceLens DeletionError exception class."""
        return DeviceLensDeletionError


class DeviceService:
    """
    Unified service layer for all device information.

    Access Control:
    - GET operations: Any authenticated user

    Returns combined view of all device brands, models, and lenses.
    """

    @staticmethod
    async def get_all_devices(user_id: UUID) -> Dict[str, Any]:
        """
        Retrieve all device information in a unified structure.

        Access: Any authenticated user

        Returns:
            Dictionary with "devices" key containing array of brand objects:
            {
                "devices": [
                    {
                        "id": "uuid",
                        "name": "brand_name_1",
                        "description": "Brand description",
                        "models": [
                            {
                                "id": "uuid",
                                "name": "model1",
                                "description": "Model description"
                            },
                            ...
                        ],
                        "lenses": [
                            {
                                "id": "uuid",
                                "name": "lens1",
                                "description": "Lens description"
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }

        Args:
            user_id: The requesting user's UUID

        Raises:
            HTTPException: 500 on database error
        """
        # Verify user is authenticated
        await RbacService.get_user_organization_id(user_id)

        async with sessionmanager.get_session() as session:
            # Get all brands with relationships loaded
            brand_data_service = DeviceBrandDataService(session)
            brands, _ = await brand_data_service.get_all()

            # Build nested structure
            devices = []
            for brand in brands:
                brand_dict = {
                    "id": str(brand.id),
                    "name": brand.name,
                    "description": brand.description,
                    "models": [
                        {
                            "id": str(model.id),
                            "name": model.name,
                            "description": model.description,
                        }
                        for model in brand.device_models
                        if model.active
                    ],
                    "lenses": [
                        {
                            "id": str(lens.id),
                            "name": lens.name,
                            "description": lens.description,
                        }
                        for lens in brand.device_lenses
                        if lens.active
                    ],
                }
                devices.append(brand_dict)

            await session.commit()
            return {"devices": devices}
