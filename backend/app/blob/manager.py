"""
Blob storage manager with singleton BlobServiceClient.

This module provides a singleton pattern for Azure Blob Storage client, following
Azure SDK best practices for reusing the thread-safe BlobServiceClient.

DESIGN RATIONALE - Singleton Pattern:

✅ BENEFITS of Singleton BlobServiceClient:
- **Performance**: Single client reuse across all requests (Azure SDK recommendation)
- **Connection Pooling**: Single connection pool shared efficiently
- **Memory Efficient**: One client instance instead of many
- **Authentication**: Single authentication flow
- **Thread Safe**: Azure SDK guarantees thread safety

📚 AZURE SDK DOCUMENTATION:
"BlobServiceClient is thread-safe and should be reused across requests for optimal performance"

The manager creates and maintains a single BlobServiceClient instance and provides
access to container and blob clients derived from it.
"""

from typing import Optional, Dict, Any, AsyncGenerator, TYPE_CHECKING
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

if TYPE_CHECKING:
    from app.api.config import Settings

from app.blob.exceptions import InvalidConfigurationError, ConnectionError
from app.blob.interface import BlobStorageInterface


class BlobStorageManager:
    """
    Manages a singleton blob storage client following Azure SDK best practices.

    This manager maintains a single BlobServiceClient instance that is thread-safe
    and reused across all requests for optimal performance.
    """

    def __init__(self) -> None:
        self._provider: Optional[str] = None
        self._config: Optional[Dict[str, Any]] = None
        self._client: Optional[BlobStorageInterface] = None
        self._initialized: bool = False
        self._lock = asyncio.Lock()

    async def init(self, provider: str, config: Dict[str, Any], **kwargs):
        """
        Initialize the BlobStorageManager with a singleton client.

        Args:
            provider: Storage provider name (e.g., 'azure')
            config: Provider-specific configuration
            **kwargs: Additional initialization options
        """
        async with self._lock:
            try:
                # Create the singleton client
                from app.blob.manager import get_blob_storage

                self._client = get_blob_storage(provider, config)

                # Test the client works
                await self._client.list_containers()

                # Store config
                self._provider = provider
                self._config = config.copy()
                self._initialized = True
                print(
                    f"🗄️  BlobStorageManager initialized with singleton client for provider: {provider}"
                )
            except Exception as e:
                raise InvalidConfigurationError(
                    "initialization",
                    f"Failed to initialize blob storage client: {str(e)}",
                )

    def get_client(self) -> BlobStorageInterface:
        """
        Get the singleton blob storage client.

        Returns:
            The singleton BlobStorageInterface instance

        Note: This client is thread-safe and should be reused across requests.
        """
        if not self._initialized or not self._client:
            raise RuntimeError("BlobStorageManager not initialized. Call init() first.")

        return self._client

    def create_client(self) -> BlobStorageInterface:
        """
        Create a blob storage client (kept for backward compatibility).

        Note: Returns the singleton client for optimal performance.
        """
        return self.get_client()

    async def health_check(self) -> bool:
        """
        Perform a health check on the blob storage connection.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._initialized or not self._client:
            return False

        try:
            # Test connectivity with the singleton client
            await self._client.list_containers()
            return True
        except Exception as e:
            print(f"⚠️  Blob storage health check failed: {e}")
            return False

    async def refresh_connection(self):
        """
        Refresh the blob storage client connection.
        """
        async with self._lock:
            if not self._config or not self._provider:
                raise RuntimeError("Cannot refresh: no configuration available")

            try:
                # Recreate the singleton client
                from .. import get_blob_storage

                self._client = get_blob_storage(self._provider, self._config)

                # Test the new client
                await self._client.list_containers()
                print("🔄 Blob storage client refreshed successfully")
            except Exception as e:
                raise ConnectionError(
                    f"Failed to refresh blob storage client: {str(e)}"
                )

    async def close(self):
        """Close the blob storage manager and cleanup resources."""
        async with self._lock:
            # With Azure SDK, no explicit close needed - client handles cleanup
            self._provider = None
            self._config = None
            self._client = None
            self._initialized = False
            print("🗄️  BlobStorageManager singleton client closed")

    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._initialized

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get a copy of the current configuration."""
        return self._config.copy() if self._config else None


