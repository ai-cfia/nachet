"""
Metadata and tags operations for S3-compatible Blob Storage (Apache Ozone).

This module handles blob metadata and tags operations including setting
and retrieving custom metadata and object tags using boto3.
"""

from beartype.typing import Dict, Any

from botocore.exceptions import ClientError

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper

# Lazy-loaded logger to avoid circular imports
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


class MetadataOperations:
    """Handles metadata and tags operations for S3-compatible storage."""

    def __init__(self, s3_client: Any):  # Type: S3Client (boto3)
        """
        Initialize metadata operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("set blob metadata")
    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """
        Set custom metadata for a blob.

        Note: In S3-compatible storage (like Apache Ozone), setting metadata
        requires re-uploading the object with new metadata since copy_object
        to self is not supported. This is different from Azure's direct metadata update.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            metadata: Dictionary of metadata key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If metadata setting operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)
        ErrorHandler.handle_metadata_validation_errors(metadata, "metadata")

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Get current metadata to check if it's different
        current_response = self._client.head_object(Bucket=container, Key=name)
        current_metadata = current_response.get("Metadata", {})

        # Normalize metadata for comparison (convert to dict if needed)
        current_metadata_dict = dict(current_metadata) if current_metadata else {}
        new_metadata_dict = dict(metadata) if metadata else {}

        # Check if metadata is actually different
        if current_metadata_dict == new_metadata_dict:
            _get_logger().info(
                "Metadata unchanged, skipping update operation",
                container=container,
                blob=name,
            )
            return

        # Apache Ozone doesn't support copy_object to self, so we need to
        # download the object content and re-upload with new metadata
        _get_logger().info(
            "Setting blob metadata via re-upload (Apache Ozone workaround)",
            container=container,
            blob=name,
        )

        # Download the current object
        obj_response = self._client.get_object(Bucket=container, Key=name)
        content = obj_response["Body"].read()
        content_type = obj_response.get("ContentType", "application/octet-stream")

        # Re-upload with new metadata, preserving content type
        self._client.put_object(
            Bucket=container,
            Key=name,
            Body=content,
            Metadata=new_metadata_dict,
            ContentType=content_type,
        )

        _get_logger().info(
            "Blob metadata set successfully",
            container=container,
            blob=name,
            size=len(content),
        )

    @ErrorHandler.handle_service_errors("get blob metadata")
    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """
        Get custom metadata for a blob.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)

        Returns:
            Dictionary of metadata key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If metadata retrieval operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Get object metadata using head_object
        response = self._client.head_object(Bucket=container, Key=name)

        # Return metadata as a regular dictionary
        metadata = response.get("Metadata", {})
        _get_logger().info(
            "Retrieved blob metadata",
            container=container,
            blob=name,
            count=len(metadata),
        )
        return dict(metadata) if metadata else {}

    @ErrorHandler.handle_service_errors("set blob tags")
    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """
        Set blob tags for searchability.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            tags: Dictionary of tag key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If tags setting operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)
        ErrorHandler.handle_metadata_validation_errors(tags, "tags")

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Set object tags
        _get_logger().info("Setting blob tags", container=container, blob=name)

        tag_set: list[dict[str, str]] = [
            {"Key": k, "Value": v} for k, v in (tags or {}).items()
        ]
        tagging: dict[str, list[dict[str, str]]] = {"TagSet": tag_set}
        try:
            self._client.put_object_tagging(Bucket=container, Key=name, Tagging=tagging)
            _get_logger().info(
                "Blob tags set successfully",
                container=container,
                blob=name,
                count=len(tags),
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # Some S3 implementations (like Garage) don't support object tagging
            if error_code == "NotImplemented":
                _get_logger().warning(
                    "Object tagging not supported, operation skipped",
                    container=container,
                    blob=name,
                    error_code=error_code,
                )
            else:
                raise

    @ErrorHandler.handle_service_errors("get blob tags")
    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """
        Get blob tags.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)

        Returns:
            Dictionary of tag key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If tags retrieval operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Get object tags
        try:
            response = self._client.get_object_tagging(Bucket=container, Key=name)
            # Convert tag set to dictionary
            tags = {tag["Key"]: tag["Value"] for tag in response.get("TagSet", [])}
            _get_logger().info(
                "Retrieved blob tags", container=container, blob=name, count=len(tags)
            )
            return tags
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # Some S3 implementations (like Garage) don't support object tagging
            if error_code == "NotImplemented":
                _get_logger().warning(
                    "Object tagging not supported, returning empty tags",
                    container=container,
                    blob=name,
                    error_code=error_code,
                )
                return {}
            else:
                raise
