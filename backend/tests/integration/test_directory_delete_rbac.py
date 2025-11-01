"""
Integration tests for RBAC role-based authorization in DirectoryService DELETE operations.

These tests validate the actual role matching logic that is bypassed by CFIA super admin tests.
They ensure org_user_role_id and org_admin_role_id matching works correctly and provides
proper cross-organization isolation.
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv
import uuid

from app.service.directory import DirectoryService
from app.db.model import Folder, Users, RbacUserRole, RbacRole, Organization
from sqlalchemy.ext.asyncio import AsyncSession

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationDeleteRBACAuthorization:
    """Integration tests for RBAC role-based authorization in DirectoryService.delete method.

    These tests validate the actual role matching logic that is bypassed by CFIA super admin tests.
    They ensure org_user_role_id and org_admin_role_id matching works correctly and provides
    proper cross-organization isolation.
    """

    async def test_delete_success_as_folder_creator(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """User should be able to delete folder they created (even without admin role)."""
        # Create org user with proper RBAC
        org_user_id = uuid4()
        org_user = Users(
            id=org_user_id,
            email=f"orguser_{org_user_id}@example.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(org_user)

        # Assign org user role in RBAC table
        user_role_mapping = RbacUserRole(
            user_id=org_user_id,
            role_id=test_org_user_role,  # Has org user role, not admin
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user_role_mapping)
        await integration_db_session.commit()

        # Create folder AS THE ORG USER (they are the creator)
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=org_user_id,  # CREATED BY THE ORG USER
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="user-created-folder",
            folder_prefix="/user-created/",
            description="Folder created by org user",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Test delete - should SUCCEED because user is the creator
        result = await DirectoryService.delete(
            org_user_id,  # User is the creator
            folder_id,  # Folder created by this user
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify folder was soft deleted (active = False)
        await integration_db_session.refresh(directory)
        assert directory.active is False

    async def test_delete_denied_as_org_user_without_matching_role(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """User with different org_user_role_id should be denied delete access."""
        # Create user with DIFFERENT org's user role
        wrong_org_user_id = uuid4()
        wrong_org_user = Users(
            id=wrong_org_user_id,
            email=f"wronguser_{wrong_org_user_id}@example.com",
            organization=test_organization,  # Same org
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(wrong_org_user)

        # Create a DIFFERENT organization first
        different_org_id = uuid4()
        different_org = Organization(
            id=different_org_id,
            name="Different Organization Delete",
            description="Different test organization for role mismatch in delete",
            folder_prefix="diff-org-del",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(different_org)

        # Create a DIFFERENT org's user role for this test
        different_org_user_role = uuid.uuid5(different_org_id, "user")

        # Create the role in RBAC
        different_role = RbacRole(
            id=different_org_user_role,
            organization_id=different_org_id,
            name="user",
            description="User role for different org",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(different_role)

        # Assign WRONG role to user
        wrong_user_role_mapping = RbacUserRole(
            user_id=wrong_org_user_id,
            role_id=different_org_user_role,  # MISMATCH!
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(wrong_user_role_mapping)
        await integration_db_session.commit()

        # Create folder with original org's user role
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,  # Different from user's role!
            org_admin_role_id=test_org_admin_role,
            name="test-folder-mismatch",
            folder_prefix="/test-mismatch/",
            description="Test folder with role mismatch",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Test delete - should FAIL 403 because roles don't match
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(
                wrong_org_user_id,  # Has different_org_user_role
                folder_id,  # Has test_org_user_role
            )
        assert exc_info.value.status_code == 403

    async def test_delete_success_as_org_admin_with_matching_role(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """User with matching org_admin_role_id should successfully delete folder."""
        # Create org admin user with proper RBAC
        org_admin_id = uuid4()
        org_admin = Users(
            id=org_admin_id,
            email=f"orgadmin_{org_admin_id}@example.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(org_admin)

        # Assign org admin role in RBAC table
        admin_role_mapping = RbacUserRole(
            user_id=org_admin_id,
            role_id=test_org_admin_role,  # Match folder's org_admin_role_id
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(admin_role_mapping)
        await integration_db_session.commit()

        # Create folder with matching org_admin_role_id
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,  # Creator can be anyone
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,  # MUST MATCH user's assigned role
            name="admin-delete-folder",
            folder_prefix="/admin-delete/",
            description="Admin test folder for delete",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Test delete - should SUCCEED because admin roles match
        result = await DirectoryService.delete(
            org_admin_id,  # User has org_admin_role_id
            folder_id,  # Folder has matching org_admin_role_id
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify folder was soft deleted (active = False)
        await integration_db_session.refresh(directory)
        assert directory.active is False

    async def test_delete_denied_as_org_admin_without_matching_role(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Admin with different org_admin_role_id should be denied delete access."""
        # Create admin user with DIFFERENT org's admin role
        wrong_admin_id = uuid4()
        wrong_admin = Users(
            id=wrong_admin_id,
            email=f"wrongadmin_{wrong_admin_id}@example.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(wrong_admin)

        # Create a DIFFERENT organization first
        different_org_id = uuid4()
        different_org = Organization(
            id=different_org_id,
            name="Different Admin Org Delete",
            description="Different test organization for admin role mismatch in delete",
            folder_prefix="diff-admin-del",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(different_org)

        # Create a DIFFERENT org's admin role for this test
        different_org_admin_role = uuid.uuid5(different_org_id, "admin")

        # Create the role in RBAC
        different_admin_role = RbacRole(
            id=different_org_admin_role,
            organization_id=different_org_id,
            name="admin",
            description="Admin role for different org",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(different_admin_role)

        # Assign WRONG admin role to user
        wrong_admin_role_mapping = RbacUserRole(
            user_id=wrong_admin_id,
            role_id=different_org_admin_role,  # MISMATCH!
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(wrong_admin_role_mapping)
        await integration_db_session.commit()

        # Create folder with original org's admin role
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,  # Different from user's role!
            name="admin-mismatch-folder",
            folder_prefix="/admin-mismatch/",
            description="Admin test folder with role mismatch",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Test delete - should FAIL 403 because admin roles don't match
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(
                wrong_admin_id,  # Has different_org_admin_role
                folder_id,  # Has test_org_admin_role
            )
        assert exc_info.value.status_code == 403

    async def test_delete_denied_cross_organization(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """User from different organization should be denied delete access even with proper role in their org."""
        # Create second organization
        other_org_id = uuid4()
        other_org = Organization(
            id=other_org_id,
            name="Other Organization for Delete",
            description="Second test organization for delete tests",
            folder_prefix="other-org-del",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_org)

        # Create roles for second org (using uuid5 pattern like seed data)
        other_org_user_role_id = uuid.uuid5(other_org_id, "user")
        other_org_admin_role_id = uuid.uuid5(other_org_id, "admin")

        other_org_user_role = RbacRole(
            id=other_org_user_role_id,
            organization_id=other_org_id,
            name="user",
            description="User role for other org (delete)",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_org_user_role)

        other_org_admin_role = RbacRole(
            id=other_org_admin_role_id,
            organization_id=other_org_id,
            name="admin",
            description="Admin role for other org (delete)",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_org_admin_role)

        # Create user in other org with proper RBAC
        other_org_user_id = uuid4()
        other_org_user = Users(
            id=other_org_user_id,
            email=f"otherorguser_{other_org_user_id}@example.com",
            organization=other_org_id,  # Different organization!
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_org_user)

        # Assign proper role in other org
        other_user_role_mapping = RbacUserRole(
            user_id=other_org_user_id,
            role_id=other_org_user_role_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_user_role_mapping)
        await integration_db_session.commit()

        # Create folder in FIRST org
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,  # First org's role
            org_admin_role_id=test_org_admin_role,
            name="first-org-delete-folder",
            folder_prefix="/test-cross-org/",
            description="Folder in first org for cross-org delete test",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Test delete - should FAIL 403 (user from other org)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(
                other_org_user_id,  # From other_org
                folder_id,  # In test_organization
            )
        assert exc_info.value.status_code == 403
