"""
Integration test suite to verify singleton pattern implementation for blob storage.

This test suite ensures that:
1. BlobStorageManager maintains a single client instance
2. Multiple calls to get_blob_storage return the same client
3. The singleton pattern works across different access methods
4. Proper initialization and cleanup behavior

This uses the real Azure blob storage implementation for proper integration testing.
"""

import pytest
import asyncio
import os
from dotenv import load_dotenv

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv(".env.test.local")

from app.api.config import Settings
from app.blob import (
    blob_storage_manager,
    get_blob_storage,
    create_blob_storage_client,
    initialize_blob_storage,
    close_blob_storage,
    reset_blob_storage,
)
from app.blob.exceptions import InvalidConfigurationError


@pytest.fixture
def clean_manager():
    """Fixture to ensure clean manager state for each test."""
    return blob_storage_manager


@pytest.fixture
def reset_manager():
    """Fixture to reset manager before and after each test."""
    # Reset the manager before each test
    reset_blob_storage()
    yield
    # Clean up after each test
    reset_blob_storage()


@pytest.fixture
def real_config():
    """Real configuration from Settings class - all storage backends."""
    settings = Settings()
    return {
        "cloud": ("azure", settings.blob_storage_config),
        "external": ("azure", settings.blob_storage_external_config),
        "onprem": ("s3", settings.s3_storage_config),
    }


@pytest.fixture
def azure_cloud_config():
    """Azure cloud storage configuration only."""
    settings = Settings()
    return {"cloud": ("azure", settings.blob_storage_config)}


@pytest.fixture
def azure_external_config():
    """Azure external storage configuration only."""
    settings = Settings()
    return {"external": ("azure", settings.blob_storage_external_config)}


@pytest.fixture
def s3_config():
    """S3 storage configuration only."""
    settings = Settings()
    return {"onprem": ("s3", settings.s3_storage_config)}


@pytest.fixture
def settings():
    """Settings instance for testing."""
    return Settings()


