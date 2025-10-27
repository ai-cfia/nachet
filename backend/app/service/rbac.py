from uuid import UUID
from beartype.typing import Optional, Dict, Any, cast
from dataclasses import dataclass
from fastapi import HTTPException, status, Request
from sqlalchemy import select
from app.db.utils import sessionmanager
from app.db.model import (
    RbacUserRole,
    RbacRole,
    RbacPermission,
    RbacResource,
    RbacRolePermissionResource,
)
from app.datastore import RbacDataService
from app.datastore.rbac import (
    RbacRoleDataService,
    RbacPermissionDataService,
    RbacResourceDataService,
    RbacRolePermissionResourceDataService,
    RbacUserRoleDataService,
)
from app.service.constants import ROLE_ADMIN, get_cfia_admin_role_id
from app.service.base_crud import BaseCRUDService
from app.exceptions import (
    RbacRoleNotFoundError,
    RbacRoleCreationError,
    RbacRoleUpdateError,
    RbacRoleDeletionError,
    RbacPermissionNotFoundError,
    RbacPermissionCreationError,
    RbacPermissionUpdateError,
    RbacPermissionDeletionError,
    RbacResourceNotFoundError,
    RbacResourceCreationError,
    RbacResourceUpdateError,
    RbacResourceDeletionError,
    RbacRolePermissionResourceNotFoundError,
    RbacRolePermissionResourceCreationError,
    RbacRolePermissionResourceUpdateError,
    RbacRolePermissionResourceDeletionError,
    RbacUserRoleNotFoundError,
    RbacUserRoleCreationError,
    RbacUserRoleUpdateError,
    RbacUserRoleDeletionError,
)


