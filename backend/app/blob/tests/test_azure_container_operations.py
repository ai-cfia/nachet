"""
Test suite for Azure Blob Storage container operations.

This comprehensive test suite covers all container management operations:
- create_container()
- container_exists()
- get_container_properties()
- delete_container()

These tests run against real Azure Blob Storage or Azurite and include:
1. Happy path scenarios for all operations
2. Error handling and edge cases
3. Container lifecycle testing
4. Validation of return types and models
5. Metadata and properties handling

Note: Tests require a valid Azure Storage connection string.
Set the environment variable AZURE_STORAGE_CONNECTION_STRING or use Azurite for local testing.
"""

import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

from app.blob.azure.storage import AzureBlobStorage
from app.blob.models import ContainerInfo
from app.blob.exceptions import (
    InvalidConfigurationError,
    ConnectionError,
    BlobStorageError,
    ContainerNotFoundError,
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


async def cleanup_test_containers():
    """Helper function to clean up test containers."""
    try:
        config = get_test_config()
        storage = AzureBlobStorage(config)

        # List all containers and delete any that start with our test prefix
        containers_result = await storage.list_containers()
        containers = containers_result.get("containers", [])

        for container_info in containers:
            container_name = container_info["name"]
            if container_name.startswith("nachet-unit-test-"):
                try:
                    await storage.delete_container(container_name)
                    print(f"Cleaned up test container: {container_name}")
                except Exception as e:
                    print(f"Failed to clean up container {container_name}: {e}")

    except Exception as e:
        print(f"Error during test container cleanup: {e}")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_and_cleanup_test_containers():
    """
    Session-level fixture to clean up test containers before and after testing.
    This ensures we start with a clean slate and don't leave containers behind.
    """
    # Clean up any existing test containers before starting
    await cleanup_test_containers()

    yield  # Run all tests

    # Clean up test containers after all tests are done
    await cleanup_test_containers()


class TestContainerOperations:
    """Test container management operations."""

    @pytest.fixture
    def storage(self):
        """Create AzureBlobStorage instance for testing."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.fixture
    def test_container_name(self):
        """Generate unique test container name."""
        # Use lowercase letters and numbers for Azure compliance
        return f"nachet-unit-test-{uuid.uuid4().hex[:8]}"

    @pytest_asyncio.fixture
    async def cleanup_containers(self, storage):
        """Fixture to clean up test containers after tests."""
        created_containers = []

        def track_container(name):
            created_containers.append(name)
            return name

        yield track_container

        # Cleanup - delete all created containers
        for container_name in created_containers:
            try:
                await storage.delete_container(container_name)
            except Exception:
                pass  # Ignore cleanup errors


class TestCreateContainer(TestContainerOperations):
    """Test create_container() method."""

    @pytest.mark.asyncio
    async def test_create_container_basic(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test basic container creation."""
        cleanup_containers(test_container_name)

        # Ensure container doesn't exist first
        exists_before = await storage.container_exists(test_container_name)
        assert not exists_before

        # Create container
        result = await storage.create_container(test_container_name)

        # Validate response
        assert isinstance(result, dict)
        assert result["name"] == test_container_name
        assert "etag" in result
        assert "last_modified" in result
        assert isinstance(result["metadata"], dict)

        # Verify container was created
        exists_after = await storage.container_exists(test_container_name)
        assert exists_after

    @pytest.mark.asyncio
    async def test_create_container_with_metadata(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test container creation with metadata."""
        cleanup_containers(test_container_name)

        metadata = {"purpose": "testing", "created_by": "test_suite", "version": "1.0"}

        # Create container with metadata
        result = await storage.create_container(test_container_name, metadata=metadata)

        # Validate metadata is included
        assert result["metadata"] == metadata

        # Verify metadata persists
        properties = await storage.get_container_properties(test_container_name)
        assert properties["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_create_container_already_exists(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test creating a container that already exists."""
        cleanup_containers(test_container_name)

        # Create container first time
        result1 = await storage.create_container(test_container_name)

        # Create container second time (should return existing)
        result2 = await storage.create_container(test_container_name)

        # Should return existing container properties
        assert result1["name"] == result2["name"]
        assert result1["etag"] == result2["etag"]

    @pytest.mark.asyncio
    async def test_create_container_invalid_name(self, storage):
        """Test container creation with invalid names."""
        invalid_names = [
            "",  # Empty name
            "ab",  # Too short (less than 3 characters)
            "a" * 64,  # Too long (more than 63 characters)
            "-startwithhyphen",  # Cannot start with hyphen
            "endwithhyphen-",  # Cannot end with hyphen
            "double--hyphen",  # Cannot have consecutive hyphens
        ]

        for invalid_name in invalid_names:
            with pytest.raises(InvalidConfigurationError):
                await storage.create_container(invalid_name)


class TestContainerExists(TestContainerOperations):
    """Test container_exists() method."""

    @pytest.mark.asyncio
    async def test_container_exists_true(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test container_exists returns True for existing container."""
        cleanup_containers(test_container_name)

        # Create container
        await storage.create_container(test_container_name)

        # Check existence
        exists = await storage.container_exists(test_container_name)
        assert exists is True

    @pytest.mark.asyncio
    async def test_container_exists_false(self, storage):
        """Test container_exists returns False for non-existing container."""
        non_existent_name = f"nachet-unit-test-nonexistent-{uuid.uuid4().hex[:8]}"

        # Check existence of non-existent container
        exists = await storage.container_exists(non_existent_name)
        assert exists is False

    @pytest.mark.asyncio
    async def test_container_exists_after_deletion(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test container_exists returns False after deletion."""
        cleanup_containers(test_container_name)

        # Create and verify container
        await storage.create_container(test_container_name)
        assert await storage.container_exists(test_container_name) is True

        # Delete container
        deleted = await storage.delete_container(test_container_name)
        assert deleted is True

        # Check existence after deletion
        exists = await storage.container_exists(test_container_name)
        assert exists is False


class TestGetContainerProperties(TestContainerOperations):
    """Test get_container_properties() method."""

    @pytest.mark.asyncio
    async def test_get_container_properties_basic(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test getting basic container properties."""
        cleanup_containers(test_container_name)

        # Create container
        await storage.create_container(test_container_name)

        # Get properties
        properties = await storage.get_container_properties(test_container_name)

        # Validate response structure
        assert isinstance(properties, dict)
        assert properties["name"] == test_container_name
        assert "etag" in properties
        assert "last_modified" in properties
        assert isinstance(properties["metadata"], dict)

    @pytest.mark.asyncio
    async def test_get_container_properties_with_metadata(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test getting container properties with metadata."""
        cleanup_containers(test_container_name)

        metadata = {
            "environment": "test",
            "owner": "test_suite",
            "purpose": "container_properties_test",
        }

        # Create container with metadata
        await storage.create_container(test_container_name, metadata=metadata)

        # Get properties
        properties = await storage.get_container_properties(test_container_name)

        # Validate metadata
        assert properties["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_get_container_properties_not_found(self, storage):
        """Test getting properties of non-existent container."""
        non_existent_name = f"nachet-unit-test-nonexistent-{uuid.uuid4().hex[:8]}"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.get_container_properties(non_existent_name)

    @pytest.mark.asyncio
    async def test_get_container_properties_model_validation(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test that returned properties can be validated as ContainerInfo model."""
        cleanup_containers(test_container_name)

        # Create container
        await storage.create_container(test_container_name)

        # Get properties
        properties = await storage.get_container_properties(test_container_name)

        # Should be able to create ContainerInfo from returned data
        container_info = ContainerInfo(**properties)
        assert container_info.name == test_container_name
        assert isinstance(container_info.last_modified, datetime)
        assert isinstance(container_info.metadata, dict)


class TestDeleteContainer(TestContainerOperations):
    """Test delete_container() method."""

    @pytest.mark.asyncio
    async def test_delete_container_success(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test successful container deletion."""
        cleanup_containers(test_container_name)

        # Create container
        await storage.create_container(test_container_name)
        assert await storage.container_exists(test_container_name) is True

        # Delete container
        deleted = await storage.delete_container(test_container_name)

        # Validate deletion
        assert deleted is True
        assert await storage.container_exists(test_container_name) is False

    @pytest.mark.asyncio
    async def test_delete_container_not_found(self, storage):
        """Test deleting non-existent container."""
        non_existent_name = f"nachet-unit-test-nonexistent-{uuid.uuid4().hex[:8]}"

        # Should return False for non-existent container
        deleted = await storage.delete_container(non_existent_name)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_container_with_metadata(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test deleting container that has metadata."""
        cleanup_containers(test_container_name)

        metadata = {"test": "data", "purpose": "deletion_test"}

        # Create container with metadata
        await storage.create_container(test_container_name, metadata=metadata)

        # Verify creation
        properties = await storage.get_container_properties(test_container_name)
        assert properties["metadata"] == metadata

        # Delete container
        deleted = await storage.delete_container(test_container_name)
        assert deleted is True

        # Verify deletion
        assert await storage.container_exists(test_container_name) is False


class TestContainerLifecycle(TestContainerOperations):
    """Test complete container lifecycle operations."""

    @pytest.mark.asyncio
    async def test_complete_container_lifecycle(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test complete container lifecycle: create -> exists -> properties -> delete."""
        cleanup_containers(test_container_name)

        # Step 1: Verify container doesn't exist
        assert await storage.container_exists(test_container_name) is False

        # Step 2: Create container with metadata
        metadata = {"lifecycle": "test", "stage": "creation"}
        result = await storage.create_container(test_container_name, metadata=metadata)

        assert result["name"] == test_container_name
        assert result["metadata"] == metadata

        # Step 3: Verify container exists
        assert await storage.container_exists(test_container_name) is True

        # Step 4: Get and validate properties
        properties = await storage.get_container_properties(test_container_name)
        assert properties["name"] == test_container_name
        assert properties["metadata"] == metadata

        # Step 5: Delete container
        deleted = await storage.delete_container(test_container_name)
        assert deleted is True

        # Step 6: Verify container no longer exists
        assert await storage.container_exists(test_container_name) is False

        # Step 7: Verify properties access fails
        with pytest.raises(ContainerNotFoundError):
            await storage.get_container_properties(test_container_name)

    @pytest.mark.asyncio
    async def test_multiple_containers_lifecycle(self, storage, cleanup_containers):
        """Test managing multiple containers simultaneously."""
        container_names = [
            f"nachet-unit-test-multi-{i}-{uuid.uuid4().hex[:6]}" for i in range(3)
        ]

        # Track all for cleanup
        for name in container_names:
            cleanup_containers(name)

        # Create multiple containers
        for i, name in enumerate(container_names):
            metadata = {"index": str(i), "batch": "multi_test"}
            await storage.create_container(name, metadata=metadata)

        # Verify all exist
        for name in container_names:
            assert await storage.container_exists(name) is True

        # Verify properties of each
        for i, name in enumerate(container_names):
            properties = await storage.get_container_properties(name)
            assert properties["name"] == name
            assert properties["metadata"]["index"] == str(i)
            assert properties["metadata"]["batch"] == "multi_test"

        # Delete all containers
        for name in container_names:
            deleted = await storage.delete_container(name)
            assert deleted is True

        # Verify all are deleted
        for name in container_names:
            assert await storage.container_exists(name) is False


class TestContainerErrorHandling(TestContainerOperations):
    """Test error handling in container operations."""

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, storage):
        """Test handling of connection errors."""
        # Mock the container operations client to raise ServiceRequestError
        with patch.object(storage._container_ops, "_client") as mock_client:
            mock_container_client = MagicMock()
            mock_client.get_container_client.return_value = mock_container_client

            # Mock ServiceRequestError
            from azure.core.exceptions import ServiceRequestError

            mock_container_client.exists.side_effect = ServiceRequestError(
                "Connection failed"
            )

            # Should raise ConnectionError
            with pytest.raises(ConnectionError):
                await storage.container_exists("test-container")

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, storage):
        """Test handling of generic errors."""
        # Mock the container operations client to raise generic exception
        with patch.object(storage._container_ops, "_client") as mock_client:
            mock_container_client = MagicMock()
            mock_client.get_container_client.return_value = mock_container_client

            # Mock generic exception
            mock_container_client.exists.side_effect = Exception("Generic error")

            # Should raise BlobStorageError
            with pytest.raises(BlobStorageError):
                await storage.container_exists("test-container")

    @pytest.mark.asyncio
    async def test_pydantic_validation_in_create(self, storage):
        """Test Pydantic validation errors in create_container."""
        # Test with invalid container name that fails Pydantic validation
        with pytest.raises(InvalidConfigurationError) as exc_info:
            await storage.create_container("INVALID_NAME")

        assert "Invalid container name" in str(exc_info.value)
