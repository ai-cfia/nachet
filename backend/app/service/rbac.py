from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status, Request
from sqlalchemy import select
from app.db.utils import sessionmanager
from app.db.model import RbacUserRole
from app.datastore import RbacDataService
from app.service.constants import ROLE_ADMIN, get_cfia_admin_role_id


class RbacService:
    """
    Role-Based Access Control service.

    NO CACHING - all checks query database in real-time for security.
    This ensures immediate access revocation and compliance with security best practices.

    Centralized authorization: Routes call authorize_request() and this service
    handles all RBAC logic by querying route permissions from the database.

    Route policies are stored in the database as:
    - Resources: route names like "GET_/pipelines"
    - Permission: "allow" permission for access
    - Mappings: rbac_role_permission_resource linking roles to routes
    """

    @staticmethod
    async def get_user_organization_id(user_id: UUID) -> Optional[UUID]:
        """
        Get the organization ID for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Organization UUID if found, None otherwise

        Raises:
            HTTPException: 403 if user not associated with an organization
        """
        # Lazy import to avoid circular dependency
        from app.datastore import OrganizationDataService
        
        async with sessionmanager.get_session() as session:
            org_id = await OrganizationDataService(session).get_user_organization_id(
                user_id
            )

            if not org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not associated with an organization",
                )

            return org_id

    @staticmethod
    async def verify_user_has_role(
        user_id: UUID, role_name: str, organization_id: Optional[UUID] = None
    ) -> None:
        """
        Verify that a user has a specific role in an organization.

        If organization_id is not provided, it will be looked up from the user's record.

        Args:
            user_id: The user's UUID
            role_name: The role name to verify (e.g., "cfia_admin")
            organization_id: Optional organization UUID (will be looked up if not provided)

        Raises:
            HTTPException: 403 if user doesn't have the role or not associated with org
        """
        # Lazy import to avoid circular dependency
        from app.datastore import OrganizationDataService
        
        async with sessionmanager.get_session() as session:
            # Get organization ID if not provided
            if organization_id is None:
                organization_id = await OrganizationDataService(
                    session
                ).get_user_organization_id(user_id)

                if not organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User not associated with an organization",
                    )

            # Check if user has the role
            has_role = await OrganizationDataService(session).user_has_role(
                user_id, organization_id, role_name
            )

            if not has_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have required role: {role_name}",
                )

    @staticmethod
    async def authorize_request(request: Request, user) -> None:
        """
        Central authorization method - single source of truth for route protection.

        Routes should call this method to check authorization. RBAC logic queries
        the database for route permissions stored as resources.

        Args:
            request: FastAPI Request object (contains method and route path)
            user: Authenticated User object from get_current_user

        Raises:
            HTTPException: 403 Forbidden if user lacks access to the route

        Usage in routes:
            @router.delete("/pictures/{id}")
            async def delete_picture(
                request: Request,
                current_user: User = Depends(get_current_user)
            ):
                await RbacService.authorize_request(request, current_user)
                # ... business logic
        """
        method = request.method

        # Get the route path template (e.g., "/pictures/{id}")
        route = request.scope.get("route")
        if not route:
            # No route found - this shouldn't happen for normal routes
            return

        path_template = route.path

        # Check if user has access to this route via database
        user_id = UUID(user.oid)

        async with sessionmanager.get_session() as session:
            has_access = await RbacDataService(session).user_has_route_access(
                user_id, method, path_template
            )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {method} {path_template}",
            )

    @staticmethod
    async def is_user_cfia_admin(user_id: UUID) -> bool:
        """
        Check if user is CFIA admin (has cross-organization authority).

        Uses direct database lookup in rbac_user_role table with CFIA admin role ID
        for efficient single-query verification.

        Args:
            user_id: The user's UUID

        Returns:
            True if user is CFIA admin, False otherwise
        """
        try:
            cfia_admin_role_id = get_cfia_admin_role_id()

            # Single query: check if user has CFIA admin role
            async with sessionmanager.get_session() as session:
                stmt = select(RbacUserRole).where(
                    RbacUserRole.user_id == user_id,
                    RbacUserRole.role_id == cfia_admin_role_id,
                    RbacUserRole.active == True,  # noqa: E712
                )
                result = await session.execute(stmt)
                user_role = result.scalar_one_or_none()

            return user_role is not None
        except Exception:
            return False

    @staticmethod
    async def verify_user_is_cfia_admin(user_id: UUID) -> None:
        """
        Verify user is CFIA admin (has cross-organization authority).

        CFIA admins have authority to create/update/delete resources across
        all organizations in the system.

        Args:
            user_id: The user's UUID

        Raises:
            HTTPException: 403 if user is not CFIA admin
        """
        if not await RbacService.is_user_cfia_admin(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This operation requires CFIA administrator authority",
            )

    @staticmethod
    async def verify_user_is_org_admin(user_id: UUID) -> UUID:
        """
        Verify user is admin in their organization.

        Unlike CFIA admin, org admins only have authority within their own
        organization's data (org-scoped authority).

        Args:
            user_id: The user's UUID

        Returns:
            UUID of user's organization

        Raises:
            HTTPException: 403 if user is not admin in their org
        """
        user_org_id = await RbacService.get_user_organization_id(user_id)

        # Verify user has "admin" role in their org
        await RbacService.verify_user_has_role(user_id, ROLE_ADMIN, user_org_id)

        return user_org_id
