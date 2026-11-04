"""
S3 client creation and configuration utilities.

This module provides functions to create and configure boto3 S3 clients
for Apache Ozone S3-compatible storage.
"""

import boto3
from botocore.config import Config
from beartype.typing import Dict, Any, Optional
from botocore.exceptions import BotoCoreError, ClientError


class S3ConfigurationError(Exception):
    """Raised when S3 configuration is invalid."""

    pass


# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

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

        if not access_key_id or not secret_access_key:
            _get_logger().error(
                "Missing S3 credentials in configuration",
                has_access_key=bool(access_key_id),
                has_secret_key=bool(secret_access_key),
            )
            raise S3ConfigurationError(
                "S3 credentials (s3_access_key_id and s3_secret_access_key) are required"
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
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
            "region_name": region,
            "use_ssl": use_ssl,
            "verify": verify,
            "config": boto_config,
        }

        # Log client creation
        _get_logger().info(
            f"Creating S3 client {'with custom endpoint' if endpoint_url else 'for AWS'}",
            endpoint_url=endpoint_url,
            region=region,
            use_ssl=use_ssl,
        )

        # Create the S3 client
        s3_client = boto3.client(**client_params)

        # Test connection with a simple operation
        try:
            s3_client.list_buckets()
            _get_logger().info("S3 client created and connection verified successfully")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                _get_logger().error(
                    "S3 authentication failed", error_code=error_code, error=str(e)
                )
                raise S3ConfigurationError(
                    f"Invalid S3 credentials: {e.response.get('Error', {}).get('Message', str(e))}"
                )
            else:
                # Other errors might not prevent basic operations
                _get_logger().warning(
                    "S3 client created but connection test failed",
                    error_code=error_code,
                    error=str(e),
                )

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
