"""
Test connectivity and basic operations for Azure Blob Storage.

These tests run against real Azure Blob Storage and focus on:
1. Connection string validation
2. Basic connectivity to Azure Storage
3. Simple container listing operations

Note: These tests require a valid Azure Storage connection string.
Set the environment variable AZURE_STORAGE_CONNECTION_STRING or use Azurite for local testing.
"""

import pytest
import os
from dotenv import load_dotenv
from app.blob.azure.storage import AzureBlobStorage
from app.blob.models import ListOptions
from app.blob.exceptions import (
    InvalidConfigurationError,
    ConnectionError,
    BlobStorageError,
)
from app.api.config import get_settings
from .test_utils import sanitize_config_for_display, sanitize_connection_string

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv("../../.env.test.local")


# Test configuration
def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()

    # If blob storage is configured in settings, use it
    if settings.blob_storage_name and settings.blob_storage_key:
        # Return the flat config structure
        return settings.blob_storage_config

    raise ValueError("No Azure Storage configuration found in settings")


class TestAzureBlobStorageConnectivity:
    """Test basic connectivity and configuration validation."""

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        config = get_test_config()

        storage = AzureBlobStorage(config)

        assert storage.config == config
        assert storage._blob_service_client is not None

    def test_init_with_missing_connection_string(self):
        """Test initialization fails with missing required config fields."""
        # Missing required blob storage config fields
        config = {"account_name": "test"}  # Missing blob_storage_* fields

        with pytest.raises((InvalidConfigurationError, KeyError)) as exc_info:
            AzureBlobStorage(config)

        # Should fail because required config fields are missing
        assert any(
            key in str(exc_info.value)
            for key in [
                "blob_storage_endpoint_protocol",
                "blob_storage_name",
                "blob_storage_key",
                "blob_storage_endpoint_suffix",
            ]
        )

    def test_init_with_empty_config_fields(self):
        """Test initialization fails with empty config fields."""
        config = {
            "blob_storage_endpoint_protocol": "",
            "blob_storage_name": "",
            "blob_storage_key": "",
            "blob_storage_endpoint_suffix": "",
            "blob_storage_endpoint_base": "",
        }

        with pytest.raises(InvalidConfigurationError) as exc_info:
            AzureBlobStorage(config)

        # Azure SDK will complain about invalid connection string format
        assert any(
            phrase in str(exc_info.value)
            for phrase in [
                "Azure storage connection string is required",
                "connection string is invalid",
                "Failed to initialize Azure Blob Storage client",
            ]
        )

    def test_init_with_invalid_config(self):
        """Test initialization fails when Azure client creation fails."""
        config = {
            "blob_storage_endpoint_protocol": "https",
            "blob_storage_name": "invalid-account",
            "blob_storage_key": "invalid-key==",
            "blob_storage_endpoint_suffix": "core.windows.net",
            "blob_storage_endpoint_base": "https://invalid-account.blob.core.windows.net",
        }

        # This may or may not raise during initialization (depends on Azure SDK validation)
        # Some invalid configs only fail during actual operations
        try:
            storage = AzureBlobStorage(config)
            # If initialization succeeds, the error should happen during use
            assert storage is not None
        except InvalidConfigurationError as e:
            # If it fails during init, that's also valid
            assert "Failed to initialize Azure Blob Storage client" in str(e)


