from typing import List, Dict, Any, Optional
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.datastore import OrganizationDataService
from app.db.model import RbacRole
from app.service.logs import LogService
from app.service.rbac import RbacService
from app.exceptions import OrganizationNotFoundError


class OrganizationService:
    """
    Service layer for Organization CRUD operations.

    System Invariants:
    - Each organization has 2 RBAC roles created automatically:
      * "admin": Administrator role (org-scoped by organization_id)
      * "user": User role (org-scoped by organization_id)
    - CFIA organization also has "verifier" role for data verification
    - Role authority determined by organization_id, not role name
    - Only CFIA admins can create, update, or delete organizations
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for OrganizationService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def _create_organization_roles(
        session, organization_id: UUID, org_name: str
    ) -> Dict[str, UUID]:
        """
        Create the 2 standard roles for a new organization.

        All organizations get:
        - "admin" role: Administrator for the organization
        - "user" role: Standard user for the organization

        Note: CFIA organization also gets "verifier" role created separately.

        Args:
            session: Database session
            organization_id: UUID of the organization
            org_name: Name of the organization (for description only)

        Returns:
            Dictionary mapping role types to their UUIDs
        """
        # Create admin role
        admin_role = RbacRole(
            organization_id=organization_id,
            name="admin",  # Generic name, scoped by organization_id
            description=f"Administrator role for {org_name}",
            active=True,
        )

        # Create user role
        user_role = RbacRole(
            organization_id=organization_id,
            name="user",  # Generic name, scoped by organization_id
            description=f"User role for {org_name}",
            active=True,
        )

        session.add(admin_role)
        session.add(user_role)
        await session.flush()

        return {
            "admin": admin_role.id,
            "user": user_role.id,
        }

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active organizations.

        Note: User must have cfia_admin role in their organization to list all organizations.

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "organizations" key containing list of organization data

        Raises:
            HTTPException: 403 if user is not cfia_admin, 500 on database error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = OrganizationDataService(session)

                # Retrieve all organizations
                organizations = await data_service.get_all()

                return {
                    "organizations": [
                        {
                            "id": str(org.id),
                            "name": org.name,
                            "description": org.description,
                            "folder_prefix": org.folder_prefix,
                            "date_created": org.date_created.isoformat(),
                            "active": org.active,
                        }
                        for org in organizations
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = OrganizationService._get_logger()
            logger.error(
                f"Failed to retrieve organizations: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve organizations",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve organizations: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, organization_id: UUID) -> Dict[str, Any]:
        """
        Retrieve an organization by ID.

        Note: User must have cfia_admin role in their organization.

        Args:
            user_id: The requesting user's UUID
            organization_id: The organization UUID to retrieve

        Returns:
            Dictionary containing organization data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = OrganizationDataService(session)

                # Retrieve organization
                organization = await data_service.get_by_id(organization_id)
                if not organization:
                    raise OrganizationNotFoundError(
                        f"Organization {organization_id} not found"
                    )

                return {
                    "id": str(organization.id),
                    "name": organization.name,
                    "description": organization.description,
                    "folder_prefix": organization.folder_prefix,
                    "date_created": organization.date_created.isoformat(),
                    "active": organization.active,
                    "rbac_roles": [
                        {
                            "id": str(role.id),
                            "name": role.name,
                            "description": role.description,
                        }
                        for role in organization.rbac_roles
                        if role.active
                    ],
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except OrganizationNotFoundError as e:
            logger = OrganizationService._get_logger()
            logger.warning(
                f"Organization not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = OrganizationService._get_logger()
            logger.error(
                f"Failed to retrieve organization: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            logger.debug(
                "Traceback for failed retrieve organization",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve organization: {str(e)}",
            )

    @staticmethod
    async def create(
        user_id: UUID,
        name: str,
        description: str,
        folder_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new organization with RBAC roles.

        System Invariant: Automatically creates 2 organization-specific RBAC roles:
        - admin_{org_prefix}_{random}: Administrator role for the organization
        - user_{org_prefix}_{random}: User role for the organization

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
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = OrganizationDataService(session)

                # Create the organization
                organization = await data_service.create(
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
                )

                # Create 2 organization-specific RBAC roles
                role_ids = await OrganizationService._create_organization_roles(
                    session, organization.id, name
                )

                # Commit the transaction
                await session.commit()

                # Refresh to get relationships
                await session.refresh(organization)

                return {
                    "id": str(organization.id),
                    "name": organization.name,
                    "description": organization.description,
                    "folder_prefix": organization.folder_prefix,
                    "date_created": organization.date_created.isoformat(),
                    "active": organization.active,
                    "roles": {
                        "admin_role_id": str(role_ids["admin"]),
                        "user_role_id": str(role_ids["user"]),
                    },
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = OrganizationService._get_logger()
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

    @staticmethod
    async def update(
        user_id: UUID,
        organization_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        folder_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an organization.

        Note: Only cfia_admin users can update organizations.

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            organization_id: The organization UUID to update
            name: New name (optional)
            description: New description (optional)
            folder_prefix: New folder prefix (optional)

        Returns:
            Dictionary containing the updated organization data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = OrganizationDataService(session)

                # Update organization
                organization = await data_service.update(
                    organization_id=organization_id,
                    name=name,
                    description=description,
                    folder_prefix=folder_prefix,
                )

                if not organization:
                    raise OrganizationNotFoundError(
                        f"Organization {organization_id} not found"
                    )

                # Commit the transaction
                await session.commit()

                return {
                    "id": str(organization.id),
                    "name": organization.name,
                    "description": organization.description,
                    "folder_prefix": organization.folder_prefix,
                    "date_created": organization.date_created.isoformat(),
                    "active": organization.active,
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except OrganizationNotFoundError as e:
            logger = OrganizationService._get_logger()
            logger.warning(
                f"Organization not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = OrganizationService._get_logger()
            logger.error(
                f"Failed to update organization: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            logger.debug(
                "Traceback for failed update organization",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update organization: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, organization_id: UUID) -> Dict[str, str]:
        """
        Soft delete an organization (sets active=False).

        System Invariant: Deletion is soft delete to maintain referential integrity.
        The organization and its relationships remain in the database but are marked inactive.

        Note: Only cfia_admin users can delete organizations.

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            organization_id: The organization UUID to delete

        Returns:
            Dictionary with success message

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = OrganizationDataService(session)

                # Soft delete organization
                organization = await data_service.soft_delete(organization_id)

                if not organization:
                    raise OrganizationNotFoundError(
                        f"Organization {organization_id} not found"
                    )

                # Commit the transaction
                await session.commit()

                return {
                    "message": f"Organization {organization_id} successfully deleted (soft delete)"
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except OrganizationNotFoundError as e:
            logger = OrganizationService._get_logger()
            logger.warning(
                f"Organization not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = OrganizationService._get_logger()
            logger.error(
                f"Failed to delete organization: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            logger.debug(
                "Traceback for failed delete organization",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete organization: {str(e)}",
            )
