"""
Integration tests for DirectoryService UPDATE operations - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

UPDATE operations tested (AuthorizedBaseCRUDService):
- Folder creator (user_id matches) OR org_admin_role_id OR CFIA admin
- EXCEPTION: Cannot update a user's default folder if the user is still active

Default Folder Protection for UPDATE:
- Blocks updates to default folders for active users (even for admins)
- Allows updates to default folders for inactive users
- Always allows updates to non-default folders (normal case)

These integration tests cover the authorization edge cases and update-specific
validation (name conflicts, default folder protection) that are difficult
to mock properly due to the complex authorization flow in AuthorizedBaseCRUDService.
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

from app.service.directory import DirectoryService
from app.db.model import Folder
from sqlalchemy.ext.asyncio import AsyncSession

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationUpdate:
    """Integration tests for DirectoryService.update method."""

    async def test_update_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin should be able to update directories."""
        # Create directory first
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Original Directory",
            folder_prefix="/original/",
            description="Original description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update directory
        result = await DirectoryService.update(
            test_admin_user, folder_id, name="Updated Directory"
        )

        # Verify
        assert result["name"] == "Updated Directory"
        assert result["id"] == str(folder_id)

    async def test_update_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should return 404 if directory not found."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update(
                test_admin_user,
                nonexistent_id,
                name="Updated",
            )

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationUpdateFolder:
    """Integration tests for DirectoryService.update_folder method."""

    async def test_update_folder_name_and_description_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should successfully update both name and description."""
        # Create folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="original-name",
            folder_prefix="/cfia/",
            description="Original description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update both
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name="updated-name",
            description="Updated description",
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify database was updated
        await integration_db_session.refresh(directory)
        assert directory.name == "updated-name"
        assert directory.description == "Updated description"

    async def test_update_folder_description_only(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should successfully update description only."""
        # Create folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="original-name",
            folder_prefix="/cfia/",
            description="Original description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update description only
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            description="New description",
        )

        assert result["id"] == str(folder_id)

        # Verify database
        await integration_db_session.refresh(directory)
        assert directory.name == "original-name"  # Unchanged
        assert directory.description == "New description"

    async def test_update_folder_name_conflict_error(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should reject update when new name conflicts with existing folder."""
        # Create first folder
        folder1_id = uuid4()
        folder1 = Folder(
            id=folder1_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="existing-name",
            folder_prefix="/cfia/",
            description="First folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder1)
        cleanup_test_folders.append(folder1_id)

        # Create second folder with different name
        folder2_id = uuid4()
        folder2 = Folder(
            id=folder2_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="original-name",
            folder_prefix="/cfia/",
            description="Second folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder2)
        cleanup_test_folders.append(folder2_id)
        await integration_db_session.commit()

        # Try to rename folder2 to conflict with folder1
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder2_id,
                name="existing-name",
            )

        # Verify error
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

    async def test_update_folder_default_folder_blocked(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block update of a folder that is a user's default folder."""
        from app.db.model import Users

        # Create a folder first
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test-folder",
            folder_prefix="/cfia/",
            description="Test description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Create a user with this folder as default
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="testuser_update@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()

        # Try to update the default folder (should fail with 403)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder_id,
                name="new-name",
                description="New description",
            )

        # Verify error
        assert exc_info.value.status_code == 403
        assert "default folder" in exc_info.value.detail.lower()
        assert "active user" in exc_info.value.detail.lower()

        # Cleanup: remove the test user
        await integration_db_session.delete(user)
        await integration_db_session.commit()

    async def test_update_folder_no_fields_provided_error(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should reject update when neither name nor description is provided."""
        # Create folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="test-folder",
            folder_prefix="/cfia/",
            description="Test description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Try to update with no fields (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder_id,
            )

        # Verify error
        assert exc_info.value.status_code == 400
        assert "at least one field" in exc_info.value.detail.lower()

    async def test_update_folder_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should handle folder not found error."""
        nonexistent_id = uuid4()

        # Should raise 404 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=nonexistent_id,
                name="new-name",
            )

        assert exc_info.value.status_code == 404

    async def test_update_folder_default_folder_for_active_user_blocked(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_user_role: UUID,
        test_org_admin_role: UUID,
    ):
        """Should block updating a folder that is an active user's default folder."""
        from app.db.model import Users

        # Create a regular user with a default folder
        regular_user_id = uuid4()
        folder_id = uuid4()

        regular_user = Users(
            id=regular_user_id,
            email=f"regularuser_{regular_user_id}@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(regular_user)

        # Create the default folder
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="default-folder",
            folder_prefix="/test/",
            description="user's default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        await integration_db_session.commit()

        # Admin tries to update the default folder (should fail because user is active)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder_id,
                name="updated-default",
            )

        assert exc_info.value.status_code == 403
        assert "default folder" in str(exc_info.value.detail).lower()

    async def test_update_folder_default_folder_for_inactive_user_allowed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
    ):
        """Should allow updating a folder that is an inactive user's default folder."""
        from app.db.model import Users

        # Create an inactive user with a default folder
        inactive_user_id = uuid4()
        folder_id = uuid4()

        inactive_user = Users(
            id=inactive_user_id,
            email=f"inactiveuser_{inactive_user_id}@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=False,  # Inactive user
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_user)

        # Create the default folder for inactive user
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="inactive-user-default",
            folder_prefix="/test/",
            description="default folder for inactive user",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        await integration_db_session.commit()

        # Admin should be able to update (user is inactive, so no protection)
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name=f"updated-inactive-{folder_id}",
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify database was updated
        await integration_db_session.refresh(directory)
        assert directory.name == f"updated-inactive-{folder_id}"

    async def test_update_folder_success_as_creator(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin acting as creator should be able to update folders they created."""
        # Create directory as test_admin_user (who is the creator)
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,  # Created by admin user
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="creator-folder",
            folder_prefix="/test/",
            description="Folder created by admin",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update as creator (should succeed)
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name="updated-by-creator",
        )

        # Verify success
        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify database was updated
        await integration_db_session.refresh(directory)
        assert directory.name == "updated-by-creator"

    async def test_update_folder_unauthorized_non_creator_non_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Non-creator, non-admin users should get 403 when updating folders."""
        from app.db.model import Users

        # Create a second user (non-admin, will not be creator)
        second_user_id = uuid4()
        second_user = Users(
            id=second_user_id,
            email="second.user@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(second_user)
        await integration_db_session.commit()

        # Create directory as admin
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,  # Created by admin, not second_user
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="admin-folder",
            folder_prefix="/test/",
            description="Created by admin",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Try to update as second user who didn't create it (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=second_user_id,
                folder_id=folder_id,
                name="unauthorized-update",
            )

        assert exc_info.value.status_code == 403

    async def test_update_folder_non_default_folder_always_allowed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Non-default folders should always be updatable by authorized users."""
        # Create a regular folder (not anyone's default)
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="non-default-folder",
            folder_prefix="/test/",
            description="Regular folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update should succeed (not a default folder)
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name="updated-non-default",
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify database was updated
        await integration_db_session.refresh(directory)
        assert directory.name == "updated-non-default"

    async def test_update_folder_success_as_org_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin (acting as org admin) should be able to update folders in their org."""
        # Create folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="org-folder",
            folder_prefix="/test/",
            description="Org folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update as org admin (should succeed)
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name="updated-by-org-admin",
        )

        assert result["id"] == str(folder_id)
        assert "successfully" in result["message"].lower()

        # Verify database was updated
        await integration_db_session.refresh(directory)
        assert directory.name == "updated-by-org-admin"

    async def test_update_folder_creator_blocked_if_default_for_another_user(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Creator should not be able to update their folder if it's another active user's default."""
        from app.db.model import Users

        # Create another user who will use this folder as default
        other_user_id = uuid4()
        folder_id = uuid4()

        other_user = Users(
            id=other_user_id,
            email=f"otheruser_{other_user_id}@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_user)

        # Create the folder (creator is test_admin_user, but it's other_user's default)
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,  # Created by admin
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="shared-folder",
            folder_prefix="/test/",
            description="Folder that is another user's default",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Creator tries to update the folder (should fail because it's another user's default)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder_id,
                name="updated-shared",
            )

        assert exc_info.value.status_code == 403
        assert "default folder" in str(exc_info.value.detail).lower()
