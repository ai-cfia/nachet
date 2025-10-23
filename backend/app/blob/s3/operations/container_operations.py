"""
Container operations for S3-compatible Blob Storage (Apache Ozone).

This module handles container (bucket) management operations including creation,
deletion, listing, and property retrieval using boto3.
"""

from typing import Dict, Any, TYPE_CHECKING
from botocore.exceptions import ClientError
from datetime import datetime

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...models import ContainerInfo, ContainerListResult, ListOptions
from ...exceptions import (
    BlobStorageError,
    ContainerNotFoundError,
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


class ContainerOperations:
    """Handles container (bucket) specific operations for S3-compatible storage."""

    def __init__(self, s3_client: "S3Client"):
        """
        Initialize container operations with S3 client.

        Args:
            s3_client: boto3 S3 client instance
        """
        self._client = s3_client

    @ErrorHandler.handle_service_errors("list containers")
    async def list_containers(self, **kwargs) -> Dict[str, Any]:
        """
        List all containers (buckets) in the S3 storage.

        Args:
            **kwargs: Additional options (can include ListOptions)

        Returns:
            ContainerListResult with list of containers

        Raises:
            ConnectionError: If unable to connect to S3 storage
            BlobStorageError: If operation fails
        """
        options = kwargs.get("options")
        if isinstance(options, dict):
            options = ListOptions(**options)
        elif options is None:
            options = ListOptions()

        containers = []
        continuation_token = None

        # List buckets using boto3
        _get_logger().info("Listing S3 buckets")
        response = self._client.list_buckets()

        count = 0
        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]

            # Apply prefix filter if specified
            if options.prefix and not bucket_name.startswith(options.prefix):
                continue

            # Apply max_results limit
            if options.max_results and count >= options.max_results:
                continuation_token = "has_more"
                break

            # Get bucket metadata if requested
            metadata = {}
            if options.include_metadata:
                try:
                    # S3 doesn't have bucket-level metadata like Azure
                    # We can get tags instead which serve a similar purpose
                    tag_response = self._client.get_bucket_tagging(Bucket=bucket_name)
                    metadata = {
                        tag["Key"]: tag["Value"]
                        for tag in tag_response.get("TagSet", [])
                    }
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    if error_code not in ["NoSuchTagSet"]:
                        _get_logger().warning(
                            "Failed to get bucket tags",
                            bucket=bucket_name,
                            error=str(e),
                        )

            # Convert S3 bucket to ContainerInfo model
            container_info = ContainerInfo(
                name=bucket_name,
                last_modified=bucket.get("CreationDate", datetime.now()),
                etag="",  # S3 buckets don't have ETags
                metadata=metadata,
                public_access=None,  # Would require additional API call to check ACL
            )
            containers.append(container_info)
            count += 1

        result = ContainerListResult(
            containers=containers,
            continuation_token=continuation_token,
            total_count=len(containers),
        )

        _get_logger().info("Listed S3 buckets successfully", count=len(containers))
        return result.model_dump()

    @ErrorHandler.handle_service_errors("create container")
    async def create_container(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new container (bucket) in S3.

        Args:
            name: Container name (bucket name)
            **kwargs: Additional options (can include metadata, public_access)

        Returns:
            ContainerInfo as dict

        Raises:
            InvalidConfigurationError: If container name is invalid
            ContainerAlreadyExistsError: If container already exists
            BlobStorageError: If container creation fails
        """
        # Validate container name using Pydantic model
        ValidationHelper.validate_container_name_with_model(
            name, kwargs.get("metadata", {})
        )

        # Check if bucket already exists
        try:
            self._client.head_bucket(Bucket=name)
            _get_logger().info("Bucket already exists", bucket=name)

            # Return existing bucket properties
            metadata = {}
            try:
                tag_response = self._client.get_bucket_tagging(Bucket=name)
                metadata = {
                    tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])
                }
            except ClientError:
                pass

            container_info = ContainerInfo(
                name=name,
                last_modified=datetime.now(),  # S3 doesn't provide last modified for buckets
                etag="",
                metadata=metadata,
                public_access=None,
            )
            return container_info.model_dump()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code not in ["NoSuchBucket", "404"]:
                raise

        # Create the bucket
        _get_logger().info("Creating S3 bucket", bucket=name)

        # For Ozone and some S3-compatible systems, we don't specify region in CreateBucket
        try:
            # Try without LocationConstraint first (for Ozone)
            self._client.create_bucket(Bucket=name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # If it requires a region, try with LocationConstraint
            if error_code == "IllegalLocationConstraintException":
                region = self._client.meta.region_name
                if region and region != "us-east-1":
                    self._client.create_bucket(
                        Bucket=name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                else:
                    raise
            else:
                raise

        # Set tags if metadata provided (S3 uses tags as metadata)
        metadata = kwargs.get("metadata", {})
        if metadata:
            tag_set = [{"Key": k, "Value": v} for k, v in metadata.items()]
            try:
                self._client.put_bucket_tagging(
                    Bucket=name, Tagging={"TagSet": tag_set}
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                # Some S3 implementations (like Garage) don't support tagging
                # If this happens, log it but don't fail the operation
                if error_code in ["BucketAlreadyExists", "NotImplemented"]:
                    _get_logger().warning(
                        "Bucket tagging not supported or failed, continuing without tags",
                        bucket=name,
                        error_code=error_code,
                    )
                else:
                    raise

        # Get the created bucket properties
        container_info = ContainerInfo(
            name=name,
            last_modified=datetime.now(),
            etag="",
            metadata=metadata,
            public_access=None,
        )

        _get_logger().info("Bucket created successfully", bucket=name)
        return container_info.model_dump()

    @ErrorHandler.handle_service_errors("delete container")
    async def delete_container(self, name: str) -> bool:
        """
        Delete a container (bucket) from S3.

        Args:
            name: Container name (bucket name)

        Returns:
            True if container was deleted successfully, False if container didn't exist

        Raises:
            ConnectionError: If unable to connect to S3 storage
            BlobStorageError: If deletion operation fails (e.g., bucket not empty)
        """
        # Validate container name
        ValidationHelper.validate_container_name(name)

        # Check if bucket exists
        try:
            self._client.head_bucket(Bucket=name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchBucket", "404"]:
                _get_logger().info(
                    "Bucket does not exist, nothing to delete", bucket=name
                )
                return False
            raise

        # Delete the bucket
        _get_logger().info("Deleting S3 bucket", bucket=name)
        try:
            self._client.delete_bucket(Bucket=name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "BucketNotEmpty":
                raise BlobStorageError(
                    f"Cannot delete bucket '{name}': bucket is not empty. "
                    "Delete all objects first."
                )
            raise

        # Verify deletion was successful
        try:
            self._client.head_bucket(Bucket=name)
            _get_logger().warning("Bucket still exists after deletion", bucket=name)
            return False
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchBucket", "404"]:
                _get_logger().info("Bucket deleted successfully", bucket=name)
                return True
            raise

    @ErrorHandler.handle_service_errors("check container existence")
    async def container_exists(self, name: str) -> bool:
        """
        Check if a container (bucket) exists in S3.

        Args:
            name: Container name (bucket name)

        Returns:
            True if container exists, False otherwise

        Raises:
            ConnectionError: If unable to connect to S3 storage
            BlobStorageError: If check operation fails
        """
        # Validate container name
        ValidationHelper.validate_container_name(name)

        # Check if bucket exists
        try:
            self._client.head_bucket(Bucket=name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchBucket", "404"]:
                return False
            # AccessDenied might mean it exists but we don't have permission
            if error_code == "AccessDenied":
                return True
            raise

    @ErrorHandler.handle_service_errors("get container properties")
    async def get_container_properties(self, name: str) -> Dict[str, Any]:
        """
        Get properties of a container (bucket) from S3.

        Args:
            name: Container name (bucket name)

        Returns:
            ContainerInfo as dict with full metadata

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ConnectionError: If unable to connect to S3 storage
            BlobStorageError: If operation fails
        """
        # Validate container name
        ValidationHelper.validate_container_name(name)

        # Check if bucket exists
        try:
            self._client.head_bucket(Bucket=name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["NoSuchBucket", "404"]:
                raise ContainerNotFoundError(name)
            raise

        # Get bucket metadata (tags)
        metadata = {}
        try:
            tag_response = self._client.get_bucket_tagging(Bucket=name)
            metadata = {
                tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])
            }
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code not in ["NoSuchTagSet"]:
                _get_logger().warning(
                    "Failed to get bucket tags", bucket=name, error=str(e)
                )

        # Convert to ContainerInfo model
        container_info = ContainerInfo(
            name=name,
            last_modified=datetime.now(),  # S3 doesn't provide last modified for buckets
            etag="",
            metadata=metadata,
            public_access=None,  # Would require additional API call to check ACL
        )

        _get_logger().info("Retrieved bucket properties", bucket=name)
        return container_info.model_dump()
