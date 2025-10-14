from typing import Type
from sqlalchemy.orm import selectinload

from app.db.model import DeviceBrand, DeviceModel, DeviceLens
from app.service.base_crud import BaseCRUDDataService


class DeviceBrandDataService(BaseCRUDDataService[DeviceBrand]):
    """Data access layer for DeviceBrand database operations."""

    @classmethod
    def get_model_class(cls) -> Type[DeviceBrand]:
        """Return the DeviceBrand model class."""
        return DeviceBrand

    def get_query_options(self) -> list:
        """Load device models and lenses relationships."""
        return [
            selectinload(DeviceBrand.device_models),
            selectinload(DeviceBrand.device_lenses),
        ]


class DeviceModelDataService(BaseCRUDDataService[DeviceModel]):
    """Data access layer for DeviceModel database operations."""

    @classmethod
    def get_model_class(cls) -> Type[DeviceModel]:
        """Return the DeviceModel model class."""
        return DeviceModel

    def get_query_options(self) -> list:
        """Load device brand relationship."""
        return [selectinload(DeviceModel.device_brand)]


class DeviceLensDataService(BaseCRUDDataService[DeviceLens]):
    """Data access layer for DeviceLens database operations."""

    @classmethod
    def get_model_class(cls) -> Type[DeviceLens]:
        """Return the DeviceLens model class."""
        return DeviceLens

    def get_query_options(self) -> list:
        """Load device brand relationship."""
        return [selectinload(DeviceLens.device_brand)]
