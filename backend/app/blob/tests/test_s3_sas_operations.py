"""
Tests for SAS (Shared Access Signature) / Presigned URL operations.

This module contains comprehensive tests for S3 presigned URL generation,
which is the S3 equivalent of Azure SAS tokens. Includes permissions validation,
expiry handling, and error cases.

In S3, presigned URLs provide temporary access to private objects without
requiring AWS credentials. This is analogous to Azure's SAS tokens.
"""

import pytest
import os
from datetime import timedelta
from dotenv import load_dotenv

from app.blob.s3.storage import S3BlobStorage
from app.blob.exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
)
from app.api.config import get_settings

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")


# Test configuration
def get_s3_test_config():
    """Get S3 storage config for testing."""
    settings = get_settings()

    # If S3 storage is configured in settings, use it
    if settings.s3_endpoint_url:
        # Return the flat config structure
        config = settings.s3_storage_config
        # Don't print raw config - it contains sensitive credentials
        return {
            "s3_endpoint_url": config["s3_endpoint_url"],
            "s3_access_key_id": config["s3_access_key"],
            "s3_secret_access_key": config["s3_secret_key"],
            "s3_region": config["s3_region_name"],  # Note: config uses 's3_region_name'
            "s3_use_ssl": config["s3_use_ssl"],
            "s3_verify": config["s3_verify"],
        }

    raise ValueError("No S3 Storage configuration found in settings")


TEST_CONTAINER = "nachet-s3-org-0000-0000-0000-0000"
TEST_SAS_CONTAINER = "nachet-s3-test-sas-container"
TEST_BLOB_NAME = "test-sas-blob.txt"


