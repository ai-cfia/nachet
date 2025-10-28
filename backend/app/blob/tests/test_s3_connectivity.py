"""
Test S3 connectivity for Apache Ozone S3 Gateway.

This test validates that the S3 blob storage implementation can connect
to an Apache Ozone S3-compatible endpoint.

Usage:
    cd /path/to/nachet/backend/app/blob
    uv run pytest tests/test_s3_connectivity.py -v
"""

import pytest
import os
from dotenv import load_dotenv
from app.blob.s3.storage import S3BlobStorage
from app.blob.s3.client import create_s3_client, validate_s3_connection
from app.api.config import get_settings

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")


# Test configuration
def get_s3_config():
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


class TestS3Connectivity:
    """Test S3 connectivity to Apache Ozone S3 Gateway."""

    def test_create_s3_client(self):
        """Test creating an S3 client with Ozone configuration."""
        config = get_s3_config()

        print("\n" + "=" * 60)
        print("S3 Configuration:")
        print("  Endpoint URL: (redacted)")
        print("  Region: (redacted)")
        print(f"  Access Key ID: {'*' * 16}... (redacted)")
        print(f"  Use SSL: {config['s3_use_ssl']}")
        print("=" * 60)

        # Create S3 client
        s3_client = create_s3_client(config)
        assert s3_client is not None, "S3 client should not be None"

        print("\n✅ S3 client created successfully")

    def test_validate_s3_connection(self):
        """Test validating S3 connection."""
        config = get_s3_config()
        s3_client = create_s3_client(config)

        # Validate connection
        is_valid = validate_s3_connection(s3_client)
        assert is_valid, "S3 connection should be valid"

        print("\n✅ S3 connection validated successfully")

    @pytest.mark.asyncio
    async def test_list_buckets(self):
        """Test listing S3 buckets."""
        config = get_s3_config()
        storage = S3BlobStorage(config)

        print("\n" + "=" * 60)
        print("Testing S3 List Buckets Operation")
        print("=" * 60)

        # List buckets
        result = await storage.list_containers()

        print(f"\nFound {result['total_count']} bucket(s)")
        for container in result.get("containers", []):
            print(f"  - {container['name']}")

        assert "containers" in result
        assert "total_count" in result
        assert isinstance(result["containers"], list)

        print("\n✅ List buckets operation successful")

    @pytest.mark.asyncio
    async def test_create_test_bucket(self):
        """Test creating a test bucket."""
        config = get_s3_config()
        storage = S3BlobStorage(config)

        test_bucket_name = "test-bucket-connectivity"

        print("\n" + "=" * 60)
        print(f"Testing S3 Create Bucket: {test_bucket_name}")
        print("=" * 60)

        # Create bucket
        result = await storage.create_container(test_bucket_name)

        print(f"\nBucket created: {result['name']}")
        print(f"  Last Modified: {result.get('last_modified')}")

        assert result["name"] == test_bucket_name

        # Verify bucket exists
        exists = await storage.container_exists(test_bucket_name)
        assert exists, f"Bucket {test_bucket_name} should exist after creation"

        print(f"✅ Bucket {test_bucket_name} exists")

        # Clean up: delete the test bucket
        try:
            deleted = await storage.delete_container(test_bucket_name)
            if deleted:
                print(f"✅ Cleaned up: deleted bucket {test_bucket_name}")
            else:
                print(
                    f"⚠️  Bucket {test_bucket_name} could not be deleted (may contain objects)"
                )
        except Exception as e:
            print(f"⚠️  Warning: Could not delete test bucket: {e}")

    @pytest.mark.asyncio
    async def test_upload_download_blob(self):
        """Test uploading and downloading a blob."""
        config = get_s3_config()
        storage = S3BlobStorage(config)

        test_bucket = "test-bucket-upload"
        test_blob = "test-object.txt"
        test_data = b"Hello from S3-compatible storage (Apache Ozone)!"

        print("\n" + "=" * 60)
        print(f"Testing S3 Upload/Download to bucket: {test_bucket}")
        print("=" * 60)

        try:
            # Create bucket
            await storage.create_container(test_bucket)
            print(f"✅ Created bucket: {test_bucket}")

            # Upload blob
            upload_result = await storage.upload_blob(
                test_bucket, test_blob, test_data, content_type="text/plain"
            )

            print(f"\n✅ Uploaded blob: {test_blob}")
            print(f"  Size: {upload_result['size']} bytes")
            print(f"  ETag: {upload_result['etag']}")
            print(f"  URL: {upload_result['url']}")

            # Download blob
            downloaded_data = await storage.download_blob(test_bucket, test_blob)

            assert downloaded_data == test_data, (
                "Downloaded data should match uploaded data"
            )
            print("\n✅ Downloaded blob matches uploaded data")
            print(f"  Downloaded {len(downloaded_data)} bytes")

        finally:
            # Clean up
            try:
                await storage.delete_blob(test_bucket, test_blob)
                print(f"\n✅ Cleaned up: deleted blob {test_blob}")
            except Exception as e:
                print(f"⚠️  Warning: Could not delete blob: {e}")

            try:
                await storage.delete_container(test_bucket)
                print(f"✅ Cleaned up: deleted bucket {test_bucket}")
            except Exception as e:
                print(f"⚠️  Warning: Could not delete bucket: {e}")

    @pytest.mark.asyncio
    async def test_blob_metadata_and_tags(self):
        """Test setting and getting blob metadata and tags."""
        config = get_s3_config()
        storage = S3BlobStorage(config)

        test_bucket = "test-bucket-metadata"
        test_blob = "test-metadata-object.txt"
        test_data = b"Test data for metadata"

        print("\n" + "=" * 60)
        print("Testing S3 Metadata and Tags")
        print("=" * 60)

        try:
            # Create bucket and upload blob
            await storage.create_container(test_bucket)
            await storage.upload_blob(test_bucket, test_blob, test_data)
            print(f"✅ Created test blob: {test_blob}")

            # Set metadata
            metadata = {"key1": "value1", "key2": "value2"}
            await storage.set_blob_metadata(test_bucket, test_blob, metadata)
            print(f"\n✅ Set metadata: {metadata}")

            # Get metadata
            retrieved_metadata = await storage.get_blob_metadata(test_bucket, test_blob)
            print(f"✅ Retrieved metadata: {retrieved_metadata}")
            assert retrieved_metadata == metadata

            # Set tags
            tags = {"environment": "test", "purpose": "connectivity-test"}
            await storage.set_blob_tags(test_bucket, test_blob, tags)
            print(f"\n✅ Set tags: {tags}")

            # Get tags
            retrieved_tags = await storage.get_blob_tags(test_bucket, test_blob)
            print(f"✅ Retrieved tags: {retrieved_tags}")
            # Tags should match, or be empty if tagging is not supported
            assert retrieved_tags == tags or retrieved_tags == {}

        finally:
            # Clean up
            try:
                await storage.delete_blob(test_bucket, test_blob)
                await storage.delete_container(test_bucket)
                print("\n✅ Cleaned up test resources")
            except Exception as e:
                print(f"⚠️  Warning during cleanup: {e}")


if __name__ == "__main__":
    """Run tests with pytest when executed directly."""
    pytest.main([__file__, "-v", "-s"])
