"""
S3-compatible Blob Storage implementation for Apache Ozone.

This module implements the BlobStorageInterface for S3-compatible storage systems,
providing operations for containers (buckets) and blobs (objects) with proper validation
using Pydantic models. The implementation uses a composition pattern
with focused operation classes for better maintainability.
"""

from typing import Dict, Any, List, Union, BinaryIO, AsyncIterator, TYPE_CHECKING
from datetime import timedelta

from ..interface import BlobStorageInterface
from ..exceptions import InvalidConfigurationError
from .client import create_s3_client
from .operations import (
    BlobOperations,
    ContainerOperations,
    MetadataOperations,
    SecurityOperations,
    AdvancedOperations,
    TierOperations,
)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


class S3BlobStorage(BlobStorageInterface):
    """
    S3-compatible Blob Storage implementation using composition pattern.

    This class serves as a facade that delegates operations to specialized
    operation classes while maintaining the BlobStorageInterface contract.
    Designed to work with Apache Ozone S3 Gateway and AWS S3.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize S3 Blob Storage client.

        Args:
            config: Configuration dictionary with connection details
                - s3_access_key_id: AWS access key ID
                - s3_secret_access_key: AWS secret access key
                - s3_region: AWS region (default: us-east-1)
                - s3_endpoint_url: Custom endpoint URL for S3-compatible services (e.g., Ozone)
                - s3_use_ssl: Whether to use SSL (optional)
                - s3_verify: Whether to verify SSL certificates (optional)
        """
        self.config = config
        self._s3_client: "S3Client" = None
        self._initialize_client()
        self._initialize_operations()

    def _initialize_client(self):
        """Initialize the S3 client using boto3."""
        try:
            if not self.config.get("s3_access_key_id") or not self.config.get(
                "s3_secret_access_key"
            ):
                raise InvalidConfigurationError(
                    "s3_credentials",
                    "S3 credentials (s3_access_key_id and s3_secret_access_key) are required",
                )

            self._s3_client = create_s3_client(self.config)
            _get_logger().info(
                "S3 Blob Storage client initialized",
                endpoint_url=self.config.get("s3_endpoint_url", "AWS S3"),
                region=self.config.get("s3_region", "us-east-1"),
            )

        except Exception as e:
            _get_logger().error(
                "Failed to initialize S3 client",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise InvalidConfigurationError(
                "s3_client",
                f"Failed to initialize S3 Blob Storage client: {str(e)}",
            )

    def _initialize_operations(self):
        """Initialize operation classes with the S3 client."""
        self._blob_ops = BlobOperations(self._s3_client)
        self._container_ops = ContainerOperations(self._s3_client)
        self._metadata_ops = MetadataOperations(self._s3_client)
        self._security_ops = SecurityOperations(self._s3_client)
        self._advanced_ops = AdvancedOperations(self._s3_client)
        self._tier_ops = TierOperations(self._s3_client)

    # Container operations - delegate to ContainerOperations
    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """List all containers (buckets) in the storage account."""
        return await self._container_ops.list_containers(**kwargs)

    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new container (bucket)."""
        return await self._container_ops.create_container(name, **kwargs)

    async def delete_container(self, name: str) -> bool:
        """Delete a container (bucket)."""
        return await self._container_ops.delete_container(name)

    async def container_exists(self, name: str) -> bool:
        """Check if a container (bucket) exists."""
        return await self._container_ops.container_exists(name)

    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """Get properties of a container (bucket)."""
        return await self._container_ops.get_container_properties(name)

    # Blob operations - delegate to BlobOperations
    async def upload_blob(
        self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs
    ) -> Dict[str, Any]:
        """Upload a blob (object) to storage."""
        return await self._blob_ops.upload_blob(container, name, data, **kwargs)

    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """Download a blob (object) from storage."""
        return await self._blob_ops.download_blob(container, name, **kwargs)

    async def download_blob_stream(
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """Download a blob (object) as a stream."""
        async for chunk in self._blob_ops.download_blob_stream(
            container, name, **kwargs
        ):
            yield chunk

    async def delete_blob(self, container: str, name: str) -> bool:
        """Delete a blob (object) from storage."""
        return await self._blob_ops.delete_blob(container, name)

    async def blob_exists(self, container: str, name: str) -> bool:
        """Check if a blob (object) exists."""
        return await self._blob_ops.blob_exists(container, name)

    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """Get detailed properties of a blob (object)."""
        return await self._blob_ops.get_blob_properties(container, name)

    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """List blobs (objects) in a container (bucket)."""
        return await self._blob_ops.list_blobs(container, **kwargs)

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Get the URL for a blob (object)."""
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
        """Copy a blob (object) within or across containers (buckets)."""
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
        """Move a blob (object) within or across containers (buckets)."""
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
        """Generate a presigned URL for a specific blob (object)."""
        return await self._security_ops.generate_sas_token(
            container, name, permissions, expiry, **kwargs
        )

    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """Generate a presigned URL for container (bucket) operations."""
        return await self._security_ops.generate_container_sas_token(
            container, permissions, expiry, **kwargs
        )

    # Metadata operations - delegate to MetadataOperations
    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Set metadata for a blob (object)."""
        await self._metadata_ops.set_blob_metadata(container, name, metadata)

    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Get metadata for a blob (object)."""
        return await self._metadata_ops.get_blob_metadata(container, name)

    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Set tags for a blob (object)."""
        await self._metadata_ops.set_blob_tags(container, name, tags)

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Get tags for a blob (object)."""
        return await self._metadata_ops.get_blob_tags(container, name)

    # Tier operations - delegate to TierOperations
    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """Set the storage class for a blob (object). Note: May not be supported by Ozone."""
        return await self._tier_ops.set_blob_tier(container, name, tier, **kwargs)
