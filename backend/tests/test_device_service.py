"""
Tests for DeviceService - CRUD operations for device brands, models, and lenses.

Access Control:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only
"""

import os
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.service.device import (
    DeviceBrandService,
    DeviceModelService,
    DeviceLensService,
    DeviceService,
)
from app.db.model import DeviceBrand, DeviceModel, DeviceLens

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


# ============================================================================
# DeviceBrandService Tests
# ============================================================================


class TestDeviceBrandServiceGetAll:
    """Test DeviceBrandService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all device brands."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand1_id = uuid4()
        brand2_id = uuid4()

        # Mock brands
        brand1 = Mock(spec=DeviceBrand)
        brand1.id = brand1_id
        brand1.name = "Apple"
        brand1.active = True

        brand2 = Mock(spec=DeviceBrand)
        brand2.id = brand2_id
        brand2.name = "Samsung"
        brand2.active = True

        # Mock RbacService - just verify user exists
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=[brand1, brand2])
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceBrandService.get_all(user_id)

        # Verify
        assert "device_brands" in result
        assert len(result["device_brands"]) == 2
        assert result["device_brands"][0]["name"] == "Apple"
        assert result["device_brands"][1]["name"] == "Samsung"
        assert result["device_brands"][0]["active"] is True


class TestDeviceBrandServiceGetById:
    """Test DeviceBrandService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a brand by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple"
        brand.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=brand)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceBrandService.get_by_id(user_id, brand_id)

        # Verify
        assert result["name"] == "Apple"
        assert result["id"] == str(brand_id)
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if brand not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - brand not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DeviceBrandService.get_by_id(user_id, brand_id)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestDeviceBrandServiceCreate:
    """Test DeviceBrandService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new brands."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple"
        brand.active = True

        # Mock RbacService - user is cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=brand)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceBrandService.create(user_id, "Apple")

        # Verify
        assert result["name"] == "Apple"
        assert result["id"] == str(brand_id)
        assert result["active"] is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RbacService - user is NOT cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await DeviceBrandService.create(user_id, "Apple")

        assert exc_info.value.status_code == 403
        assert "role" in exc_info.value.detail


class TestDeviceBrandServiceUpdate:
    """Test DeviceBrandService.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update brands."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock updated brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple Inc."
        brand.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=brand)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceBrandService.update(user_id, brand_id, "Apple Inc.")

        # Verify
        assert result["name"] == "Apple Inc."
        assert result["id"] == str(brand_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if brand not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - brand not found
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DeviceBrandService.update(user_id, brand_id, "Apple Inc.")

        assert exc_info.value.status_code == 404


class TestDeviceBrandServiceDelete:
    """Test DeviceBrandService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete brands."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceBrandService.delete(user_id, brand_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if brand not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - brand not found
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=False)
        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DeviceBrandService.delete(user_id, brand_id)

        assert exc_info.value.status_code == 404


# ============================================================================
# DeviceModelService Tests
# ============================================================================


class TestDeviceModelServiceGetAll:
    """Test DeviceModelService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_with_brand_info(self, monkeypatch):
        """Any authenticated user should be able to list all models with brand info."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()
        model1_id = uuid4()
        model2_id = uuid4()

        # Mock brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple"

        # Mock models
        model1 = Mock(spec=DeviceModel)
        model1.id = model1_id
        model1.name = "iPhone 15"
        model1.brand_id = brand_id
        model1.brand = brand
        model1.active = True

        model2 = Mock(spec=DeviceModel)
        model2.id = model2_id
        model2.name = "iPhone 15 Pro"
        model2.brand_id = brand_id
        model2.brand = brand
        model2.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=[model1, model2])
        monkeypatch.setattr(
            "app.service.device.DeviceModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceModelService.get_all(user_id)

        # Verify
        assert "device_models" in result
        assert len(result["device_models"]) == 2
        assert result["device_models"][0]["name"] == "iPhone 15"
        assert result["device_models"][0]["brand_name"] == "Apple"
        assert result["device_models"][1]["name"] == "iPhone 15 Pro"


class TestDeviceModelServiceGetById:
    """Test DeviceModelService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a model by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()
        model_id = uuid4()

        # Mock brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple"

        # Mock model
        model = Mock(spec=DeviceModel)
        model.id = model_id
        model.name = "iPhone 15"
        model.brand_id = brand_id
        model.brand = brand
        model.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.device.DeviceModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceModelService.get_by_id(user_id, model_id)

        # Verify
        assert result["name"] == "iPhone 15"
        assert result["brand_name"] == "Apple"
        assert result["brand_id"] == str(brand_id)


class TestDeviceModelServiceCreate:
    """Test DeviceModelService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new models."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand_id = uuid4()
        model_id = uuid4()

        # Mock brand
        brand = Mock(spec=DeviceBrand)
        brand.id = brand_id
        brand.name = "Apple"

        # Mock model
        model = Mock(spec=DeviceModel)
        model.id = model_id
        model.name = "iPhone 15"
        model.brand_id = brand_id
        model.brand = brand
        model.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.device.DeviceModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceModelService.create(user_id, "iPhone 15", brand_id)

        # Verify
        assert result["name"] == "iPhone 15"
        assert result["brand_name"] == "Apple"
        mock_session.commit.assert_called_once()


# ============================================================================
# DeviceLensService Tests
# ============================================================================


class TestDeviceLensServiceGetAll:
    """Test DeviceLensService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success(self, monkeypatch):
        """Any authenticated user should be able to list all lenses."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        lens1_id = uuid4()
        lens2_id = uuid4()

        # Mock lenses
        lens1 = Mock(spec=DeviceLens)
        lens1.id = lens1_id
        lens1.name = "Wide Angle"
        lens1.active = True

        lens2 = Mock(spec=DeviceLens)
        lens2.id = lens2_id
        lens2.name = "Macro"
        lens2.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=[lens1, lens2])
        monkeypatch.setattr(
            "app.service.device.DeviceLensDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceLensService.get_all(user_id)

        # Verify
        assert "device_lenses" in result
        assert len(result["device_lenses"]) == 2
        assert result["device_lenses"][0]["name"] == "Wide Angle"
        assert result["device_lenses"][1]["name"] == "Macro"


class TestDeviceLensServiceCreate:
    """Test DeviceLensService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new lenses."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        lens_id = uuid4()

        # Mock lens
        lens = Mock(spec=DeviceLens)
        lens.id = lens_id
        lens.name = "Wide Angle"
        lens.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=lens)
        monkeypatch.setattr(
            "app.service.device.DeviceLensDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceLensService.create(user_id, "Wide Angle")

        # Verify
        assert result["name"] == "Wide Angle"
        assert result["id"] == str(lens_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when creating lenses."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RbacService - user is NOT cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await DeviceLensService.create(user_id, "Wide Angle")

        assert exc_info.value.status_code == 403


class TestDeviceLensServiceDelete:
    """Test DeviceLensService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete lenses."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        lens_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.device.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.service.device.DeviceLensDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DeviceLensService.delete(user_id, lens_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()


# ============================================================================
# Unified DeviceService Tests
# ============================================================================


class TestDeviceServiceGetAllDevices:
    """Test DeviceService.get_all_devices method."""

    @pytest.mark.asyncio
    async def test_get_all_devices_success(self, monkeypatch):
        """Any authenticated user should be able to get all devices organized by brand."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        brand1_id = uuid4()
        brand2_id = uuid4()

        # Mock brands
        brand1 = Mock(spec=DeviceBrand)
        brand1.id = brand1_id
        brand1.name = "Apple"
        brand1.description = "Apple Inc."
        brand1.active = True

        brand2 = Mock(spec=DeviceBrand)
        brand2.id = brand2_id
        brand2.name = "Samsung"
        brand2.description = "Samsung Electronics"
        brand2.active = True

        # Mock models
        model1 = Mock(spec=DeviceModel)
        model1.id = uuid4()
        model1.name = "iPhone 15"
        model1.description = "Latest iPhone model"
        model1.brand_id = brand1_id
        model1.active = True

        model2 = Mock(spec=DeviceModel)
        model2.id = uuid4()
        model2.name = "Galaxy S24"
        model2.description = "Latest Galaxy model"
        model2.brand_id = brand2_id
        model2.active = True

        # Mock lenses
        lens1 = Mock(spec=DeviceLens)
        lens1.id = uuid4()
        lens1.name = "Wide Angle"
        lens1.description = "Wide angle lens"
        lens1.brand_id = brand1_id
        lens1.active = True

        lens2 = Mock(spec=DeviceLens)
        lens2.id = uuid4()
        lens2.name = "Macro"
        lens2.description = "Macro lens"
        lens2.brand_id = brand2_id
        lens2.active = True

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data services
        mock_brand_service = AsyncMock()
        mock_brand_service.get_all = AsyncMock(return_value=[brand1, brand2])

        mock_model_service = AsyncMock()
        mock_model_service.get_all = AsyncMock(return_value=[model1, model2])

        mock_lens_service = AsyncMock()
        mock_lens_service.get_all = AsyncMock(return_value=[lens1, lens2])

        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_brand_service,
        )
        monkeypatch.setattr(
            "app.service.device.DeviceModelDataService",
            lambda session: mock_model_service,
        )
        monkeypatch.setattr(
            "app.service.device.DeviceLensDataService",
            lambda session: mock_lens_service,
        )

        # Call service
        result = await DeviceService.get_all_devices(user_id)

        # Verify structure
        assert "devices" in result
        assert isinstance(result["devices"], list)
        assert len(result["devices"]) == 2

        # Find Apple and Samsung in the array
        apple_data = next((d for d in result["devices"] if d["name"] == "Apple"), None)
        samsung_data = next(
            (d for d in result["devices"] if d["name"] == "Samsung"), None
        )

        assert apple_data is not None
        assert samsung_data is not None

        # Verify Apple data
        assert "id" in apple_data
        assert "name" in apple_data
        assert "description" in apple_data
        assert apple_data["id"] == str(brand1_id)
        assert apple_data["name"] == "Apple"
        assert apple_data["description"] == "Apple Inc."
        assert "models" in apple_data
        assert "lenses" in apple_data

        # Verify Apple models
        assert len(apple_data["models"]) == 1
        apple_model = apple_data["models"][0]
        assert "id" in apple_model
        assert "name" in apple_model
        assert "description" in apple_model
        assert apple_model["name"] == "iPhone 15"
        assert apple_model["description"] == "Latest iPhone model"

        # Verify Apple lenses
        assert len(apple_data["lenses"]) == 1
        apple_lens = apple_data["lenses"][0]
        assert "id" in apple_lens
        assert "name" in apple_lens
        assert "description" in apple_lens
        assert apple_lens["name"] == "Wide Angle"
        assert apple_lens["description"] == "Wide angle lens"

        # Verify Samsung data
        assert "id" in samsung_data
        assert "name" in samsung_data
        assert "description" in samsung_data
        assert samsung_data["id"] == str(brand2_id)
        assert samsung_data["name"] == "Samsung"
        assert samsung_data["description"] == "Samsung Electronics"
        assert "models" in samsung_data
        assert "lenses" in samsung_data

        # Verify Samsung models
        assert len(samsung_data["models"]) == 1
        samsung_model = samsung_data["models"][0]
        assert "id" in samsung_model
        assert "name" in samsung_model
        assert "description" in samsung_model
        assert samsung_model["name"] == "Galaxy S24"
        assert samsung_model["description"] == "Latest Galaxy model"

        # Verify Samsung lenses
        assert len(samsung_data["lenses"]) == 1
        samsung_lens = samsung_data["lenses"][0]
        assert "id" in samsung_lens
        assert "name" in samsung_lens
        assert "description" in samsung_lens
        assert samsung_lens["name"] == "Macro"
        assert samsung_lens["description"] == "Macro lens"

    @pytest.mark.asyncio
    async def test_get_all_devices_empty_brands(self, monkeypatch):
        """Should return empty array when no brands exist."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.device.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data services - empty results
        mock_brand_service = AsyncMock()
        mock_brand_service.get_all = AsyncMock(return_value=[])

        mock_model_service = AsyncMock()
        mock_model_service.get_all = AsyncMock(return_value=[])

        mock_lens_service = AsyncMock()
        mock_lens_service.get_all = AsyncMock(return_value=[])

        monkeypatch.setattr(
            "app.service.device.DeviceBrandDataService",
            lambda session: mock_brand_service,
        )
        monkeypatch.setattr(
            "app.service.device.DeviceModelDataService",
            lambda session: mock_model_service,
        )
        monkeypatch.setattr(
            "app.service.device.DeviceLensDataService",
            lambda session: mock_lens_service,
        )

        # Call service
        result = await DeviceService.get_all_devices(user_id)

        # Verify empty result
        assert result == {"devices": []}
