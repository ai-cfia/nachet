"""
Custom exception classes for user-related database operations.
"""


class UserCreationError(Exception):
    """Raised when user creation fails."""

    pass


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""

    pass


class ContainerNotSetError(Exception):
    """Raised when a user's container URL is not set."""

    pass


class SecurityValidationError(Exception):
    """Raised when input validation fails for security reasons."""

    pass
