"""
Blob operations for Azure Blob Storage.

This module handles basic blob CRUD operations including upload, download,
delete, existence checks, and property retrieval.
"""

import base64
from beartype.typing import Dict, Any, Union, BinaryIO, AsyncIterator, Optional
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError

from ..client import create_container_client
from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...models import (
    UploadResult,
    BlobInfo,
    BlobProperties,
    ListOptions,
    BlobListResult,
)
from ...exceptions import (
    # BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    # ConnectionError,
)


class BlobOperations:
    """Handles blob-specific operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize blob operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

    @ErrorHandler.handle_service_errors("upload blob")
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
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)
            ValidationHelper.validate_data_not_none(data)

            # Check if container exists
            await ErrorHandler.check_container_exists(self._client, container)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Extract options
            content_type = kwargs.get("content_type", "application/octet-stream")
            metadata = kwargs.get("metadata", {})
            tags = kwargs.get("tags", {})
            overwrite = kwargs.get("overwrite", True)

            # Convert data to bytes if it's a string
            data = ValidationHelper.convert_string_data_to_bytes(data)

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
            content_md5 = self._extract_content_md5(blob_properties)

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

    @ErrorHandler.handle_service_errors("download blob")
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
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

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

        except (ContainerNotFoundError, BlobNotFoundError):
            raise
        except ResourceNotFoundError:
            handler = ErrorHandler.handle_resource_not_found(container, name)
            await handler(self._client, ResourceNotFoundError())
            # This line should never be reached as handler always raises
            raise BlobNotFoundError(container, name)

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
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Extract download options
            offset = kwargs.get("offset")
            length = kwargs.get("length")
            validate_content = kwargs.get("validate_content", False)
            timeout = kwargs.get("timeout")

            # Download blob as stream
            download_stream = blob_client.download_blob(
                offset=offset,
                length=length,
                validate_content=validate_content,
                timeout=timeout,
            )

            # Yield chunks
            # download_stream.chunks() returns an iterator, not async iterator
            for chunk in download_stream.chunks():
                yield chunk

        except (ContainerNotFoundError, BlobNotFoundError):
            raise
        except ResourceNotFoundError:
            handler = ErrorHandler.handle_resource_not_found(container, name)
            await handler(self._client, ResourceNotFoundError())
            # This line should never be reached as handler always raises
            raise BlobNotFoundError(container, name)

    @ErrorHandler.handle_service_errors("delete blob")
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
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container exists
            await ErrorHandler.check_container_exists(self._client, container)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

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
            # Blob doesn't exist, consider it successfully deleted
            return False

    @ErrorHandler.handle_service_errors("check blob existence")
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
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Get blob client
        blob_client = self._client.get_blob_client(container=container, blob=name)

        # Check if blob exists
        return blob_client.exists()

    @ErrorHandler.handle_service_errors("get blob properties")
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
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get blob client
            blob_client = self._client.get_blob_client(container=container, blob=name)

            # Get blob properties
            props = blob_client.get_blob_properties()

            # Handle content_md5 conversion
            content_md5 = self._extract_content_md5(props)

            # Convert to our BlobProperties model
            blob_properties = BlobProperties(
                name=name,
                container=container,
                size=props.size,
                last_modified=props.last_modified,
                creation_time=getattr(props, "creation_time", None),
                etag=props.etag,
                content_type=(
                    props.content_settings.content_type
                    if props.content_settings and props.content_settings.content_type
                    else "application/octet-stream"
                ),
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

        except (ContainerNotFoundError, BlobNotFoundError):
            raise
        except ResourceNotFoundError:
            handler = ErrorHandler.handle_resource_not_found(container, name)
            await handler(self._client, ResourceNotFoundError())
            # This line should never be reached as handler always raises
            raise BlobNotFoundError(container, name)

    @ErrorHandler.handle_service_errors("list blobs")
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
            # Validate inputs
            ValidationHelper.validate_container_name(container)

            options = kwargs.get("options")
            if isinstance(options, dict):
                options = ListOptions(**options)
            elif options is None:
                options = ListOptions()  # type: ignore[call-arg]

            # Get container client
            container_client = create_container_client(self._client, container)

            # Check if container exists
            if not container_client.exists():
                raise ContainerNotFoundError(container)

            blobs = []
            continuation_token = None

            # List blobs in the container
            # Build include list based on options
            include_list = []
            if options.include_metadata:
                include_list.append("metadata")
            if options.include_tags:
                include_list.append("tags")
            if options.include_versions:
                include_list.append("versions")
            if options.include_snapshots:
                include_list.append("snapshots")

            # type: ignore comment to suppress false positive from Azure SDK type stubs
            blob_iter = container_client.list_blobs(  # type: ignore[call-arg]
                name_starts_with=options.prefix,
                include=include_list if include_list else None,
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
                    content_type=(
                        blob.content_settings.content_type
                        if blob.content_settings and blob.content_settings.content_type
                        else "application/octet-stream"
                    ),
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

    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """Get the URL for a blob."""
        # This was not implemented in the original class
        raise NotImplementedError("get_blob_url not implemented yet")

    def _extract_content_md5(self, props) -> Optional[str]:
        """
        Extract and convert content MD5 from blob properties.

        Args:
            props: Blob properties object

        Returns:
            MD5 hash as base64 string or None
        """
        content_md5 = None
        if props.content_settings and props.content_settings.content_md5:
            # Convert bytearray/bytes to base64 string
            if isinstance(props.content_settings.content_md5, (bytes, bytearray)):
                content_md5 = base64.b64encode(
                    props.content_settings.content_md5
                ).decode("utf-8")
            else:
                content_md5 = str(props.content_settings.content_md5)
        return content_md5
