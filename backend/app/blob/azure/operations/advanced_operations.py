"""
Advanced operations for Azure Blob Storage.

This module handles advanced blob operations including copy and move operations
with transaction safety and rollback capabilities.
"""

from typing import Dict, Any
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ServiceRequestError

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    # ConnectionError,
)


class AdvancedOperations:
    """Handles advanced operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize advanced operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

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
        Copy a blob from source to destination.

        Args:
            source_container: Source container name
            source_name: Source blob name
            dest_container: Destination container name
            dest_name: Destination blob name
            **kwargs: Additional options

        Returns:
            Dict containing copy result information

        Raises:
            BlobNotFoundError: If source blob doesn't exist
            ContainerNotFoundError: If source or dest container doesn't exist
            BlobStorageError: If copy operation fails
        """
        try:
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

            # Get source blob URL for copy operation
            source_blob_client = self._client.get_blob_client(
                container=source_container, blob=source_name
            )
            source_blob_url = source_blob_client.url

            # Get destination blob client
            dest_blob_client = self._client.get_blob_client(
                container=dest_container, blob=dest_name
            )

            # Start copy operation
            copy_props = dest_blob_client.start_copy_from_url(source_blob_url)
            copy_status = copy_props["copy_status"]
            copy_id = copy_props["copy_id"]

            # For same-account copies, the copy is usually immediate
            # But we'll check the status to be safe
            if copy_status != "success":
                # Poll for completion if needed (though usually immediate for same-account)
                properties = dest_blob_client.get_blob_properties()
                if properties.copy.status == "pending":
                    # In practice, intra-account copies are usually immediate
                    # If still pending, we'll return the current status
                    pass
                elif properties.copy.status == "failed":
                    raise BlobStorageError(
                        f"Copy operation failed: {properties.copy.status_description}"
                    )

            # Get final properties of the copied blob
            final_properties = dest_blob_client.get_blob_properties()

            return {
                "source_container": source_container,
                "source_name": source_name,
                "dest_container": dest_container,
                "dest_name": dest_name,
                "copy_id": copy_id,
                "copy_status": final_properties.copy.status,
                "etag": final_properties.etag,
                "last_modified": final_properties.last_modified,
                "size": final_properties.size,
                "url": dest_blob_client.url,
            }

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            raise e
        except ServiceRequestError as e:
            if e.status_code == 404:
                if "ContainerNotFound" in str(e):
                    # Try to determine which container is missing
                    try:
                        await ErrorHandler.check_container_exists(
                            self._client, source_container
                        )
                        raise ContainerNotFoundError(
                            dest_container, f"Destination container not found: {str(e)}"
                        )
                    except ContainerNotFoundError:
                        raise ContainerNotFoundError(
                            source_container, f"Source container not found: {str(e)}"
                        )
                else:
                    raise BlobNotFoundError(
                        source_container,
                        source_name,
                        f"Source blob not found: {str(e)}",
                    )
            else:
                raise BlobStorageError(f"Failed to copy blob: {str(e)}")

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
            source_container: Source container name
            source_name: Source blob name
            dest_container: Destination container name
            dest_name: Destination blob name
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
            copy_result = await self.copy_blob(
                source_container, source_name, dest_container, dest_name, **kwargs
            )
            copy_successful = True

            # Step 2: Verify the copy was successful
            if copy_result.get("copy_status") == "failed":
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
            delete_successful = await self._delete_blob_for_move(
                source_container, source_name
            )

            if not delete_successful:
                # Copy succeeded but delete failed - this is not ideal but not catastrophic
                # The destination blob exists, we just have a duplicate
                print(
                    f"Warning: Failed to delete source blob after successful copy. "
                    f"Source: {source_container}/{source_name}, "
                    f"Destination: {dest_container}/{dest_name}"
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
                await self._rollback_copy(dest_container, dest_name)
            raise e
        except Exception as e:
            # Unexpected error - attempt rollback if copy was successful
            if copy_successful and copy_result:
                await self._rollback_copy(dest_container, dest_name)
            raise BlobStorageError(f"Unexpected error during blob move: {str(e)}")

    async def _get_blob_properties_for_verification(
        self, container: str, name: str
    ) -> Dict[str, Any]:
        """
        Get blob properties for verification during move operations.

        Args:
            container: Container name
            name: Blob name

        Returns:
            Dictionary with blob properties
        """
        blob_client = self._client.get_blob_client(container=container, blob=name)
        properties = blob_client.get_blob_properties()
        return {"size": properties.size}

    async def _delete_blob_for_move(self, container: str, name: str) -> bool:
        """
        Delete a blob as part of move operation.

        Args:
            container: Container name
            name: Blob name

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            blob_client = self._client.get_blob_client(container=container, blob=name)
            if not blob_client.exists():
                return False
            blob_client.delete_blob()
            return not blob_client.exists()
        except Exception:
            return False

    async def _rollback_copy(self, dest_container: str, dest_name: str) -> None:
        """
        Rollback a copy operation by deleting the destination blob.

        Args:
            dest_container: Destination container name
            dest_name: Destination blob name
        """
        try:
            blob_client = self._client.get_blob_client(
                container=dest_container, blob=dest_name
            )
            blob_client.delete_blob()
            print(
                f"Rollback: Successfully deleted destination blob after failed move: "
                f"{dest_container}/{dest_name}"
            )
        except Exception as cleanup_error:
            print(
                f"Rollback failed: Could not delete destination blob after failed move: "
                f"{dest_container}/{dest_name}. Error: {str(cleanup_error)}"
            )
