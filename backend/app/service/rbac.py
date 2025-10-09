from uuid import UUID
from fastapi import HTTPException, status, Request
from app.db.utils import sessionmanager
from app.datastore.rbac import RbacDataService


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
