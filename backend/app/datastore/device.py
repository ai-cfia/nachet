from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import DeviceBrand, DeviceModel, DeviceLens


class DeviceBrandDataService:
    """Data access layer for DeviceBrand database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[DeviceBrand]:
        """
        Retrieve all active device brands.

        Returns:
            List of DeviceBrand objects
        """
        query = (
            select(DeviceBrand)
            .where(DeviceBrand.active.is_(True))
            .options(selectinload(DeviceBrand.device_models))
            .options(selectinload(DeviceBrand.device_lenses))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, brand_id: UUID) -> Optional[DeviceBrand]:
        """
        Retrieve a device brand by ID.

        Args:
            brand_id: The device brand UUID

        Returns:
            DeviceBrand object if found and active, None otherwise
        """
        query = (
            select(DeviceBrand)
            .where(DeviceBrand.id == brand_id)
            .where(DeviceBrand.active.is_(True))
            .options(selectinload(DeviceBrand.device_models))
            .options(selectinload(DeviceBrand.device_lenses))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> DeviceBrand:
        """
        Create a new device brand.

        Args:
            name: Device brand name
            description: Optional device brand description

        Returns:
            The created DeviceBrand object
        """
        device_brand = DeviceBrand(
            name=name,
            description=description,
            active=True,
        )
        self.session.add(device_brand)
        await self.session.flush()
        await self.session.refresh(device_brand)
        return device_brand

    async def update(
        self,
        brand_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[DeviceBrand]:
        """
        Update a device brand.

        Args:
            brand_id: The device brand UUID
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Updated DeviceBrand object if found, None otherwise
        """
        device_brand = await self.get_by_id(brand_id)
        if not device_brand:
            return None

        if name is not None:
            device_brand.name = name
        if description is not None:
            device_brand.description = description

        await self.session.flush()
        await self.session.refresh(device_brand)
        return device_brand

    async def soft_delete(self, brand_id: UUID) -> Optional[DeviceBrand]:
        """
        Soft delete a device brand by setting active to False.

        Args:
            brand_id: The device brand UUID

        Returns:
            The soft-deleted DeviceBrand object if found, None otherwise
        """
        query = select(DeviceBrand).where(DeviceBrand.id == brand_id)
        result = await self.session.execute(query)
        device_brand = result.scalar_one_or_none()

        if not device_brand:
            return None

        device_brand.active = False
        await self.session.flush()
        await self.session.refresh(device_brand)
        return device_brand


class DeviceModelDataService:
    """Data access layer for DeviceModel database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[DeviceModel]:
        """
        Retrieve all active device models.

        Returns:
            List of DeviceModel objects
        """
        query = (
            select(DeviceModel)
            .where(DeviceModel.active.is_(True))
            .options(selectinload(DeviceModel.device_brand))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, model_id: UUID) -> Optional[DeviceModel]:
        """
        Retrieve a device model by ID.

        Args:
            model_id: The device model UUID

        Returns:
            DeviceModel object if found and active, None otherwise
        """
        query = (
            select(DeviceModel)
            .where(DeviceModel.id == model_id)
            .where(DeviceModel.active.is_(True))
            .options(selectinload(DeviceModel.device_brand))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        device_brand_id: UUID,
        name: str,
        description: Optional[str] = None,
    ) -> DeviceModel:
        """
        Create a new device model.

        Args:
            device_brand_id: UUID of the associated device brand
            name: Device model name
            description: Optional device model description

        Returns:
            The created DeviceModel object
        """
        device_model = DeviceModel(
            device_brand_id=device_brand_id,
            name=name,
            description=description,
            active=True,
        )
        self.session.add(device_model)
        await self.session.flush()
        await self.session.refresh(device_model)
        return device_model

    async def update(
        self,
        model_id: UUID,
        device_brand_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[DeviceModel]:
        """
        Update a device model.

        Args:
            model_id: The device model UUID
            device_brand_id: New device brand ID (if provided)
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Updated DeviceModel object if found, None otherwise
        """
        device_model = await self.get_by_id(model_id)
        if not device_model:
            return None

        if device_brand_id is not None:
            device_model.device_brand_id = device_brand_id
        if name is not None:
            device_model.name = name
        if description is not None:
            device_model.description = description

        await self.session.flush()
        await self.session.refresh(device_model)
        return device_model

    async def soft_delete(self, model_id: UUID) -> Optional[DeviceModel]:
        """
        Soft delete a device model by setting active to False.

        Args:
            model_id: The device model UUID

        Returns:
            The soft-deleted DeviceModel object if found, None otherwise
        """
        query = select(DeviceModel).where(DeviceModel.id == model_id)
        result = await self.session.execute(query)
        device_model = result.scalar_one_or_none()

        if not device_model:
            return None

        device_model.active = False
        await self.session.flush()
        await self.session.refresh(device_model)
        return device_model


class DeviceLensDataService:
    """Data access layer for DeviceLens database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[DeviceLens]:
        """
        Retrieve all active device lenses.

        Returns:
            List of DeviceLens objects
        """
        query = (
            select(DeviceLens)
            .where(DeviceLens.active.is_(True))
            .options(selectinload(DeviceLens.device_brand))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, lens_id: UUID) -> Optional[DeviceLens]:
        """
        Retrieve a device lens by ID.

        Args:
            lens_id: The device lens UUID

        Returns:
            DeviceLens object if found and active, None otherwise
        """
        query = (
            select(DeviceLens)
            .where(DeviceLens.id == lens_id)
            .where(DeviceLens.active.is_(True))
            .options(selectinload(DeviceLens.device_brand))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        device_brand_id: UUID,
        name: str,
        description: Optional[str] = None,
    ) -> DeviceLens:
        """
        Create a new device lens.

        Args:
            device_brand_id: UUID of the associated device brand
            name: Device lens name
            description: Optional device lens description

        Returns:
            The created DeviceLens object
        """
        device_lens = DeviceLens(
            device_brand_id=device_brand_id,
            name=name,
            description=description,
            active=True,
        )
        self.session.add(device_lens)
        await self.session.flush()
        await self.session.refresh(device_lens)
        return device_lens

    async def update(
        self,
        lens_id: UUID,
        device_brand_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[DeviceLens]:
        """
        Update a device lens.

        Args:
            lens_id: The device lens UUID
            device_brand_id: New device brand ID (if provided)
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Updated DeviceLens object if found, None otherwise
        """
        device_lens = await self.get_by_id(lens_id)
        if not device_lens:
            return None

        if device_brand_id is not None:
            device_lens.device_brand_id = device_brand_id
        if name is not None:
            device_lens.name = name
        if description is not None:
            device_lens.description = description

        await self.session.flush()
        await self.session.refresh(device_lens)
        return device_lens

    async def soft_delete(self, lens_id: UUID) -> Optional[DeviceLens]:
        """
        Soft delete a device lens by setting active to False.

        Args:
            lens_id: The device lens UUID

        Returns:
            The soft-deleted DeviceLens object if found, None otherwise
        """
        query = select(DeviceLens).where(DeviceLens.id == lens_id)
        result = await self.session.execute(query)
        device_lens = result.scalar_one_or_none()

        if not device_lens:
            return None

        device_lens.active = False
        await self.session.flush()
        await self.session.refresh(device_lens)
        return device_lens
