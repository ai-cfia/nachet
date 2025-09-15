"""
Blob storage module for Nachet application.

This module provides a unified interface for managing blob storage operations
across different cloud storage providers, with built-in validation using Pydantic.
"""

from .exceptions import (
    BlobStorageError,
    BlobNotFoundError,
    ContainerNotFoundError,
    BlobAlreadyExistsError,
    ContainerAlreadyExistsError,
    PermissionError,
    ConnectionError,
    InvalidConfigurationError,
    ValidationError,
    OperationTimeoutError,
    QuotaExceededError,
    ContentValidationError,
    UnsupportedOperationError,
)

from .models import (
    BlobInfo,
    ContainerInfo,
    UploadResult,
    BlobListResult,
    ContainerListResult,
    SASTokenInfo,
    BlobProperties,
    UploadOptions,
    DownloadOptions,
    ListOptions,
)

from .interface import BlobStorageInterface
from .manager import (
    BlobStorageManager,
    blob_storage_manager,
    get_blob_storage as get_blob_storage_dependency,
    blob_storage_context,
    initialize_blob_storage,
    close_blob_storage,
    reset_blob_storage,
    BlobStorageHealthCheck,
)

__all__ = [
    # Exceptions
    "BlobStorageError",
    "BlobNotFoundError",
    "ContainerNotFoundError",
    "BlobAlreadyExistsError",
    "ContainerAlreadyExistsError",
    "PermissionError",
    "ConnectionError",
    "InvalidConfigurationError",
    "ValidationError",
    "OperationTimeoutError",
    "QuotaExceededError",
    "ContentValidationError",
    "UnsupportedOperationError",
    # Models
    "BlobInfo",
    "ContainerInfo",
    "UploadResult",
    "BlobListResult",
    "ContainerListResult",
    "SASTokenInfo",
    "BlobProperties",
    "UploadOptions",
    "DownloadOptions",
    "ListOptions",
    # Interface
    "BlobStorageInterface",
    # Manager
    "BlobStorageManager",
    "blob_storage_manager",
    "get_blob_storage_dependency",
    "blob_storage_context",
    "initialize_blob_storage",
    "close_blob_storage",
    "reset_blob_storage",
    "BlobStorageHealthCheck",
    # Factory and Singleton
    "create_blob_storage_client",
    "get_blob_storage",
]


def create_blob_storage_client(provider: str, config: dict) -> BlobStorageInterface:
    """
    Factory function to create a new blob storage client instance.

    Args:
        provider: Storage provider name (e.g., 'azure', 'aws', 'gcp')
        config: Provider-specific configuration

    Returns:
        New BlobStorageInterface implementation

    Raises:
        InvalidConfigurationError: If provider is not supported or config is invalid
    """
    if provider.lower() == "azure":
        from .azure.storage import AzureBlobStorage

        return AzureBlobStorage(config)
    else:
        raise InvalidConfigurationError(
            "provider", f"Unsupported provider: {provider}. Supported providers: azure"
        )


def get_blob_storage() -> BlobStorageInterface:
    """
    Get the singleton blob storage client from the manager.

    Returns:
        BlobStorageInterface singleton instance

    Raises:
        RuntimeError: If blob storage manager is not initialized
    """
    return blob_storage_manager.get_client()
