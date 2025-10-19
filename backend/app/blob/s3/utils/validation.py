"""
Validation utilities for S3-compatible Blob Storage operations.

This module provides common validation patterns and helper functions
used across different operation classes for S3-compatible storage (Apache Ozone).
"""

from typing import Dict, Any, Optional

from ...exceptions import BlobStorageError, InvalidConfigurationError
from ...models import BlobTierInfo, ContainerInfo


class ValidationHelper:
    """Utility class for common validation operations for S3."""

    @staticmethod
    def validate_blob_name(name: str) -> str:
        """
        Validate blob name (S3 object key) is not empty.

        S3 object keys can contain any UTF-8 character, but we enforce
        basic constraints for consistency with Azure implementation.

        Args:
            name: Blob name to validate

        Returns:
            Validated blob name

        Raises:
            BlobStorageError: If name is invalid
        """
        if not name or name.strip() == "":
            raise BlobStorageError("Blob name cannot be empty")

        # S3 allows most characters, but we maintain similar constraints to Azure
        # for consistency across implementations
        if not all(c.isalnum() or c in "-_/." for c in name):
            raise BlobStorageError(
                "Blob name can only contain letters, numbers, hyphens, underscores, periods, and slashes"
            )
        return name.strip()

    @staticmethod
    def validate_container_name(container: str) -> str:
        """
        Validate container name (S3 bucket name) follows S3 naming rules.

        S3 bucket naming rules:
        - Must be 3-63 characters long
        - Can contain lowercase letters, numbers, hyphens, and periods
        - Must start with a letter or number
        - Must not be formatted as an IP address
        - No consecutive periods or hyphens next to periods

        Args:
            container: Container name to validate

        Returns:
            Validated container name (lowercase)

        Raises:
            BlobStorageError: If name is invalid
        """
        if not container or container.strip() == "":
            raise BlobStorageError("Container name cannot be empty")

        container = container.strip().lower()

        # Length check
        if len(container) < 3 or len(container) > 63:
            raise BlobStorageError("Container name must be between 3 and 63 characters")

        # Must start with letter or number
        if not (container[0].isalpha() or container[0].isdigit()):
            raise BlobStorageError("Container name must start with a letter or number")

        # Must end with letter or number
        if not (container[-1].isalpha() or container[-1].isdigit()):
            raise BlobStorageError("Container name must end with a letter or number")

        # Check valid characters
        if not all(c.islower() or c.isdigit() or c in "-." for c in container):
            raise BlobStorageError(
                "Container name can only contain lowercase letters, numbers, hyphens, and periods"
            )

        # Check for consecutive periods or hyphens next to periods
        if ".." in container or ".-" in container or "-." in container:
            raise BlobStorageError(
                "Container name cannot contain consecutive periods or hyphens adjacent to periods"
            )

        # Check if formatted as IP address (basic check)
        parts = container.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            raise BlobStorageError("Container name cannot be formatted as an IP address")

        return container

    @staticmethod
    def validate_data_not_none(data: Any) -> None:
        """
        Validate that data is not None.

        Args:
            data: Data to validate

        Raises:
            BlobStorageError: If data is None
        """
        if data is None:
            raise BlobStorageError("Data cannot be None")

    @staticmethod
    def validate_blob_tier(tier: str) -> str:
        """
        Validate blob tier string for S3 storage classes.

        Note: Apache Ozone may not support storage classes, so we only
        validate STANDARD for consistency with the plan.

        Args:
            tier: Tier string to validate

        Returns:
            Validated tier string

        Raises:
            BlobStorageError: If tier is invalid
        """
        valid_tiers = {"STANDARD"}

        if tier not in valid_tiers:
            raise BlobStorageError(
                f"Invalid tier '{tier}'. Must be one of: {', '.join(valid_tiers)}"
            )

        return tier

    @staticmethod
    def validate_sas_permissions(
        permissions: list, operation_type: str = "blob"
    ) -> None:
        """
        Validate permissions list for presigned URLs.

        S3 presigned URLs use different permission model than Azure SAS,
        but we validate similar permission strings for consistency.

        Args:
            permissions: List of permission strings
            operation_type: Type of operation (blob/container)

        Raises:
            BlobStorageError: If permissions are invalid
        """
        if operation_type == "blob":
            valid_permissions = {"read", "write", "delete"}
        else:  # container
            valid_permissions = {"read", "write", "delete", "list"}

        for permission in permissions:
            if permission not in valid_permissions:
                raise BlobStorageError(
                    f"Invalid permission '{permission}'. "
                    f"Valid permissions for {operation_type}s: {', '.join(valid_permissions)}"
                )

    @staticmethod
    def validate_credentials_available(
        access_key_id: Optional[str], secret_access_key: Optional[str]
    ) -> tuple[str, str]:
        """
        Validate that S3 credentials are available for presigned URL generation.

        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key

        Returns:
            Tuple of (access_key_id, secret_access_key)

        Raises:
            InvalidConfigurationError: If credentials are not available
        """
        if not access_key_id or not secret_access_key:
            raise InvalidConfigurationError(
                "access_key_id and secret_access_key",
                "S3 credentials are required for presigned URL generation"
            )

        return access_key_id, secret_access_key

    @staticmethod
    def validate_container_name_with_model(
        name: str, metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Validate container name using Pydantic model validation.

        Args:
            name: Container name to validate
            metadata: Optional metadata for validation

        Raises:
            InvalidConfigurationError: If validation fails
        """
        try:
            from datetime import datetime

            ContainerInfo(
                name=name,
                last_modified=datetime.now(),
                etag="temp",
                metadata=metadata or {},
                public_access=None,
            )
        except ValueError as e:
            raise InvalidConfigurationError(
                "container_name", f"Invalid container name: {str(e)}"
            )

    @staticmethod
    def validate_blob_tier_with_model(container: str, name: str, tier: str) -> None:
        """
        Validate blob tier using Pydantic model validation.

        Args:
            container: Container name
            name: Blob name
            tier: Tier to validate

        Raises:
            BlobStorageError: If validation fails
        """
        try:
            BlobTierInfo(
                container=container,
                name=name,
                tier=tier,
            )
        except ValueError as e:
            raise BlobStorageError(f"Invalid tier '{tier}': {str(e)}")

    @staticmethod
    def convert_string_data_to_bytes(data: Any) -> Any:
        """
        Convert string data to bytes if needed.

        Args:
            data: Data to convert

        Returns:
            Converted data (bytes if was string, original otherwise)
        """
        if isinstance(data, str):
            return data.encode("utf-8")
        return data

    @staticmethod
    def validate_url_format(url: str) -> None:
        """
        Validate URL has proper format.

        Args:
            url: URL to validate

        Raises:
            BlobStorageError: If URL format is invalid
        """
        if not url.startswith(("http://", "https://")):
            raise BlobStorageError("URL must be a valid HTTP/HTTPS URL")
