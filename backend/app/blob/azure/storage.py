"""
Azure Blob Storage implementation.

This module implements the BlobStorageInterface for Azure Blob Storage,
providing list operations for containers and blobs with proper validation
using Pydantic models.
"""

from typing import Dict, Any, List, Optional, Union, BinaryIO, AsyncIterator
from datetime import datetime

# import io
import base64

from azure.storage.blob import BlobServiceClient, StandardBlobTier, ContentSettings
from azure.core.exceptions import ServiceRequestError, ResourceNotFoundError

from ..interface import BlobStorageInterface
from ..models import (
    BlobInfo,
    ContainerInfo,
    BlobListResult,
    ContainerListResult,
    ListOptions,
    UploadResult,
    BlobProperties,
    BlobTierInfo,
)
from ..exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    ConnectionError,
    InvalidConfigurationError,
)
from .client import create_blob_service_client, create_container_client


class AzureBlobStorage(BlobStorageInterface):
    """Azure Blob Storage implementation of the blob storage interface."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure Blob Storage client.

        Args:
            config: Configuration dictionary with connection details
        """
        self.config = config
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client."""
        try:
            connection_string = self.azure_storage_connection_string()
            print(f"🔗 Using Azure Storage connection string: \n{connection_string}")
            if not connection_string:
                raise InvalidConfigurationError(
                    "connection_string", "Azure storage connection string is required"
                )

            self._blob_service_client = create_blob_service_client(connection_string)
            print("🔵 Azure Blob Storage client initialized")

        except Exception as e:
            raise InvalidConfigurationError(
                "azure_client",
                f"Failed to initialize Azure Blob Storage client: {str(e)}",
            )

    def azure_storage_connection_string(self) -> str:
        """Build Azure storage connection string from config dictionary."""
        return (
            f"DefaultEndpointsProtocol={self.config['blob_storage_endpoint_protocol']};"
            f"AccountName={self.config['blob_storage_name']};"
            f"AccountKey={self.config['blob_storage_key']};"
            f"EndpointSuffix={self.config['blob_storage_endpoint_suffix']};"
            f"BlobEndpoint={self.config['blob_storage_endpoint_base']}/{self.config['blob_storage_name']};"
        )

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
            container_iter = self._blob_service_client.list_containers(
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

    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """
        List blobs in a container.

        Args:
            container: Container name
            **kwargs: Additional options (can include ListOptions)

        Returns:
            BlobListResult with list of blobs
        """
        try:
            options = kwargs.get("options")
            if isinstance(options, dict):
                options = ListOptions(**options)
            elif options is None:
                options = ListOptions()

            # Get container client
            container_client = create_container_client(
                self._blob_service_client, container
            )

            # Check if container exists
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            blobs = []
            continuation_token = None

            # List blobs in the container
            blob_iter = container_client.list_blobs(
                name_starts_with=options.prefix,
                include=["metadata", "tags"]
                if (options.include_metadata or options.include_tags)
                else None,
            )

            count = 0
            for blob in blob_iter:
                if options.max_results and count >= options.max_results:
                    continuation_token = "has_more"  # Simplified for demo
                    break

                # Convert Azure blob to our BlobInfo model
                blob_info = BlobInfo(
                    name=blob.name,
                    container=container,
                    size=blob.size,
                    last_modified=blob.last_modified,
                    etag=blob.etag,
                    content_type=blob.content_settings.content_type
                    if blob.content_settings
                    else "application/octet-stream",
                    metadata=blob.metadata or {},
                    tags=getattr(blob, "tags", {}) or {},
                )
                blobs.append(blob_info)
                count += 1

            result = BlobListResult(
                blobs=blobs,
                continuation_token=continuation_token,
                prefix=options.prefix,
                container=container,
                total_count=len(blobs),
            )

            return result.model_dump()

        except ContainerNotFoundError:
            raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to list blobs in container '{container}': {str(e)}"
            )

    # Stub implementations for required interface methods (not implemented yet)
    async def upload_blob(
        self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs
    ) -> Dict[str, Any]:
        """
        Upload a blob to storage.

        Args:
            container: Container name
            name: Blob name
            data: Data to upload (bytes, str, or file-like object)
            **kwargs: Additional options (content_type, metadata, tags, overwrite, etc.)

        Returns:
            UploadResult as dict

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If upload fails
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Extract options
            content_type = kwargs.get("content_type", "application/octet-stream")
            metadata = kwargs.get("metadata", {})
            tags = kwargs.get("tags", {})
            overwrite = kwargs.get("overwrite", True)

            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode("utf-8")

            # Validate data
            if data is None:
                raise BlobStorageError("Data cannot be None")

            # Create content settings
            content_settings = ContentSettings(
                content_type=content_type,
                content_encoding=kwargs.get("content_encoding"),
                content_language=kwargs.get("content_language"),
                cache_control=kwargs.get("cache_control"),
                content_disposition=kwargs.get("content_disposition"),
            )

            # Upload blob
            upload_response = blob_client.upload_blob(
                data,
                content_settings=content_settings,
                metadata=metadata if metadata else None,
                tags=tags if tags else None,
                overwrite=overwrite,
                timeout=kwargs.get("timeout"),
            )

            # Get blob properties to build result
            blob_properties = blob_client.get_blob_properties()

            # Create UploadResult
            content_md5 = None
            if (
                blob_properties.content_settings
                and blob_properties.content_settings.content_md5
            ):
                # Convert bytearray/bytes to base64 string
                if isinstance(
                    blob_properties.content_settings.content_md5, (bytes, bytearray)
                ):
                    content_md5 = base64.b64encode(
                        blob_properties.content_settings.content_md5
                    ).decode("utf-8")
                else:
                    content_md5 = str(blob_properties.content_settings.content_md5)

            upload_result = UploadResult(
                container=container,
                name=name,
                etag=upload_response["etag"],
                last_modified=upload_response["last_modified"],
                url=blob_client.url,
                size=blob_properties.size,
                content_md5=content_md5,
            )

            return upload_result.model_dump()

        except ContainerNotFoundError:
            raise
        except ResourceNotFoundError:
            raise ContainerNotFoundError(container)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to upload blob '{name}' to container '{container}': {str(e)}"
            )

    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """
        Download a blob from storage.

        Args:
            container: Container name
            name: Blob name
            **kwargs: Additional options (offset, length, validate_content, timeout)

        Returns:
            Blob data as bytes

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If download fails
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)

            # Extract download options
            offset = kwargs.get("offset")
            length = kwargs.get("length")
            validate_content = kwargs.get("validate_content", False)
            timeout = kwargs.get("timeout")

            # Download blob
            download_stream = blob_client.download_blob(
                offset=offset,
                length=length,
                validate_content=validate_content,
                timeout=timeout,
            )

            # Read all data
            blob_data = download_stream.readall()
            return blob_data

        except ContainerNotFoundError:
            raise
        except BlobNotFoundError:
            raise
        except ResourceNotFoundError:
            # This could be either container or blob not found
            # Check if container exists to determine which error to raise
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
            else:
                raise BlobNotFoundError(container, name)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to download blob '{name}' from container '{container}': {str(e)}"
            )

    async def download_blob_stream(
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """
        Download a blob as a stream.

        Args:
            container: Container name
            name: Blob name
            **kwargs: Additional options (offset, length, validate_content, timeout, chunk_size)

        Returns:
            AsyncIterator yielding chunks of blob data

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If download fails
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)

            # Extract download options
            offset = kwargs.get("offset")
            length = kwargs.get("length")
            validate_content = kwargs.get("validate_content", False)
            timeout = kwargs.get("timeout")
            # chunk_size = kwargs.get("chunk_size", 4096)

            # Download blob as stream
            download_stream = blob_client.download_blob(
                offset=offset,
                length=length,
                validate_content=validate_content,
                timeout=timeout,
            )

            # Yield chunks
            async for chunk in download_stream.chunks():
                yield chunk

        except ContainerNotFoundError:
            raise
        except BlobNotFoundError:
            raise
        except ResourceNotFoundError:
            # This could be either container or blob not found
            # Check if container exists to determine which error to raise
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
            else:
                raise BlobNotFoundError(container, name)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to download blob stream '{name}' from container '{container}': {str(e)}"
            )

    async def delete_blob(self, container: str, name: str) -> bool:
        """
        Delete a blob from storage.

        Args:
            container: Container name
            name: Blob name

        Returns:
            True if blob was deleted successfully, False if blob didn't exist

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If deletion operation fails
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            if not blob_client.exists():
                return False  # Blob doesn't exist, consider it "successfully deleted"

            # Delete the blob
            blob_client.delete_blob()

            # Verify deletion was successful
            return not blob_client.exists()

        except ContainerNotFoundError:
            raise
        except ResourceNotFoundError:
            # This could be either container or blob not found
            # Check if container exists to determine which error to raise
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
            else:
                return False  # Blob not found, consider it deleted
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to delete blob '{name}' from container '{container}': {str(e)}"
            )

    async def blob_exists(self, container: str, name: str) -> bool:
        """
        Check if a blob exists.

        Args:
            container: Container name
            name: Blob name

        Returns:
            True if blob exists, False otherwise

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If unable to connect to Azure storage
            BlobStorageError: If check operation fails
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            return blob_client.exists()

        except ContainerNotFoundError:
            raise
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to check blob existence '{name}' in container '{container}': {str(e)}"
            )

    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """
        Get detailed properties of a blob.

        Args:
            container: Container name
            name: Blob name

        Returns:
            BlobProperties as dict

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If operation fails
            ConnectionError: If unable to connect to Azure storage
        """
        try:
            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)

            # Get blob properties
            props = blob_client.get_blob_properties()

            # Handle content_md5 conversion
            content_md5 = None
            if props.content_settings and props.content_settings.content_md5:
                # Convert bytearray/bytes to base64 string
                if isinstance(props.content_settings.content_md5, (bytes, bytearray)):
                    content_md5 = base64.b64encode(
                        props.content_settings.content_md5
                    ).decode("utf-8")
                else:
                    content_md5 = str(props.content_settings.content_md5)

            # Convert to our BlobProperties model
            blob_properties = BlobProperties(
                name=name,
                container=container,
                size=props.size,
                last_modified=props.last_modified,
                creation_time=getattr(props, "creation_time", None),
                etag=props.etag,
                content_type=props.content_settings.content_type
                if props.content_settings
                else "application/octet-stream",
                content_encoding=props.content_settings.content_encoding
                if props.content_settings
                else None,
                content_language=props.content_settings.content_language
                if props.content_settings
                else None,
                cache_control=props.content_settings.cache_control
                if props.content_settings
                else None,
                content_disposition=props.content_settings.content_disposition
                if props.content_settings
                else None,
                content_md5=content_md5,
                metadata=props.metadata or {},
                tags=getattr(props, "tags", {}) or {},
                blob_type=str(props.blob_type)
                if hasattr(props, "blob_type")
                else "BlockBlob",
                lease_status=str(props.lease.status)
                if hasattr(props, "lease") and props.lease
                else None,
                lease_state=str(props.lease.state)
                if hasattr(props, "lease") and props.lease
                else None,
                server_encrypted=getattr(props, "server_encrypted", None),
                blob_tier=str(props.blob_tier)
                if hasattr(props, "blob_tier") and props.blob_tier
                else None,
                blob_tier_change_time=getattr(props, "blob_tier_change_time", None),
                blob_tier_inferred=getattr(props, "blob_tier_inferred", None),
                last_accessed_on=getattr(props, "last_accessed_on", None),
            )

            return blob_properties.model_dump()

        except ContainerNotFoundError:
            raise
        except BlobNotFoundError:
            raise
        except ResourceNotFoundError:
            # This could be either container or blob not found
            # Check if container exists to determine which error to raise
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
            else:
                raise BlobNotFoundError(container, name)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to get blob properties '{name}' in container '{container}': {str(e)}"
            )

    async def copy_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("copy_blob not implemented yet")

    async def move_blob(
        self,
        source_container: str,
        source_name: str,
        dest_container: str,
        dest_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("move_blob not implemented yet")

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
            # Validate container name using our ContainerInfo model
            # This will raise validation errors if the name doesn't meet Azure requirements
            ContainerInfo(
                name=name,
                last_modified=datetime.now(),
                etag="temp",
                metadata=kwargs.get("metadata", {}),
                public_access=kwargs.get("public_access"),
            )

            # Get container client (don't auto-create)
            container_client = self._blob_service_client.get_container_client(name)

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
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(f"Failed to create container '{name}': {str(e)}")

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
            # Get container client (but don't create it)
            container_client = self._blob_service_client.get_container_client(name)

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
        try:
            # Get container client (but don't create it)
            container_client = self._blob_service_client.get_container_client(name)

            # Check if container exists
            return container_client.exists()

        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to check container existence '{name}': {str(e)}"
            )

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
            # Get container client (but don't create it)
            container_client = self._blob_service_client.get_container_client(name)

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

    async def generate_sas_token(
        self, container: str, name: str, permissions: List[str], expiry, **kwargs
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("generate_sas_token not implemented yet")

    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry, **kwargs
    ) -> Dict[str, Any]:
        """Not implemented yet."""
        raise NotImplementedError("generate_container_sas_token not implemented yet")

    async def set_blob_metadata(
        self, container: str, name: str, metadata: Dict[str, str]
    ) -> None:
        """Not implemented yet."""
        raise NotImplementedError("set_blob_metadata not implemented yet")

    async def get_blob_metadata(self, container: str, name: str) -> Dict[str, str]:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_metadata not implemented yet")

    async def set_blob_tags(
        self, container: str, name: str, tags: Dict[str, str]
    ) -> None:
        """Not implemented yet."""
        raise NotImplementedError("set_blob_tags not implemented yet")

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_tags not implemented yet")

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Not implemented yet."""
        raise NotImplementedError("get_blob_url not implemented yet")

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
            # Validate tier using our BlobTierInfo model
            BlobTierInfo(
                container=container,
                name=name,
                tier=tier,
            )

            # Get container client to check if container exists
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            # Get blob client
            blob_client = container_client.get_blob_client(name)

            # Check if blob exists
            if not blob_client.exists():
                raise BlobNotFoundError(container, name)

            # Map tier string to Azure StandardBlobTier
            tier_mapping = {
                "Hot": StandardBlobTier.Hot,
                "Cool": StandardBlobTier.Cool,
            }

            if tier not in tier_mapping:
                raise BlobStorageError(
                    f"Invalid tier '{tier}'. Must be one of: Hot, Cool"
                )

            azure_tier = tier_mapping[tier]

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
            container_client = self._blob_service_client.get_container_client(container)
            if not container_client.exists():
                raise ContainerNotFoundError(container)
            else:
                raise BlobNotFoundError(container, name)
        except ServiceRequestError as e:
            raise ConnectionError(f"Failed to connect to Azure storage: {str(e)}")
        except Exception as e:
            raise BlobStorageError(
                f"Failed to set blob tier '{tier}' for '{name}' in container '{container}': {str(e)}"
            )