class TestBlobSASOperations:
    """Test blob-specific presigned URL operations (S3 SAS equivalent)."""

    @pytest.fixture
    def storage(self):
        """Create S3BlobStorage instance for testing."""
        config = get_s3_test_config()
        return S3BlobStorage(config)

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        return b"Sample image data for SAS testing"

    @pytest.mark.asyncio
    async def test_generate_blob_sas_read_permission(
        self, storage: S3BlobStorage, sample_image_data: bytes
    ):
        """Test generating presigned URL with read permission."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
        )

        assert "sas_token" in result or "presigned_url" in result
        assert "sas_url" in result or "url" in result
        assert "blob_url" in result or "url" in result
        assert result.get("permissions") == ["read"] or "read" in str(result)
        assert result["container"] == TEST_CONTAINER
        assert result["blob_name"] == TEST_BLOB_NAME
        assert "expiry" in result or "expires" in result

        # Verify URL structure
        url = result.get("sas_url") or result.get("url")
        assert TEST_CONTAINER in url
        assert TEST_BLOB_NAME in url
        assert "?" in url or "X-Amz" in url  # Presigned URL has query parameters

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)

    @pytest.mark.asyncio
    async def test_generate_blob_sas_multiple_permissions(
        self, storage: S3BlobStorage, sample_image_data: bytes
    ):
        """Test generating presigned URL with multiple permissions."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read", "write", "delete"],
            expiry=timedelta(hours=2),
        )

        # In S3, presigned URLs are typically for single operations
        # but we should still get a valid URL
        assert "sas_url" in result or "url" in result

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)

    @pytest.mark.asyncio
    async def test_generate_blob_sas_custom_expiry(
        self, storage: S3BlobStorage, sample_image_data: bytes
    ):
        """Test generating presigned URL with custom expiry time."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        # Short expiry: 30 minutes
        result_short = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(minutes=30),
        )

        assert "sas_url" in result_short or "url" in result_short

        # Longer expiry: 24 hours
        result_long = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=24),
        )

        assert "sas_url" in result_long or "url" in result_long

        # URLs should be different due to different expiry times
        url_short = result_short.get("sas_url") or result_short.get("url")
        url_long = result_long.get("sas_url") or result_long.get("url")
        assert url_short != url_long

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)

    @pytest.mark.asyncio
    async def test_generate_blob_sas_nonexistent_blob(self, storage: S3BlobStorage):
        """Test generating presigned URL for non-existent blob."""
        non_existent_blob = "nonexistent-blob-for-sas.txt"

        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # S3 allows generating presigned URLs for non-existent objects
        # (they can be used for uploads), but we'll test error handling
        try:
            result = await storage.generate_sas_token(
                container=TEST_CONTAINER,
                name=non_existent_blob,
                permissions=["read"],
                expiry=timedelta(hours=1),
            )
            # If successful, URL should still be generated
            assert "sas_url" in result or "url" in result
        except BlobNotFoundError:
            # Some implementations may raise error for non-existent blob
            pass

    @pytest.mark.asyncio
    async def test_generate_blob_sas_nonexistent_container(
        self, storage: S3BlobStorage
    ):
        """Test generating presigned URL for blob in non-existent container."""
        non_existent_container = "nachet-s3-test-nonexistent-container"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.generate_sas_token(
                container=non_existent_container,
                name=TEST_BLOB_NAME,
                permissions=["read"],
                expiry=timedelta(hours=1),
            )

    @pytest.mark.asyncio
    async def test_generate_blob_sas_write_permission(
        self, storage: S3BlobStorage, sample_image_data: bytes
    ):
        """Test generating presigned URL with write permission."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # For write, blob doesn't need to exist yet
        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name="new-upload-blob.txt",
            permissions=["write"],
            expiry=timedelta(hours=1),
        )

        assert "sas_url" in result or "url" in result
        url = result.get("sas_url") or result.get("url")
        assert TEST_CONTAINER in url

        # Cleanup if blob was created
        try:
            await storage.delete_blob(TEST_CONTAINER, "new-upload-blob.txt")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_generate_blob_sas_invalid_permissions(
        self, storage: S3BlobStorage, sample_image_data: bytes
    ):
        """Test generating presigned URL with invalid permissions."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        # Test with invalid permission
        # Note: S3 might handle this differently than Azure
        try:
            _result = await storage.generate_sas_token(
                container=TEST_CONTAINER,
                name=TEST_BLOB_NAME,
                permissions=["invalid_permission"],
                expiry=timedelta(hours=1),
            )
            # Some implementations may ignore invalid permissions
            # or map them to valid S3 operations
        except (ValueError, BlobStorageError):
            # Expected if validation is strict
            pass

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)


class TestContainerSASOperations:
    """Test container-specific presigned URL operations."""

    @pytest.fixture
    def storage(self):
        """Create S3BlobStorage instance for testing."""
        config = get_s3_test_config()
        return S3BlobStorage(config)

    @pytest.mark.asyncio
    async def test_generate_container_sas_read_permission(self, storage: S3BlobStorage):
        """Test generating container-level presigned URL with read permission."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read"],
            expiry=timedelta(hours=1),
        )

        # S3 doesn't have exact container-level SAS like Azure
        # Implementation may provide bucket-level access or list operations
        assert isinstance(result, dict)
        assert "container" in result or "bucket" in result

    @pytest.mark.asyncio
    async def test_generate_container_sas_list_permission(self, storage: S3BlobStorage):
        """Test generating container presigned URL with list permission."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["list"],
            expiry=timedelta(hours=2),
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_container_sas_multiple_permissions(
        self, storage: S3BlobStorage
    ):
        """Test generating container presigned URL with multiple permissions."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read", "write", "list"],
            expiry=timedelta(hours=4),
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_container_sas_nonexistent_container(
        self, storage: S3BlobStorage
    ):
        """Test generating presigned URL for non-existent container."""
        non_existent_container = "nachet-s3-test-nonexistent-sas"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.generate_container_sas_token(
                container=non_existent_container,
                permissions=["read"],
                expiry=timedelta(hours=1),
            )

    @pytest.mark.asyncio
    async def test_generate_container_sas_custom_expiry(self, storage: S3BlobStorage):
        """Test generating container presigned URL with different expiry times."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # Short expiry
        result_short = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read"],
            expiry=timedelta(minutes=15),
        )

        # Long expiry
        result_long = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read"],
            expiry=timedelta(days=1),
        )

        # Both should succeed
        assert isinstance(result_short, dict)
        assert isinstance(result_long, dict)


class TestSASEdgeCases:
    """Test edge cases for presigned URL generation."""

    @pytest.fixture
    def storage(self):
        """Create S3BlobStorage instance for testing."""
        config = get_s3_test_config()
        return S3BlobStorage(config)

    @pytest.mark.asyncio
    async def test_generate_sas_minimum_expiry(self, storage: S3BlobStorage):
        """Test generating presigned URL with minimum expiry time."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # Upload test blob
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, b"test")

        # Very short expiry (1 minute)
        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(minutes=1),
        )

        assert "sas_url" in result or "url" in result

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)

    @pytest.mark.asyncio
    async def test_generate_sas_maximum_expiry(self, storage: S3BlobStorage):
        """Test generating presigned URL with maximum expiry time."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # Upload test blob
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, b"test")

        # Long expiry (7 days - S3 max is typically 7 days)
        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(days=7),
        )

        assert "sas_url" in result or "url" in result

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)

    @pytest.mark.asyncio
    async def test_generate_sas_empty_permissions(self, storage: S3BlobStorage):
        """Test generating presigned URL with empty permissions list."""
        # Ensure container exists
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # Upload test blob
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, b"test")

        # Empty permissions should fail or default to read
        try:
            result = await storage.generate_sas_token(
                container=TEST_CONTAINER,
                name=TEST_BLOB_NAME,
                permissions=[],
                expiry=timedelta(hours=1),
            )
            # If it succeeds, it should have a URL
            assert "sas_url" in result or "url" in result
        except (ValueError, BlobStorageError):
            # Expected if validation requires at least one permission
            pass

        # Cleanup
        await storage.delete_blob(TEST_CONTAINER, TEST_BLOB_NAME)


if __name__ == "__main__":
    """Run tests with pytest when executed directly."""
    pytest.main([__file__, "-v", "-s"])
