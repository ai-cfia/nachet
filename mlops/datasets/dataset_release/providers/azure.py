"""Azure configuration and conflict translation for dataset publication."""

from typing import Any

from azure.core.exceptions import ResourceExistsError
from blob.azure.storage import AzureBlobStorage
from blob.exceptions import BlobAlreadyExistsError, BlobStorageError


class DatasetAzureBlobStorage(AzureBlobStorage):
    """Extend the shared Azure provider without changing the shared copy."""

    def azure_storage_connection_string(self) -> str:
        """Accept the dataset command's connection string or the shared config."""
        if self.config.get("connection_string"):
            return self.config["connection_string"]
        return super().azure_storage_connection_string()

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        """Translate Azure create-only conflicts to the dataset conflict contract."""
        try:
            return await super().upload_blob(container, name, data, **kwargs)
        except BlobStorageError as error:
            # The shared provider wraps SDK errors with their exception context.
            if not kwargs.get("overwrite", True) and isinstance(
                error.__context__, ResourceExistsError
            ):
                raise BlobAlreadyExistsError(container, name) from error
            raise

    def close(self) -> None:
        """Release the dataset provider's SDK connection pool."""
        self._blob_service_client.close()
