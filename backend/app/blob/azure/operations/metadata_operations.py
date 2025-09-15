"""
Metadata and tags operations for Azure Blob Storage.

This module handles blob metadata and tags operations including setting
and retrieving custom metadata and index tags.
"""

from typing import Dict
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


class MetadataOperations:
    """Handles metadata and tags operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize metadata operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

    @ErrorHandler.handle_service_errors("set blob metadata")
    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """
        Set custom metadata for a blob.

        Args:
            container: Container name
            name: Blob name
            metadata: Dictionary of metadata key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If metadata setting operation fails
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)
            ErrorHandler.handle_metadata_validation_errors(metadata, "metadata")

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client and set metadata
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Azure blob metadata is set as a dictionary
            blob_client.set_blob_metadata(metadata=metadata or {})

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            raise e
        except ServiceRequestError as e:
            if e.status_code == 404:
                if "ContainerNotFound" in str(e):
                    raise ContainerNotFoundError(
                        container, f"Container not found: {str(e)}"
                    )
                else:
                    raise BlobNotFoundError(
                        container, name, f"Blob not found: {str(e)}"
                    )
            else:
                raise BlobStorageError(f"Failed to set blob metadata: {str(e)}")

    @ErrorHandler.handle_service_errors("get blob metadata")
    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """
        Get custom metadata for a blob.

        Args:
            container: Container name
            name: Blob name

        Returns:
            Dictionary of metadata key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If metadata retrieval operation fails
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client and retrieve metadata
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Get blob properties which includes metadata
            properties = blob_client.get_blob_properties()

            # Return metadata as a regular dictionary (Azure returns BlobProperties with metadata attribute)
            return dict(properties.metadata) if properties.metadata else {}

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            raise e
        except ServiceRequestError as e:
            if e.status_code == 404:
                if "ContainerNotFound" in str(e):
                    raise ContainerNotFoundError(
                        container, f"Container not found: {str(e)}"
                    )
                else:
                    raise BlobNotFoundError(
                        container, name, f"Blob not found: {str(e)}"
                    )
            else:
                raise BlobStorageError(f"Failed to get blob metadata: {str(e)}")

    @ErrorHandler.handle_service_errors("set blob tags")
    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """
        Set blob index tags for searchability.

        Args:
            container: Container name
            name: Blob name
            tags: Dictionary of tag key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If tags setting operation fails
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)
            ErrorHandler.handle_metadata_validation_errors(tags, "tags")

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client and set tags
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Azure blob tags are set as a dictionary
            blob_client.set_blob_tags(tags=tags or {})

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            raise e
        except ServiceRequestError as e:
            if e.status_code == 404:
                if "ContainerNotFound" in str(e):
                    raise ContainerNotFoundError(
                        container, f"Container not found: {str(e)}"
                    )
                else:
                    raise BlobNotFoundError(
                        container, name, f"Blob not found: {str(e)}"
                    )
            else:
                raise BlobStorageError(f"Failed to set blob tags: {str(e)}")

    @ErrorHandler.handle_service_errors("get blob tags")
    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """
        Get blob index tags.

        Args:
            container: Container name
            name: Blob name

        Returns:
            Dictionary of tag key-value pairs

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If tags retrieval operation fails
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client and retrieve tags
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Get blob tags
            tags_response = blob_client.get_blob_tags()

            # Return tags as a regular dictionary
            return dict(tags_response) if tags_response else {}

        except (ContainerNotFoundError, BlobNotFoundError) as e:
            raise e
        except ServiceRequestError as e:
            if e.status_code == 404:
                if "ContainerNotFound" in str(e):
                    raise ContainerNotFoundError(
                        container, f"Container not found: {str(e)}"
                    )
                else:
                    raise BlobNotFoundError(
                        container, name, f"Blob not found: {str(e)}"
                    )
            else:
                raise BlobStorageError(f"Failed to get blob tags: {str(e)}")
