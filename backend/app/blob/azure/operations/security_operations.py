"""
Security operations for Azure Blob Storage.

This module handles security-related operations including SAS token generation
for both blobs and containers with various permissions and expiry settings.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    ContainerSasPermissions,
    generate_blob_sas,
    generate_container_sas,
)

from ..utils.error_handling import ErrorHandler
from ..utils.validation import ValidationHelper
from ...exceptions import (
    # BlobStorageError,
    ContainerNotFoundError,
    BlobNotFoundError,
    InvalidConfigurationError,
)


class SecurityOperations:
    """Handles security operations for Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """
        Initialize security operations with Azure client.

        Args:
            blob_service_client: Azure BlobServiceClient instance
        """
        self._client = blob_service_client

    @ErrorHandler.handle_service_errors("generate SAS token")
    async def generate_sas_token(
        self,
        container: str,
        name: str,
        permissions: List[str],
        expiry: timedelta,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a SAS token for a specific blob with given permissions and expiry.

        Args:
            container: Container name
            name: Blob name
            permissions: List of permissions ('read', 'write', 'delete', 'add', 'create')
            expiry: Token expiry duration from now
            **kwargs: Optional parameters:
                - start_time: When the token becomes valid (default: now)
                - ip: IP address or range to restrict access
                - content_type: Content type header for blob
                - content_disposition: Content disposition header
                - content_encoding: Content encoding header
                - content_language: Content language header
                - cache_control: Cache control header

        Returns:
            Dictionary containing:
                - sas_token: The SAS token string
                - sas_url: Full URL with SAS token
                - permissions: List of granted permissions
                - expiry: Token expiry datetime
                - start_time: Token start datetime (if specified)

        Raises:
            BlobNotFoundError: If blob doesn't exist
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If SAS token generation fails
            InvalidConfigurationError: If account key is not available
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_blob_name(name)
            ValidationHelper.validate_sas_permissions(permissions, "blob")

            # Validate container and blob exist
            await ErrorHandler.check_container_exists(self._client, container)
            await ErrorHandler.check_blob_exists(self._client, container, name)

            # Get account credentials
            account_name, account_key = ValidationHelper.validate_account_key_available(
                self._client
            )

            # Create permissions object using keyword arguments
            permission_kwargs = {perm: True for perm in permissions}
            sas_permissions = BlobSasPermissions(**permission_kwargs)

            # Calculate expiry time
            start_time = kwargs.get("start_time", datetime.now(timezone.utc))
            expiry_time = (
                start_time + expiry
                if isinstance(start_time, datetime)
                else datetime.now(timezone.utc) + expiry
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=name,
                account_key=account_key,
                permission=sas_permissions,
                expiry=expiry_time,
                start=start_time if isinstance(start_time, datetime) else None,
                ip=kwargs.get("ip"),
                content_type=kwargs.get("content_type"),
                content_disposition=kwargs.get("content_disposition"),
                content_encoding=kwargs.get("content_encoding"),
                content_language=kwargs.get("content_language"),
                cache_control=kwargs.get("cache_control"),
            )

            # Construct full URL
            blob_url = (
                f"https://{account_name}.blob.core.windows.net/{container}/{name}"
            )
            sas_url = f"{blob_url}?{sas_token}"

            result = {
                "sas_token": sas_token,
                "sas_url": sas_url,
                "blob_url": blob_url,
                "permissions": permissions,
                "expiry": expiry_time.isoformat(),
                "container": container,
                "blob_name": name,
            }

            if isinstance(start_time, datetime):
                result["start_time"] = start_time.isoformat()

            return result

        except (ContainerNotFoundError, BlobNotFoundError, InvalidConfigurationError):
            raise

    @ErrorHandler.handle_service_errors("generate container SAS token")
    async def generate_container_sas_token(
        self, container: str, permissions: List[str], expiry: timedelta, **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a SAS token for a container with given permissions and expiry.

        Args:
            container: Container name
            permissions: List of permissions ('read', 'write', 'delete', 'list', 'add', 'create')
            expiry: Token expiry duration from now
            **kwargs: Optional parameters:
                - start_time: When the token becomes valid (default: now)
                - ip: IP address or range to restrict access

        Returns:
            Dictionary containing:
                - sas_token: The SAS token string
                - sas_url: Full container URL with SAS token
                - permissions: List of granted permissions
                - expiry: Token expiry datetime
                - start_time: Token start datetime (if specified)

        Raises:
            ContainerNotFoundError: If container doesn't exist
            BlobStorageError: If SAS token generation fails
            InvalidConfigurationError: If account key is not available
        """
        try:
            # Validate inputs
            ValidationHelper.validate_container_name(container)
            ValidationHelper.validate_sas_permissions(permissions, "container")

            # Validate container exists
            await ErrorHandler.check_container_exists(self._client, container)

            # Get account credentials
            account_name, account_key = ValidationHelper.validate_account_key_available(
                self._client
            )

            # Create permissions object using keyword arguments
            permission_kwargs = {perm: True for perm in permissions}
            sas_permissions = ContainerSasPermissions(**permission_kwargs)

            # Calculate expiry time
            start_time = kwargs.get("start_time", datetime.now(timezone.utc))
            expiry_time = (
                start_time + expiry
                if isinstance(start_time, datetime)
                else datetime.now(timezone.utc) + expiry
            )

            # Generate SAS token
            sas_token = generate_container_sas(
                account_name=account_name,
                container_name=container,
                account_key=account_key,
                permission=sas_permissions,
                expiry=expiry_time,
                start=start_time if isinstance(start_time, datetime) else None,
                ip=kwargs.get("ip"),
            )

            # Construct full URL
            container_url = f"https://{account_name}.blob.core.windows.net/{container}"
            sas_url = f"{container_url}?{sas_token}"

            result = {
                "sas_token": sas_token,
                "sas_url": sas_url,
                "container_url": container_url,
                "permissions": permissions,
                "expiry": expiry_time.isoformat(),
                "container": container,
            }

            if isinstance(start_time, datetime):
                result["start_time"] = start_time.isoformat()

            return result

        except (ContainerNotFoundError, InvalidConfigurationError):
            raise
