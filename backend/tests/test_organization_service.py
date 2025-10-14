"""
Tests for OrganizationService - CRUD operations with RBAC authorization.
"""

import os
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from dotenv import load_dotenv
from datetime import datetime

from app.service.organization import OrganizationService
from app.db.model import Organization, RbacRole

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


class TestOrganizationServiceGetAll:
    """Test the get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_as_cfia_admin(self, monkeypatch):
        """cfia_admin users should be able to list all organizations."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org1_id = uuid4()
        org2_id = uuid4()

        # Mock organizations
        org1 = Mock(spec=Organization)
        org1.id = org1_id
        org1.name = "CFIA"
        org1.description = "Canadian Food Inspection Agency"
        org1.folder_prefix = "cfia"
        org1.date_created = datetime.now()
        org1.active = True

        org2 = Mock(spec=Organization)
        org2.id = org2_id
        org2.name = "External Org"
        org2.description = "External Organization"
        org2.folder_prefix = "ext"
        org2.date_created = datetime.now()
        org2.active = True

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=[org1, org2])
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await OrganizationService.get_all(user_id)

        # Verify
        assert "organizations" in result
        assert len(result["organizations"]) == 2
        assert result["organizations"][0]["name"] == "CFIA"
        assert result["organizations"][1]["name"] == "External Org"

    @pytest.mark.asyncio
    async def test_get_all_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()

        # Mock RbacService - user is NOT CFIA admin
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This operation requires CFIA administrator authority",
            )

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_all(user_id)

        assert exc_info.value.status_code == 403


class TestOrganizationServiceGetById:
    """Test the get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """cfia_admin should be able to retrieve organization by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()
        role_id = uuid4()

        # Mock organization with roles
        role = Mock(spec=RbacRole)
        role.id = role_id
        role.name = "cfia_admin"
        role.description = "CFIA Administrator"
        role.active = True

        org = Mock(spec=Organization)
        org.id = org_id
        org.name = "CFIA"
        org.description = "Canadian Food Inspection Agency"
        org.folder_prefix = "cfia"
        org.date_created = datetime.now()
        org.active = True
        org.rbac_roles = [role]

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=org)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await OrganizationService.get_by_id(user_id, org_id)

        # Verify
        assert result["name"] == "CFIA"
        assert "rbac_roles" in result
        assert len(result["rbac_roles"]) == 1
        assert result["rbac_roles"][0]["name"] == "cfia_admin"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if organization not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - organization not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_by_id(user_id, org_id)

        assert exc_info.value.status_code == 404


class TestOrganizationServiceCreate:
    """Test the create method."""

    @pytest.mark.asyncio
    async def test_create_success(self, monkeypatch):
        """cfia_admin should be able to create new organizations with 2 roles."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        new_org_id = uuid4()
        admin_role_id = uuid4()
        user_role_id = uuid4()

        # Mock new organization
        new_org = Mock(spec=Organization)
        new_org.id = new_org_id
        new_org.name = "New Organization"
        new_org.description = "A new organization"
        new_org.folder_prefix = "new"
        new_org.date_created = datetime.now()
        new_org.active = True

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=new_org)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Mock _create_organization_roles
        async def mock_create_roles(session, org_id, org_name):
            return {
                "admin": admin_role_id,
                "user": user_role_id,
            }

        monkeypatch.setattr(
            "app.service.organization.OrganizationService._create_organization_roles",
            mock_create_roles,
        )

        # Call service
        result = await OrganizationService.create(
            user_id,
            name="New Organization",
            description="A new organization",
            folder_prefix="new",
        )

        # Verify
        assert result["name"] == "New Organization"
        assert result["description"] == "A new organization"
        assert result["folder_prefix"] == "new"
        assert "roles" in result
        assert "admin_role_id" in result["roles"]
        assert "user_role_id" in result["roles"]
        assert result["roles"]["admin_role_id"] == str(admin_role_id)
        assert result["roles"]["user_role_id"] == str(user_role_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized(self, monkeypatch):
        """Non-admin users should not be able to create organizations."""
        user_id = uuid4()

        # Mock RbacService - user is NOT CFIA admin, raise 403
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA administrator",
            )

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.create(
                user_id,
                name="New Organization",
                description="A new organization",
            )

        assert exc_info.value.status_code == 403


class TestOrganizationServiceUpdate:
    """Test the update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """cfia_admin should be able to update organizations."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()

        # Mock updated organization
        updated_org = Mock(spec=Organization)
        updated_org.id = org_id
        updated_org.name = "Updated Name"
        updated_org.description = "Updated description"
        updated_org.folder_prefix = "updated"
        updated_org.date_created = datetime.now()
        updated_org.active = True

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=updated_org)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await OrganizationService.update(
            user_id,
            org_id,
            name="Updated Name",
            description="Updated description",
        )

        # Verify
        assert result["name"] == "Updated Name"
        assert result["description"] == "Updated description"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if organization not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - organization not found
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.update(user_id, org_id, name="New Name")

        assert exc_info.value.status_code == 404


class TestOrganizationServiceDelete:
    """Test the delete method (soft delete)."""

    @pytest.mark.asyncio
    async def test_delete_success_soft_delete(self, monkeypatch):
        """cfia_admin should be able to soft delete organizations."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()

        # Mock deleted organization
        deleted_org = Mock(spec=Organization)
        deleted_org.id = org_id
        deleted_org.active = False

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=deleted_org)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await OrganizationService.delete(user_id, org_id)

        # Verify
        assert "message" in result
        assert "soft delete" in result["message"].lower()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if organization not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        org_id = uuid4()

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - organization not found
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.delete(user_id, org_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized(self, monkeypatch):
        """Non-admin users should not be able to delete organizations."""
        user_id = uuid4()
        org_id = uuid4()

        # Mock RbacService - user is NOT CFIA admin, raise 403
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA administrator",
            )

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.delete(user_id, org_id)

        assert exc_info.value.status_code == 403


class TestOrganizationServiceAuthorization:
    """Test authorization invariants."""

    @pytest.mark.asyncio
    async def test_user_without_organization_gets_403(self, monkeypatch):
        """Users not associated with an organization should get 403."""
        user_id = uuid4()

        # Mock RbacService - user is not CFIA admin
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA administrator",
            )

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_all(user_id)

        assert exc_info.value.status_code == 403
        assert "not a CFIA administrator" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
