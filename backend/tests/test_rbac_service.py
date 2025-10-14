"""
Tests for RBAC Service - Role-Based Access Control
"""

import os
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, Request
from dotenv import load_dotenv

from app.service.rbac import RbacService
from app.service.auth import User

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


class TestRbacServiceAuthorizeRequest:
    """Test the centralized authorize_request method."""

    @pytest.mark.asyncio
    async def test_authorize_request_no_policy_denies_access(self, monkeypatch):
        """Routes without policy in database should deny access."""
        from app.db.utils import sessionmanager

        # Mock request
        request = Mock(spec=Request)
        request.method = "GET"
        route_mock = Mock()
        route_mock.path = "/some-unprotected-route"
        request.scope = {"route": route_mock}

        # Mock user
        user = Mock(spec=User)
        user.oid = str(uuid4())

        # Mock sessionmanager and RbacDataService
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        mock_data_service = AsyncMock()
        mock_data_service.user_has_route_access = AsyncMock(return_value=False)
        monkeypatch.setattr(
            "app.service.rbac.RbacDataService", lambda session: mock_data_service
        )

        # Should raise HTTPException 403
        with pytest.raises(HTTPException) as exc_info:
            await RbacService.authorize_request(request, user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authorize_request_with_access_allows(self, monkeypatch):
        """Routes with database policy should allow access when user has permission."""
        from app.db.utils import sessionmanager

        # Mock request for a route with policy
        request = Mock(spec=Request)
        request.method = "GET"
        route_mock = Mock()
        route_mock.path = "/health"
        request.scope = {"route": route_mock}

        # Mock user
        user = Mock(spec=User)
        user.oid = str(uuid4())

        # Mock sessionmanager and RbacDataService
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        mock_data_service = AsyncMock()
        mock_data_service.user_has_route_access = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.service.rbac.RbacDataService", lambda session: mock_data_service
        )

        # Should not raise exception
        await RbacService.authorize_request(request, user)

    @pytest.mark.asyncio
    async def test_authorize_request_denies_without_permission(self, monkeypatch):
        """User without route permission should get 403."""
        from app.db.utils import sessionmanager

        # Mock request for protected route
        request = Mock(spec=Request)
        request.method = "GET"
        route_mock = Mock()
        route_mock.path = "/pipelines"
        request.scope = {"route": route_mock}

        # Mock user
        user = Mock(spec=User)
        user.oid = str(uuid4())

        # Mock sessionmanager and RbacDataService
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        mock_data_service = AsyncMock()
        mock_data_service.user_has_route_access = AsyncMock(return_value=False)
        monkeypatch.setattr(
            "app.service.rbac.RbacDataService", lambda session: mock_data_service
        )

        # Should raise HTTPException 403
        with pytest.raises(HTTPException) as exc_info:
            await RbacService.authorize_request(request, user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authorize_request_allows_with_permission(self, monkeypatch):
        """User with route permission should be allowed access."""
        from app.db.utils import sessionmanager

        # Mock request for protected route
        request = Mock(spec=Request)
        request.method = "GET"
        route_mock = Mock()
        route_mock.path = "/pipelines"
        request.scope = {"route": route_mock}

        # Mock user
        user = Mock(spec=User)
        user.oid = str(uuid4())

        # Mock sessionmanager and RbacDataService
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        mock_data_service = AsyncMock()
        mock_data_service.user_has_route_access = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.service.rbac.RbacDataService", lambda session: mock_data_service
        )

        # Should not raise exception
        await RbacService.authorize_request(request, user)

    @pytest.mark.asyncio
    async def test_authorize_request_no_route_in_scope(self):
        """Request without route in scope should not raise exception."""
        # Mock request without route
        request = Mock(spec=Request)
        request.method = "GET"
        request.scope = {}  # No route

        # Mock user
        user = Mock(spec=User)
        user.oid = str(uuid4())

        # Should not raise exception
        await RbacService.authorize_request(request, user)


class TestRbacServiceGetUserOrganizationId:
    """Test RbacService.get_user_organization_id method."""

    @pytest.mark.asyncio
    async def test_get_user_organization_id_success(self, monkeypatch):
        """User successfully retrieves their organization ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_id = uuid4()

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService
        mock_data_service = AsyncMock()
        mock_data_service.get_user_organization_id = AsyncMock(return_value=org_id)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await RbacService.get_user_organization_id(user_id)

        # Verify
        assert result == org_id
        mock_data_service.get_user_organization_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_organization_id_not_associated(self, monkeypatch):
        """User not associated with organization should raise 403."""
        from app.db.utils import sessionmanager

        user_id = uuid4()

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService - returns None (no org)
        mock_data_service = AsyncMock()
        mock_data_service.get_user_organization_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await RbacService.get_user_organization_id(user_id)

        assert exc_info.value.status_code == 403
        assert "not associated with an organization" in exc_info.value.detail


class TestRbacServiceVerifyUserHasRole:
    """Test RbacService.verify_user_has_role method."""

    @pytest.mark.asyncio
    async def test_verify_user_has_role_with_org_id_success(self, monkeypatch):
        """User has role when organization_id is provided."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_id = uuid4()
        role_name = "cfia_admin"

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService
        mock_data_service = AsyncMock()
        mock_data_service.user_has_role = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service - should not raise exception
        await RbacService.verify_user_has_role(user_id, role_name, org_id)

        # Verify role check was called
        mock_data_service.user_has_role.assert_called_once_with(
            user_id, org_id, role_name
        )

    @pytest.mark.asyncio
    async def test_verify_user_has_role_without_org_id_success(self, monkeypatch):
        """User has role when organization_id is looked up."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_id = uuid4()
        role_name = "cfia_admin"

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService
        mock_data_service = AsyncMock()
        mock_data_service.get_user_organization_id = AsyncMock(return_value=org_id)
        mock_data_service.user_has_role = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service without org_id - should not raise exception
        await RbacService.verify_user_has_role(user_id, role_name)

        # Verify both lookup and role check were called
        mock_data_service.get_user_organization_id.assert_called_once_with(user_id)
        mock_data_service.user_has_role.assert_called_once_with(
            user_id, org_id, role_name
        )

    @pytest.mark.asyncio
    async def test_verify_user_has_role_user_lacks_role(self, monkeypatch):
        """User without required role should raise 403."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_id = uuid4()
        role_name = "cfia_admin"

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService - user does NOT have role
        mock_data_service = AsyncMock()
        mock_data_service.user_has_role = AsyncMock(return_value=False)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await RbacService.verify_user_has_role(user_id, role_name, org_id)

        assert exc_info.value.status_code == 403
        assert f"does not have required role: {role_name}" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_user_has_role_no_org_association(self, monkeypatch):
        """User not associated with org when org_id is None should raise 403."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        role_name = "cfia_admin"

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock OrganizationDataService - returns None (no org)
        mock_data_service = AsyncMock()
        mock_data_service.get_user_organization_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.datastore.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await RbacService.verify_user_has_role(user_id, role_name)

        assert exc_info.value.status_code == 403
        assert "not associated with an organization" in exc_info.value.detail


class TestRbacServiceDatabaseDriven:
    """Test database-driven RBAC service."""

    def test_rbac_service_uses_database(self):
        """RbacService should use database for authorization, not hardcoded policies."""
        # Verify ROUTE_POLICIES no longer exists
        assert not hasattr(RbacService, "ROUTE_POLICIES")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
