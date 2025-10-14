"""
Service-layer constants.

These constants are used for business logic authorization checks.
Role names are generic across all organizations.
"""

from uuid import UUID
from app.api.config import get_settings

# Generic role name constants (used across all organizations)
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_VERIFIER = "verifier"  # CFIA-specific role (other orgs don't have this)


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
    settings = get_settings()
    if not settings.cfia_organization_id:
        raise ValueError(
            "CFIA_ORGANIZATION_ID not configured in environment. "
            "This is required to determine cross-organization authority."
        )
    return UUID(settings.cfia_organization_id)
