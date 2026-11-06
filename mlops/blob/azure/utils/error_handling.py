"""
Error handling utilities for Azure Blob Storage operations.

This module provides common error handling patterns extracted from the original
AzureBlobStorage class to promote code reuse and consistency.
"""

from beartype.typing import Callable, Any, Optional
from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    ConnectionError,
    InvalidConfigurationError,
)


class ErrorHandler:
    """Utility class for handling common Azure Blob Storage errors."""

    @staticmethod
    def handle_service_errors(operation_name: str):
        """
        Decorator to handle common Azure service errors.

        Args:
            operation_name: Name of the operation for error messages
        """

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except (
                    ContainerNotFoundError,
                    BlobNotFoundError,
                    ConnectionError,
                    BlobStorageError,
                    InvalidConfigurationError,
                ):
                    # Re-raise our custom exceptions without wrapping
                    raise
                except ServiceRequestError as e:
                    raise ConnectionError(
                        f"Failed to connect to Azure storage during {operation_name}: {str(e)}"
                    )
                except Exception as e:
                    raise BlobStorageError(f"Failed to {operation_name}: {str(e)}")

            return wrapper

        return decorator

    @staticmethod
    async def check_container_exists(client: BlobServiceClient, container: str) -> None:
        """
        Check if a container exists and raise appropriate error if not.

        Args:
            client: Azure BlobServiceClient instance
            container: Container name to check

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        try:
            container_client = client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to check container existence: {str(e)}")

    @staticmethod
    async def check_blob_exists(
        client: BlobServiceClient, container: str, name: str
    ) -> None:
        """
        Check if a blob exists and raise appropriate error if not.

        Args:
            client: Azure BlobServiceClient instance
            container: Container name
            name: Blob name to check

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
        """
        try:
            # First check container exists
            await ErrorHandler.check_container_exists(client, container)

            # Then check blob exists
            blob_client = client.get_blob_client(container=container, blob=name)
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)
        except (ContainerNotFoundError, BlobNotFoundError):
            raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to check blob existence: {str(e)}")

    @staticmethod
    def handle_resource_not_found(container: str, blob_name: Optional[str] = None):
        """
        Handle ResourceNotFoundError by determining if it's a container or blob issue.

        Args:
            container: Container name
            blob_name: Optional blob name (if None, assumes container operation)

        Returns:
            Function that takes client and original exception
        """

        async def handler(
            client: BlobServiceClient, original_error: ResourceNotFoundError
        ):
            try:
                container_client = client.get_container_client(container)
                if not container_client.exists():
                    raise ContainerNotFoundError(
                        container,
                        {"error": f"Container not found: {str(original_error)}"},
                    )
                elif blob_name:
                    raise BlobNotFoundError(
                        container,
                        blob_name,
                        {"error": f"Blob not found: {str(original_error)}"},
                    )
                else:
                    raise ContainerNotFoundError(
                        container,
                        {"error": f"Container not found: {str(original_error)}"},
                    )
            except (ContainerNotFoundError, BlobNotFoundError):
                raise
            except Exception:
                # If we can't determine the specific error, fall back to the original
                if blob_name:
                    raise BlobNotFoundError(
                        container,
                        blob_name,
                        {"error": f"Resource not found: {str(original_error)}"},
                    )
                else:
                    raise ContainerNotFoundError(
                        container,
                        {"error": f"Resource not found: {str(original_error)}"},
                    )

        return handler

    @staticmethod
    def handle_metadata_validation_errors(
        metadata: dict, operation_type: str = "metadata"
    ):
        """
        Validate metadata dictionary and raise appropriate errors.

        Args:
            metadata: Metadata dictionary to validate
            operation_type: Type of operation (metadata/tags) for error messages

        Raises:
            BlobStorageError: If validation fails
        """
        if metadata:
            for key, value in metadata.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise BlobStorageError(
                        f"{operation_type.title()} keys and values must be strings"
                    )
                if not key.strip():
                    raise BlobStorageError(
                        f"{operation_type.title()} keys cannot be empty"
                    )