# Global BlobStorageManager singleton
blob_storage_manager = BlobStorageManager()


async def get_blob_storage() -> BlobStorageInterface:
    """
    FastAPI dependency to get blob storage client.

    Returns the singleton BlobStorageInterface client that is thread-safe
    and optimized for reuse across requests.

    Usage in routes:
        @app.get("/upload")
        async def upload_file(storage: BlobStorageInterface = Depends(get_blob_storage)):
            # Use storage client here - same singleton client for all requests
    """
    return blob_storage_manager.get_client()


@asynccontextmanager
async def blob_storage_context() -> AsyncGenerator[BlobStorageInterface, None]:
    """
    Context manager for blob storage operations with automatic error handling.

    Uses the singleton client for consistency and performance.

    Usage:
        async with blob_storage_context() as storage:
            result = await storage.upload_blob(...)
    """
    storage = blob_storage_manager.get_client()
    try:
        yield storage
    except Exception as e:
        # Log error, could add retry logic here
        print(f"❌ Blob storage operation failed: {e}")
        raise


async def close_blob_storage():
    """
    Close the blob storage manager and cleanup resources.
    Should be called during application shutdown.
    """
    await blob_storage_manager.close()


def reset_blob_storage():
    """
    Reset the BlobStorageManager instance (useful for testing).
    """
    blob_storage_manager._provider = None
    blob_storage_manager._config = None
    blob_storage_manager._client = None
    blob_storage_manager._initialized = False


async def initialize_blob_storage(settings: "Settings" = None):
    """
    Initialize and validate blob storage on application startup.

    This function should be called during application initialization
    to ensure blob storage is properly configured and accessible.

    Args:
        settings: Settings instance containing blob storage connection info.
    """
    print("🗄️  Initializing blob storage...")

    if settings is None:
        raise ValueError("Settings instance must be provided")

    # Get config and extract provider
    blob_config = settings.blob_storage_config
    provider = blob_config.get("blob_storage_provider") or "azure"

    # Initialize the BlobStorageManager with singleton client
    await blob_storage_manager.init(provider, blob_config)

    # Validate connection
    if await blob_storage_manager.health_check():
        print("✅ Blob storage initialization completed successfully")
    else:
        raise ConnectionError("Blob storage health check failed during initialization")

    print("=" * 60)


class BlobStorageHealthCheck:
    """Health check utilities for blob storage monitoring."""

    @staticmethod
    async def check_connection() -> Dict[str, Any]:
        """
        Comprehensive health check for blob storage.

        Returns:
            Dictionary with health check results
        """
        if not blob_storage_manager.is_initialized():
            return {
                "status": "unhealthy",
                "error": "BlobStorageManager not initialized",
                "timestamp": datetime.utcnow().isoformat(),
            }

        try:
            start_time = datetime.utcnow()

            # Perform health check
            is_healthy = await blob_storage_manager.health_check()

            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat(),
                "provider": blob_storage_manager.get_config().get("provider")
                if blob_storage_manager.get_config()
                else None,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    async def check_with_retry(
        max_retries: int = 3, delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Health check with automatic retry logic.

        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds

        Returns:
            Dictionary with health check results
        """
        last_error = None

        for attempt in range(max_retries + 1):
            result = await BlobStorageHealthCheck.check_connection()

            if result["status"] == "healthy":
                if attempt > 0:
                    result["retries"] = attempt
                return result

            last_error = result.get("error", "Unknown error")

            if attempt < max_retries:
                print(
                    f"🔄 Blob storage health check failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        return {
            "status": "unhealthy",
            "error": f"Failed after {max_retries + 1} attempts. Last error: {last_error}",
            "retries": max_retries,
            "timestamp": datetime.utcnow().isoformat(),
        }