@dataclass
class UserOrgRoles:
    """
    Container for user's organization and role information.

    Attributes:
        org_id: Organization UUID
        org_prefix: Organization folder prefix (e.g., "/cfia/")
        org_admin_role_id: Admin role UUID for the organization
        org_user_role_id: User role UUID for the organization
    """

    org_id: UUID
    org_prefix: str
    org_admin_role_id: UUID
    org_user_role_id: UUID


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
    async def get_org_admin_role_id(organization_id: UUID) -> UUID:
        """
        Get the admin role ID for an organization.

        Args:
            organization_id: The organization's UUID

        Returns:
            UUID of the admin role for the organization

        Raises:
            HTTPException: 500 if organization admin role not found
        """
        async with sessionmanager.get_session() as session:
            stmt = select(RbacRole).where(
                RbacRole.organization_id == organization_id,
                RbacRole.name == "admin",
                RbacRole.active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            org_admin_role = result.scalar_one_or_none()

            if not org_admin_role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization admin role not found",
                )

            return cast(UUID, org_admin_role.id)

    @staticmethod
    async def get_user_org_roles(user_id: UUID) -> UserOrgRoles:
        """
        Get organization ID, prefix, admin role ID, and user role ID in a single database call.

        This is an optimized method that retrieves all four values with one query,
        reducing database round-trips.

        Args:
            user_id: The user's UUID

        Returns:
            UserOrgRoles dataclass containing:
                - org_id: Organization UUID
                - org_prefix: Organization folder prefix
                - org_admin_role_id: Admin role UUID
                - org_user_role_id: User role UUID

        Raises:
            HTTPException: 403 if user not associated with an organization
            HTTPException: 500 if organization roles not found
        """
        from app.datastore import OrganizationDataService

        async with sessionmanager.get_session() as session:
            result = await OrganizationDataService(session).get_user_org_roles(user_id)

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not associated with an organization or organization roles not found",
                )

            org_id, org_prefix, org_admin_role_id, org_user_role_id = result
            return UserOrgRoles(
                org_id=org_id,
                org_prefix=org_prefix,
                org_admin_role_id=org_admin_role_id,
                org_user_role_id=org_user_role_id,
            )

    @staticmethod
    async def get_org_user_role_id(organization_id: UUID) -> UUID:
        """
        Get the user role ID for an organization.

        Args:
            organization_id: The organization's UUID

        Returns:
            UUID of the user role for the organization

        Raises:
            HTTPException: 500 if organization user role not found
        """
        async with sessionmanager.get_session() as session:
            stmt = select(RbacRole).where(
                RbacRole.organization_id == organization_id,
                RbacRole.name == "user",
                RbacRole.active == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            org_user_role = result.scalar_one_or_none()

            if not org_user_role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization user role not found",
                )

            return cast(UUID, org_user_role.id)

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
        assert user_org_id is not None  # get_user_organization_id raises if None

        # Verify user has "admin" role in their org
        await RbacService.verify_user_has_role(user_id, ROLE_ADMIN, user_org_id)

        return user_org_id

    @staticmethod
    async def verify_user_has_entity_access(
        user_id: UUID,
        entity_org_user_role_id: Optional[UUID],
        entity_org_admin_role_id: Optional[UUID],
    ) -> bool:
        """
        Verify if user has access to an entity based on entity's role fields.

        User has access if they have:
        - CFIA admin role (cross-organization authority), OR
        - Organization admin role matching entity's org_admin_role_id, OR
        - Organization user role matching entity's org_user_role_id

        Args:
            user_id: The user's UUID
            entity_org_user_role_id: Entity's org_user_role_id field
            entity_org_admin_role_id: Entity's org_admin_role_id field

        Returns:
            True if user has access, False otherwise
        """
        try:
            # Check if user is CFIA admin (highest authority)
            if await RbacService.is_user_cfia_admin(user_id):
                return True

            # Get user's roles in their organization
            async with sessionmanager.get_session() as session:
                from app.datastore import OrganizationDataService

                # Get user's organization
                user_org_id = await OrganizationDataService(
                    session
                ).get_user_organization_id(user_id)
                if not user_org_id:
                    return False

                # Check if user has admin role matching entity's org_admin_role_id
                if entity_org_admin_role_id:
                    has_admin_role = await OrganizationDataService(
                        session
                    ).user_has_specific_role(
                        user_id, entity_org_admin_role_id, user_org_id
                    )
                    if has_admin_role:
                        return True

                # Check if user has user role matching entity's org_user_role_id
                if entity_org_user_role_id:
                    has_user_role = await OrganizationDataService(
                        session
                    ).user_has_specific_role(
                        user_id, entity_org_user_role_id, user_org_id
                    )
                    if has_user_role:
                        return True

                return False

        except Exception:
            return False

    @staticmethod
    async def verify_user_has_entity_admin_access(
        user_id: UUID, entity_org_admin_role_id: Optional[UUID]
    ) -> bool:
        """
        Verify if user has admin-level access to an entity.

        User has admin access if they have:
        - CFIA admin role (cross-organization authority), OR
        - Organization admin role matching entity's org_admin_role_id

        Args:
            user_id: The user's UUID
            entity_org_admin_role_id: Entity's org_admin_role_id field

        Returns:
            True if user has admin access, False otherwise
        """
        try:
            # Check if user is CFIA admin (highest authority)
            if await RbacService.is_user_cfia_admin(user_id):
                return True

            # Check if user has admin role matching entity's org_admin_role_id
            if entity_org_admin_role_id:
                async with sessionmanager.get_session() as session:
                    from app.datastore import OrganizationDataService

                    # Get user's organization
                    user_org_id = await OrganizationDataService(
                        session
                    ).get_user_organization_id(user_id)
                    if not user_org_id:
                        return False

                    has_admin_role = await OrganizationDataService(
                        session
                    ).user_has_specific_role(
                        user_id, entity_org_admin_role_id, user_org_id
                    )
                    return has_admin_role

            return False

        except Exception:
            return False


# ============================================================================
# CRUD Services for RBAC entities
# ============================================================================


