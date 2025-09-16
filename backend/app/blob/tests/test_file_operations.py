"""
Test suite for Azure Blob Storage file operations.

This comprehensive test suite covers all file management operations:
- upload_blob()
- download_blob()
- download_blob_stream()
- delete_blob()
- blob_exists()
- get_blob_properties()

These tests run against real Azure Blob Storage or Azurite and include:
1. File upload/download with PNG images and JSON metadata
2. Blob lifecycle testing with original/clean/metadata folder structure
3. Error handling and edge cases
4. Validation of return types and models
5. Comprehensive cleanup of test blobs

Test Configuration:
- Container: nachet-org-0000-0000-0000-0000 (persistent, not deleted after tests)
- File structure: original/{uuid}.png, clean/{uuid}.png, metadata/{uuid}.json
- Test files: single-pixel.png, sample-metadata.json
- Blob cleanup: All test blobs are cleaned up after test suite completion

Note: Tests require a valid Azure Storage connection string.
Set the environment variable AZURE_STORAGE_CONNECTION_STRING or use Azurite for local testing.
"""

import pytest
import pytest_asyncio
import os
import uuid
import json

# from datetime import datetime
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from pathlib import Path

from app.blob.azure.storage import AzureBlobStorage

# from app.blob.models import BlobInfo, UploadResult, BlobProperties, BlobTierInfo
from app.blob.exceptions import (
    # InvalidConfigurationError,
    ConnectionError,
    BlobStorageError,
    BlobNotFoundError,
    ContainerNotFoundError,
)
from app.api.config import get_settings

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")

# Test configuration constants
TEST_CONTAINER = "nachet-org-0000-0000-0000-0000"
TEST_FILES_DIR = Path(__file__).parent / "files"
SAMPLE_IMAGE_PATH = TEST_FILES_DIR / "single-pixel.png"
SAMPLE_METADATA_PATH = TEST_FILES_DIR / "sample-metadata.json"


def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()

    # If blob storage is configured in settings, use it
    if settings.blob_storage_name and settings.blob_storage_key:
        return settings.blob_storage_config

    raise ValueError("No Azure Storage configuration found in settings")


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
        config = get_test_config()
        storage = AzureBlobStorage(config)

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
        config = get_test_config()
        storage = AzureBlobStorage(config)

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


class TestFileOperations:
    """Test file management operations."""

    @pytest.fixture
    def storage(self):
        """Create AzureBlobStorage instance for testing."""
        config = get_test_config()
        return AzureBlobStorage(config)

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


class TestUploadBlob(TestFileOperations):
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
        assert properties["content_type"] == "application/json"
        assert properties["metadata"] == metadata

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
        modified_data = sample_image_data + b"extra"
        result2 = await storage.upload_blob(
            TEST_CONTAINER, blob_path, modified_data, content_type="image/png"
        )

        # Verify overwrite
        assert result2["size"] == len(modified_data)
        assert result1["etag"] != result2["etag"]  # ETag should change

    @pytest.mark.asyncio
    async def test_upload_invalid_container(self, storage, sample_image_data):
        """Test upload to non-existent container."""
        non_existent_container = "non-existent-container"
        blob_path = "test/image.png"

        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.upload_blob(
                non_existent_container, blob_path, sample_image_data
            )


