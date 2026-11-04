"""
Tests for SAS (Shared Access Signature) token operations.

This module contains comprehensive tests for blob and container SAS token generation,
including permissions validation, expiry handling, and error cases.
"""

import pytest
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from ..azure.storage import AzureBlobStorage
from ..exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
)
from app.api.config import get_settings

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")


def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()

    # If blob storage is configured in settings, use it
    if settings.blob_storage_name and settings.blob_storage_key:
        return settings.blob_storage_config

    raise ValueError("No Azure Storage configuration found in settings")


TEST_CONTAINER = "nachet-org-0000-0000-0000-0000"
TEST_SAS_CONTAINER = "nachet-unit-test-sas-container"
TEST_BLOB_NAME = "test-sas-blob.txt"


class TestBlobSASOperations:
    """Test blob-specific SAS token operations."""

    @pytest.fixture
    def storage(self):
        """Create AzureBlobStorage instance for testing."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        return b"Sample image data for SAS testing"

    @pytest.mark.asyncio
    async def test_generate_blob_sas_read_permission(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with read permission."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
        )

        assert "sas_token" in result
        assert "sas_url" in result
        assert "blob_url" in result
        assert result["permissions"] == ["read"]
        assert result["container"] == TEST_CONTAINER
        assert result["blob_name"] == TEST_BLOB_NAME
        assert "expiry" in result

        # Verify URL structure
        assert TEST_CONTAINER in result["sas_url"]
        assert TEST_BLOB_NAME in result["sas_url"]
        assert "?" in result["sas_url"]  # SAS token separator

    @pytest.mark.asyncio
    async def test_generate_blob_sas_multiple_permissions(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with multiple permissions."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read", "write", "delete"],
            expiry=timedelta(hours=2),
        )

        assert result["permissions"] == ["read", "write", "delete"]
        assert "sas_token" in result
        assert len(result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_generate_blob_sas_with_start_time(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with custom start time."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        start_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
            start_time=start_time,
        )

        assert "start_time" in result
        # Verify start time is properly formatted
        parsed_start = datetime.fromisoformat(
            result["start_time"].replace("Z", "+00:00").replace("+00:00", "")
        ).replace(tzinfo=timezone.utc)
        assert abs((parsed_start - start_time).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_generate_blob_sas_with_content_headers(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with content headers."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
            content_type="text/plain",
            content_disposition="attachment; filename=test.txt",
            cache_control="max-age=3600",
        )

        assert "sas_token" in result
        # Content headers are embedded in the SAS token, so we can't directly verify them
        # but we can ensure the token was generated successfully
        assert len(result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_generate_blob_sas_with_ip_restriction(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with IP restriction."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
            ip="192.168.1.0/24",
        )

        assert "sas_token" in result
        assert len(result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_generate_blob_sas_invalid_permission(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with invalid permission."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        with pytest.raises(BlobStorageError) as exc_info:
            await storage.generate_sas_token(
                container=TEST_CONTAINER,
                name=TEST_BLOB_NAME,
                permissions=["invalid_permission"],
                expiry=timedelta(hours=1),
            )

        assert "Invalid permission 'invalid_permission'" in str(exc_info.value)
        assert "Valid permissions for blobs:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_blob_sas_nonexistent_container(
        self, storage: AzureBlobStorage
    ):
        """Test generating SAS token for blob in nonexistent container."""
        with pytest.raises(ContainerNotFoundError) as exc_info:
            await storage.generate_sas_token(
                container="nonexistent-container",
                name=TEST_BLOB_NAME,
                permissions=["read"],
                expiry=timedelta(hours=1),
            )

        assert "nonexistent-container" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_blob_sas_nonexistent_blob(self, storage: AzureBlobStorage):
        """Test generating SAS token for nonexistent blob."""
        await storage.create_container(TEST_CONTAINER)

        with pytest.raises(BlobNotFoundError) as exc_info:
            await storage.generate_sas_token(
                container=TEST_CONTAINER,
                name="nonexistent-blob.txt",
                permissions=["read"],
                expiry=timedelta(hours=1),
            )

        assert "nonexistent-blob.txt" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_blob_sas_all_permissions(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test generating SAS token with all available permissions."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        all_permissions = ["read", "write", "delete", "add", "create"]
        result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=all_permissions,
            expiry=timedelta(hours=1),
        )

        assert result["permissions"] == all_permissions
        assert len(result["sas_token"]) > 0


class TestContainerSASOperations:
    """Test container-level SAS token operations."""

    @pytest.fixture
    def storage(self):
        """Create AzureBlobStorage instance for testing."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        return b"Sample image data for SAS testing"

    @pytest.mark.asyncio
    async def test_generate_container_sas_read_permission(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with read permission."""
        await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER, permissions=["read"], expiry=timedelta(hours=1)
        )

        assert "sas_token" in result
        assert "sas_url" in result
        assert "container_url" in result
        assert result["permissions"] == ["read"]
        assert result["container"] == TEST_CONTAINER
        assert "expiry" in result

        # Verify URL structure
        assert TEST_CONTAINER in result["sas_url"]
        assert "?" in result["sas_url"]  # SAS token separator

    @pytest.mark.asyncio
    async def test_generate_container_sas_list_permission(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with list permission."""
        await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER, permissions=["list"], expiry=timedelta(hours=1)
        )

        assert result["permissions"] == ["list"]
        assert len(result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_generate_container_sas_multiple_permissions(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with multiple permissions."""
        await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read", "write", "list", "delete"],
            expiry=timedelta(hours=2),
        )

        assert result["permissions"] == ["read", "write", "list", "delete"]
        assert "sas_token" in result

    @pytest.mark.asyncio
    async def test_generate_container_sas_with_start_time(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with custom start time."""
        await storage.create_container(TEST_CONTAINER)

        start_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read"],
            expiry=timedelta(hours=1),
            start_time=start_time,
        )

        assert "start_time" in result
        parsed_start = datetime.fromisoformat(
            result["start_time"].replace("Z", "+00:00").replace("+00:00", "")
        ).replace(tzinfo=timezone.utc)
        assert abs((parsed_start - start_time).total_seconds()) < 2

    @pytest.mark.asyncio
    async def test_generate_container_sas_with_ip_restriction(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with IP restriction."""
        await storage.create_container(TEST_CONTAINER)

        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=["read", "list"],
            expiry=timedelta(hours=1),
            ip="10.0.0.0/8",
        )

        assert "sas_token" in result
        assert len(result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_generate_container_sas_invalid_permission(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with invalid permission."""
        await storage.create_container(TEST_CONTAINER)

        with pytest.raises(BlobStorageError) as exc_info:
            await storage.generate_container_sas_token(
                container=TEST_CONTAINER,
                permissions=["invalid_permission"],
                expiry=timedelta(hours=1),
            )

        assert "Invalid permission 'invalid_permission'" in str(exc_info.value)
        assert "Valid permissions for containers:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_container_sas_nonexistent_container(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token for nonexistent container."""
        with pytest.raises(ContainerNotFoundError) as exc_info:
            await storage.generate_container_sas_token(
                container="nonexistent-container",
                permissions=["read"],
                expiry=timedelta(hours=1),
            )

        assert "nonexistent-container" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_container_sas_all_permissions(
        self, storage: AzureBlobStorage
    ):
        """Test generating container SAS token with all available permissions."""
        await storage.create_container(TEST_CONTAINER)

        all_permissions = ["read", "write", "delete", "list", "add", "create"]
        result = await storage.generate_container_sas_token(
            container=TEST_CONTAINER,
            permissions=all_permissions,
            expiry=timedelta(hours=1),
        )

        assert result["permissions"] == all_permissions
        assert len(result["sas_token"]) > 0


class TestSASIntegrationScenarios:
    """Test real-world SAS integration scenarios."""

    @pytest.fixture
    def storage(self):
        """Create AzureBlobStorage instance for testing."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        return b"Sample image data for SAS testing"

    @pytest.mark.asyncio
    async def test_sas_workflow_blob_upload_scenario(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test complete workflow: create container, generate SAS for upload, verify blob."""
        container_name = "test-sas-workflow"
        blob_name = "uploaded-via-sas.txt"

        # Create container and upload a blob
        await storage.create_container(container_name)
        await storage.upload_blob(container_name, blob_name, sample_image_data)

        # Generate SAS token for read access
        sas_result = await storage.generate_sas_token(
            container=container_name,
            name=blob_name,
            permissions=["read"],
            expiry=timedelta(hours=1),
        )

        # Verify the blob can be accessed (indirectly by checking properties)
        properties = await storage.get_blob_properties(container_name, blob_name)
        assert properties["name"] == blob_name
        assert sas_result["sas_url"] is not None

    @pytest.mark.asyncio
    async def test_sas_workflow_container_operations(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test container-level SAS operations workflow."""
        container_name = "test-sas-container-ops"
        blob_name = "test-blob.txt"

        # Create container and upload blob
        await storage.create_container(container_name)
        await storage.upload_blob(container_name, blob_name, sample_image_data)

        # Generate container SAS token with list and read permissions
        sas_result = await storage.generate_container_sas_token(
            container=container_name,
            permissions=["list", "read"],
            expiry=timedelta(hours=1),
        )

        # Verify container operations work
        container_exists = await storage.container_exists(container_name)
        assert container_exists

        # List blobs to verify container access would work
        blob_list = await storage.list_blobs(container_name)
        assert len(blob_list["blobs"]) > 0
        assert any(blob["name"] == blob_name for blob in blob_list["blobs"])
        assert sas_result["sas_url"] is not None

    @pytest.mark.asyncio
    async def test_sas_expiry_boundary_conditions(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test SAS token generation with various expiry times."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        # Test very short expiry (1 minute)
        short_result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(minutes=1),
        )

        # Test longer expiry (7 days - maximum for user delegation SAS)
        long_result = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(days=7),
        )

        assert short_result["sas_token"] != long_result["sas_token"]
        assert len(short_result["sas_token"]) > 0
        assert len(long_result["sas_token"]) > 0

    @pytest.mark.asyncio
    async def test_sas_permission_combinations(
        self, storage: AzureBlobStorage, sample_image_data: bytes
    ):
        """Test various permission combinations for practical use cases."""
        await storage.create_container(TEST_CONTAINER)
        await storage.upload_blob(TEST_CONTAINER, TEST_BLOB_NAME, sample_image_data)

        # Read-only access (common for downloads)
        read_only = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read"],
            expiry=timedelta(hours=1),
        )

        # Write access (for uploads/updates)
        write_access = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read", "write", "create"],
            expiry=timedelta(hours=1),
        )

        # Full access (administrative)
        full_access = await storage.generate_sas_token(
            container=TEST_CONTAINER,
            name=TEST_BLOB_NAME,
            permissions=["read", "write", "delete", "add", "create"],
            expiry=timedelta(hours=1),
        )

        # Verify all tokens are different and valid
        tokens = [
            read_only["sas_token"],
            write_access["sas_token"],
            full_access["sas_token"],
        ]
        assert len(set(tokens)) == 3  # All tokens should be unique
        assert all(len(token) > 0 for token in tokens)