class TestBlobStorageSingleton:
    """Test cases for blob storage singleton pattern using real Azure Blob Storage."""

    @pytest.mark.asyncio
    async def test_singleton_client_same_instance_s3(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that multiple calls to get_blob_storage return the same S3 client instance."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Initialize the manager with S3 storage only
        await clean_manager.init_multiple(s3_config)

        # Get onprem client multiple times
        client1 = clean_manager.get_client("onprem")
        client2 = clean_manager.get_client("onprem")
        client3 = get_blob_storage("onprem")

        # Verify all calls return the same instance
        assert client1 is client2
        assert client2 is client3
        assert client1 is client3

        # Verify it's the actual S3BlobStorage instance
        assert hasattr(client1, "_s3_client")  # Should have the underlying S3 client

    @pytest.mark.asyncio
    async def test_singleton_client_same_instance_azure_cloud(
        self, clean_manager, azure_cloud_config, reset_manager
    ):
        """Test that multiple calls to get_blob_storage return the same Azure cloud client instance."""
        # Skip test if no configuration available
        _, config = azure_cloud_config["cloud"]
        if not config.get("blob_storage_name") or not config.get("blob_storage_key"):
            pytest.skip("Azure cloud Blob Storage configuration not available")

        # Initialize the manager with Azure cloud storage only
        await clean_manager.init_multiple(azure_cloud_config)

        # Get cloud client multiple times
        client1 = clean_manager.get_client("cloud")
        client2 = clean_manager.get_client("cloud")
        client3 = get_blob_storage("cloud")

        # Verify all calls return the same instance
        assert client1 is client2
        assert client2 is client3
        assert client1 is client3

        # Verify it's the actual AzureBlobStorage instance
        assert hasattr(
            client1, "_blob_service_client"
        )  # Should have the underlying Azure client

    @pytest.mark.asyncio
    async def test_singleton_client_same_instance_all_backends(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that singleton pattern works when all storage backends are initialized together."""
        # Skip test if any configuration is not available
        _, s3_config = real_config["onprem"]
        _, azure_cloud_config = real_config["cloud"]
        _, azure_external_config = real_config["external"]

        if not s3_config.get("s3_access_key") or not s3_config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")
        if not azure_cloud_config.get(
            "blob_storage_name"
        ) or not azure_cloud_config.get("blob_storage_key"):
            pytest.skip("Azure cloud Blob Storage configuration not available")
        if not azure_external_config.get(
            "blob_storage_name"
        ) or not azure_external_config.get("blob_storage_key"):
            pytest.skip("Azure external Blob Storage configuration not available")

        # Initialize the manager with all storage accounts
        await clean_manager.init_multiple(real_config)

        # Test S3 client
        s3_client1 = clean_manager.get_client("onprem")
        s3_client2 = get_blob_storage("onprem")
        assert s3_client1 is s3_client2
        assert hasattr(s3_client1, "_s3_client")

        # Test Azure cloud client
        azure_cloud1 = clean_manager.get_client("cloud")
        azure_cloud2 = get_blob_storage("cloud")
        assert azure_cloud1 is azure_cloud2
        assert hasattr(azure_cloud1, "_blob_service_client")

        # Test Azure external client
        azure_ext1 = clean_manager.get_client("external")
        azure_ext2 = get_blob_storage("external")
        assert azure_ext1 is azure_ext2
        assert hasattr(azure_ext1, "_blob_service_client")

    @pytest.mark.asyncio
    async def test_factory_creates_new_instances(self, s3_config, reset_manager):
        """Test that the factory function creates new instances each time."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Create multiple clients using factory
        client1 = create_blob_storage_client("s3", config)
        client2 = create_blob_storage_client("s3", config)

        # Verify different instances
        assert client1 is not client2
        assert id(client1) != id(client2)

    @pytest.mark.asyncio
    async def test_manager_initialization_reuse(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that manager reuses the same client after initialization."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Verify not initialized initially
        assert not clean_manager.is_initialized()

        # Initialize with S3 storage only
        await clean_manager.init_multiple(s3_config)

        # Verify initialized
        assert clean_manager.is_initialized()

        # Get onprem client multiple times and verify same instance
        clients = [clean_manager.get_client("onprem") for _ in range(5)]

        # All should be the same instance
        for i in range(1, len(clients)):
            assert clients[0] is clients[i]

    @pytest.mark.asyncio
    async def test_refresh_connection_maintains_singleton(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that refreshing connection creates a new client but maintains singleton pattern."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Initialize with S3 storage only
        await clean_manager.init_multiple(s3_config)
        client_before = clean_manager.get_client("onprem")
        client_before_id = id(client_before)

        # Refresh onprem connection
        await clean_manager.refresh_connection("onprem")
        client_after = clean_manager.get_client("onprem")

        # Should now have a new instance
        assert id(client_after) != client_before_id
        assert client_after is not client_before

        # Multiple calls after refresh should return same new instance
        client_after2 = clean_manager.get_client("onprem")
        assert client_after is client_after2

    @pytest.mark.asyncio
    async def test_get_blob_storage_before_init_raises_error(
        self, clean_manager, reset_manager
    ):
        """Test that getting blob storage before initialization raises an error."""
        # Ensure manager is not initialized
        assert not clean_manager.is_initialized()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="BlobStorageManager not initialized"):
            clean_manager.get_client("onprem")

        with pytest.raises(RuntimeError, match="BlobStorageManager not initialized"):
            get_blob_storage("onprem")

    @pytest.mark.asyncio
    async def test_concurrent_access_same_instance(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that concurrent access returns the same singleton instance."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Initialize with S3 storage only
        await clean_manager.init_multiple(s3_config)
        expected_client = clean_manager.get_client("onprem")

        # Concurrent access simulation
        async def get_client_task():
            return clean_manager.get_client("onprem")

        # Run multiple concurrent tasks
        tasks = [get_client_task() for _ in range(10)]
        clients = await asyncio.gather(*tasks)

        # All should be the same instance
        for client in clients:
            assert client is expected_client
            assert client is clients[0]

    @pytest.mark.asyncio
    async def test_close_and_reinit_creates_new_singleton(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that closing and reinitializing creates a new singleton instance."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # First initialization
        await clean_manager.init_multiple(s3_config)
        client1 = clean_manager.get_client("onprem")
        client1_id = id(client1)

        # Close
        await clean_manager.close()
        assert not clean_manager.is_initialized()

        # Reinitialize
        await clean_manager.init_multiple(s3_config)
        client2 = clean_manager.get_client("onprem")

        # Should be different instance
        assert id(client2) != client1_id
        assert client2 is not client1

        # Multiple calls should return the new singleton
        client3 = clean_manager.get_client("onprem")
        assert client3 is client2

    def test_unsupported_provider_raises_error(self, s3_config):
        """Test that unsupported provider raises InvalidConfigurationError."""
        _, config = s3_config["onprem"]
        with pytest.raises(
            InvalidConfigurationError, match="Unsupported provider: unsupported"
        ):
            create_blob_storage_client("unsupported", config)

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, clean_manager, reset_manager):
        """Test that initialization errors are properly handled."""
        # Use invalid configuration
        invalid_config = {
            "onprem": (
                "s3",
                {
                    "s3_access_key": "invalid",
                    "s3_secret_key": "invalid",
                    "s3_endpoint_url": "http://invalid:9878",
                    "s3_region": "us-east-1",
                },
            )
        }

        # Should raise InvalidConfigurationError
        with pytest.raises(
            InvalidConfigurationError, match="Failed to initialize blob storage clients"
        ):
            await clean_manager.init_multiple(invalid_config)

        # Manager should not be initialized
        assert not clean_manager.is_initialized()

    @pytest.mark.asyncio
    async def test_health_check_with_singleton(
        self, clean_manager, s3_config, reset_manager
    ):
        """Test that health check uses the singleton client."""
        # Skip test if no configuration available
        _, config = s3_config["onprem"]
        if not config.get("s3_access_key") or not config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")

        # Initialize with S3 storage only
        await clean_manager.init_multiple(s3_config)

        # Health check should pass for all initialized storages
        health_result = await clean_manager.health_check()
        assert health_result is True

        # Health check for specific storage
        health_result_onprem = await clean_manager.health_check("onprem")
        assert health_result_onprem is True

        # Verify the singleton client is still the same
        client = clean_manager.get_client("onprem")
        expected_client = clean_manager.get_client("onprem")
        assert client is expected_client


class TestBlobStorageIntegration:
    """Integration tests for blob storage singleton with the full system."""

    @pytest.mark.asyncio
    async def test_initialize_blob_storage_function(self, settings, reset_manager):
        """Test the global initialize_blob_storage function with all storage backends."""
        # Skip test if any configuration is not available
        s3_config = settings.s3_storage_config
        azure_cloud_config = settings.blob_storage_config
        azure_external_config = settings.blob_storage_external_config

        if not s3_config.get("s3_access_key") or not s3_config.get("s3_secret_key"):
            pytest.skip("S3 Blob Storage configuration not available")
        if not azure_cloud_config.get(
            "blob_storage_name"
        ) or not azure_cloud_config.get("blob_storage_key"):
            pytest.skip("Azure cloud Blob Storage configuration not available")
        if not azure_external_config.get(
            "blob_storage_name"
        ) or not azure_external_config.get("blob_storage_key"):
            pytest.skip("Azure external Blob Storage configuration not available")

        # Initialize using the global function with real settings
        await initialize_blob_storage(settings)

        # Verify S3 storage is accessible
        client_onprem = get_blob_storage("onprem")
        assert client_onprem is not None
        assert hasattr(client_onprem, "_s3_client")

        # Verify Azure cloud storage is accessible
        client_cloud = get_blob_storage("cloud")
        assert client_cloud is not None
        assert hasattr(client_cloud, "_blob_service_client")

        # Verify Azure external storage is accessible
        client_external = get_blob_storage("external")
        assert client_external is not None
        assert hasattr(client_external, "_blob_service_client")

        # Clean up
        await close_blob_storage()

    @pytest.mark.asyncio
    async def test_reset_blob_storage_clears_singleton(self, reset_manager):
        """Test that reset_blob_storage properly clears the singleton."""
        # Should not be initialized
        assert not blob_storage_manager.is_initialized()

        # Should raise error when trying to get client
        with pytest.raises(RuntimeError):
            get_blob_storage("onprem")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
