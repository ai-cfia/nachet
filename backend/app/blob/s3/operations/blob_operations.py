"""
Blob operations for S3-compatible Blob Storage (Apache Ozone).

This module handles basic blob CRUD operations including upload, download,
delete, existence checks, and property retrieval using boto3.
"""

from typing import Dict, Any, Union, BinaryIO, AsyncIterator, TYPE_CHECKING
from botocore.exceptions import ClientError

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
    ContainerNotFoundError,
    BlobNotFoundError,
    ConnectionError,
    BlobStorageError,
)

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


class BlobOperations:
    """Handles blob-specific operations for S3-compatible storage."""

    def __init__(self, s3_client: "S3Client"):
        """
        Initialize blob operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("upload blob")
    async def upload_blob(
        self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs
    ) -> Dict[str, Any]:
        """
        Upload a blob to S3 storage.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            data: Data to upload (bytes, str, or file-like object)
            **kwargs: Additional options (content_type, metadata, tags, overwrite, etc.)

        Returns:
            UploadResult as dict

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If upload fails
            ConnectionError: If unable to connect to S3 storage
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)
        ValidationHelper.validate_data_not_none(data)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Extract options
        content_type = kwargs.get("content_type", "application/octet-stream")
        metadata = kwargs.get("metadata", {})
        tags = kwargs.get("tags", {})
        overwrite = kwargs.get("overwrite", True)

        # Convert data to bytes if it's a string
        data = ValidationHelper.convert_string_data_to_bytes(data)

        # Check if blob exists when overwrite is False
        if not overwrite:
            try:
                self._client.head_object(Bucket=container, Key=name)
                from ...exceptions import BlobAlreadyExistsError

                raise BlobAlreadyExistsError(container, name)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code != "404":
                    raise

        # Prepare put_object parameters
        put_params = {
            "Bucket": container,
            "Key": name,
            "Body": data,
            "ContentType": content_type,
        }

        # Add metadata if provided
        if metadata:
            put_params["Metadata"] = metadata

        # Add optional content settings
        if kwargs.get("content_encoding"):
            put_params["ContentEncoding"] = kwargs.get("content_encoding")
        if kwargs.get("content_language"):
            put_params["ContentLanguage"] = kwargs.get("content_language")
        if kwargs.get("cache_control"):
            put_params["CacheControl"] = kwargs.get("cache_control")
        if kwargs.get("content_disposition"):
            put_params["ContentDisposition"] = kwargs.get("content_disposition")

        # Upload blob
        _get_logger().info("Uploading blob to S3", container=container, blob=name)
        response = self._client.put_object(**put_params)

        # Add tags if provided (separate operation in S3)
        if tags:
            tag_set = [{"Key": k, "Value": v} for k, v in tags.items()]
            self._client.put_object_tagging(
                Bucket=container, Key=name, Tagging={"TagSet": tag_set}
            )

        # Get object metadata to build result
        head_response = self._client.head_object(Bucket=container, Key=name)

        # Build object URL
        endpoint_url = self._client.meta.endpoint_url
        object_url = f"{endpoint_url}/{container}/{name}"

        # Extract content MD5
        content_md5 = head_response.get("ContentMD5") or response.get("ETag", "").strip(
            '"'
        )

        # Create UploadResult
        upload_result = UploadResult(
            container=container,
            name=name,
            etag=response.get("ETag", "").strip('"'),
            last_modified=head_response.get("LastModified"),
            url=object_url,
            size=head_response.get("ContentLength", 0),
            content_md5=content_md5,
        )

        _get_logger().info("Blob uploaded successfully", container=container, blob=name)
        return upload_result.model_dump()

    @ErrorHandler.handle_service_errors("download blob")
    async def download_blob(self, container: str, name: str, **kwargs) -> bytes:
        """
        Download a blob from S3 storage.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            **kwargs: Additional options (offset, length, validate_content, timeout)

        Returns:
            Blob data as bytes

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If download fails
            ConnectionError: If unable to connect to S3 storage
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Extract download options
        offset = kwargs.get("offset")
        length = kwargs.get("length")

        # Build get_object parameters
        get_params = {
            "Bucket": container,
            "Key": name,
        }

        # Add Range header if offset/length specified
        if offset is not None or length is not None:
            start = offset or 0
            if length is not None:
                end = start + length - 1
                get_params["Range"] = f"bytes={start}-{end}"
            else:
                get_params["Range"] = f"bytes={start}-"

        # Download blob
        _get_logger().info("Downloading blob from S3", container=container, blob=name)
        response = self._client.get_object(**get_params)

        # Read all data from the StreamingBody
        blob_data = response["Body"].read()

        _get_logger().info(
            "Blob downloaded successfully",
            container=container,
            blob=name,
            size=len(blob_data),
        )
        return blob_data

    async def download_blob_stream(
        self, container: str, name: str, **kwargs
    ) -> AsyncIterator[bytes]:
        """
        Download a blob as a stream from S3.

        Note: Error handling is done inline since the ErrorHandler decorator
        doesn't support async generators properly.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            **kwargs: Additional options (offset, length, validate_content, timeout, chunk_size)

        Returns:
            AsyncIterator yielding chunks of blob data

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If download fails
            ConnectionError: If unable to connect to S3 storage
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)

            # Check if container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Extract download options
            offset = kwargs.get("offset")
            length = kwargs.get("length")
            chunk_size = kwargs.get("chunk_size", 1024 * 1024)  # 1MB default

            # Build get_object parameters
            get_params = {
                "Bucket": container,
                "Key": name,
            }

            # Add Range header if offset/length specified
            if offset is not None or length is not None:
                start = offset or 0
                if length is not None:
                    end = start + length - 1
                    get_params["Range"] = f"bytes={start}-{end}"
                else:
                    get_params["Range"] = f"bytes={start}-"

            # Download blob as stream
            _get_logger().info(
                "Downloading blob stream from S3", container=container, blob=name
            )
            response = self._client.get_object(**get_params)

            # Yield chunks from StreamingBody
            streaming_body = response["Body"]
            while True:
                chunk = streaming_body.read(chunk_size)
                if not chunk:
                    break
                yield chunk

            _get_logger().info(
                "Blob stream download completed", container=container, blob=name
            )

        except (
            ContainerNotFoundError,
            BlobNotFoundError,
            ConnectionError,
            BlobStorageError,
        ):
            # Re-raise our custom exceptions without wrapping
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchBucket":
                raise ContainerNotFoundError(container)
            elif error_code == "NoSuchKey":
                raise BlobNotFoundError(container, name)
            else:
                _get_logger().error(
                    "S3 ClientError during download blob stream",
                    error_code=error_code,
                    error=str(e),
                )
                raise BlobStorageError(
                    f"Failed to download blob stream: {error_code} - {str(e)}"
                )
        except Exception as e:
            _get_logger().error(
                "Unexpected error during download blob stream",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise BlobStorageError(f"Failed to download blob stream: {str(e)}")

    @ErrorHandler.handle_service_errors("delete blob")
    async def delete_blob(self, container: str, name: str) -> bool:
        """
        Delete a blob from S3 storage.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)

        Returns:
            True if blob was deleted successfully, False if blob didn't exist

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If deletion operation fails
            ConnectionError: If unable to connect to S3 storage
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Check if blob exists before deletion
        try:
            self._client.head_object(Bucket=container, Key=name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchKey", "404"]:
                _get_logger().info(
                    "Blob does not exist, nothing to delete",
                    container=container,
                    blob=name,
                )
                return False
            raise

        # Delete the blob
        _get_logger().info("Deleting blob from S3", container=container, blob=name)
        self._client.delete_object(Bucket=container, Key=name)

        # Verify deletion (S3 delete_object doesn't fail if object doesn't exist)
        try:
            self._client.head_object(Bucket=container, Key=name)
            _get_logger().warning(
                "Blob still exists after deletion", container=container, blob=name
            )
            return False
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchKey", "404"]:
                _get_logger().info(
                    "Blob deleted successfully", container=container, blob=name
                )
                return True
            raise

    @ErrorHandler.handle_service_errors("check blob existence")
    async def blob_exists(self, container: str, name: str) -> bool:
        """
        Check if a blob exists in S3.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)

        Returns:
            True if blob exists, False otherwise

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If unable to connect to S3 storage
            BlobStorageError: If check operation fails
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Check if blob exists
        try:
            self._client.head_object(Bucket=container, Key=name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchKey", "404"]:
                return False
            raise

    @ErrorHandler.handle_service_errors("get blob properties")
    async def get_blob_properties(self, container: str, name: str) -> Dict[str, Any]:
        """
        Get detailed properties of a blob from S3.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)

        Returns:
            BlobProperties as dict

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
            BlobStorageError: If operation fails
            ConnectionError: If unable to connect to S3 storage
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Get object metadata
        response = self._client.head_object(Bucket=container, Key=name)

        # Get object tags (separate API call)
        tags = {}
        try:
            tag_response = self._client.get_object_tagging(Bucket=container, Key=name)
            tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])}
        except ClientError as e:
            _get_logger().warning(
                "Failed to get object tags",
                container=container,
                blob=name,
                error=str(e),
            )

        # Convert to BlobProperties model
        blob_properties = BlobProperties(
            name=name,
            container=container,
            size=response.get("ContentLength", 0),
            last_modified=response.get("LastModified"),
            creation_time=None,  # S3 doesn't provide creation time
            etag=response.get("ETag", "").strip('"'),
            content_type=response.get("ContentType", "application/octet-stream"),
            content_encoding=response.get("ContentEncoding"),
            content_language=response.get("ContentLanguage"),
            cache_control=response.get("CacheControl"),
            content_disposition=response.get("ContentDisposition"),
            content_md5=response.get("ContentMD5"),
            metadata=response.get("Metadata", {}),
            tags=tags,
            blob_type="S3Object",
            lease_status=None,  # S3 doesn't have lease concept
            lease_state=None,
            server_encrypted=response.get("ServerSideEncryption") is not None,
            blob_tier=response.get("StorageClass", "STANDARD"),
            blob_tier_change_time=None,
            blob_tier_inferred=False,
            last_accessed_on=None,
        )

        return blob_properties.model_dump()

    @ErrorHandler.handle_service_errors("list blobs")
    async def list_blobs(self, container: str, **kwargs) -> Dict[str, Any]:
        """
        List blobs in an S3 container (bucket).

        Args:
            container: Container name (S3 bucket)
            **kwargs: Additional options (can include ListOptions)

        Returns:
            BlobListResult with list of blobs

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)

        # Check if container exists
        await ErrorHandler.check_container_exists(self._client, container)

        # Parse options
        options = kwargs.get("options")
        if isinstance(options, dict):
            options = ListOptions(**options)
        elif options is None:
            options = ListOptions()

        blobs = []
        continuation_token = None

        # List objects in the bucket
        list_params = {
            "Bucket": container,
        }

        if options.prefix:
            list_params["Prefix"] = options.prefix

        if options.max_results:
            list_params["MaxKeys"] = options.max_results

        _get_logger().info(
            "Listing blobs in S3 bucket", container=container, prefix=options.prefix
        )
        response = self._client.list_objects_v2(**list_params)

        # Process results
        for obj in response.get("Contents", []):
            # Get tags if requested (requires separate API call per object)
            tags = {}
            if options.include_tags:
                try:
                    tag_response = self._client.get_object_tagging(
                        Bucket=container, Key=obj["Key"]
                    )
                    tags = {
                        tag["Key"]: tag["Value"]
                        for tag in tag_response.get("TagSet", [])
                    }
                except ClientError as e:
                    _get_logger().warning(
                        "Failed to get tags for object",
                        container=container,
                        blob=obj["Key"],
                        error=str(e),
                    )

            # Get metadata if requested (requires separate API call per object)
            metadata = {}
            if options.include_metadata:
                try:
                    head_response = self._client.head_object(
                        Bucket=container, Key=obj["Key"]
                    )
                    metadata = head_response.get("Metadata", {})
                except ClientError as e:
                    _get_logger().warning(
                        "Failed to get metadata for object",
                        container=container,
                        blob=obj["Key"],
                        error=str(e),
                    )

            # Create BlobInfo
            blob_info = BlobInfo(
                name=obj["Key"],
                container=container,
                size=obj.get("Size", 0),
                last_modified=obj.get("LastModified"),
                etag=obj.get("ETag", "").strip('"'),
                content_type="application/octet-stream",  # Not available in list response
                metadata=metadata,
                tags=tags,
            )
            blobs.append(blob_info)

        # Check for continuation token
        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")

        result = BlobListResult(
            blobs=blobs,
            continuation_token=continuation_token,
            prefix=options.prefix,
            container=container,
            total_count=len(blobs),
        )

        _get_logger().info(
            "Listed blobs successfully", container=container, count=len(blobs)
        )
        return result.model_dump()

    @ErrorHandler.handle_service_errors("get blob URL")
    async def get_blob_url(self, container: str, name: str, **kwargs) -> str:
        """
        Get the URL for a blob in S3.

        Args:
            container: Container name (S3 bucket)
            name: Blob name (S3 object key)
            **kwargs: Additional options

        Returns:
            URL string for the blob

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobNotFoundError: If blob doesn't exist
        """
        # Validate inputs
        ValidationHelper.validate_container_name(container)
        ValidationHelper.validate_blob_name(name)

        # Check if container and blob exist
        await ErrorHandler.check_container_exists(self._client, container)
        await ErrorHandler.check_blob_exists(self._client, container, name)

        # Build object URL
        endpoint_url = self._client.meta.endpoint_url
        object_url = f"{endpoint_url}/{container}/{name}"

        return object_url
