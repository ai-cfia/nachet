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
from typing import no_type_check
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from dbos import DBOS
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.db.model import Folder, ImageProcessingState, Picture
from app.service.blob_operations import (
    download_sanitized_blob,
    upload_to_azure_blob,
)
from app.service.constants import ProcessingStatus
from tests.fixtures.mock_azure import MockBlobStorage
from tests.fixtures.test_images import get_test_seed_image

# from app.service.sanitization import (
#     trigger_sanitization_function,
# )


@no_type_check
@DBOS.workflow()
async def upload_workflow_wrapper(
    image_id: UUID,
    file_bytes: bytes,
    org_prefix: str,
    user_id: UUID,
) -> str:
    """
    Workflow wrapper for upload_to_azure_blob for testing purposes.

    This allows testing the DBOS @step retry logic by invoking
    upload_to_azure_blob from within a @workflow context.

    Note: Named without 'test_' prefix to avoid pytest collection.
    """
    return await upload_to_azure_blob(
        image_id=image_id,
        file_bytes=file_bytes,
        org_prefix=org_prefix,
        user_id=user_id,
    )


def create_mock_blob_manager_get_client(mock_storage):
    """Helper to create a mock for blob_storage_manager.get_client()."""

    def _mock(account_name: str):
        return mock_storage

    return _mock


@pytest_asyncio.fixture
async def test_folder(
    integration_db_session: AsyncSession,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
):
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


@pytest.fixture
def mock_blob_storage() -> MockBlobStorage:
    """Provide a mock Azure Blob Storage instance."""
    return MockBlobStorage()