class RbacRoleService(BaseCRUDService[RbacRole]):
    """
    Service for RbacRole CRUD operations.

    Access Control:
    - GET operations: Any authenticated user
    - CUD operations: CFIA admin only

    Inherits get_all(), get_by_id(), create(), update(), delete() from BaseCRUDService.
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "RbacRole"

    @classmethod
    def get_data_service_class(cls) -> type[RbacRoleDataService]:
        """Return the data service class."""
        return RbacRoleDataService

    @classmethod
    def serialize_entity(cls, entity: RbacRole) -> Dict[str, Any]:
        """Convert RbacRole entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "organization_id": str(entity.organization_id)
            if entity.organization_id
            else None,
            "active": entity.active,
            "date_created": entity.date_created.isoformat()
            if hasattr(entity, "date_created")
            else None,
            "date_updated": entity.date_updated.isoformat()
            if hasattr(entity, "date_updated")
            else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> type[Exception]:
        """Return RbacRole NotFoundError exception class."""
        return RbacRoleNotFoundError

    @classmethod
    def get_creation_exception(cls) -> type[Exception]:
        """Return RbacRole CreationError exception class."""
        return RbacRoleCreationError

    @classmethod
    def get_update_exception(cls) -> type[Exception]:
        """Return RbacRole UpdateError exception class."""
        return RbacRoleUpdateError

    @classmethod
    def get_deletion_exception(cls) -> type[Exception]:
        """Return RbacRole DeletionError exception class."""
        return RbacRoleDeletionError


class RbacPermissionService(BaseCRUDService[RbacPermission]):
    """
    Service for RbacPermission CRUD operations.

    Access Control:
    - GET operations: Any authenticated user
    - CUD operations: CFIA admin only

    Inherits get_all(), get_by_id(), create(), update(), delete() from BaseCRUDService.
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "RbacPermission"

    @classmethod
    def get_data_service_class(cls) -> type[RbacPermissionDataService]:
        """Return the data service class."""
        return RbacPermissionDataService

    @classmethod
    def serialize_entity(cls, entity: RbacPermission) -> Dict[str, Any]:
        """Convert RbacPermission entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "active": entity.active,
            "date_created": entity.date_created.isoformat()
            if hasattr(entity, "date_created")
            else None,
            "date_updated": entity.date_updated.isoformat()
            if hasattr(entity, "date_updated")
            else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> type[Exception]:
        """Return RbacPermission NotFoundError exception class."""
        return RbacPermissionNotFoundError

    @classmethod
    def get_creation_exception(cls) -> type[Exception]:
        """Return RbacPermission CreationError exception class."""
        return RbacPermissionCreationError

    @classmethod
    def get_update_exception(cls) -> type[Exception]:
        """Return RbacPermission UpdateError exception class."""
        return RbacPermissionUpdateError

    @classmethod
    def get_deletion_exception(cls) -> type[Exception]:
        """Return RbacPermission DeletionError exception class."""
        return RbacPermissionDeletionError


class RbacResourceService(BaseCRUDService[RbacResource]):
    """
    Service for RbacResource CRUD operations.

    Access Control:
    - GET operations: Any authenticated user
    - CUD operations: CFIA admin only

    Inherits get_all(), get_by_id(), create(), update(), delete() from BaseCRUDService.
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "RbacResource"

    @classmethod
    def get_data_service_class(cls) -> type[RbacResourceDataService]:
        """Return the data service class."""
        return RbacResourceDataService

    @classmethod
    def serialize_entity(cls, entity: RbacResource) -> Dict[str, Any]:
        """Convert RbacResource entity to dictionary."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "active": entity.active,
            "date_created": entity.date_created.isoformat()
            if hasattr(entity, "date_created")
            else None,
            "date_updated": entity.date_updated.isoformat()
            if hasattr(entity, "date_updated")
            else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> type[Exception]:
        """Return RbacResource NotFoundError exception class."""
        return RbacResourceNotFoundError

    @classmethod
    def get_creation_exception(cls) -> type[Exception]:
        """Return RbacResource CreationError exception class."""
        return RbacResourceCreationError

    @classmethod
    def get_update_exception(cls) -> type[Exception]:
        """Return RbacResource UpdateError exception class."""
        return RbacResourceUpdateError

    @classmethod
    def get_deletion_exception(cls) -> type[Exception]:
        """Return RbacResource DeletionError exception class."""
        return RbacResourceDeletionError


