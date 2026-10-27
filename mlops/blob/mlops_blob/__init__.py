"""Standalone copy of backend app.blob; see README.md for provenance."""

from .exceptions import InvalidConfigurationError
from .interface import BlobStorageInterface

__all__ = ["BlobStorageInterface", "create_blob_storage_client"]


def create_blob_storage_client(provider: str, config: dict) -> BlobStorageInterface:
    """Create a provider without starting the backend application or its manager."""
    if provider.lower() == "azure":
        from .azure.storage import AzureBlobStorage

        return AzureBlobStorage(config)
    if provider.lower() == "s3":
        from .s3.storage import S3BlobStorage

        return S3BlobStorage(config)
    raise InvalidConfigurationError(
        "provider", f"Unsupported provider: {provider}. Supported providers: azure, s3"
    )