@pytest_asyncio.fixture
def mock_settings():
    """Mock settings for testing."""
    mock = MagicMock()
    mock.is_test_environment = True
    mock.azure_sanitization_function_url = (
        "https://test-sanitizer.azurewebsites.net/api/sanitize"
    )
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
        user_id = uuid4()
        file_bytes = get_test_seed_image()
        org_prefix = "cfia-org"

        # Patch blob_storage_manager.get_client to return our mock
        with patch(
            "app.blob.manager.blob_storage_manager.get_client",
            side_effect=create_mock_blob_manager_get_client(mock_blob_storage),
        ):
            with patch("app.api.config.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_settings.blob_container_prefix = ""
                mock_get_settings.return_value = mock_settings

                # Act
                blob_url = await upload_to_azure_blob(
                    image_id=image_id,
                    file_bytes=file_bytes,
                    org_prefix=org_prefix,
                    user_id=user_id,
                )

        # Assert
        assert blob_url is not None
        # upload_to_azure_blob returns just the blob name: {org_prefix}/{image_id}.png
        assert str(image_id) in blob_url
        assert f"{org_prefix}" in blob_url
        assert blob_url == f"{org_prefix}/{image_id}.png"

        # Verify blob was stored in mock (mock storage uses container/blob_name as key)
        expected_key = f"original-test/{org_prefix}/{image_id}.png"
        assert expected_key in mock_blob_storage.uploaded_blobs

    @pytest.mark.asyncio
    async def test_upload_to_azure_blob_retry_on_failure(
        self, mock_blob_storage, dbos_runtime
    ):
        """Test upload retries on transient failures.

        This test uses the test_upload_workflow wrapper to invoke upload_to_azure_blob
        within a DBOS workflow context, which enables the @step retry logic.
        """
        # Arrange
        image_id = uuid7()
        file_bytes = get_test_seed_image()
        user_id = uuid4()

        # Configure mock to fail twice, then succeed
        mock_blob_storage.set_failure_count(2)

        # Patch blob_storage_manager.get_client to return our mock
        with patch(
            "app.blob.manager.blob_storage_manager.get_client",
            side_effect=create_mock_blob_manager_get_client(mock_blob_storage),
        ):
            with patch("app.api.config.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_settings.blob_container_prefix = ""
                mock_get_settings.return_value = mock_settings

                # Act - Call through workflow wrapper to enable retry logic
                blob_url = await upload_workflow_wrapper(
                    image_id=image_id,
                    file_bytes=file_bytes,
                    org_prefix="test-org",
                    user_id=user_id,
                )

        # Assert - Should succeed after retries
        assert blob_url is not None
        assert str(image_id) in blob_url
        # Mock should have been called 3 times (2 failures + 1 success)
        assert mock_blob_storage.attempt_count == 3

    @pytest.mark.asyncio
    async def test_download_sanitized_blob(self, mock_blob_storage):
        """Test downloading sanitized blob."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"

        # Upload a test blob to mock storage
        test_data = get_test_seed_image()
        await mock_blob_storage.upload_blob(
            container="sanitized-test",
            name=f"{org_prefix}/{image_id}.png",
            data=test_data,
        )

        # Patch blob_storage_manager.get_client to return our mock
        with patch(
            "app.blob.manager.blob_storage_manager.get_client",
            side_effect=create_mock_blob_manager_get_client(mock_blob_storage),
        ):
            with patch("app.api.config.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_settings.blob_container_prefix = ""
                mock_get_settings.return_value = mock_settings

                # Act
                downloaded_bytes = await download_sanitized_blob(
                    image_id=image_id,
                    org_prefix=org_prefix,
                )

        # Assert
        assert downloaded_bytes == test_data


class TestSanitizationOperations:
    """Test sanitization operation steps."""

    # @pytest.mark.asyncio
    # async def test_trigger_sanitization_function_success(self, mock_settings):
    #     """Test triggering sanitization Azure Function."""
    #     # Arrange
    #     image_id = uuid7()
    #     genus = "avena"
    #     species = "fatua"
    #     blob_url_original = f"https://test.blob.core.windows.net/nachet-original/test-org/avena-fatua/{image_id}.png"

    #     # Mock aiohttp session properly
    #     mock_response = AsyncMock()
    #     mock_response.status = 200
    #     # Make raise_for_status a regular MagicMock (not awaitable)
    #     mock_response.raise_for_status = MagicMock()
    #     mock_response.json = AsyncMock(
    #         return_value={"message": "Sanitization started", "status": "accepted"}
    #     )

    #     # Create async context manager for the response
    #     mock_post_ctx = AsyncMock()
    #     mock_post_ctx.__aenter__.return_value = mock_response
    #     mock_post_ctx.__aexit__.return_value = None

    #     # Create async context manager for the session
    #     mock_session_inst = MagicMock()
    #     mock_session_inst.post.return_value = mock_post_ctx

    #     mock_session_ctx = AsyncMock()
    #     mock_session_ctx.__aenter__.return_value = mock_session_inst
    #     mock_session_ctx.__aexit__.return_value = None

    #     # Patch both get_settings and aiohttp.ClientSession
    #     with patch("app.api.config.get_settings", return_value=mock_settings):
    #         with patch(
    #             "app.service.sanitization.aiohttp.ClientSession",
    #             return_value=mock_session_ctx,
    #         ):
    #             # Act
    #             await trigger_sanitization_function(
    #                 image_id=image_id,
    #                 genus=genus,
    #                 species=species,
    #                 blob_url_original=blob_url_original,
    #             )

    #     # Assert - Verify the POST request was made
    #     mock_session_inst.post.assert_called_once()
    #     call_args = mock_session_inst.post.call_args

    #     # Verify URL
    #     assert call_args[0][0] == mock_settings.azure_sanitization_function_url

    #     # Verify request payload
    #     json_payload = call_args[1]["json"]
    #     assert json_payload["image_id"] == str(image_id)
    #     assert json_payload["genus"] == genus
    #     assert json_payload["species"] == species
    #     assert json_payload["blob_url_original"] == blob_url_original

    # @pytest.mark.asyncio
    # async def test_trigger_sanitization_function_failure(self, mock_settings):
    #     """Test sanitization trigger failure handling."""
    #     # Arrange
    #     from app.exceptions import SanitizationError
    #     import aiohttp

    #     image_id = uuid7()

    #     # Mock aiohttp session to raise error
    #     mock_response = AsyncMock()
    #     mock_response.status = 500
    #     # Make raise_for_status a regular MagicMock that raises (not awaitable)
    #     mock_response.raise_for_status = MagicMock(
    #         side_effect=aiohttp.ClientResponseError(
    #             request_info=MagicMock(),
    #             history=(),
    #             status=500,
    #             message="Internal Server Error",
    #         )
    #     )

    #     # Create proper async context manager for the response
    #     mock_post_ctx = AsyncMock()
    #     mock_post_ctx.__aenter__.return_value = mock_response
    #     mock_post_ctx.__aexit__.return_value = None

    #     # Create async context manager for the session
    #     mock_session_inst = MagicMock()
    #     mock_session_inst.post.return_value = mock_post_ctx

    #     mock_session_ctx = AsyncMock()
    #     mock_session_ctx.__aenter__.return_value = mock_session_inst
    #     mock_session_ctx.__aexit__.return_value = None

    #     # Patch both get_settings and aiohttp.ClientSession
    #     with patch("app.api.config.get_settings", return_value=mock_settings):
    #         with patch(
    #             "app.service.sanitization.aiohttp.ClientSession",
    #             return_value=mock_session_ctx,
    #         ):
    #             # Act & Assert
    #             with pytest.raises(SanitizationError) as exc_info:
    #                 await trigger_sanitization_function(
    #                     image_id=image_id,
    #                     genus="avena",
    #                     species="fatua",
    #                     blob_url_original="https://test.blob.core.windows.net/nachet-original/test.png",
    #                 )

    #             assert "Failed to trigger sanitization" in str(exc_info.value)


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
        processing_state.blob_url_original = (
            "https://test.blob.core.windows.net/nachet-original/test.png"
        )
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
        processing_state.blob_url_sanitized = (
            "https://test.blob.core.windows.net/nachet-sanitized/avena/fatua/test.png"
        )
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

        # Patch blob_storage_manager.get_client to return our mock
        with patch(
            "app.blob.manager.blob_storage_manager.get_client",
            side_effect=create_mock_blob_manager_get_client(mock_blob_storage),
        ):
            with patch("app.api.config.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.is_test_environment = True
                mock_settings.blob_container_prefix = ""
                mock_get_settings.return_value = mock_settings

                # Act & Assert
                with pytest.raises(BlobUploadError) as exc_info:
                    await upload_to_azure_blob(
                        image_id=image_id,
                        file_bytes=file_bytes,
                        org_prefix="test-org",
                        user_id=uuid4(),
                    )

                assert "Failed to upload blob" in str(exc_info.value)