class RbacRolePermissionResourceService(BaseCRUDService[RbacRolePermissionResource]):
    """
    Service for RbacRolePermissionResource CRUD operations.

    Access Control:
    - GET operations: Any authenticated user
    - CUD operations: CFIA admin only

    NOTE: This is a junction table with composite primary key (role_id, permission_id, resource_id).
    Inherits standard CRUD methods from BaseCRUDService, plus custom composite key methods.
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "RbacRolePermissionResource"

    @classmethod
    def get_data_service_class(cls) -> type[RbacRolePermissionResourceDataService]:
        """Return the data service class."""
        return RbacRolePermissionResourceDataService

    @classmethod
    def serialize_entity(cls, entity: RbacRolePermissionResource) -> Dict[str, Any]:
        """Convert RbacRolePermissionResource entity to dictionary."""
        return {
            "role_id": str(entity.role_id),
            "permission_id": str(entity.permission_id),
            "resource_id": str(entity.resource_id),
            "date_created": entity.date_created.isoformat()
            if hasattr(entity, "date_created")
            else None,
            "date_updated": entity.date_updated.isoformat()
            if hasattr(entity, "date_updated")
            else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> type[Exception]:
        """Return RbacRolePermissionResource NotFoundError exception class."""
        return RbacRolePermissionResourceNotFoundError

    @classmethod
    def get_creation_exception(cls) -> type[Exception]:
        """Return RbacRolePermissionResource CreationError exception class."""
        return RbacRolePermissionResourceCreationError

    @classmethod
    def get_update_exception(cls) -> type[Exception]:
        """Return RbacRolePermissionResource UpdateError exception class."""
        return RbacRolePermissionResourceUpdateError

    @classmethod
    def get_deletion_exception(cls) -> type[Exception]:
        """Return RbacRolePermissionResource DeletionError exception class."""
        return RbacRolePermissionResourceDeletionError

    # Custom methods for composite key operations
    @staticmethod
    async def get_by_composite_key(
        user_id: UUID, role_id: UUID, permission_id: UUID, resource_id: UUID
    ) -> Dict[str, Any]:
        """
        Get a role-permission-resource mapping by composite key.

        Args:
            user_id: The requesting user's UUID (for RBAC)
            role_id: The role UUID
            permission_id: The permission UUID
            resource_id: The resource UUID

        Returns:
            Dictionary representation of the mapping

        Raises:
            RbacRolePermissionResourceNotFoundError: If mapping not found
        """
        try:
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = RbacRolePermissionResourceDataService(session)
                entity = await data_service.get_by_composite_key(
                    role_id, permission_id, resource_id
                )

                if not entity:
                    raise RbacRolePermissionResourceNotFoundError(
                        f"RbacRolePermissionResource with role_id={role_id}, "
                        f"permission_id={permission_id}, resource_id={resource_id} not found"
                    )

                return RbacRolePermissionResourceService.serialize_entity(entity)
        except HTTPException:
            raise
        except RbacRolePermissionResourceNotFoundError:
            raise
        except Exception as e:
            raise RbacRolePermissionResourceNotFoundError(
                f"Failed to retrieve RbacRolePermissionResource: {str(e)}"
            )

    @staticmethod
    async def delete_by_composite_key(
        user_id: UUID, role_id: UUID, permission_id: UUID, resource_id: UUID
    ) -> None:
        """
        Delete a role-permission-resource mapping by composite key.

        Args:
            user_id: The requesting user's UUID (for RBAC)
            role_id: The role UUID
            permission_id: The permission UUID
            resource_id: The resource UUID

        Raises:
            RbacRolePermissionResourceNotFoundError: If mapping not found
        """
        try:
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = RbacRolePermissionResourceDataService(session)
                deleted = await data_service.delete_by_composite_key(
                    role_id, permission_id, resource_id
                )

                if not deleted:
                    raise RbacRolePermissionResourceNotFoundError(
                        f"RbacRolePermissionResource with role_id={role_id}, "
                        f"permission_id={permission_id}, resource_id={resource_id} not found"
                    )

                await session.commit()
        except HTTPException:
            raise
        except RbacRolePermissionResourceNotFoundError:
            raise
        except Exception as e:
            raise RbacRolePermissionResourceDeletionError(
                f"Failed to delete RbacRolePermissionResource: {str(e)}"
            )


class RbacUserRoleService(BaseCRUDService[RbacUserRole]):
    """
    Service for RbacUserRole CRUD operations.

    Access Control:
    - GET operations: Any authenticated user
    - CUD operations: CFIA admin only

    NOTE: This is a junction table with composite primary key (user_id, role_id).
    Inherits standard CRUD methods from BaseCRUDService, plus custom composite key methods.
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return entity name for error messages."""
        return "RbacUserRole"

    @classmethod
    def get_data_service_class(cls) -> type[RbacUserRoleDataService]:
        """Return the data service class."""
        return RbacUserRoleDataService

    @classmethod
    def serialize_entity(cls, entity: RbacUserRole) -> Dict[str, Any]:
        """Convert RbacUserRole entity to dictionary."""
        return {
            "user_id": str(entity.user_id),
            "role_id": str(entity.role_id),
            "active": entity.active,
            "date_created": entity.date_created.isoformat()
            if hasattr(entity, "date_created")
            else None,
            "date_updated": entity.date_updated.isoformat()
            if hasattr(entity, "date_updated")
            else None,
        }

    @classmethod
    def get_not_found_exception(cls) -> type[Exception]:
        """Return RbacUserRole NotFoundError exception class."""
        return RbacUserRoleNotFoundError

    @classmethod
    def get_creation_exception(cls) -> type[Exception]:
        """Return RbacUserRole CreationError exception class."""
        return RbacUserRoleCreationError

    @classmethod
    def get_update_exception(cls) -> type[Exception]:
        """Return RbacUserRole UpdateError exception class."""
        return RbacUserRoleUpdateError

    @classmethod
    def get_deletion_exception(cls) -> type[Exception]:
        """Return RbacUserRole DeletionError exception class."""
        return RbacUserRoleDeletionError

    # Custom methods for composite key operations
    @staticmethod
    async def get_by_composite_key(
        requesting_user_id: UUID, target_user_id: UUID, role_id: UUID
    ) -> Dict[str, Any]:
        """
        Get a user-role mapping by composite key.

        Args:
            requesting_user_id: The requesting user's UUID (for RBAC)
            target_user_id: The target user's UUID (part of composite key)
            role_id: The role UUID (part of composite key)

        Returns:
            Dictionary representation of the mapping

        Raises:
            RbacUserRoleNotFoundError: If mapping not found
        """
        try:
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.get_user_organization_id(requesting_user_id)

            async with sessionmanager.get_session() as session:
                data_service = RbacUserRoleDataService(session)
                entity = await data_service.get_by_composite_key(
                    target_user_id, role_id
                )

                if not entity:
                    raise RbacUserRoleNotFoundError(
                        f"RbacUserRole with user_id={target_user_id}, role_id={role_id} not found"
                    )

                return RbacUserRoleService.serialize_entity(entity)
        except HTTPException:
            raise
        except RbacUserRoleNotFoundError:
            raise
        except Exception as e:
            raise RbacUserRoleNotFoundError(
                f"Failed to retrieve RbacUserRole: {str(e)}"
            )

    @staticmethod
    async def delete_by_composite_key(
        requesting_user_id: UUID, target_user_id: UUID, role_id: UUID
    ) -> None:
        """
        Soft delete a user-role mapping by composite key.

        Args:
            requesting_user_id: The requesting user's UUID (for RBAC)
            target_user_id: The target user's UUID (part of composite key)
            role_id: The role UUID (part of composite key)

        Raises:
            RbacUserRoleNotFoundError: If mapping not found
        """
        try:
            # Lazy import to avoid circular dependency
            from app.service.rbac import RbacService

            await RbacService.verify_user_is_cfia_admin(requesting_user_id)

            async with sessionmanager.get_session() as session:
                data_service = RbacUserRoleDataService(session)
                deleted = await data_service.delete_by_composite_key(
                    target_user_id, role_id
                )

                if not deleted:
                    raise RbacUserRoleNotFoundError(
                        f"RbacUserRole with user_id={target_user_id}, role_id={role_id} not found"
                    )

                await session.commit()
        except HTTPException:
            raise
        except RbacUserRoleNotFoundError:
            raise
        except Exception as e:
            raise RbacUserRoleDeletionError(f"Failed to delete RbacUserRole: {str(e)}")
