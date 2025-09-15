"""
Azure Blob Storage implementation.

This module implements the BlobStorageInterface for Azure Blob Storage,
providing list operations for containers and blobs with proper validation
using Pydantic models.
"""

from typing import Dict, Any, List, Optional

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ServiceRequestError

from ..interface import BlobStorageInterface
from ..models import (
    BlobInfo,
    ContainerInfo,
    BlobListResult,
    ContainerListResult,
    ListOptions,
)
from ..exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    ConnectionError,
    InvalidConfigurationError,
)
from .client import create_blob_service_client, create_container_client


class AzureBlobStorage(BlobStorageInterface):
    """Azure Blob Storage implementation of the blob storage interface."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure Blob Storage client.

        Args:
            config: Configuration dictionary with connection details
        """
        self.config = config
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client."""
        try:
            connection_string = self.azure_storage_connection_string()
            print(f"🔗 Using Azure Storage connection string: \n{connection_string}")
            if not connection_string:
                raise InvalidConfigurationError(
                    "connection_string", "Azure storage connection string is required"
                )

            self._blob_service_client = create_blob_service_client(connection_string)
            print("🔵 Azure Blob Storage client initialized")

        except Exception as e:
            raise InvalidConfigurationError(
                "azure_client",
                f"Failed to initialize Azure Blob Storage client: {str(e)}",
            )

    def azure_storage_connection_string(self) -> str:
        """Build Azure storage connection string from config dictionary."""
        return (
            f"DefaultEndpointsProtocol={self.config['blob_storage_endpoint_protocol']};"
            f"AccountName={self.config['blob_storage_name']};"
            f"AccountKey={self.config['blob_storage_key']};"
            f"EndpointSuffix={self.config['blob_storage_endpoint_suffix']};"
            f"BlobEndpoint={self.config['blob_storage_endpoint_base']}/{self.config['blob_storage_name']};"
        )

    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """
        List all containers in the storage account.

        Args:
            **kwargs: Additional options (can include ListOptions)

        Returns:
            ContainerListResult with list of containers
        """
        try:
            options = kwargs.get("options")
            if isinstance(options, dict):
                options = ListOptions(**options)
            elif options is None:
                options = ListOptions()

            containers = []
            continuation_token = None

            # Use Azure SDK to list containers
            container_iter = self._blob_service_client.list_containers(
                name_starts_with=options.prefix,
                include_metadata=options.include_metadata,
            )

            count = 0
            for container in container_iter:
                if options.max_results and count >= options.max_results:
                    continuation_token = "has_more"  # Simplified for demo
                    break

                # Convert Azure container to our ContainerInfo model
                container_info = ContainerInfo(
                    name=container.name,
                    last_modified=container.last_modified,
                    etag=container.etag,
                    metadata=container.metadata or {},
                    public_access=getattr(container, "public_access", None),
                )
                containers.append(container_info)
                count += 1

            result = ContainerListResult(
                containers=containers,
                continuation_token=continuation_token,
                total_count=len(containers),
            )

            return result.model_dump()

        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(f"Failed to list containers: {str(e)}")

    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """
        List blobs in a container.

        Args:
            container: Container name
            **kwargs: Additional options (can include ListOptions)

        Returns:
            BlobListResult with list of blobs
        """
        try:
            options = kwargs.get("options")
            if isinstance(options, dict):
                options = ListOptions(**options)
            elif options is None:
                options = ListOptions()

            # Get container client
            container_client = create_container_client(
                self._blob_service_client, container
            )

            # Check if container exists
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            blobs = []
            continuation_token = None

            # List blobs in the container
            blob_iter = container_client.list_blobs(
                name_starts_with=options.prefix,
                include=["metadata", "tags"]
                if (options.include_metadata or options.include_tags)
                else None,
            )

            count = 0
            for blob in blob_iter:
                if options.max_results and count >= options.max_results:
                    continuation_token = "has_more"  # Simplified for demo
                    break

                # Convert Azure blob to our BlobInfo model
                blob_info = BlobInfo(
                    name=blob.name,
                    container=container,
                    size=blob.size,
                    last_modified=blob.last_modified,
                    etag=blob.etag,
                    content_type=blob.content_settings.content_type
                    if blob.content_settings
                    else "application/octet-stream",
                    metadata=blob.metadata or {},
                    tags=getattr(blob, "tags", {}) or {},
                )
                blobs.append(blob_info)
                count += 1

            result = BlobListResult(
                blobs=blobs,
                continuation_token=continuation_token,
                prefix=options.prefix,
                container=container,
                total_count=len(blobs),
            )

            return result.model_dump()

        except ContainerNotFoundError:
            raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to list blobs in container '{container}': {str(e)}"
            )

    # Stub implementations for required interface methods (not implemented yet)
    async def upload_blob(
        self, container: str, name: str, data, **kwargs
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("upload_blob not implemented yet")

    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """Not implemented yet."""
        raise NotImplementedError("download_blob not implemented yet")

    async def download_blob_stream(self, container: str, name: str, **kwargs):
        """Not implemented yet."""
        raise NotImplementedError("download_blob_stream not implemented yet")

    async def delete_blob(self, container: str, name: str) -> bool:
        """Not implemented yet."""
        raise NotImplementedError("delete_blob not implemented yet")

    async def blob_exists(self, container: str, name: str) -> bool:
        """Not implemented yet."""
        raise NotImplementedError("blob_exists not implemented yet")

    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_properties not implemented yet")

    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("copy_blob not implemented yet")

    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("move_blob not implemented yet")

    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("create_container not implemented yet")

    async def delete_container(self, name: str) -> bool:
        """Not implemented yet."""
        raise NotImplementedError("delete_container not implemented yet")

    async def container_exists(self, name: str) -> bool:
        """Not implemented yet."""
        raise NotImplementedError("container_exists not implemented yet")

    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("get_container_properties not implemented yet")

    async def generate_sas_token(
        self, container: str, name: str, permissions: List[str], expiry, **kwargs
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("generate_sas_token not implemented yet")

    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry, **kwargs
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("generate_container_sas_token not implemented yet")

    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Not implemented yet."""
        raise NotImplementedError("set_blob_metadata not implemented yet")

    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_metadata not implemented yet")

    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Not implemented yet."""
        raise NotImplementedError("set_blob_tags not implemented yet")

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_tags not implemented yet")

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_url not implemented yet")
