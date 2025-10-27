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

from beartype.typing import Optional, Dict, Any, AsyncGenerator, TYPE_CHECKING
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

if TYPE_CHECKING:
    from app.api.config import Settings

from app.blob.exceptions import InvalidConfigurationError, ConnectionError
from app.blob.interface import BlobStorageInterface

# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


class BlobStorageManager:
    """
    Manages multiple singleton blob storage clients following Azure SDK best practices.

    This manager maintains multiple BlobServiceClient instances (one per storage account)
    that are thread-safe and reused across all requests for optimal performance.

    Supported storage accounts:
    - 'cloud': Primary Azure Blob Storage
    - 'external': External Azure Blob Storage
    - 'onprem': S3-compatible storage (Apache Ozone)
    """

    def __init__(self) -> None:
        self._providers: Dict[str, str] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, BlobStorageInterface] = {}
        self._initialized: bool = False
        self._lock = asyncio.Lock()

    async def init_multiple(
        self, storage_configs: Dict[str, tuple[str, Dict[str, Any]]], **kwargs
    ):
        """
        Initialize the BlobStorageManager with multiple storage clients.

        Args:
            storage_configs: Dictionary mapping storage names to (provider, config) tuples
                Example: {
                    'cloud': ('azure', azure_config),
                    'external': ('azure', azure_external_config),
                    'onprem': ('s3', s3_config)
                }
            **kwargs: Additional initialization options
        """
        async with self._lock:
            try:
                from app.blob import create_blob_storage_client

                for name, (provider, config) in storage_configs.items():
                    # Create a client for each storage account
                    client = create_blob_storage_client(provider, config)

                    # Test the client works
                    await client.list_containers()

                    # Store config and client
                    self._providers[name] = provider
                    self._configs[name] = config.copy()
                    self._clients[name] = client

                    _get_logger().info(
                        f"BlobStorageManager initialized storage account '{name}'",
                        provider=provider,
                    )

                self._initialized = True
                _get_logger().info(
                    f"BlobStorageManager initialized with {len(self._clients)} storage accounts"
                )
            except Exception as e:
                raise InvalidConfigurationError(
                    "initialization",
                    f"Failed to initialize blob storage clients: {str(e)}",
                )

    async def init(self, provider: str, config: Dict[str, Any], **kwargs):
        """
        Legacy initialization method for backward compatibility.
        Initializes a single storage account named 'default'.

        DEPRECATED: Use init_multiple() instead.

        Args:
            provider: Storage provider name (e.g., 'azure', 's3')
            config: Provider-specific configuration
            **kwargs: Additional initialization options
        """
        _get_logger().warning(
            "BlobStorageManager.init() is deprecated. Use init_multiple() instead."
        )
        await self.init_multiple({"default": (provider, config)}, **kwargs)

    def get_client(self, name: str) -> BlobStorageInterface:
        """
        Get a specific blob storage client by name.

        Args:
            name: Storage account name ('cloud', 'external', or 'onprem')

        Returns:
            The BlobStorageInterface instance for the specified storage

        Raises:
            RuntimeError: If manager not initialized
            KeyError: If storage name not found

        Note: These clients are thread-safe and should be reused across requests.
        """
        if not self._initialized:
            raise RuntimeError(
                "BlobStorageManager not initialized. Call init_multiple() first."
            )

        if name not in self._clients:
            available = ", ".join(self._clients.keys())
            raise KeyError(
                f"Storage account '{name}' not found. Available: {available}"
            )

        return self._clients[name]

    def create_client(self, name: str = "default") -> BlobStorageInterface:
        """
        Create a blob storage client (kept for backward compatibility).

        DEPRECATED: Use get_client(name) instead.

        Args:
            name: Storage account name (default: 'default')

        Returns:
            The BlobStorageInterface instance for the specified storage
        """
        _get_logger().warning(
            "BlobStorageManager.create_client() is deprecated. Use get_client(name) instead."
        )
        return self.get_client(name)

    async def health_check(self, name: Optional[str] = None) -> bool:
        """
        Perform a health check on blob storage connections.

        Args:
            name: Specific storage account to check, or None to check all

        Returns:
            True if all checked connections are healthy, False otherwise
        """
        if not self._initialized or not self._clients:
            return False

        # Check specific storage or all storages
        clients_to_check = {name: self._clients[name]} if name else self._clients

        try:
            all_healthy = True
            for storage_name, client in clients_to_check.items():
                try:
                    await client.list_containers()
                    _get_logger().debug(
                        f"Health check passed for storage '{storage_name}'"
                    )
                except Exception as e:
                    all_healthy = False
                    _get_logger().warning(
                        f"Blob storage health check failed for '{storage_name}'",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            return all_healthy
        except Exception as e:
            _get_logger().warning(
                "Blob storage health check failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def refresh_connection(self, name: Optional[str] = None):
        """
        Refresh blob storage client connections.

        Args:
            name: Specific storage account to refresh, or None to refresh all
        """
        async with self._lock:
            if not self._configs or not self._providers:
                raise RuntimeError("Cannot refresh: no configuration available")

            # Refresh specific storage or all storages
            storages_to_refresh = [name] if name else list(self._clients.keys())

            try:
                from app.blob import create_blob_storage_client

                for storage_name in storages_to_refresh:
                    if storage_name not in self._configs:
                        raise RuntimeError(
                            f"Cannot refresh '{storage_name}': no configuration available"
                        )

                    # Recreate the client using the factory function
                    provider = self._providers[storage_name]
                    config = self._configs[storage_name]
                    self._clients[storage_name] = create_blob_storage_client(
                        provider, config
                    )

                    # Test the new client
                    await self._clients[storage_name].list_containers()
                    _get_logger().info(
                        f"Blob storage client '{storage_name}' refreshed successfully"
                    )
            except Exception as e:
                raise ConnectionError(
                    f"Failed to refresh blob storage client: {str(e)}"
                )

    async def close(self):
        """Close the blob storage manager and cleanup resources."""
        async with self._lock:
            # With Azure SDK, no explicit close needed - client handles cleanup
            self._providers = {}
            self._configs = {}
            self._clients = {}
            self._initialized = False
            _get_logger().info("BlobStorageManager closed all storage clients")

    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._initialized

    def get_config(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a copy of storage configuration(s).

        Args:
            name: Specific storage account name, or None to get all configs

        Returns:
            Single config dict if name provided, or dict of all configs if None
        """
        if name:
            return self._configs[name].copy() if name in self._configs else None
        return {k: v.copy() for k, v in self._configs.items()}


# Global BlobStorageManager singleton
blob_storage_manager = BlobStorageManager()


async def get_blob_storage(name: str = "cloud") -> BlobStorageInterface:
    """
    FastAPI dependency to get blob storage client.

    DEPRECATED: Use blob_storage_manager.get_client(name) directly instead.

    Args:
        name: Storage account name ('cloud', 'external', or 'onprem')

    Returns:
        The BlobStorageInterface client for the specified storage

    Usage in routes:
        @app.get("/upload")
        async def upload_file(storage: BlobStorageInterface = Depends(get_blob_storage)):
            # Use storage client here
    """
    return blob_storage_manager.get_client(name)


@asynccontextmanager
async def blob_storage_context(
    name: str = "cloud",
) -> AsyncGenerator[BlobStorageInterface, None]:
    """
    Context manager for blob storage operations with automatic error handling.

    Args:
        name: Storage account name ('cloud', 'external', or 'onprem')

    Usage:
        async with blob_storage_context('cloud') as storage:
            result = await storage.upload_blob(...)
    """
    storage = blob_storage_manager.get_client(name)
    try:
        yield storage
    except Exception as e:
        # Log error, could add retry logic here
        _get_logger().error(
            f"Blob storage operation failed for '{name}'",
            error=str(e),
            error_type=type(e).__name__,
        )
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
    blob_storage_manager._providers = {}
    blob_storage_manager._configs = {}
    blob_storage_manager._clients = {}
    blob_storage_manager._initialized = False


async def initialize_blob_storage(settings: Optional["Settings"] = None):
    """
    Initialize and validate blob storage on application startup.

    This function should be called during application initialization
    to ensure blob storage is properly configured and accessible.

    Initializes three storage accounts:
    - 'cloud': Primary Azure Blob Storage
    - 'external': External Azure Blob Storage
    - 'onprem': S3-compatible storage (Apache Ozone)

    Args:
        settings: Settings instance containing blob storage connection info.
    """
    _get_logger().info("Initializing blob storage accounts...")

    if settings is None:
        raise ValueError("Settings instance must be provided")

    # Build storage configs for all three accounts
    storage_configs = {
        "cloud": ("azure", settings.blob_storage_config),
        "external": ("azure", settings.blob_storage_external_config),
        "onprem": ("s3", settings.s3_storage_config),
    }

    # Initialize the BlobStorageManager with all storage clients
    await blob_storage_manager.init_multiple(storage_configs)

    # Validate connections for all storage accounts
    if await blob_storage_manager.health_check():
        _get_logger().info(
            "All blob storage accounts initialized and validated successfully"
        )
    else:
        raise ConnectionError(
            "One or more blob storage accounts failed health check during initialization"
        )

    _get_logger().info("=" * 60)


class BlobStorageHealthCheck:
    """Health check utilities for blob storage monitoring."""

    @staticmethod
    async def check_connection(name: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive health check for blob storage.

        Args:
            name: Specific storage account to check, or None to check all

        Returns:
            Dictionary with health check results for all or specific storage
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
            is_healthy = await blob_storage_manager.health_check(name)

            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()

            configs = blob_storage_manager.get_config(name)
            storage_info = {}
            if name:
                storage_info = {
                    name: configs.get("blob_storage_provider") if configs else None
                }
            else:
                storage_info = (
                    {k: v.get("blob_storage_provider") for k, v in configs.items()}
                    if configs
                    else {}
                )

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat(),
                "storages": storage_info,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    async def check_with_retry(
        max_retries: int = 3, delay: float = 1.0, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Health check with automatic retry logic.

        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            name: Specific storage account to check, or None to check all

        Returns:
            Dictionary with health check results
        """
        last_error = None

        for attempt in range(max_retries + 1):
            result = await BlobStorageHealthCheck.check_connection(name)

            if result["status"] == "healthy":
                if attempt > 0:
                    result["retries"] = attempt
                return result

            last_error = result.get("error", "Unknown error")

            if attempt < max_retries:
                _get_logger().warning(
                    "Blob storage health check failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=max_retries + 1,
                    delay_seconds=delay,
                    storage_name=name or "all",
                )
                await asyncio.sleep(delay)

        return {
            "status": "unhealthy",
            "error": f"Failed after {max_retries + 1} attempts. Last error: {last_error}",
            "retries": max_retries,
            "timestamp": datetime.utcnow().isoformat(),
        }
