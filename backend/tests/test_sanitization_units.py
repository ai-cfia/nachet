"""
Unit tests for sanitization DBOS step.

These tests mock blob storage and PIL to test sanitization in isolation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid6 import uuid7

from app.service.sanitization import trigger_sanitization_function_local
from app.exceptions import SanitizationError
from app.service.constants import BlobAccount


@pytest.mark.asyncio
class TestTriggerSanitizationFunctionLocal:
    """Unit tests for trigger_sanitization_function_local DBOS step."""

    async def test_sanitization_success(self):
        """Test successful image sanitization."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"

        # Create fake image bytes
        fake_image_bytes = b"fake PNG image data"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(return_value=fake_image_bytes)

        mock_sanitized_storage = AsyncMock()
        mock_sanitized_storage.upload_blob = AsyncMock(
            return_value={
                "url": f"https://test.blob/sanitized/{org_prefix}/{image_id}.png"
            }
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = "nachet-"
        mock_settings.is_test_environment = True

        # Mock PIL Image
        mock_image = MagicMock()
        mock_image.mode = "RGB"
        mock_image.size = (640, 480)

        mock_sanitized_image = MagicMock()

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
            patch("PIL.Image") as mock_pil,
        ):
            # Setup storage manager to return different clients
            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            # Setup PIL mocks
            mock_pil.open.return_value = mock_image
            mock_pil.new.return_value = mock_sanitized_image

            result = await trigger_sanitization_function_local(
                image_id=image_id,
                org_prefix=org_prefix,
            )

            # Assert
            assert result == f"{org_prefix}/{image_id}.png"

            # Verify download from original container
            mock_external_storage.download_blob.assert_awaited_once()
            download_call = mock_external_storage.download_blob.call_args
            assert download_call.args[0] == "nachet-original-test"
            assert download_call.args[1] == f"{org_prefix}/{image_id}.png"

            # Verify upload to sanitized container
            mock_sanitized_storage.upload_blob.assert_awaited_once()
            upload_call = mock_sanitized_storage.upload_blob.call_args
            assert upload_call.kwargs["container"] == "nachet-sanitized-test"
            assert upload_call.kwargs["name"] == f"{org_prefix}/{image_id}.png"

    async def test_sanitization_download_failure(self):
        """Test that download failures raise SanitizationError."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(
            side_effect=Exception("Blob not found")
        )

        mock_sanitized_storage = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        # Act & Assert
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
        ):

            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            with pytest.raises(SanitizationError) as exc_info:
                await trigger_sanitization_function_local(
                    image_id=image_id,
                    org_prefix=org_prefix,
                )

            assert "Failed to sanitize image" in str(exc_info.value)

    async def test_sanitization_image_conversion_rgb(self):
        """Test that non-RGB images are converted to RGB."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"
        fake_image_bytes = b"fake RGBA image"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(return_value=fake_image_bytes)

        mock_sanitized_storage = AsyncMock()
        mock_sanitized_storage.upload_blob = AsyncMock(
            return_value={"url": "https://test"}
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        # Mock PIL Image with RGBA mode
        mock_image = MagicMock()
        mock_image.mode = "RGBA"  # Not RGB
        mock_image.size = (800, 600)

        mock_rgb_image = MagicMock()
        mock_rgb_image.mode = "RGB"
        mock_image.convert.return_value = mock_rgb_image

        mock_sanitized_image = MagicMock()

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
            patch("PIL.Image") as mock_pil,
        ):

            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            mock_pil.open.return_value = mock_image
            mock_pil.new.return_value = mock_sanitized_image

            result = await trigger_sanitization_function_local(
                image_id=image_id,
                org_prefix=org_prefix,
            )

            # Assert - verify convert() was called
            mock_image.convert.assert_called_once_with("RGB")
            assert result == f"{org_prefix}/{image_id}.png"

    async def test_sanitization_upload_failure(self):
        """Test that upload failures raise SanitizationError."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"
        fake_image_bytes = b"fake image"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(return_value=fake_image_bytes)

        mock_sanitized_storage = AsyncMock()
        mock_sanitized_storage.upload_blob = AsyncMock(
            side_effect=Exception("Upload quota exceeded")
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        mock_image = MagicMock()
        mock_image.mode = "RGB"
        mock_image.size = (640, 480)

        mock_sanitized_image = MagicMock()

        # Act & Assert
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
            patch("PIL.Image") as mock_pil,
        ):

            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            mock_pil.open.return_value = mock_image
            mock_pil.new.return_value = mock_sanitized_image

            with pytest.raises(SanitizationError) as exc_info:
                await trigger_sanitization_function_local(
                    image_id=image_id,
                    org_prefix=org_prefix,
                )

            assert "Failed to sanitize image" in str(exc_info.value)

    async def test_sanitization_corrupted_image(self):
        """Test that corrupted images raise SanitizationError."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"
        corrupted_bytes = b"not a valid image"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(return_value=corrupted_bytes)

        mock_sanitized_storage = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        # Act & Assert
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
            patch("PIL.Image") as mock_pil,
        ):

            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            # PIL.Image.open should raise error for corrupted image
            mock_pil.open.side_effect = Exception("cannot identify image file")

            with pytest.raises(SanitizationError) as exc_info:
                await trigger_sanitization_function_local(
                    image_id=image_id,
                    org_prefix=org_prefix,
                )

            assert "Failed to sanitize image" in str(exc_info.value)

    async def test_sanitization_metadata_added(self):
        """Test that sanitized blob includes metadata."""
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"
        fake_image_bytes = b"fake image"

        mock_external_storage = AsyncMock()
        mock_external_storage.download_blob = AsyncMock(return_value=fake_image_bytes)

        mock_sanitized_storage = AsyncMock()
        mock_sanitized_storage.upload_blob = AsyncMock(
            return_value={"url": "https://test"}
        )

        mock_settings = MagicMock()
        mock_settings.blob_container_prefix = ""
        mock_settings.is_test_environment = False

        mock_image = MagicMock()
        mock_image.mode = "RGB"
        mock_image.size = (640, 480)

        mock_sanitized_image = MagicMock()

        # Act
        with (
            patch("app.blob.manager.blob_storage_manager") as mock_manager,
            patch("app.api.config.get_settings", return_value=mock_settings),
            patch("app.service.sanitization.DBOS") as mock_dbos,
            patch("PIL.Image") as mock_pil,
        ):

            def get_client_side_effect(account):
                if account == BlobAccount.EXTERNAL.value:
                    return mock_external_storage
                return mock_sanitized_storage

            mock_manager.get_client.side_effect = get_client_side_effect
            mock_dbos.logger = MagicMock()

            mock_pil.open.return_value = mock_image
            mock_pil.new.return_value = mock_sanitized_image

            await trigger_sanitization_function_local(
                image_id=image_id,
                org_prefix=org_prefix,
            )

            # Assert - verify metadata in upload call
            upload_call = mock_sanitized_storage.upload_blob.call_args
            metadata = upload_call.kwargs["metadata"]
            assert "original_image_id" in metadata
            assert metadata["original_image_id"] == str(image_id)
            assert "date_sanitized" in metadata
