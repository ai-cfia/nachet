"""
Integration tests for DirectoryService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested (AuthorizedBaseCRUDService):
- GET operations (get_all, get_by_id):
  Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
- UPDATE operations:
  Users with folder's org_user_role_id OR org_admin_role_id OR CFIA admin
- DELETE operations:
  Users with folder's org_admin_role_id OR CFIA admin (admin-only)
- CREATE operations: CFIA admin only

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

    async def test_create_unauthorized_non_admin(
        self,
        test_regular_user: UUID,
    ):
        """Non-admin users should get 403."""
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

    async def test_delete_unauthorized_non_admin(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Non-admin users should get 403 when deleting."""
        # Create directory as admin first
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

        # Try to delete as non-admin user (should fail)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_regular_user, folder_id)

        assert exc_info.value.status_code == 403


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