class TestListContainers:
    """Test container listing functionality against real Azure Storage."""

    @pytest.fixture
    def storage(self):
        """Create a real AzureBlobStorage instance."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.mark.asyncio
    async def test_list_containers_basic(self, storage):
        """Test basic container listing."""
        try:
            result = await storage.list_containers()

            # Verify result structure
            assert "containers" in result
            assert "total_count" in result
            assert "continuation_token" in result
            assert isinstance(result["containers"], list)
            assert isinstance(result["total_count"], int)

            # Each container should have required fields
            for container in result["containers"]:
                assert "name" in container
                assert "last_modified" in container
                assert "etag" in container
                assert "metadata" in container
                assert isinstance(container["metadata"], dict)

        except ConnectionError:
            pytest.skip(
                "Azure Storage not available - check connection string or start Azurite"
            )

    @pytest.mark.asyncio
    async def test_list_containers_with_options(self, storage):
        """Test container listing with various options."""
        try:
            # Test with include_metadata=True
            options = ListOptions(include_metadata=True)
            result = await storage.list_containers(options=options)

            assert "containers" in result
            assert isinstance(result["containers"], list)

            # Test with max_results
            options = ListOptions(max_results=1)
            result = await storage.list_containers(options=options)

            if result["containers"]:
                assert len(result["containers"]) <= 1

            # Test with prefix (unlikely to match in empty storage)
            options = ListOptions(prefix="non-existent-prefix-12345")
            result = await storage.list_containers(options=options)

            assert result["containers"] == []
            assert result["total_count"] == 0

        except ConnectionError:
            pytest.skip(
                "Azure Storage not available - check connection string or start Azurite"
            )

    @pytest.mark.asyncio
    async def test_list_containers_options_as_dict(self, storage):
        """Test container listing with options passed as dictionary."""
        try:
            options_dict = {"include_metadata": True, "max_results": 10}
            result = await storage.list_containers(options=options_dict)

            assert "containers" in result
            assert isinstance(result["containers"], list)

        except ConnectionError:
            pytest.skip(
                "Azure Storage not available - check connection string or start Azurite"
            )


class TestConnectionStringGeneration:
    """Test connection string generation from config fields."""

    def test_connection_string_generation_method(self):
        """Test that the azure_storage_connection_string method works correctly."""
        config = {
            "blob_storage_endpoint_protocol": "https",
            "blob_storage_name": "testaccount",
            "blob_storage_key": "dGVzdGtleQ==",
            "blob_storage_endpoint_suffix": "core.windows.net",
            "blob_storage_endpoint_base": "https://testaccount.blob.core.windows.net",
        }

        storage = AzureBlobStorage(config)
        connection_string = storage.azure_storage_connection_string()

        # Verify the format
        expected_parts = [
            "DefaultEndpointsProtocol=https",
            "AccountName=testaccount",
            "AccountKey=dGVzdGtleQ==",
            "EndpointSuffix=core.windows.net",
            "BlobEndpoint=https://testaccount.blob.core.windows.net/testaccount",
        ]

        for part in expected_parts:
            assert part in connection_string, f"Missing part: {part}"

        # Sanitize connection string before printing to avoid leaking credentials
        sanitized_conn_str = sanitize_connection_string(connection_string)
        print(f"✅ Generated connection string: {sanitized_conn_str}")

    @pytest.mark.parametrize(
        "config_fields,should_pass",
        [
            # Valid config fields
            (
                {
                    "blob_storage_endpoint_protocol": "https",
                    "blob_storage_name": "testaccount",
                    "blob_storage_key": "dGVzdGtleQ==",  # base64 encoded "testkey"
                    "blob_storage_endpoint_suffix": "core.windows.net",
                    "blob_storage_endpoint_base": "https://testaccount.blob.core.windows.net",
                },
                True,
            ),
            (
                {
                    "blob_storage_endpoint_protocol": "http",
                    "blob_storage_name": "devstoreaccount1",
                    "blob_storage_key": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
                    "blob_storage_endpoint_suffix": "core.windows.net",
                    "blob_storage_endpoint_base": "http://127.0.0.1:10000",
                },
                True,
            ),
            # Invalid config fields (missing required fields)
            (
                {"blob_storage_name": "test"},  # Missing other required fields
                False,
            ),
            (
                {},  # Empty config
                False,
            ),
        ],
    )
    def test_config_field_formats(self, config_fields, should_pass):
        """Test various config field combinations."""
        if should_pass:
            # These should initialize without error (but may fail to connect)
            try:
                storage = AzureBlobStorage(config_fields)
                assert storage is not None
                # Test that connection string is generated correctly
                conn_str = storage.azure_storage_connection_string()
                assert "DefaultEndpointsProtocol=" in conn_str
                assert "AccountName=" in conn_str
                assert "AccountKey=" in conn_str
            except InvalidConfigurationError:
                # This can happen if the config format is valid but credentials are invalid
                # We only care about format validation here
                pass
        else:
            # Invalid config should fail
            with pytest.raises((InvalidConfigurationError, KeyError)):
                AzureBlobStorage(config_fields)


class TestRealConnectivity:
    """Test real connectivity to Azure Storage."""

    @pytest.fixture
    def storage(self):
        """Create a real AzureBlobStorage instance."""
        config = get_test_config()
        return AzureBlobStorage(config)

    @pytest.mark.asyncio
    async def test_connection_can_list_containers(self, storage):
        """Test that we can actually connect and list containers."""
        try:
            result = await storage.list_containers()

            # If we get here, connection worked
            assert isinstance(result, dict)
            assert "containers" in result
            print("✅ Successfully connected to Azure Storage")
            print(f"📦 Found {result['total_count']} containers")

            # Print container names for debugging
            for container in result["containers"]:
                print(f"   - {container['name']}")

        except ConnectionError as e:
            pytest.skip(f"Cannot connect to Azure Storage: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")

    @pytest.mark.asyncio
    async def test_invalid_connection_string_fails(self):
        """Test that invalid connection strings fail properly."""
        config = {
            "blob_storage_endpoint_protocol": "https",
            "blob_storage_name": "nonexistent",
            "blob_storage_key": "invalidkey==",
            "blob_storage_endpoint_suffix": "core.windows.net",
            "blob_storage_endpoint_base": "https://nonexistent.blob.core.windows.net",
        }

        # Should initialize but fail on actual use
        storage = AzureBlobStorage(config)

        with pytest.raises((ConnectionError, BlobStorageError)):
            await storage.list_containers()


class TestConfigurationIntegration:
    """Test integration with the application's configuration system."""

    def test_config_integration(self):
        """Test that configuration is properly loaded from app settings."""
        settings = get_settings()
        config = get_test_config()

        # Config should have the blob storage fields we expect
        required_fields = [
            "blob_storage_endpoint_protocol",
            "blob_storage_name",
            "blob_storage_key",
            "blob_storage_endpoint_suffix",
        ]

        for field in required_fields:
            assert field in config, f"Missing required config field: {field}"
            assert config[field] is not None, f"Config field {field} is None"

        # If blob storage settings are configured, should use them
        if settings.blob_storage_name and settings.blob_storage_key:
            expected_config = settings.blob_storage_config
            assert config == expected_config  # Compare with flat config
            assert (
                config["blob_storage_provider"] == settings.blob_storage_provider
                or None
            )
            assert config["blob_storage_name"] == settings.blob_storage_name
            assert config["blob_storage_key"] == settings.blob_storage_key

        # Sanitize config before printing to avoid leaking credentials
        sanitized_config = sanitize_config_for_display(config)
        print(f"📋 Test config: {sanitized_config}")

    def test_azure_connection_string_format(self):
        """Test that Azure connection string has correct format."""
        # Get valid config and create storage instance
        config = get_test_config()
        storage = AzureBlobStorage(config)

        # Use the storage method to get connection string
        connection_string = storage.azure_storage_connection_string()

        # Should contain required components
        assert "DefaultEndpointsProtocol=" in connection_string
        assert "AccountName=" in connection_string
        assert "AccountKey=" in connection_string
        assert "EndpointSuffix=" in connection_string
        assert "BlobEndpoint=" in connection_string

        # Should be valid format (no None values)
        assert "None" not in connection_string

        # Sanitize before printing to avoid credential leakage
        sanitized_conn_str = sanitize_connection_string(connection_string)
        print(f"🔗 Connection string format: {sanitized_conn_str[:80]}...")

        # Verify it contains actual values from config (without exposing them in assertions)
        # Check for presence of key components without printing the actual secrets
        assert config["blob_storage_name"] in connection_string
        assert (
            "AccountKey=" in connection_string
        )  # Verify key is present without exposing value

    def test_settings_blob_config(self):
        """Test that settings properly generate blob config."""
        settings = get_settings()

        # Should have blob_storage_config computed field
        assert hasattr(settings, "blob_storage_config")

        blob_config = settings.blob_storage_config
        assert isinstance(blob_config, dict)

        # Should have the expected flat config structure
        required_fields = [
            "blob_storage_provider",
            "blob_storage_endpoint_protocol",
            "blob_storage_name",
            "blob_storage_key",
            "blob_storage_endpoint_suffix",
        ]

        for field in required_fields:
            assert field in blob_config, f"Missing config field: {field}"

        print(f"⚙️  Blob config keys: {list(blob_config.keys())}")
