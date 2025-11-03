"""
Unit tests for batch upload functionality.

This module tests the batch upload service layer and datastore operations.
Tests are marked as unit tests (fast, no external dependencies).

Note: These tests use mocking and patching to avoid database dependencies.
The codebase uses beartype for runtime type checking, so we patch at the
service layer rather than mocking low-level database objects.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.service.batch_upload import BatchUploadService
from app.model.batch_upload import BatchUploadImageRequest
from app.service.auth.user import User
from app.exceptions import SeedNotFoundError


# Test fixtures
@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_folder_id():
    """Sample folder UUID."""
    return uuid4()


@pytest.fixture
def sample_session_id():
    """Sample session UUID."""
    return uuid4()


@pytest.fixture
def sample_seed_id():
    """Sample seed UUID."""
    return uuid4()


@pytest.fixture
def mock_batch_session(sample_session_id, sample_user_id, sample_folder_id):
    """Mock BatchUploadSession instance."""
    session = MagicMock()
    session.id = sample_session_id
    session.user_id = sample_user_id
    session.folder_id = sample_folder_id
    session.file_count = 10
    session.uploaded_count = 0
    session.duplicate_count = 0
    session.active = True
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    session.date_created = datetime.now(timezone.utc)
    return session


class TestBatchUploadServiceInitialize:
    """Tests for BatchUploadService.initialize_batch_session()."""

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.RbacService.get_user_org_roles")
    @patch("app.service.batch_upload.DirectoryService.check_folder_exists")
    @patch("app.service.batch_upload.sessionmanager.get_session")
    async def test_initialize_success(
        self,
        mock_sessionmanager,
        mock_check_folder,
        mock_get_org_roles,
        sample_user_id,
        sample_folder_id,
    ):
        """Test successful session initialization."""
        # Mock org roles with org_user_role_id
        mock_org_roles = MagicMock()
        mock_org_roles.org_user_role_id = uuid4()
        mock_get_org_roles.return_value = mock_org_roles

        # Mock folder exists and belongs to organization
        mock_check_folder.return_value = AsyncMock(return_value="/org/folder/")

        # Mock database session
        mock_db_session = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_sessionmanager.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        mock_sessionmanager.return_value.__aexit__ = AsyncMock()

        # Mock BatchUploadSessionDataService
        with patch(
            "app.service.batch_upload.BatchUploadSessionDataService"
        ) as mock_data_service:
            mock_service_instance = mock_data_service.return_value
            mock_service_instance.create_session = AsyncMock()

            result = await BatchUploadService.initialize_batch_session(
                user_id=sample_user_id,
                folder_id=sample_folder_id,
                file_count=10,
            )

        assert "session_id" in result
        assert UUID(result["session_id"])  # Verify it's a valid UUID
        mock_get_org_roles.assert_called_once_with(sample_user_id)
        mock_check_folder.assert_called_once()
        mock_service_instance.create_session.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.RbacService.get_user_org_roles")
    async def test_initialize_file_count_exceeds_limit(
        self, mock_get_org_roles, sample_user_id, sample_folder_id
    ):
        """Test initialization fails when file_count > 1000."""
        mock_get_org_roles.return_value = MagicMock()

        # After security fix (CWE-209), errors are sanitized
        with pytest.raises(ValueError, match="Failed to initialize upload session"):
            await BatchUploadService.initialize_batch_session(
                user_id=sample_user_id,
                folder_id=sample_folder_id,
                file_count=1001,
            )

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.RbacService.get_user_org_roles")
    @patch("app.service.batch_upload.DirectoryService.check_folder_exists")
    async def test_initialize_folder_not_found(
        self, mock_check_folder, mock_get_org_roles, sample_user_id, sample_folder_id
    ):
        """Test initialization fails when folder doesn't exist or doesn't belong to org."""
        # Mock org roles with org_user_role_id
        mock_org_roles = MagicMock()
        mock_org_roles.org_user_role_id = uuid4()
        mock_get_org_roles.return_value = mock_org_roles

        # Mock folder not found (check_folder_exists raises DirectoryNotFoundError)
        from app.exceptions import DirectoryNotFoundError

        mock_check_folder.side_effect = DirectoryNotFoundError("Folder not found")

        # After security fix (CWE-209), errors are sanitized to ValueError
        with pytest.raises(ValueError, match="Failed to initialize upload session"):
            await BatchUploadService.initialize_batch_session(
                user_id=sample_user_id,
                folder_id=sample_folder_id,
                file_count=10,
            )

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.RbacService.get_user_org_roles")
    @patch("app.service.batch_upload.DirectoryService.check_folder_exists")
    async def test_initialize_folder_wrong_organization(
        self, mock_check_folder, mock_get_org_roles, sample_user_id, sample_folder_id
    ):
        """Test initialization fails when folder belongs to different organization."""
        # Mock org roles with org_user_role_id
        mock_org_roles = MagicMock()
        mock_org_roles.org_user_role_id = uuid4()
        mock_get_org_roles.return_value = mock_org_roles

        # Folder belongs to a different organization (check_folder_exists raises error)
        from app.exceptions import DirectoryNotFoundError

        mock_check_folder.side_effect = DirectoryNotFoundError(
            f"Folder {sample_folder_id} not found or access denied"
        )

        # After security fix (CWE-209), errors are sanitized to ValueError
        with pytest.raises(ValueError, match="Failed to initialize upload session"):
            await BatchUploadService.initialize_batch_session(
                user_id=sample_user_id,
                folder_id=sample_folder_id,
                file_count=10,
            )


class TestBatchUploadServiceUpload:
    """Tests for BatchUploadService.upload_picture_batch()."""

    @pytest.fixture
    def test_user(self, sample_user_id):
        """Create a real User object for testing."""
        return User(
            aud="test-audience",
            iss="test-issuer",
            iat=1234567890,
            nbf=1234567890,
            exp=1234567890 + 3600,
            sub="test-subject",
            oid=str(sample_user_id),
            ver="2.0",
            claims={},
            access_token="test-token",
            is_guest=False,
        )

    @pytest.fixture
    def batch_upload_request(self, sample_session_id, sample_seed_id):
        """Real BatchUploadImageRequest object."""
        return BatchUploadImageRequest(
            session_id=str(sample_session_id),
            seed_id=str(sample_seed_id),
            tray_code="A",
            sample_id="SAMPLE-001",
            image_description="Test batch upload image",
            device_brand_id=str(uuid4()),
            device_model_id=str(uuid4()),
            device_lens_id=str(uuid4()),
            magnification=10.0,
            image="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        )

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.sessionmanager.get_session")
    async def test_upload_session_not_found(
        self, mock_sessionmanager, batch_upload_request, test_user
    ):
        """Test upload fails when session doesn't exist."""
        # Mock database session
        mock_db_session = MagicMock()
        mock_sessionmanager.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        mock_sessionmanager.return_value.__aexit__ = AsyncMock()

        # Mock BatchUploadSessionDataService
        with patch(
            "app.service.batch_upload.BatchUploadSessionDataService"
        ) as mock_data_service:
            mock_service_instance = mock_data_service.return_value
            mock_service_instance.get_by_id = AsyncMock(return_value=None)

            result = await BatchUploadService.upload_picture_batch(
                request=batch_upload_request,
                user=test_user,
            )

        assert result["success"] is False
        assert "Invalid session_id" in result["error"]

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.sessionmanager.get_session")
    async def test_upload_session_inactive(
        self, mock_sessionmanager, batch_upload_request, test_user, mock_batch_session
    ):
        """Test upload fails when session is inactive."""
        mock_batch_session.active = False

        # Mock database session
        mock_db_session = MagicMock()
        mock_sessionmanager.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        mock_sessionmanager.return_value.__aexit__ = AsyncMock()

        # Mock BatchUploadSessionDataService
        with patch(
            "app.service.batch_upload.BatchUploadSessionDataService"
        ) as mock_data_service:
            mock_service_instance = mock_data_service.return_value
            mock_service_instance.get_by_id = AsyncMock(return_value=mock_batch_session)

            result = await BatchUploadService.upload_picture_batch(
                request=batch_upload_request,
                user=test_user,
            )

        assert result["success"] is False
        assert "inactive" in result["error"]

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.sessionmanager.get_session")
    async def test_upload_session_expired(
        self, mock_sessionmanager, batch_upload_request, test_user, mock_batch_session
    ):
        """Test upload fails when session is expired."""
        mock_batch_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        # Mock database session
        mock_db_session = MagicMock()
        mock_sessionmanager.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        mock_sessionmanager.return_value.__aexit__ = AsyncMock()

        # Mock BatchUploadSessionDataService
        with patch(
            "app.service.batch_upload.BatchUploadSessionDataService"
        ) as mock_data_service:
            mock_service_instance = mock_data_service.return_value
            mock_service_instance.get_by_id = AsyncMock(return_value=mock_batch_session)

            result = await BatchUploadService.upload_picture_batch(
                request=batch_upload_request,
                user=test_user,
            )

        assert result["success"] is False
        assert "expired" in result["error"]

    @pytest.mark.asyncio
    @patch("app.service.batch_upload.sessionmanager.get_session")
    @patch("app.service.batch_upload.SeedService.get_by_id")
    async def test_upload_seed_not_found(
        self,
        mock_get_seed,
        mock_sessionmanager,
        batch_upload_request,
        test_user,
        mock_batch_session,
    ):
        """Test upload fails when seed doesn't exist."""
        # Mock database session
        mock_db_session = MagicMock()
        mock_sessionmanager.return_value.__aenter__ = AsyncMock(
            return_value=mock_db_session
        )
        mock_sessionmanager.return_value.__aexit__ = AsyncMock()

        # Mock BatchUploadSessionDataService
        with patch(
            "app.service.batch_upload.BatchUploadSessionDataService"
        ) as mock_data_service:
            mock_service_instance = mock_data_service.return_value
            mock_service_instance.get_by_id = AsyncMock(return_value=mock_batch_session)

            # Mock seed service to raise not found
            mock_get_seed.side_effect = SeedNotFoundError("Seed not found")

            result = await BatchUploadService.upload_picture_batch(
                request=batch_upload_request,
                user=test_user,
            )

        assert result["success"] is False
        assert "Seed not found" in result["error"]


# Run with: uv run pytest tests/test_batch_upload.py -v
