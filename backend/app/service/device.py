from typing import List, Dict, Any
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.datastore import (
    DeviceBrandDataService,
    DeviceModelDataService,
    DeviceLensDataService,
)
from app.db.data.data_constants import ROLE_CFIA_ADMIN
from app.service.logs import LogService
from app.service.rbac import RbacService
from app.exceptions import (
    DeviceBrandNotFoundError,
    DeviceModelNotFoundError,
    DeviceLensNotFoundError,
)


class DeviceBrandService:
    """
    Service layer for DeviceBrand operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active brands are returned by default
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for DeviceBrandService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active device brands.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "device_brands" key containing list of brand data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceBrandDataService(session)

                # Retrieve all brands
                brands = await data_service.get_all()

                return {
                    "device_brands": [
                        {
                            "id": str(brand.id),
                            "name": brand.name,
                            "active": brand.active,
                        }
                        for brand in brands
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceBrandService._get_logger()
            logger.error(
                f"Failed to retrieve device brands: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve device brands",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device brands: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, brand_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a device brand by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            brand_id: The device brand UUID to retrieve

        Returns:
            Dictionary containing device brand data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceBrandDataService(session)

                # Retrieve brand
                brand = await data_service.get_by_id(brand_id)
                if not brand:
                    raise DeviceBrandNotFoundError(f"Device brand {brand_id} not found")

                return {
                    "id": str(brand.id),
                    "name": brand.name,
                    "active": brand.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceBrandNotFoundError as e:
            logger = DeviceBrandService._get_logger()
            logger.warning(
                f"Device brand not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceBrandService._get_logger()
            logger.error(
                f"Failed to retrieve device brand: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            logger.debug(
                "Traceback for failed retrieve device brand",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device brand: {str(e)}",
            )

    @staticmethod
    async def create(user_id: UUID, name: str) -> Dict[str, Any]:
        """
        Create a new device brand.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Brand name

        Returns:
            Dictionary containing the created brand data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceBrandDataService(session)

                # Create the brand
                brand = await data_service.create(name=name)
                await session.commit()

                logger = DeviceBrandService._get_logger()
                logger.info(
                    f"Created device brand: {brand.name}",
                    brand_id=str(brand.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(brand.id),
                    "name": brand.name,
                    "active": brand.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceBrandService._get_logger()
            logger.error(
                f"Failed to create device brand: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                brand_name=name,
            )
            logger.debug(
                "Traceback for failed create device brand",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create device brand: {str(e)}",
            )

    @staticmethod
    async def update(user_id: UUID, brand_id: UUID, name: str) -> Dict[str, Any]:
        """
        Update an existing device brand.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            brand_id: The device brand UUID to update
            name: New brand name

        Returns:
            Dictionary containing the updated brand data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceBrandDataService(session)

                # Update the brand
                brand = await data_service.update(brand_id=brand_id, name=name)
                if not brand:
                    raise DeviceBrandNotFoundError(f"Device brand {brand_id} not found")

                await session.commit()

                logger = DeviceBrandService._get_logger()
                logger.info(
                    f"Updated device brand: {brand.name}",
                    brand_id=str(brand.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(brand.id),
                    "name": brand.name,
                    "active": brand.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceBrandNotFoundError as e:
            logger = DeviceBrandService._get_logger()
            logger.warning(
                f"Device brand not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceBrandService._get_logger()
            logger.error(
                f"Failed to update device brand: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            logger.debug(
                "Traceback for failed update device brand",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update device brand: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, brand_id: UUID) -> Dict[str, str]:
        """
        Soft delete a device brand (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            brand_id: The device brand UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceBrandDataService(session)

                # Soft delete the brand
                success = await data_service.soft_delete(brand_id)
                if not success:
                    raise DeviceBrandNotFoundError(f"Device brand {brand_id} not found")

                await session.commit()

                logger = DeviceBrandService._get_logger()
                logger.info(
                    f"Deleted device brand: {brand_id}",
                    brand_id=str(brand_id),
                    user_id=str(user_id),
                )

                return {"message": f"Device brand {brand_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceBrandNotFoundError as e:
            logger = DeviceBrandService._get_logger()
            logger.warning(
                f"Device brand not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceBrandService._get_logger()
            logger.error(
                f"Failed to delete device brand: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                brand_id=str(brand_id),
            )
            logger.debug(
                "Traceback for failed delete device brand",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete device brand: {str(e)}",
            )


class DeviceModelService:
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

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for DeviceModelService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active device models.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "device_models" key containing list of model data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceModelDataService(session)

                # Retrieve all models
                models = await data_service.get_all()

                return {
                    "device_models": [
                        {
                            "id": str(model.id),
                            "name": model.name,
                            "brand_id": str(model.brand_id),
                            "brand_name": model.brand.name if model.brand else None,
                            "active": model.active,
                        }
                        for model in models
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceModelService._get_logger()
            logger.error(
                f"Failed to retrieve device models: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve device models",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device models: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, model_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a device model by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            model_id: The device model UUID to retrieve

        Returns:
            Dictionary containing device model data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceModelDataService(session)

                # Retrieve model
                model = await data_service.get_by_id(model_id)
                if not model:
                    raise DeviceModelNotFoundError(f"Device model {model_id} not found")

                return {
                    "id": str(model.id),
                    "name": model.name,
                    "brand_id": str(model.brand_id),
                    "brand_name": model.brand.name if model.brand else None,
                    "active": model.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceModelNotFoundError as e:
            logger = DeviceModelService._get_logger()
            logger.warning(
                f"Device model not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceModelService._get_logger()
            logger.error(
                f"Failed to retrieve device model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed retrieve device model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device model: {str(e)}",
            )

    @staticmethod
    async def create(user_id: UUID, name: str, brand_id: UUID) -> Dict[str, Any]:
        """
        Create a new device model.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Model name
            brand_id: Device brand UUID

        Returns:
            Dictionary containing the created model data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceModelDataService(session)

                # Create the model
                model = await data_service.create(name=name, brand_id=brand_id)
                await session.commit()

                logger = DeviceModelService._get_logger()
                logger.info(
                    f"Created device model: {model.name}",
                    model_id=str(model.id),
                    brand_id=str(brand_id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(model.id),
                    "name": model.name,
                    "brand_id": str(model.brand_id),
                    "brand_name": model.brand.name if model.brand else None,
                    "active": model.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceModelService._get_logger()
            logger.error(
                f"Failed to create device model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_name=name,
                brand_id=str(brand_id),
            )
            logger.debug(
                "Traceback for failed create device model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create device model: {str(e)}",
            )

    @staticmethod
    async def update(
        user_id: UUID, model_id: UUID, name: str, brand_id: UUID
    ) -> Dict[str, Any]:
        """
        Update an existing device model.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            model_id: The device model UUID to update
            name: New model name
            brand_id: Device brand UUID

        Returns:
            Dictionary containing the updated model data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceModelDataService(session)

                # Update the model
                model = await data_service.update(
                    model_id=model_id, name=name, brand_id=brand_id
                )
                if not model:
                    raise DeviceModelNotFoundError(f"Device model {model_id} not found")

                await session.commit()

                logger = DeviceModelService._get_logger()
                logger.info(
                    f"Updated device model: {model.name}",
                    model_id=str(model.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(model.id),
                    "name": model.name,
                    "brand_id": str(model.brand_id),
                    "brand_name": model.brand.name if model.brand else None,
                    "active": model.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceModelNotFoundError as e:
            logger = DeviceModelService._get_logger()
            logger.warning(
                f"Device model not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceModelService._get_logger()
            logger.error(
                f"Failed to update device model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed update device model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update device model: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, model_id: UUID) -> Dict[str, str]:
        """
        Soft delete a device model (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            model_id: The device model UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceModelDataService(session)

                # Soft delete the model
                success = await data_service.soft_delete(model_id)
                if not success:
                    raise DeviceModelNotFoundError(f"Device model {model_id} not found")

                await session.commit()

                logger = DeviceModelService._get_logger()
                logger.info(
                    f"Deleted device model: {model_id}",
                    model_id=str(model_id),
                    user_id=str(user_id),
                )

                return {"message": f"Device model {model_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceModelNotFoundError as e:
            logger = DeviceModelService._get_logger()
            logger.warning(
                f"Device model not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceModelService._get_logger()
            logger.error(
                f"Failed to delete device model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed delete device model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete device model: {str(e)}",
            )


class DeviceLensService:
    """
    Service layer for DeviceLens operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active lenses are returned by default
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for DeviceLensService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active device lenses.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "device_lenses" key containing list of lens data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceLensDataService(session)

                # Retrieve all lenses
                lenses = await data_service.get_all()

                return {
                    "device_lenses": [
                        {
                            "id": str(lens.id),
                            "name": lens.name,
                            "active": lens.active,
                        }
                        for lens in lenses
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceLensService._get_logger()
            logger.error(
                f"Failed to retrieve device lenses: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve device lenses",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device lenses: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, lens_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a device lens by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            lens_id: The device lens UUID to retrieve

        Returns:
            Dictionary containing device lens data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = DeviceLensDataService(session)

                # Retrieve lens
                lens = await data_service.get_by_id(lens_id)
                if not lens:
                    raise DeviceLensNotFoundError(f"Device lens {lens_id} not found")

                return {
                    "id": str(lens.id),
                    "name": lens.name,
                    "active": lens.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceLensNotFoundError as e:
            logger = DeviceLensService._get_logger()
            logger.warning(
                f"Device lens not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceLensService._get_logger()
            logger.error(
                f"Failed to retrieve device lens: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            logger.debug(
                "Traceback for failed retrieve device lens",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve device lens: {str(e)}",
            )

    @staticmethod
    async def create(user_id: UUID, name: str) -> Dict[str, Any]:
        """
        Create a new device lens.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Lens name

        Returns:
            Dictionary containing the created lens data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceLensDataService(session)

                # Create the lens
                lens = await data_service.create(name=name)
                await session.commit()

                logger = DeviceLensService._get_logger()
                logger.info(
                    f"Created device lens: {lens.name}",
                    lens_id=str(lens.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(lens.id),
                    "name": lens.name,
                    "active": lens.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceLensService._get_logger()
            logger.error(
                f"Failed to create device lens: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                lens_name=name,
            )
            logger.debug(
                "Traceback for failed create device lens",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create device lens: {str(e)}",
            )

    @staticmethod
    async def update(user_id: UUID, lens_id: UUID, name: str) -> Dict[str, Any]:
        """
        Update an existing device lens.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            lens_id: The device lens UUID to update
            name: New lens name

        Returns:
            Dictionary containing the updated lens data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceLensDataService(session)

                # Update the lens
                lens = await data_service.update(lens_id=lens_id, name=name)
                if not lens:
                    raise DeviceLensNotFoundError(f"Device lens {lens_id} not found")

                await session.commit()

                logger = DeviceLensService._get_logger()
                logger.info(
                    f"Updated device lens: {lens.name}",
                    lens_id=str(lens.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(lens.id),
                    "name": lens.name,
                    "active": lens.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceLensNotFoundError as e:
            logger = DeviceLensService._get_logger()
            logger.warning(
                f"Device lens not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceLensService._get_logger()
            logger.error(
                f"Failed to update device lens: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            logger.debug(
                "Traceback for failed update device lens",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update device lens: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, lens_id: UUID) -> Dict[str, str]:
        """
        Soft delete a device lens (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            lens_id: The device lens UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = DeviceLensDataService(session)

                # Soft delete the lens
                success = await data_service.soft_delete(lens_id)
                if not success:
                    raise DeviceLensNotFoundError(f"Device lens {lens_id} not found")

                await session.commit()

                logger = DeviceLensService._get_logger()
                logger.info(
                    f"Deleted device lens: {lens_id}",
                    lens_id=str(lens_id),
                    user_id=str(user_id),
                )

                return {"message": f"Device lens {lens_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except DeviceLensNotFoundError as e:
            logger = DeviceLensService._get_logger()
            logger.warning(
                f"Device lens not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = DeviceLensService._get_logger()
            logger.error(
                f"Failed to delete device lens: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                lens_id=str(lens_id),
            )
            logger.debug(
                "Traceback for failed delete device lens",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete device lens: {str(e)}",
            )


class DeviceService:
    """
    Unified service layer for all device information.

    Access Control:
    - GET operations: Any authenticated user

    Returns combined view of all device brands, models, and lenses.
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for DeviceService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

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
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                brand_service = DeviceBrandDataService(session)
                model_service = DeviceModelDataService(session)
                lens_service = DeviceLensDataService(session)

                # Retrieve all data
                brands = await brand_service.get_all()
                models = await model_service.get_all()
                lenses = await lens_service.get_all()

                # Build the response structure as an array
                devices = []

                for brand in brands:
                    # Get models for this brand
                    brand_models = [
                        {
                            "id": str(model.id),
                            "name": model.name,
                            "description": model.description,
                        }
                        for model in models
                        if model.brand_id == brand.id and model.active
                    ]

                    # Get lenses for this brand
                    brand_lenses = [
                        {
                            "id": str(lens.id),
                            "name": lens.name,
                            "description": lens.description,
                        }
                        for lens in lenses
                        if lens.brand_id == brand.id and lens.active
                    ]

                    devices.append(
                        {
                            "id": str(brand.id),
                            "name": brand.name,
                            "description": brand.description,
                            "models": brand_models,
                            "lenses": brand_lenses,
                        }
                    )

                return {"devices": devices}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = DeviceService._get_logger()
            logger.error(
                f"Failed to retrieve devices: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve devices",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve devices: {str(e)}",
            )
