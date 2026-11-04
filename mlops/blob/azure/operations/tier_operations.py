"""
Tier operations for Azure Blob Storage.

This module handles blob tier management operations including setting
access tiers for cost optimization (Hot, Cool, Archive).
"""

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    ConnectionError,
)


class TierOperations:
    """Handles blob tier operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize tier operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

    @ErrorHandler.handle_service_errors("set blob tier")
    async def set_blob_tier(
        self, container: str, name: str, tier: str, **kwargs
    ) -> bool:
        """
        Set the access tier for a blob (Hot, Cool).

        Args:
            container: Container name
            name: Blob name
            tier: Access tier (Hot, Cool)
            **kwargs: Additional options

        Returns:
            True if tier was set successfully

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If tier setting fails or invalid tier
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)
            ValidationHelper.validate_blob_tier_with_model(container, name, tier)

            # Check if container exists
            await ErrorHandler.check_container_exists(self._client, container)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Check if blob exists
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)

            # Validate and get Azure tier enum
            azure_tier = ValidationHelper.validate_blob_tier(tier)

            # Set blob tier
            blob_client.set_standard_blob_tier(azure_tier)

            return True

        except ContainerNotFoundError:
            raise
        except BlobNotFoundError:
            raise
        except ValueError as e:
            # This catches Pydantic validation errors
            raise BlobStorageError(f"Invalid tier '{tier}': {str(e)}")
        except ResourceNotFoundError:
            # This could be either container or blob not found
            # Check if container exists to determine which error to raise
            try:
                await ErrorHandler.check_container_exists(self._client, container)
                raise BlobNotFoundError(container, name)
            except ContainerNotFoundError:
                raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to set blob tier '{tier}' for '{name}' in container '{container}': {str(e)}"
            )
