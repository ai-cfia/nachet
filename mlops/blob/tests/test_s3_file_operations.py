"""
Test suite for S3-compatible Blob Storage file operations.

This comprehensive test suite covers all file management operations:
- upload_blob()
- download_blob()
- download_blob_stream()
- delete_blob()
- blob_exists()
- get_blob_properties()
- list_blobs()

These tests run against Apache Ozone S3 Gateway (or AWS S3) and include:
1. File upload/download with PNG images and JSON metadata
2. Blob lifecycle testing with original/clean/metadata folder structure
3. Error handling and edge cases
4. Validation of return types and models
5. Comprehensive cleanup of test blobs

Test Configuration:
- Container: nachet-s3-org-0000-0000-0000-0000 (persistent, not deleted after tests)
- File structure: original/{uuid}.png, clean/{uuid}.png, metadata/{uuid}.json
- Test files: single-pixel.png, sample-metadata.json
- Blob cleanup: All test blobs are cleaned up after test suite completion

Note: Tests require S3 connection configuration.
Set environment variables: S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY
"""

import pytest
import pytest_asyncio
import os
import uuid
import json
from pathlib import Path
from dotenv import load_dotenv

from app.blob.s3.storage import S3BlobStorage
from app.blob.exceptions import (
    BlobNotFoundError,
    ContainerNotFoundError,
)
from app.api.config import get_settings

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")

# Test configuration constants
TEST_CONTAINER = "nachet-s3-org-0000-0000-0000-0000"
TEST_FILES_DIR = Path(__file__).parent / "files"
SAMPLE_IMAGE_PATH = TEST_FILES_DIR / "single-pixel.png"
SAMPLE_METADATA_PATH = TEST_FILES_DIR / "sample-metadata.json"


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


def generate_test_blob_paths():
    """Generate unique blob paths for testing."""
    test_uuid = str(uuid.uuid4()).lower()
    return {
        "original": f"original/{test_uuid}.png",
        "clean": f"clean/{test_uuid}.png",
        "metadata": f"metadata/{test_uuid}.json",
    }


async def cleanup_test_blobs():
    """Helper function to clean up test blobs."""
    try:
        config = get_s3_test_config()
        storage = S3BlobStorage(config)

        # Ensure container exists (don't delete it after tests)
        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)

        # List all blobs and delete any that start with our test prefixes
        blobs_result = await storage.list_blobs(TEST_CONTAINER)
        blobs = blobs_result.get("blobs", [])

        for blob_info in blobs:
            blob_name = blob_info["name"]
            # Only delete test blobs (original/, clean/, metadata/ with test patterns)
            if any(
                blob_name.startswith(prefix)
                for prefix in ["original/", "clean/", "metadata/"]
            ):
                # Additional check to ensure it's a test blob with UUID pattern
                path_parts = blob_name.split("/")
                if len(path_parts) == 2:
                    filename = path_parts[1]
                    # Check if filename looks like a UUID (rough check)
                    if len(filename) > 30 and (
                        "-" in filename or filename.endswith((".png", ".json"))
                    ):
                        try:
                            await storage.delete_blob(TEST_CONTAINER, blob_name)
                            print(f"Cleaned up test blob: {blob_name}")
                        except Exception as e:
                            print(f"Failed to clean up blob {blob_name}: {e}")

    except Exception as e:
        print(f"Error during test blob cleanup: {e}")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_and_cleanup_test_blobs():
    """
    Session-level fixture to set up test container and clean up blobs.
    Ensures the container exists and cleans up test blobs after all tests.
    """
    # Set up: Ensure test container exists
    try:
        config = get_s3_test_config()
        storage = S3BlobStorage(config)

        if not await storage.container_exists(TEST_CONTAINER):
            await storage.create_container(TEST_CONTAINER)
            print(f"Created test container: {TEST_CONTAINER}")
        else:
            print(f"Test container already exists: {TEST_CONTAINER}")
    except Exception as e:
        print(f"Failed to set up test container: {e}")

    # Clean up any existing test blobs before starting
    await cleanup_test_blobs()

    yield  # Run all tests

    # Clean up test blobs after all tests are done
    await cleanup_test_blobs()


