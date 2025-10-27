"""
Test suite for S3-compatible Blob Storage container operations.

This comprehensive test suite covers all container management operations:
- create_container()
- container_exists()
- get_container_properties()
- delete_container()
- list_containers()

These tests run against Apache Ozone S3 Gateway (or AWS S3) and include:
1. Happy path scenarios for all operations
2. Error handling and edge cases
3. Container lifecycle testing
4. Validation of return types and models
5. Metadata and properties handling

Note: Tests require S3 connection configuration.
Set environment variables: S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY
or use defaults for local Apache Ozone.
"""

import pytest
import pytest_asyncio
import os
import uuid
from dotenv import load_dotenv

from app.blob.s3.storage import S3BlobStorage
from app.blob.exceptions import (
    InvalidConfigurationError,
    BlobStorageError,
    ContainerNotFoundError,
)  # Load test environment variables
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
            "s3_access_key": config["s3_access_key"],
            "s3_secret_key": config["s3_secret_key"],
            "s3_region_name": config[
                "s3_region_name"
            ],  # Note: config uses 's3_region_name'
            "s3_use_ssl": config["s3_use_ssl"],
            "s3_verify": config["s3_verify"],
        }

    raise ValueError("No S3 Storage configuration found in settings")


async def cleanup_test_containers():
    """Helper function to clean up test containers."""
    try:
        config = get_s3_test_config()
        storage = S3BlobStorage(config)

        # List all containers and delete any that start with our test prefix
        containers_result = await storage.list_containers()
        containers = containers_result.get("containers", [])

        for container_info in containers:
            container_name = container_info["name"]
            if container_name.startswith("nachet-s3-test-"):
                try:
                    # Delete all objects in the container first
                    blobs_result = await storage.list_blobs(container_name)
                    for blob in blobs_result.get("blobs", []):
                        await storage.delete_blob(container_name, blob["name"])

                    # Now delete the container
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


class TestS3ContainerOperations:
    """Test container management operations."""

    @pytest.fixture
    def storage(self):
        """Create S3BlobStorage instance for testing."""
        config = get_s3_test_config()
        return S3BlobStorage(config)

    @pytest.fixture
    def test_container_name(self):
        """Generate unique test container name."""
        # S3 bucket names: lowercase letters, numbers, hyphens (3-63 chars)
        return f"nachet-s3-test-{uuid.uuid4().hex[:8]}"

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
                # Delete all blobs first
                try:
                    blobs_result = await storage.list_blobs(container_name)
                    for blob in blobs_result.get("blobs", []):
                        await storage.delete_blob(container_name, blob["name"])
                except Exception:
                    pass

                # Delete container
                await storage.delete_container(container_name)
            except Exception:
                pass  # Ignore cleanup errors


