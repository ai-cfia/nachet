"""
Simplified integration tests for RBAC in DirectoryService CREATE operations.

These tests focus on the key authorization and role assignment behaviors.
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
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
class TestDirectoryCreateRBACSimple:
    """Simplified tests for folder creation authorization and behavior."""

    async def test_create_directory_as_org_user(
        self,
        integration_db_session: AsyncSession,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Any user with organization membership can create folders."""
        # Create user with org
        user_id = uuid4()
        user = Users(
            id=user_id,
            email=f"user_{user_id}@example.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)

        # Add user role
        user_role = RbacUserRole(
            user_id=user_id,
            role_id=test_org_user_role,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user_role)
        await integration_db_session.commit()

        # Create folder
        result = await DirectoryService.create_directory(
            user_id=user_id,
            fullpath="test-folder",
            description="Test folder",
        )

        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        # Verify success
        assert result["id"]
        assert "successfully" in result["message"].lower()

        # Check role assignments
        folder = await integration_db_session.get(Folder, folder_id)
        assert folder is not None
        assert folder.org_user_role_id == test_org_user_role
        assert folder.org_admin_role_id == test_org_admin_role
        assert folder.user_id == user_id

    async def test_create_directory_role_assignments(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Created folders get org roles assigned automatically."""
        result = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="role-test",
            description="Testing role assignments",
        )

        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        folder = await integration_db_session.get(Folder, folder_id)
        assert folder is not None

        # Roles are auto-assigned from creator's org
        assert folder.org_user_role_id == test_org_user_role
        assert folder.org_admin_role_id == test_org_admin_role
        assert folder.user_id == test_admin_user

    async def test_create_directory_org_prefix(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_folders: list,
    ):
        """Organization prefix is automatically prepended."""
        result = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="my/nested/folder",
            description="Testing prefix",
        )

        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        folder = await integration_db_session.get(Folder, folder_id)
        assert folder is not None

        # Prefix includes org but structure varies
        assert folder.folder_prefix.startswith("/test-org/")
        assert folder.name == "folder"  # Just the last part

    async def test_create_directory_duplicates_allowed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Duplicate folder names are allowed during creation."""
        # Create first folder
        result1 = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="duplicate",
            description="First",
        )
        folder1_id = UUID(result1["id"])
        cleanup_test_folders.append(folder1_id)

        # Create second with same name
        result2 = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="duplicate",
            description="Second",
        )
        folder2_id = UUID(result2["id"])
        cleanup_test_folders.append(folder2_id)

        # Both should exist
        folder1 = await integration_db_session.get(Folder, folder1_id)
        folder2 = await integration_db_session.get(Folder, folder2_id)
        assert folder1 is not None
        assert folder2 is not None

        assert folder1.name == folder2.name
        assert folder1.id != folder2.id

    async def test_get_or_create_folder_idempotent(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_folders: list,
    ):
        """get_or_create_folder returns existing folder if found."""
        # First call creates
        result1 = await DirectoryService.get_or_create_folder(
            user_id=test_admin_user,
            normalized_path="idempotent",
            description="First",
        )
        folder1_id = UUID(result1["folder_id"])
        cleanup_test_folders.append(folder1_id)

        # Second call returns same
        result2 = await DirectoryService.get_or_create_folder(
            user_id=test_admin_user,
            normalized_path="idempotent",
            description="Second",
        )
        folder2_id = UUID(result2["folder_id"])

        assert folder1_id == folder2_id

    async def test_create_with_folder_user_id(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """create() method accepts folder_user_id for ownership."""
        # Create owner
        owner_id = uuid4()
        owner = Users(
            id=owner_id,
            email=f"owner_{owner_id}@example.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(owner)
        await integration_db_session.commit()

        # Admin creates for owner
        result = await DirectoryService.create(
            test_admin_user,
            name="delegated",
            folder_prefix="/test-org/delegated/",
            folder_user_id=owner_id,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            description="Created for another user",
        )

        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        folder = await integration_db_session.get(Folder, folder_id)
        assert folder is not None
        assert folder.user_id == owner_id  # Owned by specified user

    async def test_cross_org_isolation(
        self,
        integration_db_session: AsyncSession,
        cleanup_test_folders: list,
    ):
        """Users create folders in their own organization's context."""
        # Create new org
        org2_id = uuid4()
        org2 = Organization(
            id=org2_id,
            name="Org Two",
            description="Second org",
            folder_prefix="org2",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org2)

        # Create roles for org2
        org2_user_role = uuid.uuid5(org2_id, "user")
        org2_admin_role = uuid.uuid5(org2_id, "admin")

        for role_id, name in [(org2_user_role, "user"), (org2_admin_role, "admin")]:
            role = RbacRole(
                id=role_id,
                organization_id=org2_id,
                name=name,
                description=f"{name} role for org2",
                active=True,
                date_created=datetime.now(timezone.utc),
                date_updated=datetime.now(timezone.utc),
            )
            integration_db_session.add(role)

        # Create user in org2
        user2_id = uuid4()
        user2 = Users(
            id=user2_id,
            email=f"user2_{user2_id}@example.com",
            organization=org2_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user2)
        await integration_db_session.commit()

        # User2 creates folder
        result = await DirectoryService.create_directory(
            user_id=user2_id,
            fullpath="org2-folder",
            description="Folder in org2",
        )

        folder_id = UUID(result["id"])
        folder = await integration_db_session.get(Folder, folder_id)
        assert folder is not None

        # Folder is in org2's context
        assert folder.folder_prefix.startswith("/org2/")
        assert folder.org_user_role_id == org2_user_role
        assert folder.org_admin_role_id == org2_admin_role

        # Cleanup
        folder.active = False
        await integration_db_session.commit()
