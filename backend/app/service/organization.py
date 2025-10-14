from typing import Dict, Any, Type, Optional
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.datastore import OrganizationDataService
from app.db.model import Organization, RbacRole
from app.service.rbac import RbacService
from app.exceptions import (
    OrganizationNotFoundError,
    OrganizationCreationError,
    OrganizationUpdateError,
    OrganizationDeletionError,
)


class OrganizationService(BaseCRUDService[Organization]):
    """
    Service layer for Organization CRUD operations.

    Uses BaseCRUDService for standard CRUD operations.
    Overrides create() to add automatic RBAC role creation.

    Access Control:
    - GET operations (get_all, get_by_id): CFIA admin only
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Each organization has 2 RBAC roles created automatically:
      * "admin": Administrator role (org-scoped by organization_id)
      * "user": User role (org-scoped by organization_id)
    - CFIA organization also has "verifier" role for data verification
    - Role authority determined by organization_id, not role name
    - Only CFIA admins can create, update, or delete organizations
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "Organization"

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[Organization]]:
        """Return the data service class."""
        return OrganizationDataService

    @classmethod
    def serialize_entity(cls, entity: Organization) -> Dict[str, Any]:
        """
        Convert Organization entity to dictionary for API response.
        
        Includes RBAC roles for the organization.
        """
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "folder_prefix": entity.folder_prefix,
            "date_created": entity.date_created.isoformat(),
            "active": entity.active,
            "rbac_roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                }
                for role in entity.rbac_roles
                if role.active
            ],
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return OrganizationNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return OrganizationCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return OrganizationUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return OrganizationDeletionError

    # ==========================================
    # Override get_all() to maintain backward-compatible response format
    # ==========================================

    @classmethod
    async def get_all(
        cls,
        user_id: UUID,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_direction: str = "asc",
    ) -> Dict[str, Any]:
        """
        Retrieve all active organizations with their RBAC roles.

        Note: User must have cfia_admin role in their organization.
        Override to maintain backward-compatible response format.

        Args:
            user_id: The requesting user's UUID
            offset: Number of records to skip (default: 0)
            limit: Maximum records to return (default: 100, max: 1000)
            filters: Dictionary of field_name: value pairs for filtering (optional)
            order_by: Field name to sort by (default: name)
            order_direction: Sort direction 'asc' or 'desc' (default: 'asc')

        Returns:
            Dictionary with "organizations" key containing list of organization data

        Raises:
            HTTPException: 403 if user is not cfia_admin, 500 on database error
        """
        # RBAC: Only CFIA admin can view all organizations
        await RbacService.verify_user_is_cfia_admin(user_id)

        # Call base class implementation with explicit order_by
        if not order_by:
            order_by = "name"  # Default ordering by name

        result = await super().get_all(
            user_id=user_id,
            offset=offset,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction,
        )

        # Rename "items" key to "organizations" for backward compatibility
        result["organizations"] = result.pop("items")
        return result

    # ==========================================
    # Override create() to add RBAC role creation
    # ==========================================

    @classmethod
    async def create(
        cls,
        user_id: UUID,
        name: str,
        description: str,
        folder_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new organization with automatic RBAC role creation.

        System Invariant: Automatically creates 2 organization-specific RBAC roles:
        - "admin": Administrator role for the organization
        - "user": User role for the organization

        Note: Only cfia_admin users can create organizations.

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Organization name
            description: Organization description
            folder_prefix: Optional folder prefix for the organization

        Returns:
            Dictionary containing the created organization data with role information

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # RBAC: Only CFIA admin can create organizations
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                # Standard: Create organization
                organization = await data_service.create(
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
                )

                # CUSTOM LOGIC: Create 2 RBAC roles for organization
                admin_role = RbacRole(
                    organization_id=organization.id,
                    name="admin",
                    description=f"Administrator role for {name}",
                    active=True,
                )
                user_role = RbacRole(
                    organization_id=organization.id,
                    name="user",
                    description=f"User role for {name}",
                    active=True,
                )
                session.add(admin_role)
                session.add(user_role)
                await session.flush()

                # Commit transaction
                await session.commit()

                # Refresh to get relationships
                await session.refresh(organization)

                logger = cls._get_logger()
                logger.info(
                    "Organization created with roles",
                    user_id=str(user_id),
                    organization_id=str(organization.id),
                    admin_role_id=str(admin_role.id),
                    user_role_id=str(user_role.id),
                )

                return cls.serialize_entity(organization)

        except HTTPException:
            raise
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create organization: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                organization_name=name,
            )
            logger.debug(
                "Traceback for failed create organization",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create organization: {str(e)}",
            )
