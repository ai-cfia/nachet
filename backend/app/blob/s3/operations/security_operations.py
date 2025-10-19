"""
Security operations for S3-compatible Blob Storage (Apache Ozone).

This module handles security-related operations including presigned URL generation
for both blobs and containers with various permissions and expiry settings.
"""

from typing import List, Dict, Any, TYPE_CHECKING
from datetime import timedelta

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

# Lazy-loaded logger to avoid circular imports
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService
        _logger = LogService.get_logger()
    return _logger


class SecurityOperations:
    """Handles security operations for S3-compatible storage."""

    def __init__(self, s3_client: "S3Client"):
        """
        Initialize security operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("generate presigned URL")
    async def generate_sas_token(
        self,
        container: str,
        name: str,
        permissions: List[str],
        expiry: timedelta,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for a specific blob with given permissions and expiry.

        Note: S3 presigned URLs work differently than Azure SAS tokens.
        Each permission type generates a different presigned URL.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            permissions: List of permissions ('read', 'write', 'delete')
            expiry: Token expiry duration from now
            **kwargs: Optional parameters (currently ignored for S3)

        Returns:
            Dictionary containing:
                - sas_token: Empty string (S3 includes token in URL)
                - sas_url: Full presigned URL
                - permissions: List of granted permissions
                - expiry: Token expiry in seconds
                - blob_url: Base object URL

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If presigned URL generation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)
        ValidationHelper.validate_sas_permissions(permissions, "blob")

        # Validate container exists
        await ErrorHandler.check_container_exists(self._client, container)
        
        # Only check blob exists for read/delete operations
        # For write operations, blob doesn't need to exist yet
        if "write" not in permissions:
            await ErrorHandler.check_blob_exists(self._client, container, name)

        # Convert timedelta to seconds for S3
        expiry_seconds = int(expiry.total_seconds())

        # S3 presigned URLs are operation-specific
        # We'll generate for the most permissive operation in the permissions list
        client_method = "get_object"  # Default to read
        if "write" in permissions:
            client_method = "put_object"
        elif "delete" in permissions:
            client_method = "delete_object"

        _get_logger().info(
            "Generating presigned URL for S3 object",
            container=container,
            blob=name,
            method=client_method,
            expiry_seconds=expiry_seconds
        )

        # Generate presigned URL
        presigned_url = self._client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": container, "Key": name},
            ExpiresIn=expiry_seconds,
        )

        # Build base object URL
        endpoint_url = self._client.meta.endpoint_url
        blob_url = f"{endpoint_url}/{container}/{name}"

        result = {
            "sas_token": "",  # S3 includes credentials in the URL itself
            "sas_url": presigned_url,
            "blob_url": blob_url,
            "permissions": permissions,
            "expiry": expiry_seconds,
            "container": container,
            "blob_name": name,
            "method": client_method,
        }

        _get_logger().info("Presigned URL generated successfully", container=container, blob=name)
        return result

    @ErrorHandler.handle_service_errors("generate container presigned URL")
    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a presigned URL for container operations.

        Note: S3 doesn't have direct container-level presigned URLs like Azure.
        This generates a presigned URL for listing objects in the bucket.

        Args:
            container: Container name (S3 bucket)
            permissions: List of permissions ('read', 'write', 'delete', 'list')
            expiry: Token expiry duration from now
            **kwargs: Optional parameters (currently ignored)

        Returns:
            Dictionary containing:
                - sas_token: Empty string
                - sas_url: Full presigned URL for list_objects
                - permissions: List of granted permissions
                - expiry: Token expiry in seconds

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If presigned URL generation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_sas_permissions(permissions, "container")

        # Validate container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Convert timedelta to seconds for S3
        expiry_seconds = int(expiry.total_seconds())

        # For container operations, we'll generate a presigned URL for list_objects_v2
        client_method = "list_objects_v2"

        _get_logger().info(
            "Generating presigned URL for S3 bucket",
            container=container,
            method=client_method,
            expiry_seconds=expiry_seconds
        )

        # Generate presigned URL
        presigned_url = self._client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": container},
            ExpiresIn=expiry_seconds,
        )

        # Build base container URL
        endpoint_url = self._client.meta.endpoint_url
        container_url = f"{endpoint_url}/{container}"

        result = {
            "sas_token": "",  # S3 includes credentials in the URL itself
            "sas_url": presigned_url,
            "container_url": container_url,
            "permissions": permissions,
            "expiry": expiry_seconds,
            "container": container,
            "method": client_method,
        }

        _get_logger().info("Container presigned URL generated successfully", container=container)
        return result
