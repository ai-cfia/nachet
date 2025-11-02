from beartype.typing import Dict, Any, Type, Optional, cast
from uuid import UUID
import traceback
import re
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.service.error_sanitizer import sanitize_error_for_user
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
        requester_id: UUID,
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
            requester_id: The requesting user's UUID
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
        await RbacService.verify_user_is_cfia_admin(requester_id)

        # Call base class implementation with explicit order_by
        if not order_by:
            order_by = "name"  # Default ordering by name

        result = await super().get_all(
            requester_id=requester_id,
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
    async def create(  # type: ignore[override]
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
        The folder_prefix (derived from name or user-provided) must be unique.

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Organization name
            description: Organization description
            folder_prefix: Optional custom folder prefix (max 20 chars, lowercase alphanumeric + dashes).
                          If not provided, auto-generated from normalized organization name.
                          If normalized name conflicts with existing org, user must provide this.

        Returns:
            Dictionary containing the created organization data with role information

        Raises:
            HTTPException: 403 if unauthorized, 409 if name/prefix conflict, 400 if invalid format, 500 on error
        """
        try:
            # RBAC: Only CFIA admin can create organizations
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service_class = cls.get_data_service_class()
                data_service = data_service_class(session)

                sanitized_name = OrganizationService.sanitize_string(name)
                sanitized_description = OrganizationService.sanitize_string(description)
                normalized_name = cls.normalize_org_name(sanitized_name)

                # Determine folder_prefix: use custom or auto-generated
                final_prefix = (
                    cls.normalize_org_name(
                        OrganizationService.sanitize_string(folder_prefix)
                    )
                    if folder_prefix
                    else normalized_name
                )

                # Validate: folder_prefix must be unique (check against existing orgs)
                # Cast to OrganizationDataService to access custom methods
                org_data_service = cast(OrganizationDataService, data_service)
                if await org_data_service.check_name_prefix_exists(final_prefix):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Organization normalized folder_prefix conflict: '{final_prefix}' already exists. Please provide a unique folder_prefix.",
                    )

                # Standard: Create organization
                # Note: folder_prefix stores normalized_name or custom prefix (max 20 chars) for blob storage paths
                organization = await data_service.create(
                    name=sanitized_name,
                    description=sanitized_description,
                    folder_prefix=final_prefix,
                )

                # CUSTOM LOGIC: Create 2 RBAC roles for organization
                admin_role = RbacRole(
                    organization_id=organization.id,
                    name="admin",
                    description=f"Administrator role for {sanitized_name}",
                    active=True,
                )
                user_role = RbacRole(
                    organization_id=organization.id,
                    name="user",
                    description=f"User role for {sanitized_name}",
                    active=True,
                )
                session.add(admin_role)
                session.add(user_role)
                await session.flush()

                # Commit transaction
                await session.commit()

                # Refresh to get relationships with eager loading
                await session.refresh(organization, attribute_names=["rbac_roles"])

                logger = cls._get_logger()
                info_msg = "Organization created with roles"
                logger.info(
                    info_msg,
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
            error_msg = f"Failed to create organization: {str(e)}"
            logger.error(
                error_msg,
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                organization_name=name,
            )
            debug_msg = "Traceback for failed create organization"
            logger.debug(
                debug_msg,
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=sanitize_error_for_user(e, context="organization"),
            )

    @staticmethod
    def normalize_org_name(name: str) -> str:
        """
        Normalize organization name for blob storage paths.

        Used to create consistent, filesystem-safe names for blob storage organization.
        Org names are used in nachet-original container paths for access control/auditing.

        Rules:
        - Lowercase only
        - Only alphanumeric (a-z, 0-9) and dashes allowed
        - Maximum 20 characters
        - Remove all other characters
        - Multiple consecutive dashes collapsed to single dash
        - Strip leading/trailing dashes

        Args:
            name: Raw organization name (e.g., "CFIA Organization")

        Returns:
            Normalized name, max 20 chars (e.g., "cfia-org")

        Example:
            >>> OrganizationService.normalize_org_name("CFIA Organization")
            'cfia-org'
            >>> OrganizationService.normalize_org_name("Research-Lab-2024")
            'research-l'
        """
        if not name:
            return "unknown"

        # Convert to lowercase
        name = name.lower().strip()

        # Replace spaces with dashes
        name = name.replace(" ", "-")

        # Remove all characters except a-z, 0-9, and dashes
        name = re.sub(r"[^a-z0-9\-]", "", name)

        # Collapse multiple consecutive dashes
        name = re.sub(r"-+", "-", name)

        # Strip leading/trailing dashes
        name = name.strip("-")

        # Truncate to 20 characters
        name = name[:20]

        # Strip trailing dashes again after truncation (may have created new trailing dash)
        name = name.rstrip("-")

        return name if name else "unknown"

    @staticmethod
    def sanitize_string(input_string: str) -> str:
        """
        Sanitize a string by removing leading/trailing whitespace and
        replacing multiple spaces with a single space.
        remove all special characters except hyphens spaces and underscores.

        Args:
            input_string: The string to sanitize

        Returns:
            The sanitized string
        """
        import re

        # Replace multiple spaces with a single space
        sanitized = re.sub(r"\s+", " ", input_string)

        # Remove all special characters except hyphens, spaces, and underscores
        # Keep A-Z a-z 0-9 hyphen - underscore _ and space
        sanitized = re.sub(r"[^A-Za-z0-9\-_ ]+", "", sanitized)

        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized
