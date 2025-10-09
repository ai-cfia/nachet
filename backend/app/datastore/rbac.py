from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from app.db.model import (
    Users,
    RbacUserRole,
    RbacRole,
    RbacResource,
    RbacPermission,
    RbacRolePermissionResource,
)


class RbacDataService:
    """Data access layer for Role-Based Access Control operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def user_has_route_access(
        self, user_id: UUID, method: str, path: str
    ) -> bool:
        """
        Check if user has access to a specific route.

        Routes are stored as resources with names like "GET_/pipelines".
        Checks if the user has any role with "allow" permission for the route resource.

        Args:
            user_id: The user's UUID
            method: HTTP method (e.g., "GET", "POST", "DELETE")
            path: Route path (e.g., "/pipelines", "/pictures/{id}")

        Returns:
            True if user has access to the route, False otherwise
        """
        resource_name = f"{method}_{path}"

        stmt = select(
            exists(
                select(1)
                .select_from(Users)
                .join(RbacUserRole, Users.id == RbacUserRole.user_id)
                .join(RbacRole, RbacUserRole.role_id == RbacRole.id)
                .join(
                    RbacRolePermissionResource,
                    RbacRole.id == RbacRolePermissionResource.role_id,
                )
                .join(
                    RbacResource,
                    RbacRolePermissionResource.resource_id == RbacResource.id,
                )
                .join(
                    RbacPermission,
                    RbacRolePermissionResource.permission_id == RbacPermission.id,
                )
                .where(Users.id == user_id)
                .where(RbacResource.name == resource_name)
                .where(RbacPermission.name == "allow")
                .where(Users.active.is_(True))
                .where(RbacUserRole.active.is_(True))
                .where(RbacRole.active.is_(True))
                .where(RbacRolePermissionResource.active.is_(True))
                .where(RbacResource.active.is_(True))
                .where(RbacPermission.active.is_(True))
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()
