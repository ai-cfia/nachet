"""
Error handling utilities for S3-compatible Blob Storage operations.

This module provides common error handling patterns for S3-compatible storage
systems (Apache Ozone), promoting code reuse and consistency.
"""

from beartype.typing import Callable, Any
from botocore.exceptions import ClientError, BotoCoreError

from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    ContainerAlreadyExistsError,
    BlobAlreadyExistsError,
    ConnectionError,
    InvalidConfigurationError,
    PermissionError as BlobPermissionError,
)

# Lazy-loaded logger to avoid circular imports
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


class ErrorHandler:
    """Utility class for handling common S3 Blob Storage errors."""

    @staticmethod
    def handle_service_errors(operation_name: str):
        """
        Decorator to handle common S3 service errors.

        Maps boto3 ClientError codes to custom exceptions:
        - NoSuchBucket -> ContainerNotFoundError
        - NoSuchKey -> BlobNotFoundError
        - BucketAlreadyExists, BucketAlreadyOwnedByYou -> ContainerAlreadyExistsError
        - AccessDenied -> PermissionError
        - Connection/network errors -> ConnectionError

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
                    ContainerAlreadyExistsError,
                    BlobAlreadyExistsError,
                    ConnectionError,
                    BlobStorageError,
                    InvalidConfigurationError,
                    BlobPermissionError,
                ):
                    # Re-raise our custom exceptions without wrapping
                    raise
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")

                    # Map S3 error codes to custom exceptions
                    if error_code == "NoSuchBucket":
                        # Extract container name from args if available
                        container = args[1] if len(args) > 1 else "unknown"
                        raise ContainerNotFoundError(container)
                    elif error_code == "NoSuchKey":
                        # Extract container and blob name from args
                        container = args[1] if len(args) > 1 else "unknown"
                        blob_name = args[2] if len(args) > 2 else "unknown"
                        raise BlobNotFoundError(container, blob_name)
                    elif error_code in [
                        "BucketAlreadyExists",
                        "BucketAlreadyOwnedByYou",
                    ]:
                        container = args[1] if len(args) > 1 else "unknown"
                        raise ContainerAlreadyExistsError(container)
                    elif error_code == "AccessDenied":
                        raise BlobPermissionError(operation_name, "S3 resource")
                    elif error_code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                        raise InvalidConfigurationError(
                            "s3_credentials",
                            f"Invalid S3 credentials: {e.response.get('Error', {}).get('Message', str(e))}",
                        )
                    else:
                        _get_logger().error(
                            f"S3 ClientError during {operation_name}",
                            error_code=error_code,
                            error=str(e),
                        )
                        raise BlobStorageError(
                            f"Failed to {operation_name}: {error_code} - {str(e)}"
                        )
                except BotoCoreError as e:
                    _get_logger().error(
                        f"BotoCoreError during {operation_name}",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise ConnectionError(
                        f"Failed to connect to S3 storage during {operation_name}: {str(e)}"
                    )
                except Exception as e:
                    _get_logger().error(
                        f"Unexpected error during {operation_name}",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise BlobStorageError(f"Failed to {operation_name}: {str(e)}")

            return wrapper

        return decorator

    @staticmethod
    async def check_container_exists(client: Any, container: str) -> None:  # Type: S3Client (boto3)
        """
        Check if a container (bucket) exists and raise appropriate error if not.

        Args:
            client: boto3 S3 client instance
            container: Container name to check

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If connection fails
        """
        try:
            client.head_bucket(Bucket=container)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchBucket", "404"]:
                raise ContainerNotFoundError(container)
            elif error_code == "AccessDenied":
                # Bucket exists but no access - don't raise NotFoundError
                raise BlobPermissionError("check container existence", container)
            else:
                raise ConnectionError(f"Failed to check container existence: {str(e)}")
        except BotoCoreError as e:
            raise ConnectionError(f"Failed to check container existence: {str(e)}")

    @staticmethod
    async def check_blob_exists(client: Any, container: str, name: str) -> None:  # Type: S3Client (boto3)
        """
        Check if a blob (object) exists and raise appropriate error if not.

        Args:
            client: boto3 S3 client instance
            container: Container name
            name: Blob name to check

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If connection fails
        """
        try:
            # First check container exists
            await ErrorHandler.check_container_exists(client, container)

            # Then check blob exists
            client.head_object(Bucket=container, Key=name)
        except ContainerNotFoundError:
            raise
        except BlobPermissionError:
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchKey", "404"]:
                raise BlobNotFoundError(container, name)
            else:
                raise ConnectionError(f"Failed to check blob existence: {str(e)}")
        except BotoCoreError as e:
            raise ConnectionError(f"Failed to check blob existence: {str(e)}")

    @staticmethod
    def handle_metadata_validation_errors(
        metadata: dict, operation_type: str = "metadata"
    ):
        """
        Validate metadata dictionary and raise appropriate errors.

        S3 metadata keys and values must be strings.

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
