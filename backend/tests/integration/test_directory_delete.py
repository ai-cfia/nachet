"""
Integration tests for DirectoryService DELETE operations - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

DELETE operations tested (AuthorizedBaseCRUDService):
- Folder creator (user_id matches) OR org_admin_role_id OR CFIA admin
- EXCEPTION: Cannot delete a user's default folder if the user is still active
- EXCEPTION: Cannot delete a folder containing active pictures

Default Folder Protection for DELETE:
- Blocks deletion of default folders for active users (even for admins and creators)
- Allows deletion of default folders for inactive users
- Always allows deletion of non-default folders (normal case)
- Users can delete folders they created (unless constraints prevent it)

Active Pictures Protection for DELETE:
- Blocks deletion of folders containing one or more active pictures
- Allows deletion of folders with no pictures
- Allows deletion of folders containing only inactive (soft-deleted) pictures
- Blocks deletion if folder has at least one active picture (even among inactive ones)

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

    async def test_delete_success_as_org_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Organization admin should be able to delete folders in their org (not created by them)."""
        from app.db.model import Users

        # Create a regular user (folder creator)
        creator_user_id = uuid4()
        creator_user = Users(
            id=creator_user_id,
            email="folder.creator@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(creator_user)
        await integration_db_session.commit()

        # Create directory as regular user
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=creator_user_id,  # Created by regular user
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="User Created Folder",
            folder_prefix="/test/",
            description="Folder created by regular user",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Delete as org admin (test_admin_user has org_admin_role)
        # Admin should be able to delete even though they didn't create it
        result = await DirectoryService.delete(test_admin_user, folder_id)

        # Verify success
        assert result["message"]
        assert "successfully" in result["message"].lower()
        assert result["id"] == str(folder_id)

    async def test_delete_creator_blocked_if_default_for_another_user(
        self,
        integration_db_session: AsyncSession,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Creator should NOT be able to delete their folder if it's another user's default."""
        from app.db.model import Users

        # Create user1 (folder creator)
        user1_id = uuid4()
        user1 = Users(
            id=user1_id,
            email="user1.creator@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user1)
        await integration_db_session.commit()

        # User1 creates a folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=user1_id,  # Created by user1
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Shared Folder",
            folder_prefix="/shared/",
            description="Folder that will be user2's default",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Create user2 who has this folder as their default
        user2_id = uuid4()
        user2 = Users(
            id=user2_id,
            email="user2.dependent@test.com",
            organization=test_organization,
            default_folder_id=folder_id,  # This folder is user2's default
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user2)
        await integration_db_session.commit()

        # User1 (creator) tries to delete the folder (should fail because it's user2's default)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(user1_id, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "default folder" in str(exc_info.value.detail).lower()
        assert "active user" in str(exc_info.value.detail).lower()

        # Note: No need to cleanup users - they don't interfere with other tests
        # and will be cleaned up at session end

    async def test_delete_creator_blocked_if_own_default_folder(
        self,
        integration_db_session: AsyncSession,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Creator should NOT be able to delete their own default folder while active."""
        from app.db.model import Users

        # Create a user
        user_id = uuid4()
        folder_id = uuid4()

        # Create the folder first
        directory = Folder(
            id=folder_id,
            user_id=user_id,  # User will create their own folder
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="My Default Folder",
            folder_prefix="/my/",
            description="User's own default folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create user with this folder as their default
        user = Users(
            id=user_id,
            email="user.owndefault@test.com",
            organization=test_organization,
            default_folder_id=folder_id,  # This folder is their own default
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()

        # User tries to delete their own default folder (should fail even though they created it)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(user_id, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "default folder" in str(exc_info.value.detail).lower()
        assert "active user" in str(exc_info.value.detail).lower()

        # Note: No need to cleanup user - it doesn't interfere with other tests
        # and will be cleaned up at session end

    async def test_delete_blocked_when_folder_has_one_active_picture(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block deletion of folder containing one active picture."""
        from app.db.model import Picture

        # Create a folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Folder With Picture",
            folder_prefix="/test/",
            description="Folder containing active picture",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create one active picture in the folder
        picture_id = uuid4()
        picture = Picture(
            id=picture_id,
            active=True,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1920,
            height=1080,
            sha256="test_sha256_hash_1",
            name="test_picture.jpg",
            blob_url_original="https://test.blob.url/original",
            format="JPEG",
            size_on_disk_original=1024.0,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()

        # Try to delete the folder (should fail due to active picture)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_admin_user, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "active picture" in str(exc_info.value.detail).lower()

        # Cleanup: remove the test picture
        await integration_db_session.delete(picture)
        await integration_db_session.commit()

    async def test_delete_blocked_when_folder_has_multiple_active_pictures(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block deletion of folder containing multiple active pictures."""
        from app.db.model import Picture

        # Create a folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Folder With Multiple Pictures",
            folder_prefix="/test/",
            description="Folder containing multiple active pictures",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create multiple active pictures in the folder
        pictures = []
        for i in range(3):
            picture_id = uuid4()
            picture = Picture(
                id=picture_id,
                active=True,
                folder_id=folder_id,
                user_id=test_admin_user,
                org_user_role_id=test_org_user_role,
                org_admin_role_id=test_org_admin_role,
                width=1920,
                height=1080,
                sha256=f"test_sha256_hash_{i}",
                name=f"test_picture_{i}.jpg",
                blob_url_original=f"https://test.blob.url/original_{i}",
                format="JPEG",
                size_on_disk_original=1024.0,
                date_created=datetime.now(timezone.utc),
            )
            integration_db_session.add(picture)
            pictures.append(picture)

        await integration_db_session.commit()

        # Try to delete the folder (should fail due to active pictures)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_admin_user, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "active picture" in str(exc_info.value.detail).lower()

        # Cleanup: remove the test pictures
        for picture in pictures:
            await integration_db_session.delete(picture)
        await integration_db_session.commit()

    async def test_delete_allowed_when_folder_has_no_pictures(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should allow deletion of folder with no pictures (normal case)."""
        # Create an empty folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Empty Folder",
            folder_prefix="/test/",
            description="Folder with no pictures",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)
        await integration_db_session.commit()

        # Delete the folder (should succeed)
        result = await DirectoryService.delete(test_admin_user, folder_id)

        # Verify success
        assert "message" in result
        assert "deleted successfully" in result["message"]

    async def test_delete_allowed_when_folder_has_only_inactive_pictures(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should allow deletion of folder containing only inactive (soft-deleted) pictures."""
        from app.db.model import Picture

        # Create a folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Folder With Inactive Pictures",
            folder_prefix="/test/",
            description="Folder containing only inactive pictures",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create inactive (soft-deleted) pictures in the folder
        pictures = []
        for i in range(2):
            picture_id = uuid4()
            picture = Picture(
                id=picture_id,
                active=False,  # Inactive (soft-deleted)
                folder_id=folder_id,
                user_id=test_admin_user,
                org_user_role_id=test_org_user_role,
                org_admin_role_id=test_org_admin_role,
                width=1920,
                height=1080,
                sha256=f"test_sha256_hash_inactive_{i}",
                name=f"test_picture_inactive_{i}.jpg",
                blob_url_original=f"https://test.blob.url/original_inactive_{i}",
                format="JPEG",
                size_on_disk_original=1024.0,
                date_created=datetime.now(timezone.utc),
            )
            integration_db_session.add(picture)
            pictures.append(picture)

        await integration_db_session.commit()

        # Delete the folder (should succeed since all pictures are inactive)
        result = await DirectoryService.delete(test_admin_user, folder_id)

        # Verify success
        assert "message" in result
        assert "deleted successfully" in result["message"]

        # Cleanup: remove the test pictures
        for picture in pictures:
            await integration_db_session.delete(picture)
        await integration_db_session.commit()

    async def test_delete_blocked_mixed_active_and_inactive_pictures(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Should block deletion if folder has at least one active picture among inactive ones."""
        from app.db.model import Picture

        # Create a folder
        folder_id = uuid4()
        directory = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Folder With Mixed Pictures",
            folder_prefix="/test/",
            description="Folder containing both active and inactive pictures",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(directory)
        cleanup_test_folders.append(folder_id)

        # Create inactive pictures
        pictures = []
        for i in range(2):
            picture_id = uuid4()
            picture = Picture(
                id=picture_id,
                active=False,  # Inactive
                folder_id=folder_id,
                user_id=test_admin_user,
                org_user_role_id=test_org_user_role,
                org_admin_role_id=test_org_admin_role,
                width=1920,
                height=1080,
                sha256=f"test_sha256_hash_inactive_{i}",
                name=f"test_picture_inactive_{i}.jpg",
                blob_url_original=f"https://test.blob.url/original_inactive_{i}",
                format="JPEG",
                size_on_disk_original=1024.0,
                date_created=datetime.now(timezone.utc),
            )
            integration_db_session.add(picture)
            pictures.append(picture)

        # Create one active picture
        active_picture_id = uuid4()
        active_picture = Picture(
            id=active_picture_id,
            active=True,  # Active
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1920,
            height=1080,
            sha256="test_sha256_hash_active",
            name="test_picture_active.jpg",
            blob_url_original="https://test.blob.url/original_active",
            format="JPEG",
            size_on_disk_original=1024.0,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(active_picture)
        pictures.append(active_picture)

        await integration_db_session.commit()

        # Try to delete the folder (should fail due to the one active picture)
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(test_admin_user, folder_id)

        # Verify 403 with appropriate message
        assert exc_info.value.status_code == 403
        assert "active picture" in str(exc_info.value.detail).lower()

        # Cleanup: remove the test pictures
        for picture in pictures:
            await integration_db_session.delete(picture)
        await integration_db_session.commit()
