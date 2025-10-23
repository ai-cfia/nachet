"""
Advanced operations for S3-compatible Blob Storage (Apache Ozone).

This module handles advanced blob operations including copy and move operations
with transaction safety and rollback capabilities using boto3.
"""

from typing import Dict, Any, TYPE_CHECKING
from botocore.exceptions import ClientError

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
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


class AdvancedOperations:
    """Handles advanced operations for S3-compatible storage."""

    def __init__(self, s3_client: "S3Client"):
        """
        Initialize advanced operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("copy blob")
    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Copy a blob from source to destination in S3.

        Args:
            source_container: Source container name (bucket)
            source_name: Source blob name (object key)
            dest_container: Destination container name (bucket)
            dest_name: Destination blob name (object key)
            **kwargs: Additional options

        Returns:
            Dict containing copy result information

        Raises:
            BlobNotFoundError: If source blob doesn't exist
            ContainerNotFoundError: If source or dest container doesn't exist
            BlobStorageError: If copy operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(source_container)
        ValidationHelper.validate_blob_name(source_name)
        ValidationHelper.validate_container_name(dest_container)
        ValidationHelper.validate_blob_name(dest_name)

        # Check if source blob exists
        await ErrorHandler.check_blob_exists(
            self._client, source_container, source_name
        )

        # Check if source and destination containers exist
        await ErrorHandler.check_container_exists(self._client, source_container)
        await ErrorHandler.check_container_exists(self._client, dest_container)

        _get_logger().info(
            "Copying S3 object",
            source_container=source_container,
            source_name=source_name,
            dest_container=dest_container,
            dest_name=dest_name,
        )

        # Perform copy operation
        copy_source = {"Bucket": source_container, "Key": source_name}
        response = self._client.copy_object(
            CopySource=copy_source,
            Bucket=dest_container,
            Key=dest_name,
        )

        # Get destination object properties
        head_response = self._client.head_object(Bucket=dest_container, Key=dest_name)

        # Build destination object URL
        endpoint_url = self._client.meta.endpoint_url
        dest_url = f"{endpoint_url}/{dest_container}/{dest_name}"

        result = {
            "source_container": source_container,
            "source_name": source_name,
            "dest_container": dest_container,
            "dest_name": dest_name,
            "copy_id": response.get("CopyObjectResult", {}).get("ETag", "").strip('"'),
            "copy_status": "success",  # S3 copy is synchronous
            "etag": response.get("CopyObjectResult", {}).get("ETag", "").strip('"'),
            "last_modified": head_response.get("LastModified"),
            "size": head_response.get("ContentLength", 0),
            "url": dest_url,
        }

        _get_logger().info(
            "S3 object copied successfully",
            source_container=source_container,
            source_name=source_name,
            dest_container=dest_container,
            dest_name=dest_name,
        )

        return result

    @ErrorHandler.handle_service_errors("move blob")
    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Move a blob from source to destination with transaction safety.

        This operation performs a copy followed by delete with rollback capability
        to ensure data integrity.

        Args:
            source_container: Source container name (bucket)
            source_name: Source blob name (object key)
            dest_container: Destination container name (bucket)
            dest_name: Destination blob name (object key)
            **kwargs: Additional options

        Returns:
            Dict containing move result information

        Raises:
            BlobNotFoundError: If source blob doesn't exist
            ContainerNotFoundError: If source or dest container doesn't exist
            BlobStorageError: If move operation fails
        """
        copy_successful = False
        copy_result = None

        try:
            # Step 1: Copy the blob to destination
            _get_logger().info(
                "Starting move operation (copy phase)",
                source_container=source_container,
                source_name=source_name,
                dest_container=dest_container,
                dest_name=dest_name,
            )

            copy_result = await self.copy_blob(
                source_container, source_name, dest_container, dest_name, **kwargs
            )
            copy_successful = True

            # Step 2: Verify the copy was successful
            if copy_result.get("copy_status") != "success":
                raise BlobStorageError(
                    f"Copy operation failed during move: {copy_result.get('copy_status')}"
                )

            # Step 3: Verify destination blob exists and matches source
            try:
                dest_properties = await self._get_blob_properties_for_verification(
                    dest_container, dest_name
                )
                source_properties = await self._get_blob_properties_for_verification(
                    source_container, source_name
                )

                # Verify size matches (basic integrity check)
                if dest_properties.get("size") != source_properties.get("size"):
                    raise BlobStorageError(
                        "Size mismatch between source and destination blobs during move"
                    )

            except Exception as e:
                raise BlobStorageError(
                    f"Failed to verify copied blob integrity: {str(e)}"
                )

            # Step 4: Delete the source blob only after successful copy and verification
            _get_logger().info(
                "Move operation copy successful, deleting source",
                source_container=source_container,
                source_name=source_name,
            )

            delete_successful = await self._delete_blob_for_move(
                source_container, source_name
            )

            if not delete_successful:
                # Copy succeeded but delete failed - this is not ideal but not catastrophic
                # The destination blob exists, we just have a duplicate
                _get_logger().warning(
                    "Failed to delete source blob after successful copy",
                    source_container=source_container,
                    source_name=source_name,
                    dest_container=dest_container,
                    dest_name=dest_name,
                )

            _get_logger().info(
                "Move operation completed",
                source_container=source_container,
                source_name=source_name,
                dest_container=dest_container,
                dest_name=dest_name,
                delete_successful=delete_successful,
            )

            return {
                "source_container": source_container,
                "source_name": source_name,
                "dest_container": dest_container,
                "dest_name": dest_name,
                "copy_id": copy_result.get("copy_id"),
                "copy_status": copy_result.get("copy_status"),
                "etag": copy_result.get("etag"),
                "last_modified": copy_result.get("last_modified"),
                "size": copy_result.get("size"),
                "url": copy_result.get("url"),
                "delete_successful": delete_successful,
                "move_completed": delete_successful,
            }

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            # These exceptions are from the copy operation
            raise e
        except BlobStorageError as e:
            # If copy was successful but something else failed, try to cleanup
            if copy_successful and copy_result:
                _get_logger().error(
                    "Move operation failed after successful copy, rolling back",
                    source_container=source_container,
                    source_name=source_name,
                    dest_container=dest_container,
                    dest_name=dest_name,
                    error=str(e),
                )
                await self._rollback_copy(dest_container, dest_name)
            raise e
        except Exception as e:
            # Unexpected error - attempt rollback if copy was successful
            if copy_successful and copy_result:
                _get_logger().error(
                    "Unexpected error during move operation, rolling back",
                    source_container=source_container,
                    source_name=source_name,
                    dest_container=dest_container,
                    dest_name=dest_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                await self._rollback_copy(dest_container, dest_name)
            raise BlobStorageError(f"Unexpected error during blob move: {str(e)}")

    async def _get_blob_properties_for_verification(
        self, container: str, name: str
    ) -> Dict[str, Any]:
        """
        Get blob properties for verification during move operations.

        Args:
            container: Container name (bucket)
            name: Blob name (object key)

        Returns:
            Dictionary with blob properties
        """
        response = self._client.head_object(Bucket=container, Key=name)
        return {"size": response.get("ContentLength", 0)}

    async def _delete_blob_for_move(self, container: str, name: str) -> bool:
        """
        Delete a blob as part of move operation.

        Args:
            container: Container name (bucket)
            name: Blob name (object key)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Check if blob exists
            try:
                self._client.head_object(Bucket=container, Key=name)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code in ["NoSuchKey", "404"]:
                    return False
                raise

            # Delete the blob
            self._client.delete_object(Bucket=container, Key=name)

            # Verify deletion
            try:
                self._client.head_object(Bucket=container, Key=name)
                return False  # Still exists
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code in ["NoSuchKey", "404"]:
                    return True  # Successfully deleted
                raise

        except Exception as e:
            _get_logger().error(
                "Failed to delete blob during move",
                container=container,
                blob=name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    async def _rollback_copy(self, dest_container: str, dest_name: str) -> None:
        """
        Rollback a copy operation by deleting the destination blob.

        Args:
            dest_container: Destination container name (bucket)
            dest_name: Destination blob name (object key)
        """
        try:
            self._client.delete_object(Bucket=dest_container, Key=dest_name)
            _get_logger().info(
                "Rollback: Successfully deleted destination blob after failed move",
                dest_container=dest_container,
                dest_name=dest_name,
            )
        except Exception as cleanup_error:
            _get_logger().error(
                "Rollback failed: Could not delete destination blob after failed move",
                dest_container=dest_container,
                dest_name=dest_name,
                error=str(cleanup_error),
                error_type=type(cleanup_error).__name__,
            )
