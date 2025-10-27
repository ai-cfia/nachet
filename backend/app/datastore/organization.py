from typing import Optional, Type, cast
from uuid import UUID
from sqlalchemy import select

from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import Organization, RbacRole, Users, RbacUserRole
from sqlalchemy.orm import selectinload


class OrganizationDataService(BaseCRUDDataService[Organization]):
    """Data access layer for Organization database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Organization]:
        """Return the Organization model class."""
        return Organization

    def get_query_options(self) -> list:
        """Load RBAC roles relationship for organizations."""
        return [selectinload(Organization.rbac_roles)]

    # ==========================================
    # Custom methods specific to Organization
    # ==========================================

    async def check_name_prefix_exists(self, folder_prefix: str) -> bool:
        """
        Check if the organization folder prefix already exist.

        This enforces the business rule that the first 20 chars of org folder prefix must be unique.

        Args:
            folder_prefix: Organization folder prefix to check

        Returns:
            True if a matching prefix exists, False otherwise
        """
        # name_prefix = name.lower()[:20]
        query = (
            select(Organization)
            .where(Organization.folder_prefix == folder_prefix)
            .where(Organization.active.is_(True))
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def user_has_role(
        self, user_id: UUID, organization_id: UUID, role_name: str
    ) -> bool:
        """
        Check if a user has a specific role in an organization.

        Args:
            user_id: The user's UUID
            organization_id: The organization UUID
            role_name: The role name to check (e.g., "cfia_admin")

        Returns:
            True if user has the role in the organization, False otherwise
        """
        query = (
            select(RbacUserRole)
            .join(RbacRole, RbacUserRole.role_id == RbacRole.id)
            .join(Users, RbacUserRole.user_id == Users.id)
            .where(Users.id == user_id)
            .where(RbacRole.organization_id == organization_id)
            .where(RbacRole.name == role_name)
            .where(Users.active.is_(True))
            .where(RbacUserRole.active.is_(True))
            .where(RbacRole.active.is_(True))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def user_has_specific_role(
        self, user_id: UUID, role_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if a user has a specific role ID in an organization.

        Args:
            user_id: The user's UUID
            role_id: The specific role UUID to check
            organization_id: The organization UUID

        Returns:
            True if user has the specific role in the organization, False otherwise
        """
        query = (
            select(RbacUserRole)
            .join(RbacRole, RbacUserRole.role_id == RbacRole.id)
            .join(Users, RbacUserRole.user_id == Users.id)
            .where(Users.id == user_id)
            .where(RbacRole.id == role_id)
            .where(RbacRole.organization_id == organization_id)
            .where(Users.active.is_(True))
            .where(RbacUserRole.active.is_(True))
            .where(RbacRole.active.is_(True))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_user_organization_id(self, user_id: UUID) -> Optional[UUID]:
        """
        Get the organization ID for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Organization UUID if found, None otherwise
        """
        query = (
            select(Users.organization)
            .where(Users.id == user_id)
            .where(Users.active.is_(True))
        )
        result = await self.session.execute(query)
        org_id = result.scalar_one_or_none()
        return cast(Optional[UUID], org_id)

    async def get_user_org_roles(
        self, user_id: UUID
    ) -> Optional[tuple[UUID, str, UUID, UUID]]:
        """
        Get organization ID, prefix, admin role ID, and user role ID in a single query.

        This method performs a single database query to retrieve:
        1. The user's organization ID
        2. The organization's folder prefix
        3. The organization's admin role ID (role with name='admin')
        4. The organization's user role ID (role with name='user')

        Args:
            user_id: The user's UUID

        Returns:
            Tuple of (org_id, org_prefix, org_admin_role_id, org_user_role_id) if found, None otherwise
        """
        # Subquery to get organization folder prefix
        org_prefix_subquery = (
            select(Organization.folder_prefix)
            .where(Organization.id == Users.organization)
            .where(Organization.active.is_(True))
            .scalar_subquery()
        )

        # Subquery to get admin role ID
        admin_role_subquery = (
            select(RbacRole.id)
            .where(RbacRole.organization_id == Users.organization)
            .where(RbacRole.name == "admin")
            .where(RbacRole.active.is_(True))
            .scalar_subquery()
        )

        # Subquery to get user role ID
        user_role_subquery = (
            select(RbacRole.id)
            .where(RbacRole.organization_id == Users.organization)
            .where(RbacRole.name == "user")
            .where(RbacRole.active.is_(True))
            .scalar_subquery()
        )

        query = (
            select(
                Users.organization,
                org_prefix_subquery,
                admin_role_subquery,
                user_role_subquery,
            )
            .where(Users.id == user_id)
            .where(Users.active.is_(True))
        )
        result = await self.session.execute(query)
        row = result.first()
        return (row[0], row[1], row[2], row[3]) if row else None
