"""
Pending registration data service.

Provides data access layer for temporary pending user registrations.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model import PendingRegistration


class PendingRegistrationDataService:
    """
    Data access layer for PendingRegistration database operations.

    Note: This table doesn't use the BaseCRUDDataService pattern since:
    - It doesn't have an 'active' field (hard deletes only)
    - Primary key is a string (azure_ad_oid) not UUID
    - It's a temporary table with simpler requirements
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_azure_oid(
        self, azure_ad_oid: str
    ) -> Optional[PendingRegistration]:
        """
        Retrieve a pending registration by Azure AD OID.

        Args:
            azure_ad_oid: The Azure AD object ID

        Returns:
            PendingRegistration object if found, None otherwise
        """
        query = select(PendingRegistration).where(
            PendingRegistration.azure_ad_oid == azure_ad_oid
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, azure_ad_oid: str, email: Optional[str] = None
    ) -> PendingRegistration:
        """
        Create a new pending registration.

        Args:
            azure_ad_oid: The Azure AD object ID
            email: User's email address (optional)

        Returns:
            The created PendingRegistration object
        """
        pending_registration = PendingRegistration(
            azure_ad_oid=azure_ad_oid, email=email
        )
        self.session.add(pending_registration)
        await self.session.flush()
        await self.session.refresh(pending_registration)
        return pending_registration

    async def delete(self, azure_ad_oid: str) -> bool:
        """
        Hard delete a pending registration.

        Args:
            azure_ad_oid: The Azure AD object ID

        Returns:
            True if deleted, False if not found
        """
        pending_registration = await self.get_by_azure_oid(azure_ad_oid)
        if not pending_registration:
            return False

        await self.session.delete(pending_registration)
        await self.session.flush()
        return True
