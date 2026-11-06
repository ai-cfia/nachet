"""Dataset-specific extensions of the reviewed shared blob providers."""

from typing import Any

from blob.exceptions import InvalidConfigurationError

from .azure import DatasetAzureBlobStorage
from .s3 import DatasetS3BlobStorage


def create_dataset_blob_storage_client(
    provider: str, config: dict[str, Any]
) -> DatasetS3BlobStorage | DatasetAzureBlobStorage:
    """Construct a dataset provider while leaving common provider behavior intact."""
    if provider.lower() == "s3":
        return DatasetS3BlobStorage(config)
    if provider.lower() == "azure":
        return DatasetAzureBlobStorage(config)
    raise InvalidConfigurationError(
        "provider", f"Unsupported provider: {provider}. Supported providers: azure, s3"
    )
