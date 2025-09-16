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
    """Real configuration from Settings class."""
    settings = Settings()
    return settings.blob_storage_config


@pytest.fixture
def settings():
    """Settings instance for testing."""
    return Settings()


class TestBlobStorageSingleton:
    """Test cases for blob storage singleton pattern using real Azure Blob Storage."""

    @pytest.mark.asyncio
    async def test_singleton_client_same_instance(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that multiple calls to get_blob_storage return the same client instance."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Initialize the manager
        await clean_manager.init("azure", real_config)

        # Get client multiple times
        client1 = clean_manager.get_client()
        client2 = clean_manager.get_client()
        client3 = get_blob_storage()

        # Verify all calls return the same instance
        assert client1 is client2
        assert client2 is client3
        assert client1 is client3

        # Verify it's the actual AzureBlobStorage instance
        assert hasattr(
            client1, "_blob_service_client"
        )  # Should have the underlying Azure client

    @pytest.mark.asyncio
    async def test_factory_creates_new_instances(self, real_config, reset_manager):
        """Test that the factory function creates new instances each time."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Create multiple clients using factory
        client1 = create_blob_storage_client("azure", real_config)
        client2 = create_blob_storage_client("azure", real_config)

        # Verify different instances
        assert client1 is not client2
        assert id(client1) != id(client2)

    @pytest.mark.asyncio
    async def test_manager_initialization_reuse(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that manager reuses the same client after initialization."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Verify not initialized initially
        assert not clean_manager.is_initialized()

        # Initialize
        await clean_manager.init("azure", real_config)

        # Verify initialized
        assert clean_manager.is_initialized()

        # Get client multiple times and verify same instance
        clients = [clean_manager.get_client() for _ in range(5)]

        # All should be the same instance
        for i in range(1, len(clients)):
            assert clients[0] is clients[i]

    @pytest.mark.asyncio
    async def test_refresh_connection_maintains_singleton(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that refreshing connection creates a new client but maintains singleton pattern."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Initialize with first instance
        await clean_manager.init("azure", real_config)
        client_before = clean_manager.get_client()
        client_before_id = id(client_before)

        # Refresh connection
        await clean_manager.refresh_connection()
        client_after = clean_manager.get_client()

        # Should now have a new instance
        assert id(client_after) != client_before_id
        assert client_after is not client_before

        # Multiple calls after refresh should return same new instance
        client_after2 = clean_manager.get_client()
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
            clean_manager.get_client()

        with pytest.raises(RuntimeError, match="BlobStorageManager not initialized"):
            get_blob_storage()

    @pytest.mark.asyncio
    async def test_concurrent_access_same_instance(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that concurrent access returns the same singleton instance."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Initialize
        await clean_manager.init("azure", real_config)
        expected_client = clean_manager.get_client()

        # Concurrent access simulation
        async def get_client_task():
            return clean_manager.get_client()

        # Run multiple concurrent tasks
        tasks = [get_client_task() for _ in range(10)]
        clients = await asyncio.gather(*tasks)

        # All should be the same instance
        for client in clients:
            assert client is expected_client
            assert client is clients[0]

    @pytest.mark.asyncio
    async def test_close_and_reinit_creates_new_singleton(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that closing and reinitializing creates a new singleton instance."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # First initialization
        await clean_manager.init("azure", real_config)
        client1 = clean_manager.get_client()
        client1_id = id(client1)

        # Close
        await clean_manager.close()
        assert not clean_manager.is_initialized()

        # Reinitialize
        await clean_manager.init("azure", real_config)
        client2 = clean_manager.get_client()

        # Should be different instance
        assert id(client2) != client1_id
        assert client2 is not client1

        # Multiple calls should return the new singleton
        client3 = clean_manager.get_client()
        assert client3 is client2

    def test_unsupported_provider_raises_error(self, real_config):
        """Test that unsupported provider raises InvalidConfigurationError."""
        with pytest.raises(
            InvalidConfigurationError, match="Unsupported provider: unsupported"
        ):
            create_blob_storage_client("unsupported", real_config)

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, clean_manager, reset_manager):
        """Test that initialization errors are properly handled."""
        # Use invalid configuration
        invalid_config = {
            "blob_storage_provider": "azure",
            "blob_storage_name": "invalid",
            "blob_storage_key": "invalid",
            "blob_storage_endpoint_protocol": "https",
            "blob_storage_endpoint_suffix": "core.windows.net",
            "blob_storage_endpoint_base": "invalid",
        }

        # Should raise InvalidConfigurationError
        with pytest.raises(
            InvalidConfigurationError, match="Failed to initialize blob storage client"
        ):
            await clean_manager.init("azure", invalid_config)

        # Manager should not be initialized
        assert not clean_manager.is_initialized()

    @pytest.mark.asyncio
    async def test_health_check_with_singleton(
        self, clean_manager, real_config, reset_manager
    ):
        """Test that health check uses the singleton client."""
        # Skip test if no configuration available
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Initialize
        await clean_manager.init("azure", real_config)

        # Health check should pass
        health_result = await clean_manager.health_check()
        assert health_result is True

        # Verify the singleton client is still the same
        client = clean_manager.get_client()
        expected_client = clean_manager.get_client()
        assert client is expected_client


class TestBlobStorageIntegration:
    """Integration tests for blob storage singleton with the full system."""

    @pytest.mark.asyncio
    async def test_initialize_blob_storage_function(self, settings, reset_manager):
        """Test the global initialize_blob_storage function."""
        # Skip test if no configuration available
        real_config = settings.blob_storage_config
        if not real_config["blob_storage_name"] or not real_config["blob_storage_key"]:
            pytest.skip("Azure Blob Storage configuration not available")

        # Initialize using the global function with real settings
        await initialize_blob_storage(settings)

        # Verify singleton is accessible
        client = get_blob_storage()
        assert client is not None
        assert hasattr(
            client, "_blob_service_client"
        )  # Should be real AzureBlobStorage instance

        # Clean up
        await close_blob_storage()

    @pytest.mark.asyncio
    async def test_reset_blob_storage_clears_singleton(self, reset_manager):
        """Test that reset_blob_storage properly clears the singleton."""
        # Should not be initialized
        assert not blob_storage_manager.is_initialized()

        # Should raise error when trying to get client
        with pytest.raises(RuntimeError):
            get_blob_storage()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