class TestS3FileOperations:
    """Test file management operations."""

    @pytest.fixture
    def storage(self):
        """Create S3BlobStorage instance for testing."""
        config = get_s3_test_config()
        return S3BlobStorage(config)

    @pytest_asyncio.fixture
    async def test_blob_paths(self):
        """Generate unique test blob paths."""
        return generate_test_blob_paths()

    @pytest_asyncio.fixture
    async def cleanup_blobs(self, storage):
        """Fixture to clean up test blobs after tests."""
        created_blobs = []

        def track_blob(blob_path):
            created_blobs.append(blob_path)
            return blob_path

        yield track_blob

        # Cleanup - delete all created blobs
        for blob_path in created_blobs:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass  # Ignore cleanup errors

    @pytest.fixture
    def sample_image_data(self):
        """Load sample PNG image data."""
        with open(SAMPLE_IMAGE_PATH, "rb") as f:
            return f.read()

    @pytest.fixture
    def sample_metadata_data(self):
        """Load sample JSON metadata."""
        with open(SAMPLE_METADATA_PATH, "r") as f:
            return f.read()

    @pytest.fixture
    def sample_metadata_dict(self):
        """Load sample metadata as dictionary."""
        with open(SAMPLE_METADATA_PATH, "r") as f:
            return json.load(f)


