"""
Service-layer constants.

These constants are used for business logic authorization checks.
Role names are generic across all organizations.
"""

from uuid import UUID
from enum import Enum

# Generic role name constants (used across all organizations)
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_VERIFIER = "verifier"  # CFIA-specific role (other orgs don't have this)

MAX_BINARY_SIZE = 10 * 1024 * 1024  # 10MB
MAX_BASE64_LENGTH = int(MAX_BINARY_SIZE * 4 / 3)


def get_cfia_org_id() -> UUID:
    """
    Get CFIA organization ID from config.

    This ID is used to determine if a user has cross-organization authority.
    CFIA admins (users with "admin" role in CFIA org) can access all org data.

    Returns:
        UUID of CFIA organization

    Raises:
        ValueError: If CFIA_ORGANIZATION_ID not configured
    """
    # Lazy import to avoid circular dependency
    from app.api.config import get_settings

    settings = get_settings()
    if not settings.cfia_organization_id:
        raise ValueError(
            "CFIA_ORGANIZATION_ID not configured in environment. "
            "This is required to determine cross-organization authority."
        )
    return UUID(settings.cfia_organization_id)


def get_cfia_admin_role_id() -> UUID:
    """
    Get CFIA admin role ID from config.

    This is the UUID of the "admin" role in the CFIA organization.
    Used for efficient direct database lookups in rbac_user_role table.

    Returns:
        UUID of CFIA admin role

    Raises:
        ValueError: If CFIA_ADMIN_ROLE_ID not configured
    """
    # Lazy import to avoid circular dependency
    from app.api.config import get_settings

    settings = get_settings()
    if not settings.cfia_admin_role_id:
        raise ValueError(
            "CFIA_ADMIN_ROLE_ID not configured in environment. "
            "This is required for CFIA administrator verification."
        )
    return UUID(settings.cfia_admin_role_id)


class Bucket(str, Enum):
    """
    Azure Blob Storage container names.

    Uses str inheritance for easy string comparison and serialization.
    """

    # Production containers
    ORIGINAL = "nachet-original"
    SANITIZED = "nachet-sanitized"
    SPLIT = "nachet-split"
    MODEL = "nachet-model"
    FRONTEND = "nachet-frontend"
    ANNOTATION = "nachet-annotation"
    ORIGINAL_METADATA = "nachet-original-metadata"

    # Test containers (used in non-production environments)
    ORIGINAL_TEST = "nachet-original-test"
    SANITIZED_TEST = "nachet-sanitized-test"

    @classmethod
    def get_original_container(cls, is_test: bool = False) -> str:
        """Get the appropriate original container based on environment."""
        return cls.ORIGINAL_TEST if is_test else cls.ORIGINAL

    @classmethod
    def get_sanitized_container(cls, is_test: bool = False) -> str:
        """Get the appropriate sanitized container based on environment."""
        return cls.SANITIZED_TEST if is_test else cls.SANITIZED


class ProcessingStatus(str, Enum):
    """
    Image processing pipeline status values (MVP: upload → scan → sanitize).

    Note: Does NOT include inference statuses, as inference is tracked separately
    and can happen multiple times per image with different models.
    """

    PENDING = "pending"
    UPLOADED = "uploaded"
    DEFENDER_SCANNING = "defender_scanning"
    DEFENDER_SCANNED = "defender_scanned"
    SANITIZING = "sanitizing"
    SANITIZED = "sanitized"
    COMPLETED = "completed"  # Upload → Scan → Sanitize complete
    FAILED = "failed"
    CANCELLED = "cancelled"
