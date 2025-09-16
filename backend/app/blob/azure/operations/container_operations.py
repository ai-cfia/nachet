"""
Container operations for Azure Blob Storage.

This module handles container management operations including creation,
deletion, listing, and property retrieval.
"""

from typing import Dict, Any
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ServiceRequestError

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...models import ContainerInfo, ContainerListResult, ListOptions
from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    ConnectionError,
    InvalidConfigurationError,
)


class ContainerOperations:
    """Handles container-specific operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize container operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

    @ErrorHandler.handle_service_errors("list containers")
    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """
        List all containers in the storage account.

        Args:
            **kwargs: Additional options (can include ListOptions)

        Returns:
            ContainerListResult with list of containers
        """
        try:
            options = kwargs.get("options")
            if isinstance(options, dict):
                options = ListOptions(**options)
            elif options is None:
                options = ListOptions()

            containers = []
            continuation_token = None

            # Use Azure SDK to list containers
            container_iter = self._client.list_containers(
                name_starts_with=options.prefix,
                include_metadata=options.include_metadata,
            )

            count = 0
            for container in container_iter:
                if options.max_results and count >= options.max_results:
                    continuation_token = "has_more"  # Simplified for demo
                    break

                # Convert Azure container to our ContainerInfo model
                container_info = ContainerInfo(
                    name=container.name,
                    last_modified=container.last_modified,
                    etag=container.etag,
                    metadata=container.metadata or {},
                    public_access=getattr(container, "public_access", None),
                )
                containers.append(container_info)
                count += 1

            result = ContainerListResult(
                containers=containers,
                continuation_token=continuation_token,
                total_count=len(containers),
            )

            return result.model_dump()

        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(f"Failed to list containers: {str(e)}")

    @ErrorHandler.handle_service_errors("create container")
    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new container.

        Args:
            name: Container name
            **kwargs: Additional options (can include metadata, public_access)

        Returns:
            ContainerInfo as dict

        Raises:
            InvalidConfigurationError: If container name is invalid
            BlobStorageError: If container creation fails
        """
        try:
            # Validate container name using Pydantic model
            ValidationHelper.validate_container_name_with_model(
                name, kwargs.get("metadata", {})
            )

            # Get container client (don't auto-create)
            container_client = self._client.get_container_client(name)

            # Check if container already exists
            if container_client.exists():
                # Return existing container properties
                properties = container_client.get_container_properties()
                container_info = ContainerInfo(
                    name=properties.name,
                    last_modified=properties.last_modified,
                    etag=properties.etag,
                    metadata=properties.metadata or {},
                    public_access=getattr(properties, "public_access", None),
                )
                return container_info.model_dump()

            # Set metadata if provided
            metadata = kwargs.get("metadata", {})
            public_access = kwargs.get("public_access")

            # Create the container
            container_client.create_container(
                metadata=metadata if metadata else None, public_access=public_access
            )

            # Get the created container properties
            properties = container_client.get_container_properties()
            container_info = ContainerInfo(
                name=properties.name,
                last_modified=properties.last_modified,
                etag=properties.etag,
                metadata=properties.metadata or {},
                public_access=getattr(properties, "public_access", None),
            )

            return container_info.model_dump()

        except ValueError as e:
            # This catches Pydantic validation errors
            raise InvalidConfigurationError(
                "container_name", f"Invalid container name: {str(e)}"
            )

    @ErrorHandler.handle_service_errors("delete container")
    async def delete_container(self, name: str) -> bool:
        """
        Delete a container.

        Args:
            name: Container name

        Returns:
            True if container was deleted successfully, False if container didn't exist

        Raises:
            ConnectionError: If unable to connect to Azure storage
            BlobStorageError: If deletion operation fails
        """
        try:
            # Validate container name
            ValidationHelper.validate_container_name(name)

            # Get container client (but don't create it)
            container_client = self._client.get_container_client(name)

            # Check if container exists
            if not container_client.exists():
                return (
                    False  # Container doesn't exist, consider it "successfully deleted"
                )

            # Delete the container
            container_client.delete_container()

            # Verify deletion was successful
            return not container_client.exists()

        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(f"Failed to delete container '{name}': {str(e)}")

    @ErrorHandler.handle_service_errors("check container existence")
    async def container_exists(self, name: str) -> bool:
        """
        Check if a container exists.

        Args:
            name: Container name

        Returns:
            True if container exists, False otherwise

        Raises:
            ConnectionError: If unable to connect to Azure storage
            BlobStorageError: If check operation fails
        """
        # Validate container name
        ValidationHelper.validate_container_name(name)

        # Get container client (but don't create it)
        container_client = self._client.get_container_client(name)

        # Check if container exists
        return container_client.exists()

    @ErrorHandler.handle_service_errors("get container properties")
    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """
        Get properties of a container.

        Args:
            name: Container name

        Returns:
            ContainerInfo as dict with full metadata

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If unable to connect to Azure storage
            BlobStorageError: If operation fails
        """
        try:
            # Validate container name
            ValidationHelper.validate_container_name(name)

            # Get container client (but don't create it)
            container_client = self._client.get_container_client(name)

            # Check if container exists
            if not container_client.exists():
                raise ContainerNotFoundError(name)

            # Get container properties
            properties = container_client.get_container_properties()

            # Convert to our ContainerInfo model
            container_info = ContainerInfo(
                name=properties.name,
                last_modified=properties.last_modified,
                etag=properties.etag,
                metadata=properties.metadata or {},
                public_access=getattr(properties, "public_access", None),
            )

            return container_info.model_dump()

        except ContainerNotFoundError:
            raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to get container properties '{name}': {str(e)}"
            )
