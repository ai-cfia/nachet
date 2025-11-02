"""
Error Sanitization Utility

This module provides utilities to sanitize error messages before exposing them
to external users via HTTP responses. This prevents information leakage through
exception stack traces, database errors, file paths, and other internal details.

Security Context:
- Addresses CWE-209 (Information Exposure Through an Error Message)
- Addresses CWE-497 (Exposure of Sensitive System Information)
- Part of fix for CodeQL Alert #71

Usage:
    from app.service.error_sanitizer import sanitize_error_for_user

    try:
        # Some operation that might fail
        result = risky_operation()
    except Exception as e:
        logger.error(f"Detailed error for debugging: {str(e)}", exc_info=True)
        safe_message = sanitize_error_for_user(e, context="operation_name")
        raise HTTPException(status_code=500, detail=safe_message)
"""

from typing import Any, Optional
from app.exceptions import (
    InvalidImageError,
    SeedNotFoundError,
    UserNotFoundError,
)
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound
from azure.core.exceptions import AzureError, ResourceNotFoundError


# Generic fallback messages for different contexts
GENERIC_MESSAGES = {
    "batch_upload": "Failed to process image upload. Please verify your image and try again.",
    "session_init": "Failed to initialize upload session. Please try again.",
    "organization": "Failed to process organization request. Please contact support.",
    "pipeline": "Failed to retrieve pipeline information. Please try again later.",
    "model": "Failed to retrieve model information. Please try again later.",
    "frontend": "Failed to retrieve resource. Please try again later.",
    "inference": "Failed to process inference request. Please try again.",
    "workflow": "Failed to retrieve workflow information. Please try again.",
    "database": "Failed to process database request. Please try again.",
    "default": "An internal error occurred. Please try again or contact support.",
}


# Mapping of exception types to user-safe messages
EXCEPTION_MESSAGE_MAP = {
    # Custom application exceptions
    InvalidImageError: "Invalid image format or corrupted image data. Please verify your image file.",
    SeedNotFoundError: "Seed record not found. Please verify the seed ID.",
    UserNotFoundError: "User not found. Please verify authentication.",
    # Database exceptions
    IntegrityError: "Database constraint violation. Please check your input data.",
    NoResultFound: "Requested resource not found.",
    # Azure exceptions
    ResourceNotFoundError: "Requested resource not found in storage.",
}


def sanitize_error_for_user(
    exception: Exception, context: str = "default", custom_message: Optional[str] = None
) -> str:
    """
    Sanitize an exception for safe exposure to external users.

    This function converts detailed internal exceptions into user-friendly
    messages that don't reveal implementation details, database schemas,
    file paths, or other sensitive information.

    Args:
        exception: The exception that was raised
        context: The context where the error occurred (e.g., "batch_upload", "pipeline")
        custom_message: Optional custom message to return instead of the default

    Returns:
        A sanitized, user-friendly error message safe for external exposure

    Examples:
        >>> try:
        ...     raise InvalidImageError("PIL cannot decode image at /internal/path/image.png")
        ... except Exception as e:
        ...     sanitize_error_for_user(e, "batch_upload")
        'Invalid image format or corrupted image data. Please verify your image file.'

        >>> try:
        ...     raise ValueError("Database column 'internal_field' violates constraint")
        ... except Exception as e:
        ...     sanitize_error_for_user(e, "database")
        'Failed to process database request. Please try again.'
    """
    # If a custom message is provided, use it
    if custom_message:
        return custom_message

    # Check if we have a specific mapping for this exception type
    exception_type = type(exception)
    if exception_type in EXCEPTION_MESSAGE_MAP:
        return EXCEPTION_MESSAGE_MAP[exception_type]

    # Check parent classes (e.g., SQLAlchemyError for database errors)
    if isinstance(exception, SQLAlchemyError):
        return GENERIC_MESSAGES.get("database", GENERIC_MESSAGES["default"])

    if isinstance(exception, AzureError):
        return "Failed to access cloud storage. Please try again later."

    # Fallback to context-specific generic message
    return GENERIC_MESSAGES.get(context, GENERIC_MESSAGES["default"])


def sanitize_error_dict(
    exception: Exception, context: str = "default", custom_message: Optional[str] = None
) -> dict[str, Any]:
    """
    Convenience function to return a sanitized error in dictionary format.

    This is useful for service methods that return result dictionaries
    instead of raising exceptions directly.

    Args:
        exception: The exception that was raised
        context: The context where the error occurred
        custom_message: Optional custom message to return instead of the default

    Returns:
        A dictionary with success=False and a sanitized error message

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     logger.error(f"Operation failed: {str(e)}", exc_info=True)
        ...     return sanitize_error_dict(e, "batch_upload")
        {'success': False, 'error': 'Failed to process image upload...'}
    """
    return {
        "success": False,
        "error": sanitize_error_for_user(exception, context, custom_message),
    }
