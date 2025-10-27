from uuid import UUID
from typing import Type, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists
from sqlalchemy.orm import selectinload
from app.db.model import (
    Users,
    RbacUserRole,
    RbacRole,
    RbacResource,
    RbacPermission,
    RbacRolePermissionResource,
)
from app.datastore.base_crud import BaseCRUDDataService


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
        return bool(result.scalar())


# ============================================================================
# CRUD DataServices for RBAC entities
# ============================================================================


class RbacRoleDataService(BaseCRUDDataService[RbacRole]):
    """Data access layer for RbacRole CRUD operations."""

    @classmethod
    def get_model_class(cls) -> Type[RbacRole]:
        """Return the RbacRole model class."""
        return RbacRole

    def get_query_options(self) -> list:
        """Load organization, user_roles, and role_permission_resources relationships."""
        return [
            selectinload(RbacRole.organization),
            selectinload(RbacRole.user_roles),
            selectinload(RbacRole.role_permission_resources),
        ]


class RbacPermissionDataService(BaseCRUDDataService[RbacPermission]):
    """Data access layer for RbacPermission CRUD operations."""

    @classmethod
    def get_model_class(cls) -> Type[RbacPermission]:
        """Return the RbacPermission model class."""
        return RbacPermission

    def get_query_options(self) -> list:
        """Load role_permission_resources relationship."""
        return [selectinload(RbacPermission.role_permission_resources)]


class RbacResourceDataService(BaseCRUDDataService[RbacResource]):
    """Data access layer for RbacResource CRUD operations."""

    @classmethod
    def get_model_class(cls) -> Type[RbacResource]:
        """Return the RbacResource model class."""
        return RbacResource

    def get_query_options(self) -> list:
        """Load role_permission_resources relationship."""
        return [selectinload(RbacResource.role_permission_resources)]


class RbacRolePermissionResourceDataService(
    BaseCRUDDataService[RbacRolePermissionResource]
):
    """
    Data access layer for RbacRolePermissionResource CRUD operations.

    NOTE: This is a junction table with composite primary key
    (role_id, permission_id, resource_id). Standard get_by_id()
    may not be applicable - use custom composite key methods instead.
    """

    @classmethod
    def get_model_class(cls) -> Type[RbacRolePermissionResource]:
        """Return the RbacRolePermissionResource model class."""
        return RbacRolePermissionResource

    def get_query_options(self) -> list:
        """Load role, permission, and resource relationships."""
        return [
            selectinload(RbacRolePermissionResource.role),
            selectinload(RbacRolePermissionResource.permission),
            selectinload(RbacRolePermissionResource.resource),
        ]

    async def get_by_composite_key(
        self, role_id: UUID, permission_id: UUID, resource_id: UUID
    ) -> Optional[RbacRolePermissionResource]:
        """
        Get a role-permission-resource mapping by composite key.

        Args:
            role_id: The role UUID
            permission_id: The permission UUID
            resource_id: The resource UUID

        Returns:
            RbacRolePermissionResource if found, None otherwise
        """
        stmt = (
            select(RbacRolePermissionResource)
            .options(*self.get_query_options())
            .where(
                RbacRolePermissionResource.role_id == role_id,
                RbacRolePermissionResource.permission_id == permission_id,
                RbacRolePermissionResource.resource_id == resource_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_composite_key(
        self, role_id: UUID, permission_id: UUID, resource_id: UUID
    ) -> bool:
        """
        Delete a role-permission-resource mapping by composite key.

        Args:
            role_id: The role UUID
            permission_id: The permission UUID
            resource_id: The resource UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_composite_key(role_id, permission_id, resource_id)
        if entity:
            await self.session.delete(entity)
            return True
        return False


class RbacUserRoleDataService(BaseCRUDDataService[RbacUserRole]):
    """
    Data access layer for RbacUserRole CRUD operations.

    NOTE: This is a junction table with composite primary key
    (user_id, role_id). Standard get_by_id() may not be applicable -
    use custom composite key methods instead.
    """

    @classmethod
    def get_model_class(cls) -> Type[RbacUserRole]:
        """Return the RbacUserRole model class."""
        return RbacUserRole

    def get_query_options(self) -> list:
        """Load user and role relationships."""
        return [
            selectinload(RbacUserRole.user),
            selectinload(RbacUserRole.role),
        ]

    async def get_by_composite_key(
        self, user_id: UUID, role_id: UUID
    ) -> Optional[RbacUserRole]:
        """
        Get a user-role mapping by composite key.

        Args:
            user_id: The user UUID
            role_id: The role UUID

        Returns:
            RbacUserRole if found, None otherwise
        """
        stmt = (
            select(RbacUserRole)
            .options(*self.get_query_options())
            .where(
                RbacUserRole.user_id == user_id,
                RbacUserRole.role_id == role_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_composite_key(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Delete a user-role mapping by composite key (soft delete via active flag).

        Args:
            user_id: The user UUID
            role_id: The role UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_composite_key(user_id, role_id)
        if entity:
            entity.active = False
            return True
        return False
