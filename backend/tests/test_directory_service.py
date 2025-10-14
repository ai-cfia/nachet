"""
Tests for DirectoryService - CRUD operations for directories (folders).

Access Control:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only
"""

import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.service.directory import DirectoryService
from app.db.model import Folder

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


# ============================================================================
# DirectoryService Tests - Standard CRUD Operations
# ============================================================================


class TestDirectoryServiceGetAll:
    """Test DirectoryService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all directories."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        dir1_id = uuid4()
        dir2_id = uuid4()

        # Mock directories
        dir1 = Mock(spec=Folder)
        dir1.id = dir1_id
        dir1.user_id = user_id
        dir1.org_admin_id = user_org_id
        dir1.name = "Test Directory 1"
        dir1.folder_prefix = "test-dir-1"
        dir1.description = "Test directory 1"
        dir1.active = True
        dir1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dir1.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        dir2 = Mock(spec=Folder)
        dir2.id = dir2_id
        dir2.user_id = user_id
        dir2.org_admin_id = user_org_id
        dir2.name = "Test Directory 2"
        dir2.folder_prefix = "test-dir-2"
        dir2.description = "Test directory 2"
        dir2.active = True
        dir2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)
        dir2.date_updated = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.directory.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([dir1, dir2], 2))
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.get_all(user_id)

        # Verify
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "Test Directory 1"
        assert result["items"][1]["name"] == "Test Directory 2"
        assert result["total"] == 2


class TestDirectoryServiceGetById:
    """Test DirectoryService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a directory by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        dir_id = uuid4()

        # Mock directory
        directory = Mock(spec=Folder)
        directory.id = dir_id
        directory.user_id = user_id
        directory.org_admin_id = user_org_id
        directory.name = "Test Directory"
        directory.folder_prefix = "test-dir"
        directory.description = "Test directory"
        directory.active = True
        directory.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        directory.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.directory.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=directory)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.get_by_id(user_id, dir_id)

        # Verify
        assert result["name"] == "Test Directory"
        assert result["id"] == str(dir_id)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if directory not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.directory.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - directory not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.get_by_id(user_id, dir_id)

        assert exc_info.value.status_code == 404


class TestDirectoryServiceCreate:
    """Test DirectoryService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new directories."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_admin_id = uuid4()
        dir_id = uuid4()

        # Mock directory
        directory = Mock(spec=Folder)
        directory.id = dir_id
        directory.user_id = user_id
        directory.org_admin_id = org_admin_id
        directory.name = "New Directory"
        directory.folder_prefix = "new-dir"
        directory.description = "New test directory"
        directory.active = True
        directory.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        directory.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=directory)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.create(
            user_id=user_id,
            org_admin_id=org_admin_id,
            name="New Directory",
            folder_prefix="new-dir",
            description="New test directory",
        )

        # Verify
        assert result["name"] == "New Directory"
        assert result["id"] == str(dir_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()
        org_admin_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.create(
                user_id=user_id,
                org_admin_id=org_admin_id,
                name="New Directory",
                folder_prefix="new-dir",
            )

        assert exc_info.value.status_code == 403


class TestDirectoryServiceUpdate:
    """Test DirectoryService.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update directories."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_admin_id = uuid4()
        dir_id = uuid4()

        # Mock updated directory
        directory = Mock(spec=Folder)
        directory.id = dir_id
        directory.user_id = user_id
        directory.org_admin_id = org_admin_id
        directory.name = "Updated Directory"
        directory.folder_prefix = "updated-dir"
        directory.description = "Updated description"
        directory.active = True
        directory.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        directory.date_updated = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=directory)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.update(
            user_id, dir_id, name="Updated Directory"
        )

        # Verify
        assert result["name"] == "Updated Directory"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if directory not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.update(user_id, dir_id, name="Updated")

        assert exc_info.value.status_code == 404


class TestDirectoryServiceDelete:
    """Test DirectoryService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete directories."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        dir_id = uuid4()

        # Mock directory
        directory = Mock(spec=Folder)
        directory.id = dir_id

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=directory)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.delete(user_id, dir_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if directory not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(user_id, dir_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when deleting."""
        user_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await DirectoryService.delete(user_id, dir_id)

        assert exc_info.value.status_code == 403


# ============================================================================
# DirectoryService Tests - Custom Methods
# ============================================================================


class TestDirectoryServiceGetUserDirectories:
    """Test DirectoryService.get_user_directories custom method."""

    @pytest.mark.asyncio
    async def test_get_user_directories_success(self, monkeypatch):
        """Should retrieve directories with picture counts for user."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()

        # Mock directory result (mimics SQL aggregation result)
        class MockDirectory:
            def _asdict(self):
                return {
                    "id": str(uuid4()),
                    "name": "Test Directory",
                    "folder_prefix": "test-dir",
                    "description": "Test",
                    "picture_count": 5,
                }

        directories = [MockDirectory(), MockDirectory()]

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.directory.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_user_directories_count = AsyncMock(
            return_value=directories
        )
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.get_user_directories(user_id)

        # Verify
        assert "directories" in result
        assert len(result["directories"]) == 2
        assert result["directories"][0]["picture_count"] == 5


class TestDirectoryServiceCreateDirectory:
    """Test DirectoryService.create_directory custom method."""

    @pytest.mark.asyncio
    async def test_create_directory_success(self, monkeypatch):
        """CFIA admin should be able to create directory with custom method."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        org_admin_id = uuid4()
        new_dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create_directory = AsyncMock(return_value=str(new_dir_id))
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.create_directory(
            user_id=user_id,
            org_admin_id=org_admin_id,
            name="Custom Directory",
            folder_prefix="custom-dir",
            description="Custom description",
        )

        # Verify
        assert "id" in result
        assert "message" in result
        assert "created successfully" in result["message"]
        mock_session.commit.assert_called_once()


class TestDirectoryServiceRenameDirectory:
    """Test DirectoryService.rename_directory custom method."""

    @pytest.mark.asyncio
    async def test_rename_directory_success(self, monkeypatch):
        """CFIA admin should be able to rename directory."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.rename_directory = AsyncMock(return_value=str(dir_id))
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await DirectoryService.rename_directory(
            user_id=user_id, directory_id=dir_id, new_name="Renamed Directory"
        )

        # Verify
        assert "id" in result
        assert "message" in result
        assert "renamed" in result["message"].lower()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rename_directory_not_found(self, monkeypatch):
        """Should handle directory not found error."""
        from app.db.utils import sessionmanager
        from app.exceptions import DirectoryNotFoundError

        user_id = uuid4()
        dir_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.directory.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - raise ValueError
        mock_data_service = AsyncMock()
        mock_data_service.rename_directory = AsyncMock(
            side_effect=ValueError("Directory not found")
        )
        monkeypatch.setattr(
            "app.service.directory.DirectoryDataService",
            lambda session: mock_data_service,
        )

        # Should raise DirectoryNotFoundError
        with pytest.raises(DirectoryNotFoundError):
            await DirectoryService.rename_directory(
                user_id=user_id, directory_id=dir_id, new_name="Renamed"
            )
