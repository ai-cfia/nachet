"""
Integration tests for DirectoryService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested (AuthorizedBaseCRUDService):
- GET operations (get_all, get_by_id):
  Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
- UPDATE operations:
  Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
  EXCEPTION: Cannot update a user's default folder if the user is still active
- DELETE operations:
  Folder creator (user_id matches) OR org_admin_role_id OR CFIA admin
  EXCEPTION: Cannot delete a user's default folder if the user is still active
- CREATE operations: Any user belonging to an organization

Default Folder Protection (UPDATE and DELETE operations):
- Blocks updates to default folders for active users (even for admins)
- Blocks deletion of default folders for active users (even for admins and creators)
- Allows updates/deletion of default folders for inactive users
- Always allows updates/deletion of non-default folders (normal case)
- Users can delete folders they created (unless it's a default folder for an active user)

These integration tests cover the authorization edge cases that are difficult
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
class TestDirectoryServiceIntegrationCreate:
    """Integration tests for DirectoryService.create method."""

    async def test_create_success_as_cfia_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin should be able to create new directories."""
        # Call service using create_directory which handles user_id correctly
        result = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="test/directory",
            description="New test directory",
        )

        # Track for cleanup
        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        # Verify response
        assert "id" in result
        assert "message" in result
        assert "created successfully" in result["message"]

    async def test_create_unauthorized_user_without_org(
        self,
        test_regular_user: UUID,
    ):
        """Users without organization membership should get 403."""
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create_directory(
                user_id=test_regular_user,
                fullpath="test/unauthorized",
                description="Should fail",
            )

        assert exc_info.value.status_code == 403


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
class TestDirectoryServiceIntegrationDelete:
    """Integration tests for DirectoryService.delete method."""

    async def test_delete_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin should be able to soft delete directories."""
        # Create directory first
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory",
            folder_prefix="/",
            description="Test",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Delete directory
        result = await DirectoryService.delete(test_admin_user, folder_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]

    async def test_delete_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should return 404 if directory not found."""
        nonexistent_id = uuid4()

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_delete_unauthorized_non_creator_non_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Non-admin users should get 403 when deleting folders they didn't create."""
        from app.db.model import Users

        # Create a second user (non-admin)
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

        # Create directory as admin first
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,  # Created by admin
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory",
            folder_prefix="/",
            description="Test",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Try to delete as second user who didn't create it (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(second_user_id, folder_id)

        assert exc_info.value.status_code == 403
        assert "folder creator" in exc_info.value.detail.lower()

        # Note: No need to cleanup second_user - it doesn't interfere with other tests
        # and will be cleaned up at session end

    async def test_delete_success_as_creator(
        self,
        integration_db_session: AsyncSession,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Users should be able to delete folders they created."""
        from app.db.model import Users

        # Create a regular user
        creator_user_id = uuid4()
        creator_user = Users(
            id=creator_user_id,
            email="creator.user@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(creator_user)
        await integration_db_session.commit()

        # Create directory as creator user
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=creator_user_id,  # Created by creator user
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory",
            folder_prefix="/test/",
            description="Test folder created by user",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Delete as creator (should succeed)
        result = await DirectoryService.delete(creator_user_id, folder_id)

        # Verify success
        assert result["message"]
        assert "successfully" in result["message"].lower()
        assert result["id"] == str(folder_id)

        # Note: No need to cleanup creator_user - it doesn't interfere with other tests
        # and will be cleaned up at session end

    async def test_delete_default_folder_for_active_user_blocked(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block deletion of default folder if user is active (even for admin)."""
        from app.db.model import Users

        # Create a test user with a default folder
        user_id = uuid4()
        folder_id = uuid4()

        # Create the folder first
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Default Folder",
            folder_prefix="/cfia/",
            description="User's default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create a user with this folder as default
        user = Users(
            id=user_id,
            email="testuser@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()

        # Try to delete the default folder (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_admin_user, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "default folder" in str(exc_info.value.detail).lower()
        assert "active user" in str(exc_info.value.detail).lower()

        # Cleanup: remove the test user
        await integration_db_session.delete(user)
        await integration_db_session.commit()

    async def test_delete_default_folder_for_inactive_user_allowed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should allow deletion of default folder if user is inactive."""
        from app.db.model import Users

        # Create a test user (inactive) with a default folder
        user_id = uuid4()
        folder_id = uuid4()

        # Create the folder first
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Default Folder",
            folder_prefix="/cfia/",
            description="Inactive user's default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create an INACTIVE user with this folder as default
        user = Users(
            id=user_id,
            email="inactiveuser@example.com",
            organization=test_organization,
            default_folder_id=folder_id,
            active=False,  # User is deactivated
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()

        # Try to delete the default folder (should succeed since user is inactive)
        result = await DirectoryService.delete(test_admin_user, folder_id)

        # Verify success
        assert "message" in result
        assert "deleted successfully" in result["message"]

        # Cleanup: remove the test user
        await integration_db_session.delete(user)
        await integration_db_session.commit()

    async def test_delete_non_default_folder_always_allowed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should allow deletion of non-default folders (normal case)."""
        from app.db.model import Users

        # Create a test user with a different default folder
        user_id = uuid4()
        default_folder_id = uuid4()
        other_folder_id = uuid4()

        # Create default folder
        default_folder = Folder(
            id=default_folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Default Folder",
            folder_prefix="/cfia/",
            description="User's default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(default_folder)
        cleanup_test_folders.append(default_folder_id)

        # Create another folder (not default)
        other_folder = Folder(
            id=other_folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Other Folder",
            folder_prefix="/cfia/",
            description="Some other folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(other_folder)
        cleanup_test_folders.append(other_folder_id)

        # Create a user with default_folder_id set to the first folder
        user = Users(
            id=user_id,
            email="testuser2@example.com",
            organization=test_organization,
            default_folder_id=default_folder_id,  # NOT other_folder_id
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()

        # Try to delete the OTHER folder (not the default) - should succeed
        result = await DirectoryService.delete(test_admin_user, other_folder_id)

        # Verify success
        assert "message" in result
        assert "deleted successfully" in result["message"]

        # Cleanup: remove the test user
        await integration_db_session.delete(user)
        await integration_db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationCreateDirectory:
    """Integration tests for DirectoryService.create_directory custom method."""

    async def test_create_directory_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """CFIA admin should be able to create directory with fullpath validation."""
        # Call service with fullpath
        result = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="org/team/project",
            description="Test project",
        )

        # Track for cleanup
        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        # Verify
        assert "id" in result
        assert "message" in result
        assert "created successfully" in result["message"]
        assert "org/team/project" in result["message"]

    async def test_create_directory_valid_path_with_allowed_chars(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should accept paths with allowed characters (alphanumeric, dash, underscore, period)."""
        # Test with valid characters: alphanumeric, dash, underscore, period
        result = await DirectoryService.create_directory(
            user_id=test_admin_user,
            fullpath="org/my_project-v1.0",  # Valid: ends with alphanumeric
            description="",
        )

        # Track for cleanup
        folder_id = UUID(result["id"])
        cleanup_test_folders.append(folder_id)

        # Verify
        assert "id" in result

    async def test_create_directory_invalid_path_with_leading_slash(
        self,
        test_admin_user: UUID,
    ):
        """Should reject paths that start with / (users should provide relative paths)."""
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create_directory(
                user_id=test_admin_user,
                fullpath="/org/team/project",  # Has leading / (causes //)
                description="Test",
            )

        assert exc_info.value.status_code == 400
        assert "consecutive slashes" in exc_info.value.detail

    async def test_create_directory_invalid_path_trailing_slash(
        self,
        test_admin_user: UUID,
    ):
        """Should reject paths that end with /."""
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create_directory(
                user_id=test_admin_user,
                fullpath="org/team/",  # Ends with /
                description="Test",
            )

        assert exc_info.value.status_code == 400
        assert "must end with an alphanumeric character" in exc_info.value.detail

    async def test_create_directory_invalid_path_consecutive_slashes(
        self,
        test_admin_user: UUID,
    ):
        """Should reject paths with consecutive slashes."""
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create_directory(
                user_id=test_admin_user,
                fullpath="org//team/project",  # Consecutive slashes
                description="Test",
            )

        assert exc_info.value.status_code == 400
        assert "cannot contain consecutive slashes" in exc_info.value.detail

    async def test_create_directory_invalid_path_special_chars(
        self,
        test_admin_user: UUID,
    ):
        """Should reject paths with invalid characters."""
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create_directory(
                user_id=test_admin_user,
                fullpath="org/team$/project",  # Invalid char: $
                description="Test",
            )

        assert exc_info.value.status_code == 400
        assert "can only contain alphanumeric" in exc_info.value.detail


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationGetAll:
    """Integration tests for DirectoryService.get_all method."""

    async def test_get_all_success_authenticated_user(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Users with proper role access should be able to list directories."""
        # Create test directories
        folder1_id = uuid4()
        folder2_id = uuid4()

        folder1 = Folder(
            id=folder1_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory 1",
            folder_prefix="test-dir-1",
            description="Test directory 1",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        folder2 = Folder(
            id=folder2_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory 2",
            folder_prefix="test-dir-2",
            description="Test directory 2",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder1)
        integration_db_session.add(folder2)
        cleanup_test_folders.extend([folder1_id, folder2_id])
        await integration_db_session.commit()

        # Call service
        result = await DirectoryService.get_all(test_admin_user)

        # Verify
        assert "items" in result
        assert len(result["items"]) >= 2
        folder_names = [d["name"] for d in result["items"]]
        assert "Test Directory 1" in folder_names
        assert "Test Directory 2" in folder_names
        assert result["total"] >= 2


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationGetById:
    """Integration tests for DirectoryService.get_by_id method."""

    async def test_get_by_id_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Users with proper role access should be able to retrieve a directory by ID."""
        # Create test directory
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Directory",
            folder_prefix="test-dir",
            description="Test directory",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Call service
        result = await DirectoryService.get_by_id(test_admin_user, folder_id)

        # Verify
        assert result["name"] == "Test Directory"
        assert result["id"] == str(folder_id)

    async def test_get_by_id_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should return 404 if directory not found."""
        nonexistent_id = uuid4()

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.get_by_id(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationGetUserDirectories:
    """Integration tests for DirectoryService.get_user_directories custom method."""

    async def test_get_user_directories_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should retrieve directories with picture counts for user."""
        # Create test directories
        folder1_id = uuid4()
        folder2_id = uuid4()

        folder1 = Folder(
            id=folder1_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="User Directory 1",
            folder_prefix="user-dir-1",
            description="User directory 1",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        folder2 = Folder(
            id=folder2_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="User Directory 2",
            folder_prefix="user-dir-2",
            description="User directory 2",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder1)
        integration_db_session.add(folder2)
        cleanup_test_folders.extend([folder1_id, folder2_id])
        await integration_db_session.commit()

        # Call service
        result = await DirectoryService.get_user_directories(test_admin_user)

        # Verify
        assert "directories" in result
        assert len(result["directories"]) >= 2
        folder_names = [d["name"] for d in result["directories"]]
        assert "User Directory 1" in folder_names
        assert "User Directory 2" in folder_names


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationGetOrgDirectories:
    """Integration tests for DirectoryService.get_org_directories custom method."""

    async def test_get_org_directories_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should retrieve all directories for a user's organization with picture counts."""
        # Create directories for the organization
        folder1_id = uuid4()
        folder2_id = uuid4()

        folder1 = Folder(
            id=folder1_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Org Directory 1",
            folder_prefix="/org/",
            description="Organization directory 1",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        folder2 = Folder(
            id=folder2_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Org Directory 2",
            folder_prefix="/org/",
            description="Organization directory 2",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder1)
        integration_db_session.add(folder2)
        cleanup_test_folders.extend([folder1_id, folder2_id])
        await integration_db_session.commit()

        # Call service
        result = await DirectoryService.get_org_directories(test_admin_user)

        # Verify
        assert "directories" in result
        assert len(result["directories"]) >= 2  # At least the two we created
        folder_names = [d["name"] for d in result["directories"]]
        assert "Org Directory 1" in folder_names
        assert "Org Directory 2" in folder_names


@pytest.mark.integration
@pytest.mark.asyncio
class TestDirectoryServiceIntegrationRenameDirectory:
    """Integration tests for DirectoryService.rename_directory custom method."""

    async def test_rename_directory_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Users with proper role access should be able to rename directory with fullpath validation."""
        # Create directory first
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="project",
            folder_prefix="/org/team/",
            description="Test directory",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Call service with fullpath
        result = await DirectoryService.rename_directory(
            user_id=test_admin_user,
            directory_id=folder_id,
            fullpath="org/team/renamed_project",
        )

        # Verify
        assert "id" in result
        assert "message" in result
        assert "renamed" in result["message"].lower()
        assert "org/team/renamed_project" in result["message"]

    async def test_rename_directory_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should handle directory not found error."""
        nonexistent_id = uuid4()

        # Should raise 404 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.rename_directory(
                user_id=test_admin_user,
                directory_id=nonexistent_id,
                fullpath="org/renamed_project",
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
        """Should successfully update both folder name and description."""
        # Create folder first
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

        # Update folder name and description
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            name="updated-name",
            description="Updated description text",
        )

        # Verify response
        assert result["id"] == str(folder_id)
        assert result["message"] == "Folder updated successfully"

        # Verify database changes
        updated_folder = await DirectoryService.get_by_id(test_admin_user, folder_id)
        assert updated_folder["name"] == "updated-name"
        assert updated_folder["description"] == "Updated description text"
        assert updated_folder["folder_prefix"] == "/cfia/"  # Prefix unchanged

    async def test_update_folder_description_only(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should successfully update only description, leaving name unchanged."""
        # Create folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="folder-name",
            folder_prefix="/cfia/",
            description="Original description",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Update only description
        result = await DirectoryService.update_folder(
            user_id=test_admin_user,
            folder_id=folder_id,
            description="New description only",
        )

        # Verify
        assert result["id"] == str(folder_id)
        updated_folder = await DirectoryService.get_by_id(test_admin_user, folder_id)
        assert updated_folder["name"] == "folder-name"  # Name unchanged
        assert updated_folder["description"] == "New description only"

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
        # Create two folders with different names
        folder1_id = uuid4()
        folder1 = Folder(
            id=folder1_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="existing-folder",
            folder_prefix="/cfia/",
            description="First folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        folder2_id = uuid4()
        folder2 = Folder(
            id=folder2_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="folder-to-rename",
            folder_prefix="/cfia/",
            description="Second folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(folder1)
        integration_db_session.add(folder2)
        cleanup_test_folders.extend([folder1_id, folder2_id])
        await integration_db_session.commit()

        # Try to rename folder2 to folder1's name (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update_folder(
                user_id=test_admin_user,
                folder_id=folder2_id,
                name="existing-folder",
            )

        # Verify error
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    async def test_update_folder_default_folder_blocked(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block updates to default folders for active users."""
        from app.db.model import Users

        # Create a test user with a default folder
        user_id = uuid4()
        folder_id = uuid4()

        # Create the folder first
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="default-folder",
            folder_prefix="/cfia/",
            description="Default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create a user with this folder as default
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
