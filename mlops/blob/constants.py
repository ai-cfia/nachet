"""Container names copied from backend service constants for the copied manager."""

from enum import Enum


class Bucket(str, Enum):
    """
    Azure Blob Storage container names.

    Uses str inheritance for easy string comparison and serialization.
    """

    # Production containers
    ORIGINAL = "original"
    SANITIZED = "sanitized"
    SPLIT = "split"
    MODEL = "model"
    FRONTEND = "frontend"
    ANNOTATION = "annotation"
    ORIGINAL_METADATA = "original-metadata"

    # Test containers (used in non-production environments)
    ORIGINAL_TEST = "original-test"
    SANITIZED_TEST = "sanitized-test"

    @classmethod
    def get_original_container(cls, is_test: bool = False) -> str:
        """Get the appropriate original container based on environment."""
        return cls.ORIGINAL_TEST if is_test else cls.ORIGINAL

    @classmethod
    def get_sanitized_container(cls, is_test: bool = False) -> str:
        """Get the appropriate sanitized container based on environment."""
        return cls.SANITIZED_TEST if is_test else cls.SANITIZED
