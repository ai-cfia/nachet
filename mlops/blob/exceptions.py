"""
Custom exceptions for the blob storage module.

This module defines all the custom exceptions used throughout the blob storage
interface, providing clear error categorization and handling.
"""

from beartype.typing import Optional, Dict, Any


class BlobStorageError(Exception):
    """Base exception for all blob storage errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BlobNotFoundError(BlobStorageError):
    """Raised when a requested blob does not exist."""

    def __init__(
        self, container: str, blob_name: str, details: Optional[Dict[str, Any]] = None
    ):
        self.container = container
        self.blob_name = blob_name
        message = f"Blob '{blob_name}' not found in container '{container}'"
        super().__init__(message, details)


class ContainerNotFoundError(BlobStorageError):
    """Raised when a requested container does not exist."""

    def __init__(self, container_name: str, details: Optional[Dict[str, Any]] = None):
        self.container_name = container_name
        message = f"Container '{container_name}' not found"
        super().__init__(message, details)


class BlobAlreadyExistsError(BlobStorageError):
    """Raised when trying to create a blob that already exists and overwrite is disabled."""

    def __init__(
        self, container: str, blob_name: str, details: Optional[Dict[str, Any]] = None
    ):
        self.container = container
        self.blob_name = blob_name
        message = f"Blob '{blob_name}' already exists in container '{container}'"
        super().__init__(message, details)


class ContainerAlreadyExistsError(BlobStorageError):
    """Raised when trying to create a container that already exists."""

    def __init__(self, container_name: str, details: Optional[Dict[str, Any]] = None):
        self.container_name = container_name
        message = f"Container '{container_name}' already exists"
        super().__init__(message, details)


class PermissionError(BlobStorageError):
    """Raised when access is denied due to insufficient permissions."""

    def __init__(
        self, operation: str, resource: str, details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.resource = resource
        message = (
            f"Permission denied for operation '{operation}' on resource '{resource}'"
        )
        super().__init__(message, details)


class ConnectionError(BlobStorageError):
    """Raised when there are network or connection issues."""

    def __init__(
        self,
        message: str = "Connection failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)


class InvalidConfigurationError(BlobStorageError):
    """Raised when the storage configuration is invalid."""

    def __init__(
        self, config_field: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        self.config_field = config_field
        full_message = f"Invalid configuration for '{config_field}': {message}"
        super().__init__(full_message, details)


class ValidationError(BlobStorageError):
    """Raised when data validation fails."""

    def __init__(
        self,
        field: str,
        value: Any,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.value = value
        full_message = f"Validation failed for field '{field}': {message}"
        super().__init__(full_message, details)


class OperationTimeoutError(BlobStorageError):
    """Raised when an operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(message, details)


class QuotaExceededError(BlobStorageError):
    """Raised when storage quota is exceeded."""

    def __init__(
        self, quota_type: str, limit: str, details: Optional[Dict[str, Any]] = None
    ):
        self.quota_type = quota_type
        self.limit = limit
        message = f"Quota exceeded for {quota_type}: {limit}"
        super().__init__(message, details)


class ContentValidationError(BlobStorageError):
    """Raised when blob content validation fails."""

    def __init__(
        self,
        validation_type: str,
        expected: str,
        actual: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.validation_type = validation_type
        self.expected = expected
        self.actual = actual
        message = f"Content validation failed ({validation_type}): expected {expected}, got {actual}"
        super().__init__(message, details)


class UnsupportedOperationError(BlobStorageError):
    """Raised when an operation is not supported by the current provider."""

    def __init__(
        self, operation: str, provider: str, details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.provider = provider
        message = f"Operation '{operation}' is not supported by provider '{provider}'"
        super().__init__(message, details)
