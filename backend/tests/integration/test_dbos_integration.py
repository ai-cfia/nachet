"""
Integration tests for DBOS workflow.

Tests the image processing pipeline with mock Azure services.
These tests focus on validating the business logic and error handling
of the workflow steps.

Note: These tests mock Azure services but test actual workflow step logic.
Full DBOS durable execution testing requires a running DBOS instance
and is covered separately in E2E tests.
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from uuid6 import uuid7
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.blob_operations import (
    upload_to_azure_blob,
    wait_for_defender_scan,
    download_sanitized_blob,
)
from app.service.sanitization import (
    trigger_sanitization_function,
)
from app.db.model import ImageProcessingState, Folder, Picture
from app.service.constants import ProcessingStatus
from tests.fixtures.mock_azure import MockBlobStorage
from tests.fixtures.test_images import get_test_seed_image


def create_mock_get_blob_storage(mock_storage):
    """Helper to create an async mock for get_blob_storage."""
    async def _mock():
        return mock_storage
    return _mock


@pytest_asyncio.fixture
async def test_folder(integration_db_session: AsyncSession, test_user: UUID, test_org_admin_role: UUID, test_org_user_role: UUID):
    """Create a test folder for image uploads."""
    folder = Folder(
        id=uuid4(),
        name="Test Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test",
        description="Test folder for DBOS integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    yield folder.id
    # Cleanup handled by conftest.py cleanup fixtures


@pytest_asyncio.fixture
def mock_blob_storage():
    """Provide a mock Azure Blob Storage instance."""
    return MockBlobStorage()


@pytest_asyncio.fixture
def mock_settings():
    """Mock settings for testing."""
    mock = MagicMock()
    mock.is_test_environment = True
    mock.azure_sanitization_function_url = "https://test-sanitizer.azurewebsites.net/api/sanitize"
    mock.azure_sanitization_function_key = "test_key_12345"
    mock.backend_url = "http://localhost:8080"
    return mock


class TestBlobOperations:
    """Test individual blob operation steps."""

    @pytest.mark.asyncio
    async def test_upload_to_azure_blob_success(self, mock_blob_storage):
        """Test successful blob upload."""
        # Arrange
        image_id = uuid7()
        file_bytes = get_test_seed_image()
        filename = "test_seed.png"
        genus = "avena"
        species = "fatua"
        org_name = "cfia-org"

        # Patch get_blob_storage to return our mock (it's an async function)
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            with patch('app.api.config.get_settings') as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_get_settings.return_value = mock_settings

                # Act
                blob_url = await upload_to_azure_blob(
                    image_id=image_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    genus=genus,
                    species=species,
                    org_name=org_name,
                )

        # Assert
        assert blob_url is not None
        assert "nachet-original-test" in blob_url  # Test environment uses -test suffix
        assert str(image_id) in blob_url
        assert f"{org_name}/{genus}-{species}" in blob_url

        # Verify blob was stored in mock
        expected_key = f"nachet-original-test/{org_name}/{genus}-{species}/{image_id}.png"
        assert expected_key in mock_blob_storage.uploaded_blobs

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="DBOS retry logic requires full DBOS runtime context. Test in E2E instead.")
    async def test_upload_to_azure_blob_retry_on_failure(self, mock_blob_storage):
        """Test upload retries on transient failures.
        
        NOTE: This test is skipped because DBOS @step decorator retry logic 
        only works within a full DBOS workflow context. When called directly,
        the function behaves like a regular async function without retry.
        
        This functionality should be tested in E2E tests where the full
        DBOS runtime is available.
        """
        # Arrange
        image_id = uuid7()
        file_bytes = get_test_seed_image()

        # Configure mock to fail twice, then succeed
        mock_blob_storage.set_failure_count(2)

        # Patch get_blob_storage to return our mock (it's an async function)
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            with patch('app.api.config.get_settings') as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_get_settings.return_value = mock_settings

                # Act
                blob_url = await upload_to_azure_blob(
                    image_id=image_id,
                    file_bytes=file_bytes,
                    filename="test.png",
                    genus="avena",
                    species="fatua",
                    org_name="test-org",
                )

        # Assert - Should succeed after retries
        assert blob_url is not None
        # Mock should have been called 3 times (2 failures + 1 success)
        assert mock_blob_storage.attempt_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_defender_scan_clean(self, mock_blob_storage):
        """Test Defender scan completion with clean result."""
        # Arrange
        image_id = uuid7()
        blob_url = f"https://test.blob.core.windows.net/nachet-original/test-org/avena-fatua/{image_id}.png"

        # Mock blob storage with clean scan result
        mock_blob_storage.set_malware_detected(False)

        # Patch both get_blob_storage and DBOS.sleep_async
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            with patch('app.service.blob_operations.DBOS.sleep_async', new_callable=AsyncMock):
                # Act
                result = await wait_for_defender_scan(
                    image_id=image_id,
                    blob_url=blob_url,
                    timeout_sec=30,
                )

        # Assert
        assert result["status"] == "clean"
        assert result["tags"]["malware_detected"] == "false"
        assert result["tags"]["defender_scan_complete"] == "true"

    @pytest.mark.asyncio
    async def test_wait_for_defender_scan_malware_detected(self, mock_blob_storage):
        """Test Defender scan with malware detection."""
        # Arrange
        from app.exceptions import DefenderScanFailedError

        image_id = uuid7()
        blob_url = f"https://test.blob.core.windows.net/nachet-original/test-org/avena-fatua/{image_id}.png"

        # Mock blob storage with malware detection
        mock_blob_storage.set_malware_detected(True)

        # Patch both get_blob_storage and DBOS.sleep_async
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            with patch('app.service.blob_operations.DBOS.sleep_async', new_callable=AsyncMock):
                # Act & Assert - Should raise exception
                with pytest.raises(DefenderScanFailedError) as exc_info:
                    await wait_for_defender_scan(
                        image_id=image_id,
                        blob_url=blob_url,
                        timeout_sec=30,
                    )

                assert "malware" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_download_sanitized_blob(self, mock_blob_storage):
        """Test downloading sanitized blob."""
        # Arrange
        image_id = uuid7()
        sanitized_blob_url = f"https://test.blob.core.windows.net/nachet-sanitized/avena/fatua/{image_id}.png"

        # Upload a test blob to mock storage
        test_data = get_test_seed_image()
        await mock_blob_storage.upload_blob(
            container="nachet-sanitized",
            name=f"avena/fatua/{image_id}.png",
            data=test_data
        )

        # Patch get_blob_storage to return our mock (it's an async function)
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            # Act
            downloaded_bytes = await download_sanitized_blob(
                image_id=image_id,
                sanitized_blob_url=sanitized_blob_url,
            )

        # Assert
        assert downloaded_bytes == test_data


class TestSanitizationOperations:
    """Test sanitization operation steps."""

    @pytest.mark.asyncio
    async def test_trigger_sanitization_function_success(self, mock_settings):
        """Test triggering sanitization Azure Function."""
        # Arrange
        image_id = uuid7()
        genus = "avena"
        species = "fatua"
        blob_url_original = f"https://test.blob.core.windows.net/nachet-original/test-org/avena-fatua/{image_id}.png"

        # Mock aiohttp session properly
        mock_response = AsyncMock()
        mock_response.status = 200
        # Make raise_for_status a regular MagicMock (not awaitable)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"message": "Sanitization started", "status": "accepted"})

        # Create async context manager for the response
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_post_ctx.__aexit__.return_value = None

        # Create async context manager for the session
        mock_session_inst = MagicMock()
        mock_session_inst.post.return_value = mock_post_ctx

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session_inst
        mock_session_ctx.__aexit__.return_value = None

        # Patch both get_settings and aiohttp.ClientSession
        with patch('app.api.config.get_settings', return_value=mock_settings):
            with patch('app.service.sanitization.aiohttp.ClientSession', return_value=mock_session_ctx):
                # Act
                await trigger_sanitization_function(
                    image_id=image_id,
                    genus=genus,
                    species=species,
                    blob_url_original=blob_url_original,
                )

        # Assert - Verify the POST request was made
        mock_session_inst.post.assert_called_once()
        call_args = mock_session_inst.post.call_args

        # Verify URL
        assert call_args[0][0] == mock_settings.azure_sanitization_function_url

        # Verify request payload
        json_payload = call_args[1]['json']
        assert json_payload['image_id'] == str(image_id)
        assert json_payload['genus'] == genus
        assert json_payload['species'] == species
        assert json_payload['blob_url_original'] == blob_url_original

    @pytest.mark.asyncio
    async def test_trigger_sanitization_function_failure(self, mock_settings):
        """Test sanitization trigger failure handling."""
        # Arrange
        from app.exceptions import SanitizationError
        import aiohttp

        image_id = uuid7()

        # Mock aiohttp session to raise error
        mock_response = AsyncMock()
        mock_response.status = 500
        # Make raise_for_status a regular MagicMock that raises (not awaitable)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
            message="Internal Server Error"
        ))

        # Create proper async context manager for the response
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_post_ctx.__aexit__.return_value = None

        # Create async context manager for the session
        mock_session_inst = MagicMock()
        mock_session_inst.post.return_value = mock_post_ctx

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session_inst
        mock_session_ctx.__aexit__.return_value = None

        # Patch both get_settings and aiohttp.ClientSession
        with patch('app.api.config.get_settings', return_value=mock_settings):
            with patch('app.service.sanitization.aiohttp.ClientSession', return_value=mock_session_ctx):
                # Act & Assert
                with pytest.raises(SanitizationError) as exc_info:
                    await trigger_sanitization_function(
                        image_id=image_id,
                        genus="avena",
                        species="fatua",
                        blob_url_original="https://test.blob.core.windows.net/nachet-original/test.png",
                    )

                assert "Failed to trigger sanitization" in str(exc_info.value)


class TestImageProcessingState:
    """Test ImageProcessingState model integration."""

    @pytest.mark.asyncio
    async def test_create_image_processing_state(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_folder: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
    ):
        """Test creating an image processing state record."""
        # Arrange
        from datetime import datetime, timezone

        image_id = uuid7()

        # First create a Picture record (required by foreign key)
        picture = Picture(
            id=image_id,
            folder_id=test_folder,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="test_seed.png",
            blob_url_original="https://test.blob.core.windows.net/test/test_seed.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_sha256_hash",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()

        # Now create the processing state
        processing_state = ImageProcessingState(
            picture_id=image_id,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )

        # Act
        integration_db_session.add(processing_state)
        await integration_db_session.commit()
        await integration_db_session.refresh(processing_state)

        # Assert
        assert processing_state.picture_id == image_id
        assert processing_state.status == ProcessingStatus.PENDING
        assert processing_state.progress_percentage == 0

        # Cleanup
        await integration_db_session.delete(processing_state)
        await integration_db_session.delete(picture)
        await integration_db_session.commit()

    @pytest.mark.asyncio
    async def test_update_image_processing_state(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_folder: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
    ):
        """Test updating image processing state through pipeline stages."""
        # Arrange
        from datetime import datetime, timezone

        image_id = uuid7()

        # First create a Picture record (required by foreign key)
        picture = Picture(
            id=image_id,
            folder_id=test_folder,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="test.png",
            blob_url_original="https://test.blob.core.windows.net/test/test.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_sha256_hash",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()

        # Now create the processing state
        processing_state = ImageProcessingState(
            picture_id=image_id,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Act - Simulate pipeline progress
        # Stage 1: Uploaded
        processing_state.status = ProcessingStatus.UPLOADED
        processing_state.progress_percentage = 25
        processing_state.uploaded_at = datetime.now(timezone.utc)
        processing_state.blob_url_original = "https://test.blob.core.windows.net/nachet-original/test.png"
        await integration_db_session.commit()

        # Stage 2: Defender scanning
        processing_state.status = ProcessingStatus.DEFENDER_SCANNING
        processing_state.progress_percentage = 50
        await integration_db_session.commit()

        # Stage 3: Defender scanned
        processing_state.status = ProcessingStatus.DEFENDER_SCANNED
        processing_state.progress_percentage = 60
        processing_state.defender_scan_completed_at = datetime.now(timezone.utc)
        await integration_db_session.commit()

        # Stage 4: Sanitizing
        processing_state.status = ProcessingStatus.SANITIZING
        processing_state.progress_percentage = 75
        await integration_db_session.commit()

        # Stage 5: Sanitized
        processing_state.status = ProcessingStatus.SANITIZED
        processing_state.progress_percentage = 90
        processing_state.sanitization_completed_at = datetime.now(timezone.utc)
        processing_state.blob_url_sanitized = "https://test.blob.core.windows.net/nachet-sanitized/avena/fatua/test.png"
        await integration_db_session.commit()

        # Stage 6: Completed
        processing_state.status = ProcessingStatus.COMPLETED
        processing_state.progress_percentage = 100
        processing_state.completed_at = datetime.now(timezone.utc)
        await integration_db_session.commit()

        # Refresh from DB
        await integration_db_session.refresh(processing_state)

        # Assert
        assert processing_state.status == ProcessingStatus.COMPLETED
        assert processing_state.progress_percentage == 100
        assert processing_state.uploaded_at is not None
        assert processing_state.defender_scan_completed_at is not None
        assert processing_state.sanitization_completed_at is not None
        assert processing_state.completed_at is not None
        assert processing_state.blob_url_original is not None
        assert processing_state.blob_url_sanitized is not None

        # Cleanup
        await integration_db_session.delete(processing_state)
        await integration_db_session.commit()


class TestErrorHandling:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_blob_upload_error_handling(self, mock_blob_storage):
        """Test error handling for blob upload failures."""
        # Arrange
        from app.exceptions import BlobUploadError

        image_id = uuid7()
        file_bytes = get_test_seed_image()

        # Configure mock to always fail
        mock_blob_storage.set_failure_count(999)

        # Patch get_blob_storage to return our mock (it's an async function)
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            with patch('app.api.config.get_settings') as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_get_settings.return_value = mock_settings

                # Act & Assert
                with pytest.raises(BlobUploadError) as exc_info:
                    await upload_to_azure_blob(
                        image_id=image_id,
                        file_bytes=file_bytes,
                        filename="test.png",
                        genus="avena",
                        species="fatua",
                        org_name="test-org",
                    )

                assert "Failed to upload blob" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_defender_scan_timeout(self, mock_blob_storage):
        """Test Defender scan timeout handling."""
        # Arrange
        from app.exceptions import DefenderScanTimeoutError

        image_id = uuid7()
        blob_url = f"https://test.blob.core.windows.net/nachet-original/test/{image_id}.png"

        # Mock with tags that never complete
        async def mock_get_tags(container, name):
            return {
                "defender_scan_complete": "false",
                "malware_detected": "false",
            }

        mock_blob_storage.get_blob_tags = mock_get_tags

        # Patch get_blob_storage to return our mock (it's an async function)
        with patch('app.service.blob_operations.get_blob_storage', side_effect=create_mock_get_blob_storage(mock_blob_storage)):
            # Use very short timeout for test
            with patch('app.service.blob_operations.DBOS.sleep_async', new_callable=AsyncMock):
                # Act & Assert
                with pytest.raises(DefenderScanTimeoutError) as exc_info:
                    await wait_for_defender_scan(
                        image_id=image_id,
                        blob_url=blob_url,
                        timeout_sec=10,  # Short timeout for test
                    )

                assert "timed out" in str(exc_info.value).lower()
