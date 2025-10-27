"""
Validation utilities for Azure Blob Storage operations.

This module provides common validation patterns and helper functions
used across different operation classes.
"""

from beartype.typing import Dict, Any, Optional, cast
from azure.storage.blob import StandardBlobTier

from ...exceptions import BlobStorageError, InvalidConfigurationError
from ...models import BlobTierInfo, ContainerInfo


class ValidationHelper:
    """Utility class for common validation operations."""

    @staticmethod
    def validate_blob_name(name: str) -> str:
        """
        Validate blob name using unified cross-platform validation.

        Uses the unified validation module to ensure compatibility with
        both Azure Blob Storage and S3.

        Args:
            name: Blob name to validate

        Returns:
            Validated blob name

        Raises:
            BlobStorageError: If name is invalid
        """
        from ...validation import validate_blob_name as unified_validate_blob_name

        return unified_validate_blob_name(name)

    @staticmethod
    def validate_container_name(container: str) -> str:
        """
        Validate container name using unified cross-platform validation.

        Uses the unified validation module to ensure compatibility with
        both Azure Blob Storage and S3.

        Args:
            container: Container name to validate

        Returns:
            Validated container name (lowercase)

        Raises:
            BlobStorageError: If name is invalid
        """
        from ...validation import (
            validate_container_name as unified_validate_container_name,
        )

        return unified_validate_container_name(container)

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
    def validate_blob_tier(tier: str) -> StandardBlobTier:
        """
        Validate and convert blob tier string to Azure StandardBlobTier.

        Args:
            tier: Tier string to validate

        Returns:
            Azure StandardBlobTier enum value

        Raises:
            BlobStorageError: If tier is invalid
        """
        tier_mapping: Dict[str, Any] = {
            "Hot": StandardBlobTier.Hot,
            "Cool": StandardBlobTier.Cool,
        }

        if tier not in tier_mapping:
            raise BlobStorageError(f"Invalid tier '{tier}'. Must be one of: Hot, Cool")

        return cast(StandardBlobTier, tier_mapping[tier])

    @staticmethod
    def validate_sas_permissions(
        permissions: list, operation_type: str = "blob"
    ) -> None:
        """
        Validate SAS permissions list.

        Args:
            permissions: List of permission strings
            operation_type: Type of operation (blob/container)

        Raises:
            BlobStorageError: If permissions are invalid
        """
        if operation_type == "blob":
            valid_permissions = {"read", "write", "delete", "add", "create"}
        else:  # container
            valid_permissions = {"read", "write", "delete", "list", "add", "create"}

        for permission in permissions:
            if permission not in valid_permissions:
                raise BlobStorageError(
                    f"Invalid permission '{permission}'. "
                    f"Valid permissions for {operation_type}s: {', '.join(valid_permissions)}"
                )

    @staticmethod
    def validate_account_key_available(client) -> tuple[str, str]:
        """
        Validate that account key is available for SAS token generation.

        Args:
            client: Azure BlobServiceClient instance

        Returns:
            Tuple of (account_name, account_key)

        Raises:
            InvalidConfigurationError: If account key is not available
        """
        if (
            not hasattr(client.credential, "account_key")
            or not client.credential.account_key
        ):
            raise InvalidConfigurationError(
                "account_key",
                "Account key is required for SAS token generation. "
                "Ensure connection string contains AccountKey parameter.",
            )

        return client.account_name, client.credential.account_key

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
                tier_change_time=None,
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
