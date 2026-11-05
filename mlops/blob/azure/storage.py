"""
Azure Blob Storage implementation.

This module implements the BlobStorageInterface for Azure Blob Storage,
providing operations for containers and blobs with proper validation
using Pydantic models. The implementation uses a composition pattern
with focused operation classes for better maintainability.
"""

from beartype.typing import Dict, Any, List, Optional, Union, BinaryIO, AsyncIterator
from datetime import timedelta

from azure.storage.blob import BlobServiceClient

from ..interface import BlobStorageInterface
from ..exceptions import InvalidConfigurationError
from .client import create_blob_service_client
from .operations import (
    BlobOperations,
    ContainerOperations,
    MetadataOperations,
    SecurityOperations,
    AdvancedOperations,
    TierOperations,
)

# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


class AzureBlobStorage(BlobStorageInterface):
    """
    Azure Blob Storage implementation using composition pattern.

    This class serves as a facade that delegates operations to specialized
    operation classes while maintaining the same interface as before.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure Blob Storage client.

        Args:
            config: Configuration dictionary with connection details
        """
        self.config = config
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._initialize_client()
        self._initialize_operations()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client."""
        try:
            connection_string = self.azure_storage_connection_string()
            # print(f"🔗 Using Azure Storage connection string: \n{connection_string}")
            if not connection_string:
                raise InvalidConfigurationError(
                    "connection_string", "Azure storage connection string is required"
                )

            # Extract timeout settings from config
            connection_timeout = self.config.get("connection_timeout")
            read_timeout = self.config.get("read_timeout")

            self._blob_service_client = create_blob_service_client(
                connection_string,
                connection_timeout=connection_timeout,
                read_timeout=read_timeout,
            )
            _get_logger().info("Azure Blob Storage client initialized")

        except Exception as e:
            raise InvalidConfigurationError(
                "azure_client",
                f"Failed to initialize Azure Blob Storage client: {str(e)}",
            )

    def _initialize_operations(self):
        """Initialize operation classes with the Azure client."""
        assert self._blob_service_client is not None, (
            "Blob service client must be initialized"
        )
        self._blob_ops = BlobOperations(self._blob_service_client)
        self._container_ops = ContainerOperations(self._blob_service_client)
        self._metadata_ops = MetadataOperations(self._blob_service_client)
        self._security_ops = SecurityOperations(self._blob_service_client)
        self._advanced_ops = AdvancedOperations(self._blob_service_client)
        self._tier_ops = TierOperations(self._blob_service_client)

    def azure_storage_connection_string(self) -> str:
        """Build Azure storage connection string from config dictionary."""
        # For core.windows.net, the account name is already in the base URL
        # For other endpoints (like Azurite), we need to append the account name
        endpoint_suffix = self.config["blob_storage_endpoint_suffix"]
        base_url = self.config["blob_storage_endpoint_base"]

        if endpoint_suffix == "core.windows.net":
            blob_endpoint = base_url
        else:
            # For Azurite and other custom endpoints, append account name
            blob_endpoint = f"{base_url}/{self.config['blob_storage_name']}"

        return (
            f"DefaultEndpointsProtocol={self.config['blob_storage_endpoint_protocol']};"
            f"AccountName={self.config['blob_storage_name']};"
            f"AccountKey={self.config['blob_storage_key']};"
            f"EndpointSuffix={endpoint_suffix};"
            f"BlobEndpoint={blob_endpoint};"
        )

    # Container operations - delegate to ContainerOperations
    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """List all containers in the storage account."""
        return await self._container_ops.list_containers(**kwargs)

    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new container."""
        return await self._container_ops.create_container(name, **kwargs)

    async def delete_container(self, name: str) -> bool:
        """Delete a container."""
        return await self._container_ops.delete_container(name)

    async def container_exists(self, name: str) -> bool:
        """Check if a container exists."""
        return await self._container_ops.container_exists(name)

    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """Get properties of a container."""
        return await self._container_ops.get_container_properties(name)

    # Blob operations - delegate to BlobOperations
    async def upload_blob(
        self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs
    ) -> Dict[str, Any]:
        """Upload a blob to storage."""
        return await self._blob_ops.upload_blob(container, name, data, **kwargs)

    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """Download a blob from storage."""
        return await self._blob_ops.download_blob(container, name, **kwargs)

    async def download_blob_stream(  # type: ignore[override]
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """Download a blob as a stream."""
        async for chunk in self._blob_ops.download_blob_stream(
            container, name, **kwargs
        ):
            yield chunk

    async def delete_blob(self, container: str, name: str) -> bool:
        """Delete a blob from storage."""
        return await self._blob_ops.delete_blob(container, name)

    async def blob_exists(self, container: str, name: str) -> bool:
        """Check if a blob exists."""
        return await self._blob_ops.blob_exists(container, name)

    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """Get detailed properties of a blob."""
        return await self._blob_ops.get_blob_properties(container, name)

    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """List blobs in a container."""
        return await self._blob_ops.list_blobs(container, **kwargs)

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Get the URL for a blob."""
        return await self._blob_ops.get_blob_url(container, name, **kwargs)

    # Advanced operations - delegate to AdvancedOperations
    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Copy a blob within or across containers."""
        return await self._advanced_ops.copy_blob(
            source_container, source_name, dest_container, dest_name, **kwargs
        )

    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Move a blob within or across containers."""
        return await self._advanced_ops.move_blob(
            source_container, source_name, dest_container, dest_name, **kwargs
        )

    # Security operations - delegate to SecurityOperations
    async def generate_sas_token(
        self,
        container: str,
        name: str,
        permissions: List[str],
        expiry: timedelta,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a SAS token for a specific blob."""
        return await self._security_ops.generate_sas_token(
            container, name, permissions, expiry, **kwargs
        )

    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """Generate a SAS token for a container."""
        return await self._security_ops.generate_container_sas_token(
            container, permissions, expiry, **kwargs
        )

    # Metadata operations - delegate to MetadataOperations
    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Set metadata for a blob."""
        await self._metadata_ops.set_blob_metadata(container, name, metadata)

    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Get metadata for a blob."""
        return await self._metadata_ops.get_blob_metadata(container, name)

    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Set tags for a blob."""
        await self._metadata_ops.set_blob_tags(container, name, tags)

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Get tags for a blob."""
        return await self._metadata_ops.get_blob_tags(container, name)

    # Tier operations - delegate to TierOperations
    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """Set the access tier for a blob (Hot, Cool)."""
        return await self._tier_ops.set_blob_tier(container, name, tier, **kwargs)
