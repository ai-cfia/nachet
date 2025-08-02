"""
Security functions for user database operations to prevent SQL injection and validate inputs.
"""

import re
import uuid
from typing import Any, Optional


# Import from local exceptions module to avoid circular imports
try:
    from .exceptions import SecurityValidationError
except ImportError:
    # Fallback definition if import fails
    class SecurityValidationError(Exception):
        """Raised when input validation fails for security reasons."""

        pass


def validate_email(email: Any) -> str:
    """
    Validate and sanitize email input to prevent SQL injection.

    Parameters:
    - email: The email input to validate

    Returns:
    - str: The validated email string

    Raises:
    - SecurityValidationError: If email is invalid or potentially malicious
    """
    # Type checking
    if not isinstance(email, str):
        raise SecurityValidationError("Email must be a string")

    # Length validation (prevent excessive input)
    if len(email) > 254:  # RFC 5321 limit
        raise SecurityValidationError("Email address too long")

    if len(email) < 3:  # Minimum reasonable email length
        raise SecurityValidationError("Email address too short")

    # Basic email format validation
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(email):
        raise SecurityValidationError("Invalid email format")

    # Check for suspicious characters that could be used for SQL injection
    suspicious_chars = ["'", '"', ";", "--", "/*", "*/", "\\", "\x00"]
    for char in suspicious_chars:
        if char in email:
            raise SecurityValidationError(
                f"Email contains suspicious character: {char}"
            )

    # Check for SQL keywords (case insensitive)
    sql_keywords = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "UNION",
        "WHERE",
        "ORDER",
        "GROUP",
        "HAVING",
        "EXEC",
        "EXECUTE",
    ]
    email_upper = email.upper()
    for keyword in sql_keywords:
        if keyword in email_upper:
            raise SecurityValidationError(f"Email contains SQL keyword: {keyword}")

    return email.strip().lower()  # Normalize email


def validate_user_id(user_id: Any) -> str:
    """
    Validate and sanitize user ID input to prevent SQL injection.

    Parameters:
    - user_id: The user ID input to validate

    Returns:
    - str: The validated user ID string

    Raises:
    - SecurityValidationError: If user_id is invalid or potentially malicious
    """
    # Type checking
    if not isinstance(user_id, (str, uuid.UUID)):
        raise SecurityValidationError("User ID must be a string or UUID")

    # Convert to string if UUID
    if isinstance(user_id, uuid.UUID):
        user_id = str(user_id)

    # Length validation
    if len(user_id) > 36:  # Standard UUID length
        raise SecurityValidationError("User ID too long")

    if len(user_id) < 36:  # Standard UUID length
        raise SecurityValidationError("User ID too short")

    # UUID format validation
    try:
        uuid_obj = uuid.UUID(user_id)
        validated_id = str(uuid_obj)  # This normalizes the format
    except ValueError:
        raise SecurityValidationError("Invalid UUID format")

    # Check for suspicious characters
    suspicious_chars = ["'", '"', ";", "--", "/*", "*/", "\\", "\x00"]
    for char in suspicious_chars:
        if char in user_id:
            raise SecurityValidationError(
                f"User ID contains suspicious character: {char}"
            )

    return validated_id


def validate_container_url(container_url: Any) -> str:
    """
    Validate and sanitize container URL input to prevent SQL injection.

    Parameters:
    - container_url: The container URL input to validate

    Returns:
    - str: The validated container URL string

    Raises:
    - SecurityValidationError: If container_url is invalid or potentially malicious
    """
    # Type checking
    if not isinstance(container_url, str):
        raise SecurityValidationError("Container URL must be a string")

    # Length validation (prevent excessive input)
    if len(container_url) > 2048:  # Reasonable URL length limit
        raise SecurityValidationError("Container URL too long")

    if len(container_url) < 8:  # Minimum reasonable URL length (https://)
        raise SecurityValidationError("Container URL too short")

    # Basic URL format validation - more permissive for valid URLs
    url_pattern = re.compile(
        r"^https?://[a-zA-Z0-9.-]+(?::[0-9]+)?(?:/[a-zA-Z0-9._~:/?#\[\]@!$&()*+,;=-]*)?$"
    )
    if not url_pattern.match(container_url):
        raise SecurityValidationError("Invalid URL format")

    # Check for suspicious characters that could be used for SQL injection
    suspicious_chars = ["'", '"', ";", "--", "/*", "*/", "\x00"]
    for char in suspicious_chars:
        if char in container_url:
            raise SecurityValidationError(
                f"Container URL contains suspicious character: {char}"
            )

    # Check for SQL keywords (case insensitive)
    sql_keywords = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "UNION",
        "WHERE",
        "ORDER",
        "GROUP",
        "HAVING",
        "EXEC",
        "EXECUTE",
    ]
    url_upper = container_url.upper()
    for keyword in sql_keywords:
        if keyword in url_upper:
            raise SecurityValidationError(
                f"Container URL contains SQL keyword: {keyword}"
            )

    return container_url.strip()


def sanitize_query_log(query: str, params: tuple) -> str:
    """
    Create a safe log entry for SQL queries without exposing sensitive data.

    Parameters:
    - query: The SQL query string
    - params: The query parameters

    Returns:
    - str: A safe log entry
    """
    # Mask sensitive data in parameters
    masked_params = []
    for param in params:
        if isinstance(param, str):
            if "@" in param:  # Likely an email
                masked_params.append("***@***.***")
            elif len(param) == 36 and "-" in param:  # Likely a UUID
                masked_params.append("********-****-****-****-************")
            else:
                masked_params.append("***")
        else:
            masked_params.append("***")

    return f"Query: {query} | Params: {tuple(masked_params)}"
