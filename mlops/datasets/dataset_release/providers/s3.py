"""Dataset S3 extensions: atomic publication, scoped credentials, and cleanup."""

from contextlib import closing
from typing import Any, BinaryIO

import boto3
from blob.exceptions import (
    BlobAlreadyExistsError,
    BlobNotFoundError,
    InvalidConfigurationError,
)
from blob.models import UploadResult
from blob.s3.client import S3ConfigurationError
from blob.s3.operations.blob_operations import BlobOperations
from blob.s3.storage import S3BlobStorage
from blob.s3.utils.error_handling import ErrorHandler
from blob.s3.utils.validation import ValidationHelper
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger


def create_s3_client(config: dict[str, Any]):
    """Create a scoped S3 client without an account-wide connectivity probe.

    Explicit access and secret keys must be paired. Otherwise boto3 keeps its
    normal credential chain. Session tokens and endpoint/TLS/timeouts are retained.
    """
    try:
        # Extract and validate credentials
        access_key_id = config.get("s3_access_key")
        secret_access_key = config.get("s3_secret_key")

        if bool(access_key_id) != bool(secret_access_key):
            logger.error(
                "Missing S3 credentials in configuration",
                has_access_key=bool(access_key_id),
                has_secret_key=bool(secret_access_key),
            )
            raise S3ConfigurationError(
                "s3_access_key and s3_secret_key must be supplied together"
            )

        # Extract configuration with defaults
        region = config.get("s3_region_name", "ceph")
        endpoint_url = config.get("s3_endpoint_url")
        use_ssl = config.get("s3_use_ssl")
        verify = config.get("s3_verify", True)
        connect_timeout = config.get("s3_connect_timeout", 5)
        read_timeout = config.get("s3_read_timeout", 10)

        # Create boto3 config with timeout settings
        boto_config = Config(
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries={"max_attempts": 2, "mode": "standard"},
        )

        # Build client parameters
        client_params = {
            "service_name": "s3",
            "endpoint_url": endpoint_url,
            "region_name": region,
            "use_ssl": use_ssl,
            "verify": verify,
            "config": boto_config,
        }

        # Log client creation
        if access_key_id:
            client_params["aws_access_key_id"] = access_key_id
            client_params["aws_secret_access_key"] = secret_access_key
        if config.get("s3_session_token"):
            client_params["aws_session_token"] = config["s3_session_token"]

        logger.info(
            f"Creating S3 client {'with custom endpoint' if endpoint_url else 'for AWS'}",
            endpoint_url=endpoint_url,
            region=region,
            use_ssl=use_ssl,
        )

        # Create the S3 client
        s3_client = boto3.client(**client_params)

        # Dataset credentials can be restricted to one bucket. Do not require
        # account-wide ListBuckets access or perform network I/O at construction.
        return s3_client

    except S3ConfigurationError:
        raise
    except BotoCoreError as e:
        logger.error(
            "BotoCoreError during S3 client creation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise S3ConfigurationError(
            f"Failed to create S3 client due to configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Unhandled exception in S3 client creation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise Exception(f"S3 client creation failed: {str(e)}")


class DatasetBlobOperations(BlobOperations):
    """Keep dataset publication safeguards outside the shared provider copy."""

    @ErrorHandler.handle_service_errors("upload blob")
    async def upload_blob(
        self, container: str, name: str, data: bytes | str | BinaryIO, **kwargs
    ) -> dict[str, Any]:
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

        # Extract options
        content_type = kwargs.get("content_type", "application/octet-stream")
        metadata = kwargs.get("metadata", {})
        tags = kwargs.get("tags", {})
        overwrite = kwargs.get("overwrite", True)

        # Convert data to bytes if it's a string
        data = ValidationHelper.convert_string_data_to_bytes(data)

        # Prepare put_object parameters
        put_params = {
            "Bucket": container,
            "Key": name,
            "Body": data,
            "ContentType": content_type,
        }

        if not overwrite:
            # The condition must be evaluated atomically by the object store.
            # A separate HEAD followed by PUT can overwrite another publisher.
            put_params["IfNoneMatch"] = "*"

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
        logger.info("Uploading blob to S3", container=container, blob=name)
        try:
            response = self._client.put_object(**put_params)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if not overwrite and code in ("PreconditionFailed", "412"):
                raise BlobAlreadyExistsError(container, name) from error
            raise

        # Add tags if provided (separate operation in S3)
        if tags:
            tag_set: list[dict[str, str]] = [
                {"Key": k, "Value": v} for k, v in tags.items()
            ]
            tagging: dict[str, list[dict[str, str]]] = {"TagSet": tag_set}
            self._client.put_object_tagging(Bucket=container, Key=name, Tagging=tagging)

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

        logger.info("Blob uploaded successfully", container=container, blob=name)
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
        logger.info("Downloading blob from S3", container=container, blob=name)
        try:
            response = self._client.get_object(**get_params)  # type: ignore[arg-type]
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "404":
                raise BlobNotFoundError(container, name) from error
            raise

        # Read all data from the StreamingBody
        with closing(response["Body"]) as stream:
            blob_data = stream.read()

        logger.info(
            "Blob downloaded successfully",
            container=container,
            blob=name,
            size=len(blob_data),
        )
        return blob_data


class DatasetS3BlobStorage(S3BlobStorage):
    """Extend the shared provider with dataset-specific client and write behavior."""

    def _initialize_client(self):
        """Initialize the S3 client using boto3."""
        try:
            self._s3_client = create_s3_client(self.config)
            logger.info(
                "S3 Blob Storage client initialized",
                endpoint_url=self.config.get("s3_endpoint_url", "AWS S3"),
                region=self.config.get("s3_region", "us-east-1"),
            )

        except Exception as e:
            logger.error(
                "Failed to initialize S3 client",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise InvalidConfigurationError(
                "s3_client",
                f"Failed to initialize S3 Blob Storage client: {str(e)}",
            )

    def _initialize_operations(self):
        """Reuse all common operations except dataset upload and download."""
        super()._initialize_operations()
        self._blob_ops = DatasetBlobOperations(self._s3_client)

    def close(self) -> None:
        """Release the dataset provider's SDK connection pool."""
        self._s3_client.close()
