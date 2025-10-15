from typing import Optional, Type
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
        return result.scalar_one_or_none()
