"""
RBAC constants for all deployment environments.

This module contains the Role-Based Access Control constants that should exist
in all deployment environments: roles, permissions, resources (routes), and their mappings.
"""

import uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.model import RbacRole, RbacPermission, RbacResource, RbacRolePermissionResource


# Fixed UUIDs for RBAC constants (consistent across all environments)
PERMISSION_ALLOW_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")

# Role IDs - these will be per organization
ROLE_CFIA_ADMIN = "cfia_admin"
ROLE_CFIA_USER = "cfia_user"
ROLE_CFIA_VERIFIER = "cfia_verifier"
ROLE_EXTERNAL_USER = "external_user"
ROLE_EXTERNAL_ADMIN = "external_admin"

# Resource IDs (routes)
RESOURCE_GET_HEALTH_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
RESOURCE_GET_VERSION_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
RESOURCE_GET_READY_ID = uuid.UUID("20000000-0000-0000-0000-000000000003")
RESOURCE_POST_GET_USER_ID_ID = uuid.UUID("20000000-0000-0000-0000-000000000004")
RESOURCE_GET_PIPELINES_ID = uuid.UUID("20000000-0000-0000-0000-000000000005")
RESOURCE_GET_MODEL_ENDPOINTS_ID = uuid.UUID("20000000-0000-0000-0000-000000000006")
RESOURCE_GET_SEEDS_ID = uuid.UUID("20000000-0000-0000-0000-000000000007")
RESOURCE_GET_DIRECTORIES_ID = uuid.UUID("20000000-0000-0000-0000-000000000008")


async def seed_rbac_permission(session: AsyncSession) -> None:
    """
    Seed the 'allow' permission used for route access control.

    This permission represents basic access rights to routes/resources.
    """
    allow_permission = RbacPermission(
        id=PERMISSION_ALLOW_ID,
        name="allow",
        description="Permission to access a route/resource",
        active=True,
    )
    session.add(allow_permission)


async def seed_rbac_resources(session: AsyncSession) -> None:
    """
    Seed all route resources.

    Routes are stored as resources with names like "GET_/pipelines".
    """
    resources = [
        RbacResource(
            id=RESOURCE_GET_HEALTH_ID,
            name="GET_/health",
            description="Health check endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_VERSION_ID,
            name="GET_/version",
            description="Version information endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_READY_ID,
            name="GET_/ready",
            description="Readiness check endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_POST_GET_USER_ID_ID,
            name="POST_/get-user-id",
            description="Get user ID endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_PIPELINES_ID,
            name="GET_/pipelines",
            description="Get pipelines endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_MODEL_ENDPOINTS_ID,
            name="GET_/model-endpoints-metadata",
            description="Get model endpoints metadata",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_SEEDS_ID,
            name="GET_/seeds",
            description="Get seeds data endpoint",
            active=True,
        ),
        RbacResource(
            id=RESOURCE_GET_DIRECTORIES_ID,
            name="GET_/get-directories",
            description="Get directories endpoint",
            active=True,
        ),
    ]
    session.add_all(resources)


async def seed_rbac_roles(session: AsyncSession, organization_id: UUID) -> dict:
    """
    Seed the 5 standard RBAC roles for an organization.

    Args:
        session: Database session
        organization_id: The organization UUID to associate roles with

    Returns:
        Dictionary mapping role names to their UUIDs
    """
    # Generate deterministic UUIDs based on organization_id and role name
    # This ensures consistent IDs across environments for the same organization
    role_ids = {
        ROLE_CFIA_ADMIN: uuid.uuid5(organization_id, ROLE_CFIA_ADMIN),
        ROLE_CFIA_USER: uuid.uuid5(organization_id, ROLE_CFIA_USER),
        ROLE_CFIA_VERIFIER: uuid.uuid5(organization_id, ROLE_CFIA_VERIFIER),
        ROLE_EXTERNAL_USER: uuid.uuid5(organization_id, ROLE_EXTERNAL_USER),
        ROLE_EXTERNAL_ADMIN: uuid.uuid5(organization_id, ROLE_EXTERNAL_ADMIN),
    }

    roles = [
        RbacRole(
            id=role_ids[ROLE_CFIA_ADMIN],
            organization_id=organization_id,
            name=ROLE_CFIA_ADMIN,
            description="CFIA Administrator with full system access",
            active=True,
        ),
        RbacRole(
            id=role_ids[ROLE_CFIA_USER],
            organization_id=organization_id,
            name=ROLE_CFIA_USER,
            description="CFIA User with standard access",
            active=True,
        ),
        RbacRole(
            id=role_ids[ROLE_CFIA_VERIFIER],
            organization_id=organization_id,
            name=ROLE_CFIA_VERIFIER,
            description="CFIA Verifier for data verification tasks",
            active=True,
        ),
        RbacRole(
            id=role_ids[ROLE_EXTERNAL_USER],
            organization_id=organization_id,
            name=ROLE_EXTERNAL_USER,
            description="External User with limited access",
            active=True,
        ),
        RbacRole(
            id=role_ids[ROLE_EXTERNAL_ADMIN],
            organization_id=organization_id,
            name=ROLE_EXTERNAL_ADMIN,
            description="External Administrator for external organization",
            active=True,
        ),
    ]
    session.add_all(roles)
    return role_ids


async def seed_rbac_route_policies(
    session: AsyncSession, organization_id: UUID, role_ids: dict
) -> None:
    """
    Seed role-permission-resource mappings for route access policies.

    This implements the route authorization policies:
    - Public routes: /health, /version, /ready, /get-user-id (no role required, handled in code)
    - Protected routes: /pipelines, /model-endpoints-metadata, /seeds, /get-directories
      (require any of the 5 roles)

    Args:
        session: Database session
        organization_id: The organization UUID
        role_ids: Dictionary mapping role names to their UUIDs
    """
    # Define which resources require which roles
    # Public routes (None in ROUTE_POLICIES) don't get mappings - they're open to authenticated users
    # Protected routes get mappings for all 5 roles

    protected_resources = [
        RESOURCE_GET_PIPELINES_ID,
        RESOURCE_GET_MODEL_ENDPOINTS_ID,
        RESOURCE_GET_SEEDS_ID,
        RESOURCE_GET_DIRECTORIES_ID,
    ]

    all_roles = [
        ROLE_CFIA_ADMIN,
        ROLE_CFIA_USER,
        ROLE_CFIA_VERIFIER,
        ROLE_EXTERNAL_USER,
        ROLE_EXTERNAL_ADMIN,
    ]

    mappings = []
    for resource_id in protected_resources:
        for role_name in all_roles:
            mapping = RbacRolePermissionResource(
                role_id=role_ids[role_name],
                permission_id=PERMISSION_ALLOW_ID,
                resource_id=resource_id,
                active=True,
            )
            mappings.append(mapping)

    session.add_all(mappings)


async def seed_rbac_constants(session: AsyncSession, organization_id: UUID) -> None:
    """
    Seed all RBAC constants for an organization.

    This is the main entry point for seeding RBAC data in any environment.
    Call this function with the appropriate organization_id for your environment.

    Args:
        session: Database session
        organization_id: The organization UUID to create roles for
    """
    # Seed permission (organization-independent)
    await seed_rbac_permission(session)

    # Seed resources (routes, organization-independent)
    await seed_rbac_resources(session)

    # Seed roles (organization-specific)
    role_ids = await seed_rbac_roles(session, organization_id)

    # Seed route policies (role-resource mappings)
    await seed_rbac_route_policies(session, organization_id, role_ids)
