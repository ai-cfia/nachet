"""
Tier operations for S3-compatible Blob Storage (Apache Ozone).

This module handles blob tier (storage class) management operations.
Note: Apache Ozone may not support storage classes, so operations may be no-ops.
"""

from typing import TYPE_CHECKING
from botocore.exceptions import ClientError

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


class TierOperations:
    """Handles blob tier (storage class) operations for S3-compatible storage."""

    def __init__(self, s3_client: "S3Client"):
        """
        Initialize tier operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("set blob tier")
    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """
        Set the storage class for a blob.

        Note: Apache Ozone may not support storage classes. This implementation
        attempts to set the storage class, but it may be a no-op on Ozone.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            tier: Storage class (currently only STANDARD is supported)
            **kwargs: Additional options

        Returns:
            True if tier was set successfully (or if operation is not supported)

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If tier setting fails or invalid tier
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)
        ValidationHelper.validate_blob_tier_with_model(container, name, tier)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Check if blob exists
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Validate tier
        validated_tier = ValidationHelper.validate_blob_tier(tier)

        _get_logger().info(
            "Attempting to set blob storage class",
            container=container,
            blob=name,
            tier=validated_tier,
        )

        try:
            # Copy object to itself with new storage class
            # This is how you change storage class in S3
            copy_source = {"Bucket": container, "Key": name}
            self._client.copy_object(
                CopySource=copy_source,
                Bucket=container,
                Key=name,
                StorageClass=validated_tier,
                MetadataDirective="COPY",  # Preserve existing metadata
            )

            _get_logger().info(
                "Blob storage class set successfully",
                container=container,
                blob=name,
                tier=validated_tier,
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            # Some S3-compatible systems (like Ozone) may not support storage classes
            if error_code in ["NotImplemented", "InvalidStorageClass"]:
                _get_logger().warning(
                    "Storage class not supported by this S3-compatible system",
                    container=container,
                    blob=name,
                    tier=validated_tier,
                    error=str(e),
                )
                # Return True as the operation is "successful" (just not supported)
                return True

            # Re-raise for error handler to process
            raise
