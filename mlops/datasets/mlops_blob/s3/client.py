"""
S3 client creation and configuration utilities.

This module provides functions to create and configure boto3 S3 clients
for Apache Ozone S3-compatible storage.
"""

import boto3
from beartype.typing import Any, Dict, Optional
from botocore.config import Config
from botocore.exceptions import BotoCoreError


class S3ConfigurationError(Exception):
    """Raised when S3 configuration is invalid."""

    pass


# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from mlops_blob.logging import LogService

        _logger = LogService.get_logger()
    return _logger


def create_s3_client(config: Dict[str, Any]):
    """
    Create a boto3 S3 client for Apache Ozone or AWS S3.

    Parameters:
        config: Configuration dictionary containing:
            - s3_access_key_id: AWS access key ID
            - s3_secret_access_key: AWS secret access key
            - s3_region_name: AWS region (default: us-east-1)
            - s3_endpoint_url: Custom endpoint URL for S3-compatible services like Ozone
            - s3_use_ssl: Whether to use SSL (default: True for https endpoints)
            - s3_verify: Whether to verify SSL certificates (default: True)
            - s3_connect_timeout: Connection timeout in seconds (default: 5)
            - s3_read_timeout: Read timeout in seconds (default: 10)

    Returns:
        boto3 S3 client instance

    Raises:
        S3ConfigurationError: If required configuration is missing or invalid
        Exception: For unhandled exceptions during client creation
    """
    try:
        # Extract and validate credentials
        access_key_id = config.get("s3_access_key")
        secret_access_key = config.get("s3_secret_key")

        if bool(access_key_id) != bool(secret_access_key):
            _get_logger().error(
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

        _get_logger().info(
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
        _get_logger().error(
            "BotoCoreError during S3 client creation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise S3ConfigurationError(
            f"Failed to create S3 client due to configuration error: {str(e)}"
        )
    except Exception as e:
        _get_logger().error(
            "Unhandled exception in S3 client creation",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise Exception(f"S3 client creation failed: {str(e)}")


def validate_s3_connection(s3_client) -> bool:
    """
    Validate S3 connection by attempting to list buckets.

    Parameters:
        s3_client: boto3 S3 client instance

    Returns:
        True if connection is valid, False otherwise
    """
    try:
        s3_client.list_buckets()
        return True
    except Exception as e:
        _get_logger().error(
            "S3 connection validation failed", error=str(e), error_type=type(e).__name__
        )
        return False


def get_s3_endpoint_url(config: Dict[str, Any]) -> Optional[str]:
    """
    Extract S3 endpoint URL from configuration.

    Parameters:
        config: Configuration dictionary

    Returns:
        Endpoint URL string or None if using AWS S3
    """
    return config.get("s3_endpoint_url")
