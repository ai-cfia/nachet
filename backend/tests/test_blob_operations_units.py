"""
Unit tests for blob_operations DBOS steps.

These tests mock blob storage and DBOS to test individual steps in isolation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from uuid6 import uuid7

from app.service.blob_operations import (
    upload_to_azure_blob,
)
from app.exceptions import (
    BlobUploadError,
)
from app.service.constants import BlobAccount


@pytest.mark.asyncio
class TestUploadToAzureBlob:
    """Unit tests for upload_to_azure_blob DBOS step."""

    async def test_upload_success(self):
        """Test successful blob upload."""
        # Arrange
        image_id = uuid7()
        file_bytes = b"fake image data"
        org_prefix = "test-org"
        user_id = uuid4()

        mock_storage = AsyncMock()
        mock_storage.upload_blob = AsyncMock(
            return_value={
                "url": f"https://test.blob.core.windows.net/container/{org_prefix}/{image_id}.png"
            }
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = "nachet-"
        mock_settings.is_test_environment = True

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.blob_operations.DBOS") as mock_dbos,
        ):
            mock_manager.get_client.return_value = mock_storage
            mock_dbos.logger = MagicMock()

            result = await upload_to_azure_blob(
                image_id=image_id,
                file_bytes=file_bytes,
                org_prefix=org_prefix,
                user_id=user_id,
            )

            # Assert
            assert result == f"{org_prefix}/{image_id}.png"
            mock_storage.upload_blob.assert_awaited_once()

            # Verify upload call arguments
            call_args = mock_storage.upload_blob.call_args
            assert call_args.kwargs["container"] == "nachet-original-test"
            assert call_args.kwargs["name"] == f"{org_prefix}/{image_id}.png"
            assert call_args.kwargs["data"] == file_bytes
            assert "user_id" in call_args.kwargs["metadata"]

    async def test_upload_blob_naming_structure(self):
        """Test that blob naming follows {org_prefix}/{image_id}.png pattern."""
        # Arrange
        image_id = uuid7()
        file_bytes = b"test data"
        org_prefix = "cfia-org"
        user_id = uuid4()

        mock_storage = AsyncMock()
        mock_storage.upload_blob = AsyncMock(return_value={"url": "https://test.blob"})

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.blob_operations.DBOS") as mock_dbos,
        ):
            mock_manager.get_client.return_value = mock_storage
            mock_dbos.logger = MagicMock()

            result = await upload_to_azure_blob(
                image_id=image_id,
                file_bytes=file_bytes,
                org_prefix=org_prefix,
                user_id=user_id,
            )

            # Assert - verify naming pattern
            expected_blob_name = f"{org_prefix}/{image_id}.png"
            assert result == expected_blob_name

            call_args = mock_storage.upload_blob.call_args
            assert call_args.kwargs["name"] == expected_blob_name

    async def test_upload_raises_blob_upload_error_on_failure(self):
        """Test that upload failures raise BlobUploadError."""
        # Arrange
        image_id = uuid7()
        file_bytes = b"test data"
        org_prefix = "test-org"
        user_id = uuid4()

        mock_storage = AsyncMock()
        mock_storage.upload_blob = AsyncMock(
            side_effect=Exception("Azure connection timeout")
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = "nachet-"
        mock_settings.is_test_environment = True

        # Act & Assert
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.blob_operations.DBOS") as mock_dbos,
        ):
            mock_manager.get_client.return_value = mock_storage
            mock_dbos.logger = MagicMock()

            with pytest.raises(BlobUploadError) as exc_info:
                await upload_to_azure_blob(
                    image_id=image_id,
                    file_bytes=file_bytes,
                    org_prefix=org_prefix,
                    user_id=user_id,
                )

            assert "Failed to upload blob" in str(exc_info.value)
            assert "Azure connection timeout" in str(exc_info.value)

    async def test_upload_uses_external_account_by_default(self):
        """Test that upload uses ONPREM account by default."""
        # Arrange
        image_id = uuid7()
        file_bytes = b"test"
        org_prefix = "test"
        user_id = uuid4()

        mock_storage = AsyncMock()
        mock_storage.upload_blob = AsyncMock(return_value={"url": "https://test"})

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.blob_operations.DBOS") as mock_dbos,
        ):
            mock_manager.get_client.return_value = mock_storage
            mock_dbos.logger = MagicMock()

            await upload_to_azure_blob(
                image_id=image_id,
                file_bytes=file_bytes,
                org_prefix=org_prefix,
                user_id=user_id,
            )

            # Assert - verify ONPREM account used
            mock_manager.get_client.assert_called_once_with(BlobAccount.ONPREM.value)