class TestDownloadBlob(TestFileOperations):
    """Test download_blob() method."""

    @pytest.mark.asyncio
    async def test_download_png_image(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test downloading PNG image."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload first
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Download and verify
        downloaded_data = await storage.download_blob(TEST_CONTAINER, blob_path)
        assert downloaded_data == sample_image_data

    @pytest.mark.asyncio
    async def test_download_json_metadata(
        self, storage, test_blob_paths, cleanup_blobs, sample_metadata_data
    ):
        """Test downloading JSON metadata."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        # Upload first
        await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_metadata_data.encode("utf-8"),
            content_type="application/json",
        )

        # Download and verify
        downloaded_data = await storage.download_blob(TEST_CONTAINER, blob_path)
        assert downloaded_data.decode("utf-8") == sample_metadata_data

    @pytest.mark.asyncio
    async def test_download_with_range(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test downloading with byte range."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload first
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Download first 10 bytes
        downloaded_data = await storage.download_blob(
            TEST_CONTAINER, blob_path, offset=0, length=10
        )
        assert len(downloaded_data) == 10
        assert downloaded_data == sample_image_data[:10]

    @pytest.mark.asyncio
    async def test_download_non_existent_blob(self, storage):
        """Test downloading non-existent blob."""
        non_existent_blob = f"non-existent/{str(uuid.uuid4()).lower()}.png"

        # Should raise BlobNotFoundError
        with pytest.raises(BlobNotFoundError):
            await storage.download_blob(TEST_CONTAINER, non_existent_blob)


class TestBlobExists(TestFileOperations):
    """Test blob_exists() method."""

    @pytest.mark.asyncio
    async def test_blob_exists_true(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test blob_exists returns True for existing blob."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Check existence
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True

    @pytest.mark.asyncio
    async def test_blob_exists_false(self, storage):
        """Test blob_exists returns False for non-existing blob."""
        non_existent_blob = f"non-existent/{str(uuid.uuid4()).lower()}.png"

        # Check existence of non-existent blob
        exists = await storage.blob_exists(TEST_CONTAINER, non_existent_blob)
        assert exists is False

    @pytest.mark.asyncio
    async def test_blob_exists_after_deletion(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test blob_exists returns False after deletion."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload and verify exists
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is True

        # Delete blob
        deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
        assert deleted is True

        # Check existence after deletion
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is False


class TestGetBlobProperties(TestFileOperations):
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

        # Validate response structure
        assert isinstance(properties, dict)
        assert properties["name"] == blob_path
        assert properties["container"] == TEST_CONTAINER
        assert properties["size"] == len(sample_image_data)
        assert properties["content_type"] == "image/png"
        assert "etag" in properties
        assert "last_modified" in properties

    @pytest.mark.asyncio
    async def test_get_blob_properties_with_metadata(
        self, storage, test_blob_paths, cleanup_blobs, sample_metadata_data
    ):
        """Test getting blob properties with metadata."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        metadata = {"file_type": "metadata", "purpose": "testing", "version": "1.0"}

        # Upload blob with metadata
        await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_metadata_data.encode("utf-8"),
            content_type="application/json",
            metadata=metadata,
        )

        # Get properties
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)

        # Validate metadata
        assert properties["metadata"] == metadata
        assert properties["content_type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_blob_properties_not_found(self, storage):
        """Test getting properties of non-existent blob."""
        non_existent_blob = f"non-existent/{str(uuid.uuid4()).lower()}.png"

        # Should raise BlobNotFoundError
        with pytest.raises(BlobNotFoundError):
            await storage.get_blob_properties(TEST_CONTAINER, non_existent_blob)


class TestDeleteBlob(TestFileOperations):
    """Test delete_blob() method."""

    @pytest.mark.asyncio
    async def test_delete_blob_success(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test successful blob deletion."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is True

        # Delete blob
        deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)

        # Validate deletion
        assert deleted is True
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is False

    @pytest.mark.asyncio
    async def test_delete_blob_not_found(self, storage):
        """Test deleting non-existent blob."""
        non_existent_blob = f"non-existent/{str(uuid.uuid4()).lower()}.png"

        # Should return False for non-existent blob
        deleted = await storage.delete_blob(TEST_CONTAINER, non_existent_blob)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_blob_with_metadata(
        self, storage, test_blob_paths, cleanup_blobs, sample_metadata_data
    ):
        """Test deleting blob that has metadata."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        metadata = {"test": "data", "purpose": "deletion_test"}

        # Upload blob with metadata
        await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_metadata_data.encode("utf-8"),
            content_type="application/json",
            metadata=metadata,
        )

        # Verify upload and metadata
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["metadata"] == metadata

        # Delete blob
        deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
        assert deleted is True

        # Verify deletion
        assert await storage.blob_exists(TEST_CONTAINER, blob_path) is False


class TestFileLifecycle(TestFileOperations):
    """Test complete file lifecycle operations."""

    @pytest.mark.asyncio
    async def test_complete_file_lifecycle(
        self,
        storage,
        test_blob_paths,
        cleanup_blobs,
        sample_image_data,
        sample_metadata_dict,
    ):
        """Test complete file lifecycle: upload -> exists -> properties -> download -> delete."""
        original_path = test_blob_paths["original"]
        clean_path = test_blob_paths["clean"]
        metadata_path = test_blob_paths["metadata"]

        # Track all blobs for cleanup
        cleanup_blobs(original_path)
        cleanup_blobs(clean_path)
        cleanup_blobs(metadata_path)

        # Step 1: Upload original image
        original_result = await storage.upload_blob(
            TEST_CONTAINER, original_path, sample_image_data, content_type="image/png"
        )
        assert original_result["name"] == original_path

        # Step 2: Upload clean image (same data for test)
        clean_result = await storage.upload_blob(
            TEST_CONTAINER, clean_path, sample_image_data, content_type="image/png"
        )
        assert clean_result["name"] == clean_path

        # Step 3: Upload metadata
        metadata_json = json.dumps(sample_metadata_dict).encode("utf-8")
        metadata_result = await storage.upload_blob(
            TEST_CONTAINER,
            metadata_path,
            metadata_json,
            content_type="application/json",
        )
        assert metadata_result["name"] == metadata_path

        # Step 4: Verify all files exist
        assert await storage.blob_exists(TEST_CONTAINER, original_path) is True
        assert await storage.blob_exists(TEST_CONTAINER, clean_path) is True
        assert await storage.blob_exists(TEST_CONTAINER, metadata_path) is True

        # Step 5: Get properties of all files
        original_props = await storage.get_blob_properties(
            TEST_CONTAINER, original_path
        )
        clean_props = await storage.get_blob_properties(TEST_CONTAINER, clean_path)
        metadata_props = await storage.get_blob_properties(
            TEST_CONTAINER, metadata_path
        )

        assert original_props["content_type"] == "image/png"
        assert clean_props["content_type"] == "image/png"
        assert metadata_props["content_type"] == "application/json"

        # Step 6: Download and verify all files
        downloaded_original = await storage.download_blob(TEST_CONTAINER, original_path)
        downloaded_clean = await storage.download_blob(TEST_CONTAINER, clean_path)
        downloaded_metadata = await storage.download_blob(TEST_CONTAINER, metadata_path)

        assert downloaded_original == sample_image_data
        assert downloaded_clean == sample_image_data
        assert json.loads(downloaded_metadata.decode("utf-8")) == sample_metadata_dict

        # Step 7: Delete all files
        deleted_original = await storage.delete_blob(TEST_CONTAINER, original_path)
        deleted_clean = await storage.delete_blob(TEST_CONTAINER, clean_path)
        deleted_metadata = await storage.delete_blob(TEST_CONTAINER, metadata_path)

        assert deleted_original is True
        assert deleted_clean is True
        assert deleted_metadata is True

        # Step 8: Verify all files are deleted
        assert await storage.blob_exists(TEST_CONTAINER, original_path) is False
        assert await storage.blob_exists(TEST_CONTAINER, clean_path) is False
        assert await storage.blob_exists(TEST_CONTAINER, metadata_path) is False

    @pytest.mark.asyncio
    async def test_multiple_files_in_folders(
        self, storage, cleanup_blobs, sample_image_data, sample_metadata_data
    ):
        """Test managing multiple files across different folders."""
        # Generate multiple test files
        test_sets = [generate_test_blob_paths() for _ in range(3)]
        all_blob_paths = []

        for test_set in test_sets:
            all_blob_paths.extend(
                [test_set["original"], test_set["clean"], test_set["metadata"]]
            )

        # Track all for cleanup
        for blob_path in all_blob_paths:
            cleanup_blobs(blob_path)

        # Upload files to different folders
        for i, test_set in enumerate(test_sets):
            # Upload original image
            await storage.upload_blob(
                TEST_CONTAINER,
                test_set["original"],
                sample_image_data,
                content_type="image/png",
                metadata={"set": str(i), "type": "original"},
            )

            # Upload clean image
            await storage.upload_blob(
                TEST_CONTAINER,
                test_set["clean"],
                sample_image_data,
                content_type="image/png",
                metadata={"set": str(i), "type": "clean"},
            )

            # Upload metadata
            await storage.upload_blob(
                TEST_CONTAINER,
                test_set["metadata"],
                sample_metadata_data.encode("utf-8"),
                content_type="application/json",
                metadata={"set": str(i), "type": "metadata"},
            )

        # Verify all files exist
        for blob_path in all_blob_paths:
            assert await storage.blob_exists(TEST_CONTAINER, blob_path) is True

        # Verify folder structure by listing blobs
        blobs_result = await storage.list_blobs(TEST_CONTAINER, prefix="original/")
        original_blobs = blobs_result["blobs"]
        assert len(original_blobs) >= 3  # At least our 3 test files

        blobs_result = await storage.list_blobs(TEST_CONTAINER, prefix="clean/")
        clean_blobs = blobs_result["blobs"]
        assert len(clean_blobs) >= 3

        blobs_result = await storage.list_blobs(TEST_CONTAINER, prefix="metadata/")
        metadata_blobs = blobs_result["blobs"]
        assert len(metadata_blobs) >= 3

        # Verify metadata on files
        for i, test_set in enumerate(test_sets):
            original_props = await storage.get_blob_properties(
                TEST_CONTAINER, test_set["original"]
            )
            assert original_props["metadata"]["set"] == str(i)
            assert original_props["metadata"]["type"] == "original"

        # Clean up all files
        for blob_path in all_blob_paths:
            deleted = await storage.delete_blob(TEST_CONTAINER, blob_path)
            assert deleted is True


class TestBlobTier(TestFileOperations):
    """Test set_blob_tier() method."""

    @pytest.mark.asyncio
    async def test_set_blob_tier_hot_to_cool(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test setting blob tier from Hot to Cool."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob (default tier is usually Hot)
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Set tier to Cool
        result = await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Cool")
        assert result is True

        # Verify tier change
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["blob_tier"] == "Cool"
        assert "blob_tier_change_time" in properties
        assert properties["blob_tier_inferred"] is False

    @pytest.mark.asyncio
    async def test_set_blob_tier_cool_to_hot(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test setting blob tier from Cool to Hot."""
        blob_path = test_blob_paths["metadata"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(
            TEST_CONTAINER,
            blob_path,
            sample_image_data,
            content_type="application/octet-stream",
        )

        # Set tier to Cool first
        await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Cool")

        # Then set to Hot
        result = await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Hot")
        assert result is True

        # Verify tier change to Hot
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["blob_tier"] == "Hot"

    @pytest.mark.asyncio
    async def test_set_blob_tier_invalid_tier(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test setting invalid blob tier."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Upload blob
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Try to set invalid tier (Archive is now invalid)
        with pytest.raises(BlobStorageError):
            await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Archive")

    @pytest.mark.asyncio
    async def test_set_blob_tier_non_existent_blob(self, storage):
        """Test setting tier for non-existent blob."""
        non_existent_blob = f"non-existent/{str(uuid.uuid4()).lower()}.png"

        # Should raise BlobNotFoundError
        with pytest.raises(BlobNotFoundError):
            await storage.set_blob_tier(TEST_CONTAINER, non_existent_blob, "Cool")

    @pytest.mark.asyncio
    async def test_blob_tier_cost_optimization_workflow(
        self, storage, test_blob_paths, cleanup_blobs, sample_image_data
    ):
        """Test complete blob tier management workflow for cost optimization."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Step 1: Upload blob (Hot tier by default for new uploads)
        await storage.upload_blob(
            TEST_CONTAINER, blob_path, sample_image_data, content_type="image/png"
        )

        # Step 2: Move to Cool tier for infrequent access
        cool_result = await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Cool")
        assert cool_result is True

        # Verify Cool tier
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["blob_tier"] == "Cool"

        # Step 3: Move back to Hot for immediate access (if needed)
        hot_result = await storage.set_blob_tier(TEST_CONTAINER, blob_path, "Hot")
        assert hot_result is True

        # Verify Hot tier
        properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
        assert properties["blob_tier"] == "Hot"

        # Verify blob still exists and is accessible
        exists = await storage.blob_exists(TEST_CONTAINER, blob_path)
        assert exists is True


class TestFileErrorHandling(TestFileOperations):
    """Test error handling in file operations."""

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, storage):
        """Test handling of connection errors."""
        # Mock the blob operations client to raise ServiceRequestError
        with patch.object(storage._blob_ops, "_client") as mock_client:
            mock_container_client = MagicMock()
            mock_client.get_container_client.return_value = mock_container_client

            # Mock ServiceRequestError on container exists check
            from azure.core.exceptions import ServiceRequestError

            mock_container_client.exists.side_effect = ServiceRequestError(
                "Connection failed"
            )

            # Should raise ConnectionError
            with pytest.raises(ConnectionError):
                await storage.blob_exists(TEST_CONTAINER, "test-blob")

    @pytest.mark.asyncio
    async def test_invalid_blob_data_upload(
        self, storage, test_blob_paths, cleanup_blobs
    ):
        """Test uploading invalid data types."""
        blob_path = test_blob_paths["original"]
        cleanup_blobs(blob_path)

        # Test with None data
        with pytest.raises(BlobStorageError):
            await storage.upload_blob(TEST_CONTAINER, blob_path, None)

    @pytest.mark.asyncio
    async def test_container_not_found_operations(self, storage, sample_image_data):
        """Test file operations on non-existent container."""
        non_existent_container = "non-existent-container-test"
        blob_path = "test/image.png"

        # All operations should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            await storage.upload_blob(
                non_existent_container, blob_path, sample_image_data
            )

        with pytest.raises(ContainerNotFoundError):
            await storage.download_blob(non_existent_container, blob_path)

        with pytest.raises(ContainerNotFoundError):
            await storage.blob_exists(non_existent_container, blob_path)

        with pytest.raises(ContainerNotFoundError):
            await storage.get_blob_properties(non_existent_container, blob_path)

        with pytest.raises(ContainerNotFoundError):
            await storage.delete_blob(non_existent_container, blob_path)

        with pytest.raises(ContainerNotFoundError):
            await storage.set_blob_tier(non_existent_container, blob_path, "Cool")

    # =============================================================================
    # Copy and Move Operations Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_copy_blob_same_container(self, storage, sample_image_data):
        """Test copying a blob within the same container."""
        source_path = f"copy-test/original-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"copy-test/copy-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload source blob
            upload_result = await storage.upload_blob(
                TEST_CONTAINER, source_path, sample_image_data
            )
            assert upload_result["name"] == source_path

            # Copy the blob
            copy_result = await storage.copy_blob(
                TEST_CONTAINER, source_path, TEST_CONTAINER, dest_path
            )

            # Verify copy result
            assert copy_result["source_container"] == TEST_CONTAINER
            assert copy_result["source_name"] == source_path
            assert copy_result["dest_container"] == TEST_CONTAINER
            assert copy_result["dest_name"] == dest_path
            assert copy_result["copy_status"] == "success"
            assert "etag" in copy_result
            assert "last_modified" in copy_result
            assert "size" in copy_result
            assert "copy_id" in copy_result

            # Verify both blobs exist
            source_exists = await storage.blob_exists(TEST_CONTAINER, source_path)
            dest_exists = await storage.blob_exists(TEST_CONTAINER, dest_path)
            assert source_exists
            assert dest_exists

            # Verify copied blob has same content
            original_data = await storage.download_blob(TEST_CONTAINER, source_path)
            copied_data = await storage.download_blob(TEST_CONTAINER, dest_path)
            assert original_data == copied_data
            assert original_data == sample_image_data

        finally:
            # Cleanup
            try:
                await storage.delete_blob(TEST_CONTAINER, source_path)
                await storage.delete_blob(TEST_CONTAINER, dest_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_copy_blob_different_containers(self, storage, sample_image_data):
        """Test copying a blob between different containers."""
        source_container = TEST_CONTAINER
        dest_container = f"nachet-unit-test-copy-dest-{uuid.uuid4().hex[:8]}"
        source_path = f"copy-test/source-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"copy-test/dest-{str(uuid.uuid4()).lower()}.png"

        try:
            # Create destination container
            await storage.create_container(dest_container)

            # Upload source blob
            await storage.upload_blob(source_container, source_path, sample_image_data)

            # Copy between containers
            copy_result = await storage.copy_blob(
                source_container, source_path, dest_container, dest_path
            )

            # Verify copy result
            assert copy_result["source_container"] == source_container
            assert copy_result["dest_container"] == dest_container
            assert copy_result["copy_status"] == "success"

            # Verify both blobs exist
            source_exists = await storage.blob_exists(source_container, source_path)
            dest_exists = await storage.blob_exists(dest_container, dest_path)
            assert source_exists
            assert dest_exists

            # Verify content matches
            original_data = await storage.download_blob(source_container, source_path)
            copied_data = await storage.download_blob(dest_container, dest_path)
            assert original_data == copied_data

        finally:
            # Cleanup
            try:
                await storage.delete_blob(source_container, source_path)
                await storage.delete_blob(dest_container, dest_path)
                await storage.delete_container(dest_container)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_copy_blob_source_not_found(self, storage):
        """Test copying a non-existent source blob."""
        source_path = f"copy-test/non-existent-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"copy-test/dest-{str(uuid.uuid4()).lower()}.png"

        with pytest.raises(BlobNotFoundError):
            await storage.copy_blob(
                TEST_CONTAINER, source_path, TEST_CONTAINER, dest_path
            )

    @pytest.mark.asyncio
    async def test_copy_blob_source_container_not_found(
        self, storage, sample_image_data
    ):
        """Test copying from a non-existent source container."""
        non_existent_container = "non-existent-source-container"
        source_path = f"copy-test/source-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"copy-test/dest-{str(uuid.uuid4()).lower()}.png"

        with pytest.raises(ContainerNotFoundError):
            await storage.copy_blob(
                non_existent_container, source_path, TEST_CONTAINER, dest_path
            )

    @pytest.mark.asyncio
    async def test_copy_blob_dest_container_not_found(self, storage, sample_image_data):
        """Test copying to a non-existent destination container."""
        non_existent_container = "non-existent-dest-container"
        source_path = f"copy-test/source-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"copy-test/dest-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload source blob
            await storage.upload_blob(TEST_CONTAINER, source_path, sample_image_data)

            # Try to copy to non-existent container
            with pytest.raises(ContainerNotFoundError):
                await storage.copy_blob(
                    TEST_CONTAINER, source_path, non_existent_container, dest_path
                )

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, source_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_move_blob_same_container(self, storage, sample_image_data):
        """Test moving a blob within the same container."""
        source_path = f"move-test/original-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"move-test/moved-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload source blob
            await storage.upload_blob(TEST_CONTAINER, source_path, sample_image_data)

            # Verify source exists before move
            source_exists_before = await storage.blob_exists(
                TEST_CONTAINER, source_path
            )
            assert source_exists_before

            # Move the blob
            move_result = await storage.move_blob(
                TEST_CONTAINER, source_path, TEST_CONTAINER, dest_path
            )

            # Verify move result
            assert move_result["source_container"] == TEST_CONTAINER
            assert move_result["source_name"] == source_path
            assert move_result["dest_container"] == TEST_CONTAINER
            assert move_result["dest_name"] == dest_path
            assert move_result["copy_status"] == "success"
            assert move_result["delete_successful"] is True
            assert move_result["move_completed"] is True
            assert "etag" in move_result
            assert "last_modified" in move_result

            # Verify source no longer exists and destination exists
            source_exists_after = await storage.blob_exists(TEST_CONTAINER, source_path)
            dest_exists = await storage.blob_exists(TEST_CONTAINER, dest_path)
            assert not source_exists_after
            assert dest_exists

            # Verify moved blob has same content
            moved_data = await storage.download_blob(TEST_CONTAINER, dest_path)
            assert moved_data == sample_image_data

        finally:
            # Cleanup (in case move failed partially)
            try:
                await storage.delete_blob(TEST_CONTAINER, source_path)
                await storage.delete_blob(TEST_CONTAINER, dest_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_move_blob_different_containers(self, storage, sample_image_data):
        """Test moving a blob between different containers."""
        source_container = TEST_CONTAINER
        dest_container = f"nachet-unit-test-move-dest-{uuid.uuid4().hex[:8]}"
        source_path = f"move-test/source-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"move-test/dest-{str(uuid.uuid4()).lower()}.png"

        try:
            # Create destination container
            await storage.create_container(dest_container)

            # Upload source blob
            await storage.upload_blob(source_container, source_path, sample_image_data)

            # Move between containers
            move_result = await storage.move_blob(
                source_container, source_path, dest_container, dest_path
            )

            # Verify move result
            assert move_result["source_container"] == source_container
            assert move_result["dest_container"] == dest_container
            assert move_result["move_completed"] is True

            # Verify source no longer exists and destination exists
            source_exists = await storage.blob_exists(source_container, source_path)
            dest_exists = await storage.blob_exists(dest_container, dest_path)
            assert not source_exists
            assert dest_exists

            # Verify content matches
            moved_data = await storage.download_blob(dest_container, dest_path)
            assert moved_data == sample_image_data

        finally:
            # Cleanup
            try:
                await storage.delete_blob(source_container, source_path)
                await storage.delete_blob(dest_container, dest_path)
                await storage.delete_container(dest_container)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_move_blob_source_not_found(self, storage):
        """Test moving a non-existent source blob."""
        source_path = f"move-test/non-existent-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"move-test/dest-{str(uuid.uuid4()).lower()}.png"

        with pytest.raises(BlobNotFoundError):
            await storage.move_blob(
                TEST_CONTAINER, source_path, TEST_CONTAINER, dest_path
            )

    @pytest.mark.asyncio
    async def test_move_blob_with_rollback(self, storage, sample_image_data):
        """Test move operation rollback when delete fails."""
        source_path = f"move-test/source-rollback-{str(uuid.uuid4()).lower()}.png"
        dest_path = f"move-test/dest-rollback-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload source blob
            await storage.upload_blob(TEST_CONTAINER, source_path, sample_image_data)

            # Mock the _delete_blob_for_move method to simulate failure after successful copy
            with patch.object(
                storage._advanced_ops, "_delete_blob_for_move", return_value=False
            ):
                move_result = await storage.move_blob(
                    TEST_CONTAINER, source_path, TEST_CONTAINER, dest_path
                )

                # Move should report partial success (copy succeeded, delete failed)
                assert move_result["copy_status"] == "success"
                assert move_result["delete_successful"] is False
                assert move_result["move_completed"] is False

                # Both blobs should exist (move was incomplete)
                source_exists = await storage.blob_exists(TEST_CONTAINER, source_path)
                dest_exists = await storage.blob_exists(TEST_CONTAINER, dest_path)
                assert source_exists  # Still exists because delete failed
                assert dest_exists  # Exists because copy succeeded

        finally:
            # Cleanup both blobs
            try:
                await storage.delete_blob(TEST_CONTAINER, source_path)
                await storage.delete_blob(TEST_CONTAINER, dest_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_move_blob_complete_lifecycle(
        self, storage, sample_image_data, sample_metadata_data
    ):
        """Test complete move workflow with multiple blob types."""
        base_uuid = uuid.uuid4()

        # Test files in different folders
        test_files = [
            (f"lifecycle/original/{base_uuid}.png", sample_image_data, "image/png"),
            (
                f"lifecycle/metadata/{base_uuid}.json",
                sample_metadata_data.encode("utf-8"),
                "application/json",
            ),
        ]

        moved_files = []

        try:
            # Upload test files
            for file_path, file_data, content_type in test_files:
                await storage.upload_blob(TEST_CONTAINER, file_path, file_data)

            # Move each file to processed folder
            for file_path, file_data, content_type in test_files:
                # Generate destination path (original -> processed)
                dest_path = file_path.replace("/original/", "/processed/").replace(
                    "/metadata/", "/processed/"
                )
                moved_files.append((file_path, dest_path, file_data))

                # Perform move
                move_result = await storage.move_blob(
                    TEST_CONTAINER, file_path, TEST_CONTAINER, dest_path
                )

                assert move_result["move_completed"] is True

                # Verify move
                source_exists = await storage.blob_exists(TEST_CONTAINER, file_path)
                dest_exists = await storage.blob_exists(TEST_CONTAINER, dest_path)
                assert not source_exists
                assert dest_exists

                # Verify content integrity
                moved_data = await storage.download_blob(TEST_CONTAINER, dest_path)
                assert moved_data == file_data

        finally:
            # Cleanup all files (both source and destination paths)
            for source_path, dest_path, _ in moved_files:
                try:
                    await storage.delete_blob(TEST_CONTAINER, source_path)
                    await storage.delete_blob(TEST_CONTAINER, dest_path)
                except Exception:
                    pass

    # =============================================================================
    # Metadata and Tags Operations Tests
    # =============================================================================

    @pytest.mark.asyncio
    async def test_set_blob_metadata_basic(self, storage, sample_image_data):
        """Test setting basic blob metadata."""
        blob_path = f"metadata-test/basic-{str(uuid.uuid4()).lower()}.png"
        metadata = {
            "source": "test_suite",
            "processed": "false",
            "version": "1.0",
            "author": "nachet-unit-test",
        }

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set metadata
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, metadata)

            # Verify metadata was set by retrieving it
            retrieved_metadata = await storage.get_blob_metadata(
                TEST_CONTAINER, blob_path
            )
            assert retrieved_metadata == metadata

            # Verify metadata is also available through blob properties
            properties = await storage.get_blob_properties(TEST_CONTAINER, blob_path)
            assert properties["metadata"] == metadata

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_get_blob_metadata_empty(self, storage, sample_image_data):
        """Test getting metadata from blob with no metadata."""
        blob_path = f"metadata-test/empty-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob without metadata
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Get metadata (should be empty)
            metadata = await storage.get_blob_metadata(TEST_CONTAINER, blob_path)
            assert metadata == {}

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_metadata_update_existing(self, storage, sample_image_data):
        """Test updating existing blob metadata."""
        blob_path = f"metadata-test/update-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set initial metadata
            initial_metadata = {"version": "1.0", "status": "draft"}
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, initial_metadata)

            # Verify initial metadata
            retrieved_metadata = await storage.get_blob_metadata(
                TEST_CONTAINER, blob_path
            )
            assert retrieved_metadata == initial_metadata

            # Update metadata (replaces all existing metadata)
            updated_metadata = {
                "version": "1.1",
                "status": "published",
                "author": "system",
            }
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, updated_metadata)

            # Verify updated metadata
            final_metadata = await storage.get_blob_metadata(TEST_CONTAINER, blob_path)
            assert final_metadata == updated_metadata
            assert "status" in final_metadata
            assert final_metadata["status"] == "published"

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_metadata_empty_dict(self, storage, sample_image_data):
        """Test setting empty metadata dictionary."""
        blob_path = f"metadata-test/empty-dict-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set initial metadata
            initial_metadata = {"version": "1.0"}
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, initial_metadata)

            # Clear metadata with empty dict
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, {})

            # Verify metadata is cleared
            metadata = await storage.get_blob_metadata(TEST_CONTAINER, blob_path)
            assert metadata == {}

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_metadata_blob_not_found(self, storage):
        """Test setting metadata on non-existent blob."""
        blob_path = f"metadata-test/non-existent-{str(uuid.uuid4()).lower()}.png"
        metadata = {"test": "value"}

        with pytest.raises(BlobNotFoundError):
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, metadata)

    @pytest.mark.asyncio
    async def test_get_blob_metadata_blob_not_found(self, storage):
        """Test getting metadata from non-existent blob."""
        blob_path = f"metadata-test/non-existent-{str(uuid.uuid4()).lower()}.png"

        with pytest.raises(BlobNotFoundError):
            await storage.get_blob_metadata(TEST_CONTAINER, blob_path)

    @pytest.mark.asyncio
    async def test_set_blob_tags_basic(self, storage, sample_image_data):
        """Test setting basic blob tags."""
        blob_path = f"tags-test/basic-{str(uuid.uuid4()).lower()}.png"
        tags = {
            "category": "test-data",
            "environment": "unittest",
            "priority": "high",
            "type": "image",
        }

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set tags
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, tags)

            # Verify tags were set by retrieving them
            retrieved_tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)
            assert retrieved_tags == tags

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_get_blob_tags_empty(self, storage, sample_image_data):
        """Test getting tags from blob with no tags."""
        blob_path = f"tags-test/empty-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob without tags
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Get tags (should be empty)
            tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)
            assert tags == {}

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_tags_update_existing(self, storage, sample_image_data):
        """Test updating existing blob tags."""
        blob_path = f"tags-test/update-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set initial tags
            initial_tags = {"version": "1.0", "status": "draft"}
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, initial_tags)

            # Verify initial tags
            retrieved_tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)
            assert retrieved_tags == initial_tags

            # Update tags (replaces all existing tags)
            updated_tags = {"version": "1.1", "status": "published", "approved": "true"}
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, updated_tags)

            # Verify updated tags
            final_tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)
            assert final_tags == updated_tags
            assert "approved" in final_tags
            assert final_tags["approved"] == "true"

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_tags_empty_dict(self, storage, sample_image_data):
        """Test setting empty tags dictionary."""
        blob_path = f"tags-test/empty-dict-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set initial tags
            initial_tags = {"version": "1.0"}
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, initial_tags)

            # Clear tags with empty dict
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, {})

            # Verify tags are cleared
            tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)
            assert tags == {}

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_set_blob_tags_blob_not_found(self, storage):
        """Test setting tags on non-existent blob."""
        blob_path = f"tags-test/non-existent-{str(uuid.uuid4()).lower()}.png"
        tags = {"test": "value"}

        with pytest.raises(BlobNotFoundError):
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, tags)

    @pytest.mark.asyncio
    async def test_get_blob_tags_blob_not_found(self, storage):
        """Test getting tags from non-existent blob."""
        blob_path = f"tags-test/non-existent-{str(uuid.uuid4()).lower()}.png"

        with pytest.raises(BlobNotFoundError):
            await storage.get_blob_tags(TEST_CONTAINER, blob_path)

    @pytest.mark.asyncio
    async def test_metadata_and_tags_combined(self, storage, sample_image_data):
        """Test setting both metadata and tags on same blob."""
        blob_path = f"combined-test/metadata-tags-{str(uuid.uuid4()).lower()}.png"
        metadata = {
            "creator": "unit-test",
            "purpose": "combined-testing",
            "timestamp": "2025-09-15",
        }
        tags = {
            "test-type": "combined",
            "category": "metadata-tags",
            "validated": "true",
        }

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Set metadata and tags
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, metadata)
            await storage.set_blob_tags(TEST_CONTAINER, blob_path, tags)

            # Verify both metadata and tags are set correctly
            retrieved_metadata = await storage.get_blob_metadata(
                TEST_CONTAINER, blob_path
            )
            retrieved_tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)

            assert retrieved_metadata == metadata
            assert retrieved_tags == tags

            # Verify they don't interfere with each other
            updated_metadata = {"creator": "updated-test", "purpose": "validation"}
            await storage.set_blob_metadata(TEST_CONTAINER, blob_path, updated_metadata)

            # Tags should remain unchanged
            final_metadata = await storage.get_blob_metadata(TEST_CONTAINER, blob_path)
            final_tags = await storage.get_blob_tags(TEST_CONTAINER, blob_path)

            assert final_metadata == updated_metadata
            assert final_tags == tags  # Tags should be unchanged

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_metadata_tags_validation_errors(self, storage, sample_image_data):
        """Test validation errors for metadata and tags."""
        blob_path = f"validation-test/errors-{str(uuid.uuid4()).lower()}.png"

        try:
            # Upload blob first
            await storage.upload_blob(TEST_CONTAINER, blob_path, sample_image_data)

            # Test invalid metadata types
            with pytest.raises(BlobStorageError, match="must be strings"):
                await storage.set_blob_metadata(TEST_CONTAINER, blob_path, {"key": 123})

            with pytest.raises(BlobStorageError, match="must be strings"):
                await storage.set_blob_metadata(
                    TEST_CONTAINER, blob_path, {123: "value"}
                )

            # Test empty metadata key
            with pytest.raises(BlobStorageError, match="cannot be empty"):
                await storage.set_blob_metadata(
                    TEST_CONTAINER, blob_path, {"": "value"}
                )

            # Test invalid tags types
            with pytest.raises(BlobStorageError, match="must be strings"):
                await storage.set_blob_tags(TEST_CONTAINER, blob_path, {"key": 123})

            with pytest.raises(BlobStorageError, match="must be strings"):
                await storage.set_blob_tags(TEST_CONTAINER, blob_path, {123: "value"})

            # Test empty tag key
            with pytest.raises(BlobStorageError, match="cannot be empty"):
                await storage.set_blob_tags(TEST_CONTAINER, blob_path, {"": "value"})

        finally:
            try:
                await storage.delete_blob(TEST_CONTAINER, blob_path)
            except Exception:
                pass