class TestUploadBlob(TestS3FileOperations):
    """Test upload_blob() method."""

    @pytest.mark.asyncio
    async def test_upload_png_image_basic(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test basic PNG image upload."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload PNG image
        result = await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Validate response
        assert isinstance(result, dict)
        assert result["name"] == blob_path
        assert result["container"] == TEST_CONTAINER
        assert "etag" in result
        assert "last_modified" in result
        assert "url" in result
        assert result["size"] == len(sample_image_data)

        # Verify blob was uploaded
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

    @pytest.mark.asyncio
    async def test_upload_json_metadata(
        self, storage, test_blob_paths, cleanup_blobs, sample_metadata_data
    ):
        """Test JSON metadata upload."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        metadata = {
            "purpose": "testing",
            "file_type": "metadata",
            "created_by": "test_suite",
        }

        # Upload JSON metadata
        result = await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_metadata_data.encode("utf-8"),
            content_type="application/json",
            metadata=metadata,
        )

        # Validate response
        assert result["name"] == blob_path
        assert result["container"] == TEST_CONTAINER
        assert result["size"] == len(sample_metadata_data.encode("utf-8"))

        # Verify blob exists and has correct properties
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        # Note: Some S3 implementations may not preserve content-type exactly
        assert properties["content_type"] in [
            "application/json",
            "binary/octet-stream",
            "application/octet-stream",
        ]

    @pytest.mark.asyncio
    async def test_upload_with_folder_structure(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test uploading files to different folder paths."""
        paths_to_test = [
            test_blob_paths["original"],
            test_blob_paths["clean"],
        ]

        for blob_path in paths_to_test:
            cleanup_blobs(blob_path)

            # Upload to specific folder path
            result = await storage.upload_blob(
                TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
            )

            # Verify correct path
            assert result["name"] == blob_path
            assert "/" in blob_path  # Ensure it has folder structure

            # Verify blob exists
            exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
            assert exists is True

    @pytest.mark.asyncio
    async def test_upload_overwrite_existing(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test overwriting existing blob."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload first time
        result1 = await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Upload second time (overwrite)
        new_data = b"New image data"
        result2 = await storage.upload_blob(
            TEST_CONTAINER, blob_path, new_data, content_type="image/png"
        )

        # ETags should be different
        assert result1["etag"] != result2["etag"]

        # Size should be updated
        assert result2["size"] == len(new_data)

        # Download and verify content was overwritten
        downloaded = await storage.download_blob(TEST_CONTAINER, blob_path)
        assert downloaded == new_data

    @pytest.mark.asyncio
    async def test_upload_empty_blob(self, storage, test_blob_paths, cleanup_blobs):
        """Test uploading empty blob."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        # Upload empty content
        result = await storage.upload_blob(
            TEST_CONTAINER, blob_path, b"", content_type="text/plain"
        )

        # Validate
        assert result["name"] == blob_path
        assert result["size"] == 0

        # Verify it exists
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

    @pytest.mark.asyncio
    async def test_upload_large_blob(self, storage, test_blob_paths, cleanup_blobs):
        """Test uploading larger blob (1 MB)."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Create 1 MB of data
        large_data = b"X" * (1024 * 1024)

        # Upload
        result = await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            large_data,
            content_type="application/octet-stream",
        )

        # Validate
        assert result["size"] == len(large_data)
        assert result["name"] == blob_path

        # Verify
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_container(self, storage, test_blob_paths):
        """Test uploading to non-existent container."""
        non_existent_container = f"nachet-s3-nonexist-{uuid.uuid4().hex[:8]}"
        blob_path = test_blob_paths["original"]

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.upload_blob(
                non_existent_container, blob_path, b"test", content_type="text/plain"
            )


class TestDownloadBlob(TestS3FileOperations):
    """Test download_blob() method."""

    @pytest.mark.asyncio
    async def test_download_blob_basic(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test basic blob download."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload first
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Download
        downloaded_data = await storage.download_blob(TEST_CONTAINER, blob_path)

        # Verify content matches
        assert downloaded_data == sample_image_data
        assert len(downloaded_data) == len(sample_image_data)

    @pytest.mark.asyncio
    async def test_download_json_blob(
        self, storage, test_blob_paths, cleanup_blobs, sample_metadata_data
    ):
        """Test downloading JSON blob."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        # Upload JSON
        await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_metadata_data.encode("utf-8"),
            content_type="application/json",
        )

        # Download
        downloaded_data = await storage.download_blob(TEST_CONTAINER, blob_path)

        # Verify content
        assert downloaded_data.decode("utf-8") == sample_metadata_data

        # Parse as JSON to verify it's valid
        parsed = json.loads(downloaded_data.decode("utf-8"))
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_download_nonexistent_blob(self, storage):
        """Test downloading non-existent blob."""
        non_existent_blob = f"nonexistent/{uuid.uuid4()}.png"

        # Should raise BlobNotFoundError
        with pytest.raises(BlobNotFoundError):
            await storage.download_blob(TEST_CONTAINER, non_existent_blob)

    @pytest.mark.asyncio
    async def test_download_from_nonexistent_container(self, storage):
        """Test downloading from non-existent container."""
        non_existent_container = f"nachet-s3-nonexist-{uuid.uuid4().hex[:8]}"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.download_blob(non_existent_container, "any-blob.txt")

    @pytest.mark.asyncio
    async def test_download_empty_blob(self, storage, test_blob_paths, cleanup_blobs):
        """Test downloading empty blob."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        # Upload empty blob
        await storage.upload_blob(TEST_CONTAINER, blob_path, b"")

        # Download
        downloaded = await storage.download_blob(TEST_CONTAINER, blob_path)

        # Should be empty
        assert downloaded == b""
        assert len(downloaded) == 0


class TestDownloadBlobStream(TestS3FileOperations):
    """Test download_blob_stream() method."""

    @pytest.mark.asyncio
    async def test_download_stream_basic(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test basic streaming download."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload first
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Download as stream
        chunks = []
        async for chunk in storage.download_blob_stream(TEST_CONTAINER, blob_path):
            chunks.append(chunk)

        # Reconstruct data
        downloaded_data = b"".join(chunks)

        # Verify content matches
        assert downloaded_data == sample_image_data

    @pytest.mark.asyncio
    async def test_download_stream_large_blob(
        self, storage, test_blob_paths, cleanup_blobs
    ):
        """Test streaming download of larger blob."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Create 1 MB blob
        large_data = b"X" * (1024 * 1024)

        # Upload
        await storage.upload_blob(TEST_CONTAINER, blob_path, large_data)

        # Download as stream
        chunks = []
        async for chunk in storage.download_blob_stream(TEST_CONTAINER, blob_path):
            chunks.append(chunk)
            assert len(chunk) > 0  # Each chunk should have data

        # Verify
        downloaded_data = b"".join(chunks)
        assert downloaded_data == large_data


class TestBlobExists(TestS3FileOperations):
    """Test blob_exists() method."""

    @pytest.mark.asyncio
    async def test_blob_exists_true(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test blob_exists returns True for existing blob."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

        # Check existence
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

    @pytest.mark.asyncio
    async def test_blob_exists_false(self, storage):
        """Test blob_exists returns False for non-existent blob."""
        non_existent_blob = f"nonexistent/{uuid.uuid4()}.png"

        # Check existence
        exists = await storage.blob_exists(TEST_CONTAINER, non_existent_blob)
        assert exists is False

    @pytest.mark.asyncio
    async def test_blob_exists_after_deletion(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test blob_exists returns False after deletion."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is True

        # Delete blob
        await storage.delete_blob(TEST_CONTAINER, blob_path)

        # Check existence
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is False


class TestDeleteBlob(TestS3FileOperations):
    """Test delete_blob() method."""

    @pytest.mark.asyncio
    async def test_delete_blob_basic(self, storage, test_blob_paths, sample_image_data):
        """Test basic blob deletion."""
        blob_path = test_blob_paths["original"]

        # Upload blob
        await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

        # Verify it exists
        exists_before = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists_before is True

        # Delete blob
        deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
        assert deleted is True

        # Verify it no longer exists
        exists_after = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists_after is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_blob(self, storage):
        """Test deleting non-existent blob."""
        non_existent_blob = f"nonexistent/{uuid.uuid4()}.png"

        # Should return False for non-existent blob (idempotent operation)
        deleted = await storage.delete_blob(TEST_CONTAINER, non_existent_blob)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_multiple_blobs(self, storage, sample_image_data):
        """Test deleting multiple blobs."""
        # Create unique blob paths
        blob_paths = [f"test-multi-delete/{uuid.uuid4()}.png" for _ in range(3)]

        try:
            # Upload multiple blobs
            for blob_path in blob_paths:
                await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Verify all exist
            for blob_path in blob_paths:
                exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
                assert exists is True

            # Delete all blobs
            for blob_path in blob_paths:
                deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
                assert deleted is True

            # Verify none exist
            for blob_path in blob_paths:
                exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
                assert exists is False

        finally:
            # Cleanup in case of failure
            for blob_path in blob_paths:
                try:
                    await storage.delete_blob(TEST_CONTAINER, blob_path)
                except Exception:
                    pass


class TestGetBlobProperties(TestS3FileOperations):
    """Test get_blob_properties() method."""

    @pytest.mark.asyncio
    async def test_get_blob_properties_basic(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test getting basic blob properties."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Get properties
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)

        # Validate response
        assert isinstance(properties, dict)
        assert properties["name"] == blob_path
        assert properties["container"] == TEST_CONTAINER
        assert properties["size"] == len(sample_image_data)
        # Note: Some S3 implementations may not preserve content-type exactly
        assert properties["content_type"] in [
            "image/png",
            "binary/octet-stream",
            "application/octet-stream",
        ]
        assert "etag" in properties
        assert "last_modified" in properties

    @pytest.mark.asyncio
    async def test_get_blob_properties_nonexistent(self, storage):
        """Test getting properties for non-existent blob."""
        non_existent_blob = f"nonexistent/{uuid.uuid4()}.png"

        # Should raise BlobNotFoundError
        with pytest.raises(BlobNotFoundError):
            await storage.get_blob_properties(TEST_CONTAINER, non_existent_blob)


class TestListBlobs(TestS3FileOperations):
    """Test list_blobs() method."""

    @pytest.mark.asyncio
    async def test_list_blobs_basic(self, storage):
        """Test basic blob listing."""
        # List blobs
        result = await storage.list_blobs(TEST_CONTAINER)

        # Validate response
        assert isinstance(result, dict)
        assert "blobs" in result
        assert isinstance(result["blobs"], list)

    @pytest.mark.asyncio
    async def test_list_blobs_with_prefix(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test listing blobs with prefix filter."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

        # List with prefix
        result = await storage.list_blobs(TEST_CONTAINER, prefix="original/")

        # Should find our blob
        blob_names = [b["name"] for b in result["blobs"]]
        assert blob_path in blob_names

    @pytest.mark.asyncio
    async def test_list_blobs_empty_container(self, storage):
        """Test listing blobs in container with no matching prefix."""
        # Use a prefix that won't match anything
        result = await storage.list_blobs(
            TEST_CONTAINER, prefix=f"nonexistent-{uuid.uuid4()}/"
        )

        # Should return empty list
        assert isinstance(result["blobs"], list)


class TestBlobLifecycle(TestS3FileOperations):
    """Test complete blob lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_blob_full_lifecycle(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test complete blob lifecycle: upload, download, properties, delete."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # 1. Upload blob
        upload_result = await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )
        assert upload_result["name"] == blob_path

        # 2. Verify it exists
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is True

        # 3. Get properties
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["size"] == len(sample_image_data)

        # 4. Download and verify content
        downloaded = await storage.download_blob(TEST_CONTAINER, blob_path)
        assert downloaded == sample_image_data

        # 5. Delete blob
        deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
        assert deleted is True

        # 6. Verify it no longer exists
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is False


if __name__ == "__main__":
    """Run tests with pytest when executed directly."""
    pytest.main([__file__, "-v", "-s"])
