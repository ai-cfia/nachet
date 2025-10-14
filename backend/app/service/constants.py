"""
Service-layer constants.

These constants are used for business logic authorization checks.
Role names are generic across all organizations.
"""

from uuid import UUID

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
