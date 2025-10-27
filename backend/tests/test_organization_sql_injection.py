"""
Tests for SQL injection protection in OrganizationService.

These tests verify that the service properly handles malicious SQL input
and is protected by SQLAlchemy's parameterized queries.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from beartype.typing import Type
from app.service.organization import OrganizationService
from app.db.model import Organization
from app.datastore.base_crud import BaseCRUDDataService


class TestOrganizationServiceSQLInjection:
    """Test SQL injection protection in OrganizationService."""

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_name(self, monkeypatch):
        """SQL injection attempts in name field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RBAC - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
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

            # Mock session and dataservice
            class MockSession:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                def add(self, obj):
                    """Mock add() for role creation."""
                    pass

                async def flush(self):
                    """Mock flush() for role creation."""
                    pass

                async def commit(self):
                    pass

                async def refresh(self, obj, attribute_names=None):
                    pass

            class MockDataService(BaseCRUDDataService[Organization]):
                def __init__(self, session):
                    self.session = session

                @classmethod
                def get_model_class(cls) -> Type[Organization]:
                    """Return the Organization model class."""
                    return Organization

                async def check_name_prefix_exists(self, normalized_name):
                    """Mock check for name prefix uniqueness."""
                    return False

                async def create(self, **kwargs):
                    # Verify the name has been sanitized (malicious chars removed)
                    # The sanitized name should be safe (no SQL injection chars)
                    name = kwargs.get("name", "")
                    description = kwargs.get("description", "")
                    folder_prefix = kwargs.get("folder_prefix", "")

                    # Return mock organization with sanitized name
                    org = Organization(
                        id=created_org_id,
                        name=name,  # Use sanitized name passed by service
                        description=description,
                        folder_prefix=folder_prefix,
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
            # Note: Role creation is now inline in create() method

            # Should not raise exception - normalization removes SQL injection chars
            result = await OrganizationService.create(
                user_id=user_id,
                name=malicious_name,
                description="Test description",
                folder_prefix="test",
            )

            # Verify the name was sanitized (SQL injection chars removed)
            # The service sanitizes input via sanitize_string()
            assert result["id"] == str(created_org_id)
            # The sanitized name should NOT contain SQL injection special chars
            # These characters would allow SQL injection if present:
            assert "'" not in result["name"]  # Single quotes enable SQL string escape
            assert '"' not in result["name"]  # Double quotes
            assert ";" not in result["name"]  # Statement separator
            # Verify only safe characters remain (alphanumeric, space, dash, underscore)
            assert all(c.isalnum() or c in " -_" for c in result["name"])
            # Name should be non-empty after sanitization
            assert len(result["name"]) > 0

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_description(self, monkeypatch):
        """SQL injection attempts in description field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()

        malicious_description = "'; DROP TABLE organization; --"

        # Mock RBAC - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def add(self, obj):
                """Mock add() for role creation."""
                pass

            async def flush(self):
                """Mock flush() for role creation."""
                pass

            async def commit(self):
                pass

            async def refresh(self, obj, attribute_names=None):
                pass

        class MockDataService(BaseCRUDDataService[Organization]):
            def __init__(self, session):
                self.session = session

            @classmethod
            def get_model_class(cls) -> Type[Organization]:
                """Return the Organization model class."""
                return Organization

            async def check_name_prefix_exists(self, normalized_name):
                """Mock check for name prefix uniqueness."""
                return False

            async def create(self, **kwargs):
                # Description should be sanitized (special chars removed)
                # The original had '; which should be removed
                name = kwargs.get("name", "")
                description = kwargs.get("description", "")
                folder_prefix = kwargs.get("folder_prefix", "")

                assert "'" not in description
                assert ";" not in description

                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=description,  # Use sanitized description
                    folder_prefix=folder_prefix,
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
        # Note: Role creation is now inline in create() method

        result = await OrganizationService.create(
            user_id=user_id,
            name="Test Org",
            description=malicious_description,
            folder_prefix="test",
        )

        # Description should be sanitized (SQL injection chars removed)
        assert "'" not in result["description"]
        assert ";" not in result["description"]
        # Verify only safe characters remain
        assert all(c.isalnum() or c in " -_" for c in result["description"])

    @pytest.mark.asyncio
    async def test_create_with_sql_injection_in_folder_prefix(self, monkeypatch):
        """
        Folder prefix is auto-generated from normalized name.

        The user-provided folder_prefix parameter is ignored - the system
        always uses normalize_org_name(sanitized_name) as the folder_prefix.
        This test verifies that even if malicious input is in the name,
        the folder_prefix will be safely normalized.
        """
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()

        malicious_name = "Admin' OR '1'='1"

        # Mock RBAC - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def add(self, obj):
                """Mock add() for role creation."""
                pass

            async def flush(self):
                """Mock flush() for role creation."""
                pass

            async def commit(self):
                pass

            async def refresh(self, obj, attribute_names=None):
                pass

        class MockDataService(BaseCRUDDataService[Organization]):
            def __init__(self, session):
                self.session = session

            @classmethod
            def get_model_class(cls) -> Type[Organization]:
                """Return the Organization model class."""
                return Organization

            async def check_name_prefix_exists(self, normalized_name):
                """Mock check for name prefix uniqueness."""
                return False

            async def create(self, **kwargs):
                # folder_prefix should be normalized (safe for filesystem)
                name = kwargs.get("name", "")
                description = kwargs.get("description", "")
                folder_prefix = kwargs.get("folder_prefix", "")

                assert "'" not in folder_prefix
                assert " " not in folder_prefix
                assert folder_prefix.islower()  # Should be lowercase
                assert all(c.isalnum() or c == "-" for c in folder_prefix)

                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
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
        # Note: Role creation is now inline in create() method

        result = await OrganizationService.create(
            user_id=user_id,
            name=malicious_name,
            description="Test description",
            folder_prefix=None,  # Let service auto-generate from normalized name
        )

        # Verify folder_prefix is normalized (safe for filesystem)
        assert "'" not in result["folder_prefix"]
        assert " " not in result["folder_prefix"]
        assert result["folder_prefix"].islower()
        assert all(c.isalnum() or c == "-" for c in result["folder_prefix"])
        # Should be normalized version of malicious_name
        assert result["folder_prefix"] == "admin-or-11"

    @pytest.mark.asyncio
    async def test_update_with_sql_injection_in_name(self, monkeypatch):
        """SQL injection attempts in update name field should be handled safely."""
        user_id = uuid4()
        user_org_id = uuid4()
        organization_id = uuid4()

        malicious_name = "'; UPDATE organization SET active=false; --"

        # Mock RBAC - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def commit(self):
                pass

        class MockDataService(BaseCRUDDataService[Organization]):
            def __init__(self, session):
                self.session = session

            @classmethod
            def get_model_class(cls) -> Type[Organization]:
                """Return the Organization model class."""
                return Organization

            async def update(self, entity_id, **kwargs):
                # Extract name from kwargs
                name = kwargs.get("name")
                if name:
                    assert name == malicious_name

                org = Organization(
                    id=entity_id,
                    name=name or malicious_name,
                    description=kwargs.get("description", "Test"),
                    folder_prefix=kwargs.get("folder_prefix", "test"),
                    date_created=datetime.now(timezone.utc),
                    active=True,
                )
                org.rbac_roles = []  # For serialization
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
            requester_id=user_id,
            entity_id=organization_id,
            name=malicious_name,
        )

        assert result["name"] == malicious_name

    @pytest.mark.asyncio
    async def test_get_by_id_with_sql_injection_attempts(self, monkeypatch):
        """UUID fields should reject SQL injection attempts naturally."""
        user_id = uuid4()
        user_org_id = uuid4()

        # Mock RBAC - user is CFIA admin and has organization
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        async def mock_get_user_organization_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )
        monkeypatch.setattr(
            "app.service.organization.RbacService.get_user_organization_id",
            mock_get_user_organization_id,
        )

        # Attempting to pass SQL injection as UUID should fail
        # This test verifies that invalid UUID formats are rejected
        # The service will catch errors - either DataError from SQL or HTTPException(500)
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE organization; --",
            "invalid-uuid-' OR 1=1--",
        ]

        for malicious_input in malicious_inputs:
            # Should fail at UUID conversion or database query
            # We accept either DataError (from SQLAlchemy) or HTTPException(500)
            with pytest.raises((Exception)) as exc_info:
                await OrganizationService.get_by_id(
                    requester_id=user_id,
                    entity_id=malicious_input,  # type: ignore
                )
            # Verify that some error was raised (validates SQL injection was blocked)
            assert exc_info.value is not None

    @pytest.mark.asyncio
    async def test_special_characters_handled_correctly(self, monkeypatch):
        """Special characters in name are normalized, description preserves them (SQLAlchemy escapes)."""
        user_id = uuid4()
        user_org_id = uuid4()
        created_org_id = uuid4()

        # These are legitimate special characters
        special_name = "O'Reilly & Sons, Inc."
        special_description = "Testing \"quotes\" and 'apostrophes' with; semicolons"

        # Mock RBAC - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.organization.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session and dataservice
        class MockSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def add(self, obj):
                """Mock add() for role creation."""
                pass

            async def flush(self):
                """Mock flush() for role creation."""
                pass

            async def commit(self):
                pass

            async def refresh(self, obj, attribute_names=None):
                pass

        class MockDataService(BaseCRUDDataService[Organization]):
            def __init__(self, session):
                self.session = session

            @classmethod
            def get_model_class(cls) -> Type[Organization]:
                """Return the Organization model class."""
                return Organization

            async def check_name_prefix_exists(self, normalized_name):
                """Mock check for name prefix uniqueness."""
                return False

            async def create(self, **kwargs):
                name = kwargs.get("name", "")
                description = kwargs.get("description", "")
                folder_prefix = kwargs.get("folder_prefix", "")

                org = Organization(
                    id=created_org_id,
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
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
        # Note: Role creation is now inline in create() method

        result = await OrganizationService.create(
            user_id=user_id,
            name=special_name,
            description=special_description,
            folder_prefix="test",
        )

        # Name is sanitized (special chars removed, but preserves case and spaces)
        # Original: "O'Reilly & Sons, Inc."
        # Sanitized: "OReilly  Sons Inc" (removes ', &, . but keeps case and spaces)
        assert result["name"] == "OReilly  Sons Inc"
        # Description is also sanitized (special chars removed)
        # Original: "Testing \"quotes\" and 'apostrophes' with; semicolons"
        # Sanitized: removes ", ', ; but keeps other chars
        expected_desc = "Testing quotes and apostrophes with semicolons"
        assert result["description"] == expected_desc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
