"""
Utility functions for blob storage tests.

This module provides helper functions for test configuration and output sanitization
to prevent secrets from leaking into test logs.
"""

from typing import Dict, Any


def sanitize_config_for_display(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive values from config for safe display in test output.

    This function creates a copy of the configuration dictionary and redacts
    any sensitive credential fields to prevent secrets from appearing in logs.

    Args:
        config: Configuration dictionary that may contain sensitive data

    Returns:
        Dictionary with sensitive values replaced by '***REDACTED***'
    """
    safe_config = config.copy()

    # List of sensitive keys that should be redacted
    sensitive_keys = [
        "blob_storage_key",
        "s3_secret_key",
        "s3_access_key",
        "s3_secret_access_key",
        "s3_access_key_id",
        "account_key",
        "secret_access_key",
        "access_key_id",
        "connection_string",
        "password",
        "secret",
        "token",
    ]

    for key in sensitive_keys:
        if key in safe_config:
            safe_config[key] = "***REDACTED***"

    return safe_config


def sanitize_connection_string(connection_string: str) -> str:
    """
    Sanitize Azure connection string for safe display.

    Removes sensitive credential portions while keeping structure visible
    for debugging purposes.

    Args:
        connection_string: Azure storage connection string

    Returns:
        Sanitized connection string with credentials redacted
    """
    if not connection_string:
        return ""

    # Replace AccountKey value with redacted placeholder
    parts = connection_string.split(";")
    sanitized_parts = []

    for part in parts:
        if "AccountKey=" in part:
            sanitized_parts.append("AccountKey=***REDACTED***")
        else:
            sanitized_parts.append(part)

    return ";".join(sanitized_parts)
