"""
Tests for RBAC CRUD Services.

Basic smoke tests to verify the 5 RBAC services follow the BaseCRUDService pattern correctly.
"""

import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

from app.service.rbac import (
    RbacRoleService,
    RbacPermissionService,
    RbacResourceService,
    RbacRolePermissionResourceService,
    RbacUserRoleService,
)
from app.db.model import (
    RbacRole,
    RbacPermission,
    RbacResource,
    RbacRolePermissionResource,
    RbacUserRole,
)

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


class TestRbacRoleService:
    """Test RbacRoleService follows BaseCRUDService pattern."""

    @pytest.mark.asyncio
    async def test_get_all_rbac_roles(self, monkeypatch):
        """Test RbacRoleService.get_all() returns paginated results."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock role
        role = Mock(spec=RbacRole)
        role.id = uuid4()
        role.name = "admin"
        role.description = "Admin role"
        role.organization_id = user_org_id
        role.active = True
        role.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        role.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RBAC check
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([role], 1))

        # Create a mock class that returns the mock instance
        class MockDataServiceClass:
            def __init__(self, session):
                pass

            async def get_all(self, **kwargs):
                return await mock_data_service.get_all(**kwargs)

        monkeypatch.setattr(
            "app.service.rbac.RbacRoleService.get_data_service_class",
            lambda: MockDataServiceClass,
        )

        # Call service
        result = await RbacRoleService.get_all(user_id)

        # Verify paginated response
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["total"] == 1


class TestRbacPermissionService:
    """Test RbacPermissionService follows BaseCRUDService pattern."""

    @pytest.mark.asyncio
    async def test_get_all_rbac_permissions(self, monkeypatch):
        """Test RbacPermissionService.get_all() returns paginated results."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock permission
        perm = Mock(spec=RbacPermission)
        perm.id = uuid4()
        perm.name = "read"
        perm.description = "Read permission"
        perm.active = True
        perm.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        perm.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RBAC check
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([perm], 1))

        # Create a mock class that returns the mock instance
        class MockDataServiceClass:
            def __init__(self, session):
                pass

            async def get_all(self, **kwargs):
                return await mock_data_service.get_all(**kwargs)

        monkeypatch.setattr(
            "app.service.rbac.RbacPermissionService.get_data_service_class",
            lambda: MockDataServiceClass,
        )

        # Call service
        result = await RbacPermissionService.get_all(user_id)

        # Verify paginated response
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["total"] == 1


class TestRbacResourceService:
    """Test RbacResourceService follows BaseCRUDService pattern."""

    @pytest.mark.asyncio
    async def test_get_all_rbac_resources(self, monkeypatch):
        """Test RbacResourceService.get_all() returns paginated results."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock resource
        resource = Mock(spec=RbacResource)
        resource.id = uuid4()
        resource.name = "GET_/users"
        resource.description = "Get users endpoint"
        resource.active = True
        resource.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        resource.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RBAC check
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([resource], 1))

        # Create a mock class that returns the mock instance
        class MockDataServiceClass:
            def __init__(self, session):
                pass

            async def get_all(self, **kwargs):
                return await mock_data_service.get_all(**kwargs)

        monkeypatch.setattr(
            "app.service.rbac.RbacResourceService.get_data_service_class",
            lambda: MockDataServiceClass,
        )

        # Call service
        result = await RbacResourceService.get_all(user_id)

        # Verify paginated response
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["total"] == 1


class TestRbacRolePermissionResourceService:
    """Test RbacRolePermissionResourceService with composite key support."""

    @pytest.mark.asyncio
    async def test_get_all_mappings(self, monkeypatch):
        """Test RbacRolePermissionResourceService.get_all() returns paginated results."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock mapping
        mapping = Mock(spec=RbacRolePermissionResource)
        mapping.role_id = uuid4()
        mapping.permission_id = uuid4()
        mapping.resource_id = uuid4()
        mapping.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mapping.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RBAC check
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([mapping], 1))

        # Create a mock class that returns the mock instance
        class MockDataServiceClass:
            def __init__(self, session):
                pass

            async def get_all(self, **kwargs):
                return await mock_data_service.get_all(**kwargs)

        monkeypatch.setattr(
            "app.service.rbac.RbacRolePermissionResourceService.get_data_service_class",
            lambda: MockDataServiceClass,
        )

        # Call service
        result = await RbacRolePermissionResourceService.get_all(user_id)

        # Verify paginated response
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["total"] == 1


class TestRbacUserRoleService:
    """Test RbacUserRoleService with composite key support."""

    @pytest.mark.asyncio
    async def test_get_all_user_roles(self, monkeypatch):
        """Test RbacUserRoleService.get_all() returns paginated results."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock user role
        user_role = Mock(spec=RbacUserRole)
        user_role.user_id = uuid4()
        user_role.role_id = uuid4()
        user_role.active = True
        user_role.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        user_role.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RBAC check
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([user_role], 1))

        # Create a mock class that returns the mock instance
        class MockDataServiceClass:
            def __init__(self, session):
                pass

            async def get_all(self, **kwargs):
                return await mock_data_service.get_all(**kwargs)

        monkeypatch.setattr(
            "app.service.rbac.RbacUserRoleService.get_data_service_class",
            lambda: MockDataServiceClass,
        )

        # Call service
        result = await RbacUserRoleService.get_all(user_id)

        # Verify paginated response
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 1
        assert result["total"] == 1