class TestCreateContainer(TestS3ContainerOperations):
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
        assert "last_modified" in result or "creation_date" in result
        assert isinstance(result.get("metadata", {}), dict)

        # Verify container was created
        exists_after = await storage.container_exists(test_container_name)
        assert exists_after

    @pytest.mark.asyncio
    async def test_create_container_with_metadata(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test container creation with metadata (S3 tags)."""
        cleanup_containers(test_container_name)

        metadata = {"purpose": "testing", "created_by": "test_suite", "version": "1.0"}

        # Create container with metadata (stored as tags in S3)
        result = await storage.create_container(test_container_name, metadata=metadata)

        # Validate container was created
        assert result["name"] == test_container_name

        # Note: S3 bucket metadata/tags might not be immediately available
        # Verify container exists
        exists = await storage.container_exists(test_container_name)
        assert exists

    @pytest.mark.asyncio
    async def test_create_container_already_exists(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test creating a container that already exists."""
        cleanup_containers(test_container_name)

        # Create container first time
        result1 = await storage.create_container(test_container_name)

        # Create container second time (should handle gracefully)
        result2 = await storage.create_container(test_container_name)

        # Should return existing container properties
        assert result1["name"] == result2["name"]

    @pytest.mark.asyncio
    async def test_create_container_invalid_name(self, storage):
        """Test container creation with invalid names."""
        invalid_names = [
            "",  # Empty name
            "ab",  # Too short (less than 3 characters)
            "a" * 64,  # Too long (more than 63 characters)
            "UPPERCASE",  # Uppercase not allowed in S3
            "under_score",  # Underscores not allowed
            "period.",  # Cannot end with period
            ".startperiod",  # Cannot start with period
            "double--hyphen",  # Cannot have consecutive hyphens
            "192.168.1.1",  # Cannot be IP address format
        ]

        for invalid_name in invalid_names:
            with pytest.raises((InvalidConfigurationError, BlobStorageError)):
                await storage.create_container(invalid_name)


class TestContainerExists(TestS3ContainerOperations):
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
        non_existent_name = f"nachet-s3-test-nonexistent-{uuid.uuid4().hex[:8]}"

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


class TestGetContainerProperties(TestS3ContainerOperations):
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
        # S3 buckets may not have etag but should have creation date or last modified
        assert "creation_date" in properties or "last_modified" in properties

    @pytest.mark.asyncio
    async def test_get_container_properties_not_found(self, storage):
        """Test getting properties for non-existent container."""
        non_existent_name = f"nachet-s3-test-nonexistent-{uuid.uuid4().hex[:8]}"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.get_container_properties(non_existent_name)

    @pytest.mark.asyncio
    async def test_get_container_properties_after_creation(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test that properties are consistent after creation."""
        cleanup_containers(test_container_name)

        # Create container
        create_result = await storage.create_container(test_container_name)

        # Get properties
        properties = await storage.get_container_properties(test_container_name)

        # Names should match
        assert create_result["name"] == properties["name"]


class TestDeleteContainer(TestS3ContainerOperations):
    """Test delete_container() method."""

    @pytest.mark.asyncio
    async def test_delete_container_basic(self, storage, test_container_name):
        """Test basic container deletion."""
        # Create container
        await storage.create_container(test_container_name)

        # Verify it exists
        exists_before = await storage.container_exists(test_container_name)
        assert exists_before is True

        # Delete container
        deleted = await storage.delete_container(test_container_name)
        assert deleted is True

        # Verify it no longer exists
        exists_after = await storage.container_exists(test_container_name)
        assert exists_after is False

    @pytest.mark.asyncio
    async def test_delete_container_not_found(self, storage):
        """Test deleting non-existent container."""
        non_existent_name = f"nachet-s3-test-nonexistent-{uuid.uuid4().hex[:8]}"

        # Should return False for non-existent container
        deleted = await storage.delete_container(non_existent_name)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_container_with_blobs(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test deleting container that contains blobs (should fail or require force)."""
        cleanup_containers(test_container_name)

        # Create container and upload a blob
        await storage.create_container(test_container_name)
        await storage.upload_blob(test_container_name, "test-file.txt", b"test content")

        # S3 requires empty bucket to delete
        # Should fail because bucket is not empty
        with pytest.raises((BlobStorageError, ContainerNotFoundError)):
            await storage.delete_container(test_container_name)

        # Clean up manually
        await storage.delete_blob(test_container_name, "test-file.txt")
        await storage.delete_container(test_container_name)


class TestListContainers(TestS3ContainerOperations):
    """Test list_containers() method."""

    @pytest.mark.asyncio
    async def test_list_containers_basic(self, storage):
        """Test basic container listing."""
        # List containers
        result = await storage.list_containers()

        # Validate response structure
        assert isinstance(result, dict)
        assert "containers" in result
        assert "total_count" in result
        assert isinstance(result["containers"], list)
        assert isinstance(result["total_count"], int)

    @pytest.mark.asyncio
    async def test_list_containers_with_test_containers(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test listing containers includes newly created ones."""
        cleanup_containers(test_container_name)

        # Get initial count
        initial_result = await storage.list_containers()
        initial_count = initial_result["total_count"]

        # Create test container
        await storage.create_container(test_container_name)

        # List containers again
        updated_result = await storage.list_containers()
        updated_count = updated_result["total_count"]

        # Should have one more container
        assert updated_count == initial_count + 1

        # Should find our test container
        container_names = [c["name"] for c in updated_result["containers"]]
        assert test_container_name in container_names

    @pytest.mark.asyncio
    async def test_list_containers_with_prefix_filter(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test listing containers with prefix filter."""
        cleanup_containers(test_container_name)

        # Create test container
        await storage.create_container(test_container_name)

        # List with prefix filter (if supported)
        result = await storage.list_containers(prefix="nachet-s3-test-")

        # Should include our test container
        container_names = [c["name"] for c in result["containers"]]
        matching = [
            name for name in container_names if name.startswith("nachet-s3-test-")
        ]

        assert len(matching) >= 1
        assert test_container_name in matching


class TestContainerLifecycle(TestS3ContainerOperations):
    """Test complete container lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_container_full_lifecycle(
        self, storage, test_container_name, cleanup_containers
    ):
        """Test complete container lifecycle: create, use, delete."""
        cleanup_containers(test_container_name)

        # 1. Create container
        create_result = await storage.create_container(test_container_name)
        assert create_result["name"] == test_container_name

        # 2. Verify it exists
        assert await storage.container_exists(test_container_name) is True

        # 3. Get properties
        properties = await storage.get_container_properties(test_container_name)
        assert properties["name"] == test_container_name

        # 4. Upload a blob
        upload_result = await storage.upload_blob(
            test_container_name, "test-blob.txt", b"test content"
        )
        assert upload_result["name"] == "test-blob.txt"

        # 5. Verify blob exists
        assert await storage.blob_exists(test_container_name, "test-blob.txt") is True

        # 6. Delete blob
        deleted_blob = await storage.delete_blob(test_container_name, "test-blob.txt")
        assert deleted_blob is True

        # 7. Delete container
        deleted_container = await storage.delete_container(test_container_name)
        assert deleted_container is True

        # 8. Verify container no longer exists
        assert await storage.container_exists(test_container_name) is False

    @pytest.mark.asyncio
    async def test_multiple_containers_management(self, storage, cleanup_containers):
        """Test managing multiple containers simultaneously."""
        container_names = [
            f"nachet-s3-test-multi-{uuid.uuid4().hex[:6]}-{i}" for i in range(3)
        ]

        try:
            # Create multiple containers
            for name in container_names:
                cleanup_containers(name)
                await storage.create_container(name)

            # Verify all exist
            for name in container_names:
                exists = await storage.container_exists(name)
                assert exists is True

            # List and verify we see them
            list_result = await storage.list_containers()
            listed_names = [c["name"] for c in list_result["containers"]]

            for name in container_names:
                assert name in listed_names

        finally:
            # Clean up all test containers
            for name in container_names:
                try:
                    await storage.delete_container(name)
                except Exception:
                    pass


if __name__ == "__main__":
    """Run tests with pytest when executed directly."""
    pytest.main([__file__, "-v", "-s"])
