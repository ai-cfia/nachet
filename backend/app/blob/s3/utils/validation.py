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
                "S3 credentials are required for presigned URL generation",
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
