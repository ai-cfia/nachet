from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import Organization, RbacRole, Users, RbacUserRole


class OrganizationDataService:
    """Data access layer for Organization database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Organization]:
        """
        Retrieve all active organizations.

        Returns:
            List of Organization objects
        """
        query = (
            select(Organization)
            .where(Organization.active.is_(True))
            .options(selectinload(Organization.rbac_roles))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        """
        Retrieve an organization by ID.

        Args:
            organization_id: The organization UUID

        Returns:
            Organization object if found and active, None otherwise
        """
        query = (
            select(Organization)
            .where(Organization.id == organization_id)
            .where(Organization.active.is_(True))
            .options(selectinload(Organization.rbac_roles))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        description: str,
        folder_prefix: Optional[str] = None,
    ) -> Organization:
        """
        Create a new organization.

        Args:
            name: Organization name
            description: Organization description
            folder_prefix: Optional folder prefix for the organization

        Returns:
            The created Organization object
        """
        organization = Organization(
            name=name,
            description=description,
            folder_prefix=folder_prefix,
            active=True,
        )
        self.session.add(organization)
        await self.session.flush()
        await self.session.refresh(organization)
        return organization

    async def update(
        self,
        organization_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        folder_prefix: Optional[str] = None,
    ) -> Optional[Organization]:
        """
        Update an organization.

        Args:
            organization_id: The organization UUID
            name: New name (if provided)
            description: New description (if provided)
            folder_prefix: New folder prefix (if provided)

        Returns:
            Updated Organization object if found, None otherwise
        """
        organization = await self.get_by_id(organization_id)
        if not organization:
            return None

        if name is not None:
            organization.name = name
        if description is not None:
            organization.description = description
        if folder_prefix is not None:
            organization.folder_prefix = folder_prefix

        await self.session.flush()
        await self.session.refresh(organization)
        return organization

    async def soft_delete(self, organization_id: UUID) -> Optional[Organization]:
        """
        Soft delete an organization by setting active to False.

        Args:
            organization_id: The organization UUID

        Returns:
            The soft-deleted Organization object if found, None otherwise
        """
        query = select(Organization).where(Organization.id == organization_id)
        result = await self.session.execute(query)
        organization = result.scalar_one_or_none()

        if not organization:
            return None

        organization.active = False
        await self.session.flush()
        await self.session.refresh(organization)
        return organization

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
