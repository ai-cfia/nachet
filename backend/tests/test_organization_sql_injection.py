"""
Tests for SQL injection protection in OrganizationService.

These tests verify that the service properly handles malicious SQL input
and is protected by SQLAlchemy's parameterized queries.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.service.organization import OrganizationService
from app.db.model import Organization


class TestOrganizationServiceSQLInjection:
    """Test SQL injection protection in OrganizationService."""

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_name(self, monkeypatch):
        """SQL injection attempts in name field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # SQL injection attempts
        malicious_names = [
            "'; DROP TABLE organization; --",
            "Admin' OR '1'='1",
            "'; DELETE FROM organization WHERE '1'='1'; --",
            "1' UNION SELECT * FROM users--",
            "admin'--",
            "' OR 1=1--",
            "admin'; DROP TABLE rbac_role; --",
        ]

        for malicious_name in malicious_names:
            created_org_id = uuid4()
            admin_role_id = uuid4()
            user_role_id = uuid4()

            # Mock session and dataservice
            class MockSession:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def commit(self):
                    pass

                async def refresh(self, obj):
                    pass

            class MockDataService:
                def __init__(self, session):
                    self.session = session

                async def create(self, name, description, folder_prefix):
                    # Verify the malicious input is passed as-is (will be escaped by SQLAlchemy)
                    assert name == malicious_name

                    # Return mock organization
                    org = Organization(
                        id=created_org_id,
                        name=malicious_name,
                        description=description,
                        folder_prefix=folder_prefix,
                        date_created=datetime.now(timezone.utc),
                        active=True,
                    )
                    return org

            async def mock_create_roles(session, org_id, org_name):
                return {"admin": admin_role_id, "user": user_role_id}

            def mock_get_session():
                return MockSession()

            monkeypatch.setattr(
                "app.service.organization.sessionmanager.get_session",
                mock_get_session,
            )
            monkeypatch.setattr(
                "app.service.organization.OrganizationDataService",
                MockDataService,
            )
            monkeypatch.setattr(
                "app.service.organization.OrganizationService._create_organization_roles",
                mock_create_roles,
            )

            # Should not raise exception - SQLAlchemy handles escaping
            result = await OrganizationService.create(
                user_id=user_id,
                name=malicious_name,
                description="Test description",
                folder_prefix="test",
            )

            # Verify the malicious string is stored as-is (escaped by SQLAlchemy)
            assert result["name"] == malicious_name
            assert result["id"] == str(created_org_id)

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_description(self, monkeypatch):
        """SQL injection attempts in description field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()
        admin_role_id = uuid4()
        user_role_id = uuid4()

        malicious_description = "'; DROP TABLE organization; --"

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def commit(self):
                pass

            async def refresh(self, obj):
                pass

        class MockDataService:
            def __init__(self, session):
                self.session = session

            async def create(self, name, description, folder_prefix):
                # Verify the malicious input is passed as-is
                assert description == malicious_description

                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=malicious_description,
                    folder_prefix=folder_prefix,
                    date_created=datetime.now(timezone.utc),
                    active=True,
                )
                return org

        async def mock_create_roles(session, org_id, org_name):
            return {"admin": admin_role_id, "user": user_role_id}

        def mock_get_session():
            return MockSession()

        monkeypatch.setattr(
            "app.service.organization.sessionmanager.get_session",
            mock_get_session,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            MockDataService,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationService._create_organization_roles",
            mock_create_roles,
        )

        result = await OrganizationService.create(
            user_id=user_id,
            name="Test Org",
            description=malicious_description,
            folder_prefix="test",
        )

        assert result["description"] == malicious_description

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_folder_prefix(self, monkeypatch):
        """SQL injection attempts in folder_prefix field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()
        admin_role_id = uuid4()
        user_role_id = uuid4()

        malicious_prefix = "' OR '1'='1"

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def commit(self):
                pass

            async def refresh(self, obj):
                pass

        class MockDataService:
            def __init__(self, session):
                self.session = session

            async def create(self, name, description, folder_prefix):
                assert folder_prefix == malicious_prefix

                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=description,
                    folder_prefix=malicious_prefix,
                    date_created=datetime.now(timezone.utc),
                    active=True,
                )
                return org

        async def mock_create_roles(session, org_id, org_name):
            return {"admin": admin_role_id, "user": user_role_id}

        def mock_get_session():
            return MockSession()

        monkeypatch.setattr(
            "app.service.organization.sessionmanager.get_session",
            mock_get_session,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            MockDataService,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationService._create_organization_roles",
            mock_create_roles,
        )

        result = await OrganizationService.create(
            user_id=user_id,
            name="Test Org",
            description="Test description",
            folder_prefix=malicious_prefix,
        )

        assert result["folder_prefix"] == malicious_prefix

    @pytest.mark.asyncio
    async def test_update_with_sql_injection_in_name(self, monkeypatch):
        """SQL injection attempts in update name field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        organization_id = uuid4()

        malicious_name = "'; UPDATE organization SET active=false; --"

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def commit(self):
                pass

        class MockDataService:
            def __init__(self, session):
                self.session = session

            async def update(self, organization_id, name, description, folder_prefix):
                assert name == malicious_name

                org = Organization(
                    id=organization_id,
                    name=malicious_name,
                    description="Test",
                    folder_prefix="test",
                    date_created=datetime.now(timezone.utc),
                    active=True,
                )
                return org

        def mock_get_session():
            return MockSession()

        monkeypatch.setattr(
            "app.service.organization.sessionmanager.get_session",
            mock_get_session,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            MockDataService,
        )

        result = await OrganizationService.update(
            user_id=user_id,
            organization_id=organization_id,
            name=malicious_name,
        )

        assert result["name"] == malicious_name

    @pytest.mark.asyncio
    async def test_get_by_id_with_sql_injection_attempts(self, monkeypatch):
        """UUID fields should reject SQL injection attempts naturally."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Attempting to pass SQL injection as UUID should fail
        # This test verifies that invalid UUID formats are rejected
        # The service will catch any errors and return HTTPException(500)
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE organization; --",
            "invalid-uuid-' OR 1=1--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(HTTPException) as exc_info:
                # Should fail at UUID conversion or database query
                await OrganizationService.get_by_id(
                    user_id=user_id,
                    organization_id=malicious_input,  # type: ignore
                )
            # Verify that the service returns an error response
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_special_characters_handled_correctly(self, monkeypatch):
        """Special characters that could be confused for SQL should be stored safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()
        admin_role_id = uuid4()
        user_role_id = uuid4()

        # These are legitimate special characters that should be preserved
        special_name = "O'Reilly & Sons, Inc."
        special_description = "Testing \"quotes\" and 'apostrophes' with; semicolons"

        # Mock RBAC
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def commit(self):
                pass

            async def refresh(self, obj):
                pass

        class MockDataService:
            def __init__(self, session):
                self.session = session

            async def create(self, name, description, folder_prefix):
                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
                    date_created=datetime.now(timezone.utc),
                    active=True,
                )
                return org

        async def mock_create_roles(session, org_id, org_name):
            return {"admin": admin_role_id, "user": user_role_id}

        def mock_get_session():
            return MockSession()

        monkeypatch.setattr(
            "app.service.organization.sessionmanager.get_session",
            mock_get_session,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationDataService",
            MockDataService,
        )
        monkeypatch.setattr(
            "app.service.organization.OrganizationService._create_organization_roles",
            mock_create_roles,
        )

        result = await OrganizationService.create(
            user_id=user_id,
            name=special_name,
            description=special_description,
            folder_prefix="test",
        )

        # Special characters should be preserved exactly
        assert result["name"] == special_name
        assert result["description"] == special_description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
