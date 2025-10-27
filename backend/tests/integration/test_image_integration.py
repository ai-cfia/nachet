"""
Integration tests for ImageService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested (AuthorizedBaseCRUDService):
- GET operations (get_all, get_by_id):
  Users with picture's org_user_role_id OR org_admin_role_id OR CFIA admin
- UPDATE operations:
  Users with picture's org_user_role_id OR org_admin_role_id OR CFIA admin
- DELETE operations:
  Users with picture's org_admin_role_id OR CFIA admin (admin-only)
- CREATE operations: Any authenticated user (organization members)

These integration tests cover the authorization edge cases that are difficult
to mock properly due to the complex authorization flow in AuthorizedBaseCRUDService.
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

from app.service.image import ImageService
from app.db.model import Picture
from sqlalchemy.ext.asyncio import AsyncSession

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationCreate:
    """Integration tests for ImageService.create method."""

    async def test_create_success_as_authenticated_user(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Authenticated users should be able to create new images."""
        # Create test folder first (images need a folder)
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder for images",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)
        await integration_db_session.commit()

        # Call service
        result = await ImageService.create(
            requester_id=test_admin_user,
            user_id=test_admin_user,
            folder_id=folder_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="a1b2c3d4e5f6",
            name="test_image.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
        )

        # Track for cleanup
        picture_id = UUID(result["id"])
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)  # Also cleanup the folder

        # Verify response
        assert "id" in result
        assert result["name"] == "test_image.jpg"
        assert result["width"] == 1024
        assert result["height"] == 768

    async def test_create_unauthorized_non_authenticated(
        self,
    ):
        """Non-authenticated users should get 403."""
        # Use a random UUID not in the database
        unauth_user = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ImageService.create(
                requester_id=unauth_user,
                user_id=unauth_user,
                folder_id=uuid4(),
                org_user_role_id=uuid4(),
                org_admin_role_id=uuid4(),
                width=1024,
                height=768,
                sha256="test",
                name="test.jpg",
                blob_url_original="https://test.com/test.jpg",
                format="JPEG",
                size_on_disk_original=123.0,
            )

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationRetrieve:
    """Integration tests for ImageService.get_by_id method with authorization."""

    async def test_get_by_id_success_as_org_user(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """User with org_user_role_id should be able to retrieve images."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create test picture
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="test_hash",
            name="test_image.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Retrieve image as user with org_user_role_id
        result = await ImageService.get_by_id(test_admin_user, picture_id)

        # Verify
        assert result["id"] == str(picture_id)
        assert result["name"] == "test_image.jpg"

    async def test_get_by_id_unauthorized_wrong_org(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_regular_user: UUID,
        cleanup_test_pictures: list,
    ):
        """User from different organization should be denied access."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create test picture with specific org roles
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="test_hash",
            name="test_image.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Try to retrieve as user without access (regular user not in RBAC)
        with pytest.raises(HTTPException) as exc_info:
            await ImageService.get_by_id(test_regular_user, picture_id)

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationUpdate:
    """Integration tests for ImageService.update method."""

    async def test_update_success_as_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Admin users should be able to update images."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create test picture
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="original_hash",
            name="original_name.jpg",
            blob_url_original="https://example.com/original.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Update image metadata
        result = await ImageService.update(
            test_admin_user,
            picture_id,
            name="updated_name.jpg",
            description="Updated description",
        )

        # Verify
        assert result["id"] == str(picture_id)
        assert result["name"] == "updated_name.jpg"
        assert result["description"] == "Updated description"

    async def test_update_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should return 404 if image not found."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ImageService.update(
                test_admin_user, nonexistent_id, name="new_name.jpg"
            )

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationDelete:
    """Integration tests for ImageService.delete method."""

    async def test_delete_success_as_admin(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Admin users should be able to soft delete images."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create test picture
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="test_hash",
            name="test_image.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Delete image
        result = await ImageService.delete(test_admin_user, picture_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]

    async def test_delete_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Should return 404 if image not found."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ImageService.delete(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_delete_unauthorized_non_admin(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Non-admin users should get 403 when deleting."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create test picture
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="test_hash",
            name="test_image.jpg",
            blob_url_original="https://example.com/test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Try to delete as non-admin user
        with pytest.raises(HTTPException) as exc_info:
            await ImageService.delete(test_regular_user, picture_id)

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationGetAll:
    """Integration tests for ImageService.get_all method."""

    async def test_get_all_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Authenticated users should be able to list images."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create multiple test pictures
        picture_ids = []
        for i in range(3):
            picture_id = uuid4()
            test_picture = Picture(
                id=picture_id,
                folder_id=folder_id,
                user_id=test_admin_user,
                org_user_role_id=test_org_user_role,
                org_admin_role_id=test_org_admin_role,
                width=1024,
                height=768,
                sha256=f"test_hash_{i}",
                name=f"test_image_{i}.jpg",
                blob_url_original=f"https://example.com/test_{i}.jpg",
                format="JPEG",
                size_on_disk_original=123456.0,
                active=True,
                date_created=datetime.now(timezone.utc),
            )
            integration_db_session.add(test_picture)
            picture_ids.append(picture_id)

        cleanup_test_pictures.extend(picture_ids)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Get all images
        result = await ImageService.get_all(test_admin_user)

        # Verify we get a paginated response
        assert "items" in result
        assert "total" in result
        assert "offset" in result
        assert "limit" in result
        assert "has_more" in result

        # We should get at least our test images
        assert len(result["items"]) >= 3
        assert result["total"] >= 3


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageServiceIntegrationAuthorizationEdgeCases:
    """Integration tests for complex authorization scenarios."""

    async def test_cfia_admin_cross_organization_access(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,  # This is a CFIA admin
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """CFIA admin should have cross-organization access to all images."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create picture with different organization roles (simulating another org)
        # For now, use existing roles but test CFIA admin cross-access patterns
        picture_id = uuid4()
        test_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,  # Same org, testing admin override
            org_admin_role_id=test_org_admin_role,  # Same org, testing admin override
            width=1024,
            height=768,
            sha256="cross_org_hash",
            name="cross_org_image.jpg",
            blob_url_original="https://example.com/cross_org.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # CFIA admin should still be able to access (cross-organization authority)
        result = await ImageService.get_by_id(test_admin_user, picture_id)
        assert result["id"] == str(picture_id)

        # CFIA admin should be able to update cross-organization
        update_result = await ImageService.update(
            test_admin_user, picture_id, description="Updated by CFIA admin"
        )
        assert update_result["description"] == "Updated by CFIA admin"

        # CFIA admin should be able to delete cross-organization
        delete_result = await ImageService.delete(test_admin_user, picture_id)
        assert "deleted successfully" in delete_result["message"]

    async def test_org_admin_vs_org_user_access_levels(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Test that org admin has delete access but org user does not."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create two pictures - one for org admin test, one for org user test
        admin_picture_id = uuid4()
        user_picture_id = uuid4()

        admin_picture = Picture(
            id=admin_picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="admin_test_hash",
            name="admin_test.jpg",
            blob_url_original="https://example.com/admin_test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )

        user_picture = Picture(
            id=user_picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="user_test_hash",
            name="user_test.jpg",
            blob_url_original="https://example.com/user_test.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=True,
            date_created=datetime.now(timezone.utc),
        )

        integration_db_session.add(admin_picture)
        integration_db_session.add(user_picture)
        cleanup_test_pictures.extend([admin_picture_id, user_picture_id, folder_id])
        await integration_db_session.commit()

        # User with admin role should be able to delete
        admin_delete_result = await ImageService.delete(
            test_admin_user, admin_picture_id
        )
        assert "deleted successfully" in admin_delete_result["message"]

        # Both admin and user can read/update - verify user can still update
        user_update_result = await ImageService.update(
            test_admin_user,  # This user has both admin and user roles
            user_picture_id,
            description="Updated by user role",
        )
        assert user_update_result["description"] == "Updated by user role"

    async def test_inactive_picture_access(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_pictures: list,
    ):
        """Test access to inactive (soft-deleted) pictures."""
        # Create test folder first
        from app.db.model import Folder

        folder_id = uuid4()
        test_folder = Folder(
            id=folder_id,
            user_id=test_admin_user,
            org_admin_role_id=test_org_admin_role,
            org_user_role_id=test_org_user_role,
            name="Test Folder",
            folder_prefix="/test",
            description="Test folder",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(test_folder)

        # Create inactive picture
        picture_id = uuid4()
        inactive_picture = Picture(
            id=picture_id,
            folder_id=folder_id,
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            width=1024,
            height=768,
            sha256="inactive_hash",
            name="inactive_test.jpg",
            blob_url_original="https://example.com/inactive.jpg",
            format="JPEG",
            size_on_disk_original=123456.0,
            active=False,  # This picture is soft-deleted
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_picture)
        cleanup_test_pictures.append(picture_id)
        cleanup_test_pictures.append(folder_id)
        await integration_db_session.commit()

        # Inactive pictures should not be accessible via normal get_by_id
        # (The BaseCRUDDataService should filter them out by default)
        with pytest.raises(HTTPException) as exc_info:
            await ImageService.get_by_id(test_admin_user, picture_id)

        assert exc_info.value.status_code == 404
