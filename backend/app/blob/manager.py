"""
Blob storage manager for connection pooling and lifecycle management.

This module provides a factory pattern for blob storage clients, creating
fresh client instances per request rather than sharing a singleton client.

DESIGN RATIONALE - Factory vs Singleton:

✅ BENEFITS of Factory Pattern:
- **Scalability**: Each client has its own connection pool (more concurrent connections)
- **Isolation**: Client failures don't affect other requests
- **Resource Management**: Clients can be garbage collected after request completion
- **Threading**: Better concurrent request handling
- **Debugging**: Easier to trace issues to specific requests

⚠️ CONSIDERATIONS:
- **Initialization Cost**: Creating clients per request has slight overhead
- **Memory**: Multiple clients use more memory than singleton
- **Connection Limits**: More clients = more connections (monitor Azure limits)

💡 MITIGATION:
- Azure SDK handles connection pooling internally per client
- Client creation is lightweight (mostly config validation)
- Benefits outweigh costs for production workloads

The manager validates configuration once at startup, then acts as a factory
for creating Azure Blob Storage clients on-demand.
"""

from typing import Optional, Dict, Any, AsyncGenerator, TYPE_CHECKING
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
import threading

if TYPE_CHECKING:
    from app.api.config import Settings

from app.blob.exceptions import InvalidConfigurationError, ConnectionError
from app.blob.interface import BlobStorageInterface


# Thread-local storage for optional client caching
_thread_local = threading.local()


class BlobStorageManager:
    """
    Manages blob storage client factory and configuration.
    
    This manager acts as a factory for creating blob storage clients rather than
    maintaining a singleton client, enabling better scalability and isolation.
    """

    def __init__(self) -> None:
        self._provider: Optional[str] = None
        self._config: Optional[Dict[str, Any]] = None
        self._initialized: bool = False
        self._lock = asyncio.Lock()
        self._enable_thread_caching: bool = False  # Optional optimization

    def init(self, provider: str, config: Dict[str, Any], enable_thread_caching: bool = False, **kwargs):
        """
        Initialize the BlobStorageManager with provider and configuration.
        
        This only stores configuration - actual clients are created on-demand.

        Args:
            provider: Storage provider name (e.g., 'azure')
            config: Provider-specific configuration
            enable_thread_caching: If True, cache one client per thread for performance
            **kwargs: Additional initialization options
        """
        try:
            # Validate config by creating a test client
            from .. import get_blob_storage
            _ = get_blob_storage(provider, config)  # Test configuration
            
            # Store config for future client creation
            self._provider = provider
            self._config = config.copy()
            self._initialized = True
            self._enable_thread_caching = enable_thread_caching
            cache_status = "with thread caching" if enable_thread_caching else "without caching"
            print(f"🗄️  BlobStorageManager initialized as factory for provider: {provider} ({cache_status})")
        except Exception as e:
            raise InvalidConfigurationError(
                "initialization", f"Failed to initialize blob storage factory: {str(e)}"
            )

    def create_client(self) -> BlobStorageInterface:
        """
        Create a new blob storage client instance.
        
        Returns:
            A new BlobStorageInterface instance for this request
            
        Note: Each call creates a fresh client with its own connection pool,
        enabling better scalability and isolation between requests.
        
        If thread caching is enabled, returns cached client for current thread.
        """
        if not self._initialized or not self._config or not self._provider:
            raise RuntimeError("BlobStorageManager not initialized. Call init() first.")
            
        # Optional thread-local caching for performance
        if self._enable_thread_caching:
            if not hasattr(_thread_local, 'client') or _thread_local.client is None:
                from .. import get_blob_storage
                _thread_local.client = get_blob_storage(self._provider, self._config)
            return _thread_local.client
        
        # Default: new client per call
        from .. import get_blob_storage
        return get_blob_storage(self._provider, self._config)

    def get_client(self) -> BlobStorageInterface:
        """
        Get a blob storage client (kept for backward compatibility).
        
        Note: This now creates a new client each time for better scalability.
        """
        return self.create_client()

    async def health_check(self) -> bool:
        """
        Perform a health check on the blob storage connection.
        
        Creates a temporary client to test connectivity.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._initialized:
            return False

        try:
            # Create a temporary client for health check
            client = self.create_client()
            # Try to list containers as a health check
            await client.list_containers()
            return True
        except Exception as e:
            print(f"⚠️  Blob storage health check failed: {e}")
            return False

    async def refresh_connection(self):
        """
        Refresh the blob storage configuration.
        
        Note: With factory pattern, this validates the config is still valid.
        Individual clients will be created fresh on each request.
        """
        async with self._lock:
            if not self._config or not self._provider:
                raise RuntimeError("Cannot refresh: no configuration available")

            try:
                # Test that we can still create clients with current config
                from .. import get_blob_storage
                _ = get_blob_storage(self._provider, self._config)  # Test configuration
                print("🔄 Blob storage configuration validated")
            except Exception as e:
                raise ConnectionError(
                    f"Failed to validate blob storage configuration: {str(e)}"
                )

    async def close(self):
        """Close the blob storage manager and cleanup configuration."""
        # With factory pattern, no persistent clients to close
        self._provider = None
        self._config = None
        self._initialized = False
        print("🗄️  BlobStorageManager factory closed")

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
    
    Creates a new client instance for each request, providing:
    - Better scalability (separate connection pools)
    - Request isolation (failures don't affect other requests)  
    - Proper resource cleanup per request

    Usage in routes:
        @app.get("/upload")
        async def upload_file(storage: BlobStorageInterface = Depends(get_blob_storage)):
            # Use storage client here - fresh client per request
    """
    return blob_storage_manager.create_client()  # New client per request


@asynccontextmanager
async def blob_storage_context() -> AsyncGenerator[BlobStorageInterface, None]:
    """
    Context manager for blob storage operations with automatic error handling.
    
    Creates a new client instance for this context, ensuring isolation.

    Usage:
        async with blob_storage_context() as storage:
            result = await storage.upload_blob(...)
    """
    storage = blob_storage_manager.create_client()  # New client per context
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
    
    # Initialize the BlobStorageManager with provider and config
    blob_storage_manager.init(provider, blob_config)

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
