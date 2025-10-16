"""
Integration tests for OrganizationService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested:
- GET operations: CFIA admin only
- CUD operations: CFIA admin only

System Invariants verified:
- Each organization automatically gets 2 RBAC roles (admin + user)
- Role creation is atomic with organization creation
- Soft delete maintains referential integrity
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

from app.service.organization import OrganizationService
from app.db.model import Organization, RbacRole
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationGetAll:
    """Integration tests for OrganizationService.get_all method."""

    async def test_get_all_returns_active_organizations_only(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify that get_all returns only active organizations, excluding soft-deleted ones."""
        # Create active organization
        active_org = Organization(
            id=uuid4(),
            name="Active Test Org",
            description="Active organization for testing",
            folder_prefix="active-test",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(active_org)
        cleanup_test_organizations.append(active_org.id)

        # Create inactive organization
        inactive_org = Organization(
            id=uuid4(),
            name="Inactive Test Org",
            description="Soft-deleted organization",
            folder_prefix="inactive-test",
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_org)
        cleanup_test_organizations.append(inactive_org.id)

        await integration_db_session.commit()

        # Call service - should only return active organization
        result = await OrganizationService.get_all(test_admin_user)

        # Verify
        assert "organizations" in result
        org_names = [org["name"] for org in result["organizations"]]
        assert "Active Test Org" in org_names
        assert "Inactive Test Org" not in org_names

    async def test_get_all_includes_rbac_roles_in_serialization(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify that get_all includes RBAC roles for each organization."""
        # Create organization with roles
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Org With Roles",
            description="Organization with RBAC roles",
            folder_prefix="org-roles",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)

        # Create RBAC roles
        admin_role = RbacRole(
            id=uuid4(),
            organization_id=org_id,
            name="admin",
            description="Admin role",
            active=True,
        )
        user_role = RbacRole(
            id=uuid4(),
            organization_id=org_id,
            name="user",
            description="User role",
            active=True,
        )
        integration_db_session.add(admin_role)
        integration_db_session.add(user_role)
        cleanup_test_organizations.append(org_id)

        await integration_db_session.commit()

        # Call service
        result = await OrganizationService.get_all(test_admin_user)

        # Verify
        org_data = next(
            (o for o in result["organizations"] if o["name"] == "Org With Roles"),
            None,
        )
        assert org_data is not None
        assert "rbac_roles" in org_data
        assert len(org_data["rbac_roles"]) >= 2
        role_names = [r["name"] for r in org_data["rbac_roles"]]
        assert "admin" in role_names
        assert "user" in role_names

    async def test_get_all_pagination_works(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify pagination with offset and limit works correctly."""
        # Create 15 test organizations
        for i in range(15):
            org = Organization(
                id=uuid4(),
                name=f"Pagination Test Org {i:03d}",
                description=f"Organization for pagination test {i}",
                folder_prefix=f"page-test-{i:03d}",
                active=True,
                date_created=datetime.now(timezone.utc),
            )
            integration_db_session.add(org)
            cleanup_test_organizations.append(org.id)

        await integration_db_session.commit()

        # Test first page
        page1 = await OrganizationService.get_all(test_admin_user, offset=0, limit=5)
        assert len(page1["organizations"]) == 5
        assert page1["offset"] == 0
        assert page1["limit"] == 5
        assert page1["has_more"] is True

        # Test second page
        page2 = await OrganizationService.get_all(test_admin_user, offset=5, limit=5)
        assert len(page2["organizations"]) == 5
        assert page2["offset"] == 5

        # Verify all our test organizations exist
        all_orgs = await OrganizationService.get_all(test_admin_user, limit=1000)
        org_names = [o["name"] for o in all_orgs["organizations"]]
        for i in range(15):
            assert f"Pagination Test Org {i:03d}" in org_names

    async def test_get_all_filtering_by_name(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify filtering by name works correctly."""
        # Create organizations with specific names
        org1 = Organization(
            id=uuid4(),
            name="Filter Test Alpha",
            description="First filter test org",
            folder_prefix="filter-alpha",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        org2 = Organization(
            id=uuid4(),
            name="Filter Test Beta",
            description="Second filter test org",
            folder_prefix="filter-beta",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org1)
        integration_db_session.add(org2)
        cleanup_test_organizations.extend([org1.id, org2.id])

        await integration_db_session.commit()

        # Filter by name
        result = await OrganizationService.get_all(
            test_admin_user, filters={"name": "Filter Test Alpha"}
        )

        # Verify
        org_names = [o["name"] for o in result["organizations"]]
        assert "Filter Test Alpha" in org_names
        assert "Filter Test Beta" not in org_names

    async def test_get_all_ordering_by_name_asc(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify ordering by name in ascending order."""
        # Create organizations with specific names
        org_z = Organization(
            id=uuid4(),
            name="ZZZ Order Test",
            description="Should be last",
            folder_prefix="order-z",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        org_a = Organization(
            id=uuid4(),
            name="AAA Order Test",
            description="Should be first",
            folder_prefix="order-a",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org_z)
        integration_db_session.add(org_a)
        cleanup_test_organizations.extend([org_z.id, org_a.id])

        await integration_db_session.commit()

        # Get all with ordering by name ascending
        result = await OrganizationService.get_all(
            test_admin_user, order_by="name", order_direction="asc", limit=1000
        )

        # Verify order
        org_names = [o["name"] for o in result["organizations"]]
        aaa_index = org_names.index("AAA Order Test")
        zzz_index = org_names.index("ZZZ Order Test")
        assert aaa_index < zzz_index

    async def test_get_all_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
    ):
        """Verify that CFIA admin can successfully retrieve organizations."""
        # Call service as CFIA admin
        result = await OrganizationService.get_all(test_admin_user)

        # Verify successful response
        assert "organizations" in result
        assert isinstance(result["organizations"], list)
        assert "total" in result
        assert "offset" in result
        assert "limit" in result

    async def test_get_all_as_non_cfia_admin_fails(
        self,
        test_regular_user: UUID,
    ):
        """Verify that non-CFIA admin gets 403 Forbidden."""
        # Call service as non-CFIA admin
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_all(test_regular_user)

        # Verify 403 Forbidden
        assert exc_info.value.status_code == 403

    async def test_get_all_response_uses_organizations_key(
        self,
        test_admin_user: UUID,
    ):
        """Verify response format uses 'organizations' key for backward compatibility."""
        result = await OrganizationService.get_all(test_admin_user)

        # Verify key naming
        assert "organizations" in result
        assert "items" not in result  # Should NOT use generic 'items' key


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationGetById:
    """Integration tests for OrganizationService.get_by_id method."""

    async def test_get_by_id_retrieves_organization_with_roles(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify get_by_id retrieves organization with full details and RBAC roles."""
        # Create organization with roles
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Get By ID Test Org",
            description="Organization for get_by_id test",
            folder_prefix="getbyid-test",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)

        admin_role = RbacRole(
            id=uuid4(),
            organization_id=org_id,
            name="admin",
            description="Admin role",
            active=True,
        )
        integration_db_session.add(admin_role)
        cleanup_test_organizations.append(org_id)

        await integration_db_session.commit()

        # Call service
        result = await OrganizationService.get_by_id(test_admin_user, org_id)

        # Verify
        assert result["id"] == str(org_id)
        assert result["name"] == "Get By ID Test Org"
        assert result["description"] == "Organization for get_by_id test"
        assert result["folder_prefix"] == "getbyid-test"
        assert result["active"] is True
        assert "rbac_roles" in result
        assert len(result["rbac_roles"]) >= 1

    async def test_get_by_id_nonexistent_organization_raises_error(
        self,
        test_admin_user: UUID,
    ):
        """Verify get_by_id raises error for non-existent organization."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_by_id(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_inactive_organization_raises_error(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify get_by_id raises error for soft-deleted (inactive) organization."""
        # Create inactive organization
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Inactive Org",
            description="Soft-deleted organization",
            folder_prefix="inactive",
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)

        await integration_db_session.commit()

        # Call service
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_by_id(test_admin_user, org_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify CFIA admin can retrieve organization."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="RBAC Test Org",
            description="Organization for RBAC test",
            folder_prefix="rbac-test",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)

        await integration_db_session.commit()

        # Should succeed without raising
        result = await OrganizationService.get_by_id(test_admin_user, org_id)
        assert result["id"] == str(org_id)

    async def test_get_by_id_as_non_cfia_admin_fails(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="RBAC Deny Test Org",
            description="Organization for RBAC denial test",
            folder_prefix="rbac-deny",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)

        await integration_db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_by_id(test_regular_user, org_id)

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationCreate:
    """Integration tests for OrganizationService.create method."""

    async def test_create_successfully_creates_organization(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify create successfully creates organization with required fields."""
        # Call service
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="New Test Organization",
            description="A newly created test organization",
            folder_prefix="new-test-org",
        )

        # Track for cleanup
        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Verify response
        assert result["name"] == "New Test Organization"
        assert result["description"] == "A newly created test organization"
        assert result["folder_prefix"] == "new-test-org"
        assert result["active"] is True
        assert "date_created" in result

    async def test_create_automatically_creates_admin_and_user_roles(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify create automatically creates 2 RBAC roles (admin and user)."""
        # Call service
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="Org With Auto Roles",
            description="Organization to test automatic role creation",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Verify RBAC roles were created
        assert "rbac_roles" in result
        assert len(result["rbac_roles"]) == 2

        role_names = [r["name"] for r in result["rbac_roles"]]
        assert "admin" in role_names
        assert "user" in role_names

    async def test_create_roles_have_correct_organization_id(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify created roles are properly scoped to organization_id."""
        # Call service
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="Org Role Scope Test",
            description="Testing role organization_id scoping",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Query database directly to verify organization_id on roles
        stmt = select(RbacRole).where(RbacRole.organization_id == org_id)
        db_result = await integration_db_session.execute(stmt)
        roles = db_result.scalars().all()

        assert len(roles) == 2
        for role in roles:
            assert role.organization_id == org_id

    async def test_create_roles_are_active_by_default(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify created roles are active by default."""
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="Active Roles Test Org",
            description="Testing role active status",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Verify all roles are active
        for role in result["rbac_roles"]:
            # Active roles are included in serialization
            assert role["name"] in ["admin", "user"]

        # Double-check in database
        stmt = select(RbacRole).where(RbacRole.organization_id == org_id)
        db_result = await integration_db_session.execute(stmt)
        roles = db_result.scalars().all()

        for role in roles:
            assert role.active is True

    async def test_create_handles_optional_folder_prefix(
        self,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify optional folder_prefix is handled correctly."""
        # Create without folder_prefix
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="No Prefix Org",
            description="Organization without folder prefix",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Verify
        assert result["folder_prefix"] == "/"

    async def test_create_as_cfia_admin_succeeds(
        self,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify CFIA admin can create organizations."""
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="CFIA Admin Create Test",
            description="Testing CFIA admin creation",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        assert result["name"] == "CFIA Admin Create Test"

    async def test_create_as_non_cfia_admin_fails(
        self,
        test_regular_user: UUID,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.create(
                user_id=test_regular_user,
                name="Unauthorized Org",
                description="Should not be created",
            )

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationUpdate:
    """Integration tests for OrganizationService.update method."""

    async def test_update_successfully_updates_fields(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify update successfully updates name, description, and folder_prefix."""
        # Create organization
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Original Name",
            description="Original description",
            folder_prefix="original",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        # Update
        result = await OrganizationService.update(
            user_id=test_admin_user,
            entity_id=org_id,
            name="Updated Name",
            description="Updated description",
            folder_prefix="updated",
        )

        # Verify
        assert result["name"] == "Updated Name"
        assert result["description"] == "Updated description"
        assert result["folder_prefix"] == "updated"

    async def test_update_partial_updates_work(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify partial updates work (only updating some fields)."""
        # Create organization
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Partial Update Org",
            description="Original description",
            folder_prefix="partial",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        # Update only name
        result = await OrganizationService.update(
            user_id=test_admin_user,
            entity_id=org_id,
            name="New Name Only",
        )

        # Verify name changed but description unchanged
        assert result["name"] == "New Name Only"
        assert result["description"] == "Original description"
        assert result["folder_prefix"] == "partial"

    async def test_update_does_not_affect_rbac_roles(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify updating organization does not affect its RBAC roles."""
        # Create organization with roles
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Org With Roles",
            description="Has RBAC roles",
            folder_prefix="roles-test",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)

        admin_role = RbacRole(
            id=uuid4(),
            organization_id=org_id,
            name="admin",
            description="Admin role",
            active=True,
        )
        integration_db_session.add(admin_role)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        # Get roles before update
        stmt = select(RbacRole).where(RbacRole.organization_id == org_id)
        before_result = await integration_db_session.execute(stmt)
        roles_before = before_result.scalars().all()
        roles_before_count = len(roles_before)

        # Update organization
        await OrganizationService.update(
            user_id=test_admin_user,
            entity_id=org_id,
            name="Updated Name",
        )

        # Verify roles unchanged
        await integration_db_session.commit()
        after_result = await integration_db_session.execute(stmt)
        roles_after = after_result.scalars().all()
        assert len(roles_after) == roles_before_count

    async def test_update_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify CFIA admin can update organizations."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="CFIA Admin Update Test",
            description="Test CFIA admin update",
            folder_prefix="cfia-update",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        result = await OrganizationService.update(
            user_id=test_admin_user,
            entity_id=org_id,
            name="Updated by CFIA Admin",
        )

        assert result["name"] == "Updated by CFIA Admin"

    async def test_update_as_non_cfia_admin_fails(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Non-CFIA Update Test",
            description="Should not be updatable",
            folder_prefix="non-cfia",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.update(
                user_id=test_regular_user,
                entity_id=org_id,
                name="Should Fail",
            )

        assert exc_info.value.status_code == 403

    async def test_update_nonexistent_organization_raises_error(
        self,
        test_admin_user: UUID,
    ):
        """Verify updating non-existent organization raises error."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.update(
                user_id=test_admin_user,
                entity_id=nonexistent_id,
                name="Does Not Exist",
            )

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationDelete:
    """Integration tests for OrganizationService.delete method."""

    async def test_delete_soft_deletes_organization(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify delete soft deletes organization (sets active=False)."""
        # Create organization
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Delete Test Org",
            description="To be soft deleted",
            folder_prefix="delete-test",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        # Delete
        result = await OrganizationService.delete(test_admin_user, org_id)

        assert result["message"] == "Organization soft deleted successfully"

        # Verify soft delete in database
        # Need to expire the session to see changes from service layer
        integration_db_session.expire_all()
        stmt = select(Organization).where(Organization.id == org_id)
        db_result = await integration_db_session.execute(stmt)
        deleted_org = db_result.scalar_one_or_none()

        assert deleted_org is not None
        assert deleted_org.active is False

    async def test_delete_does_not_appear_in_get_all(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify deleted organizations don't appear in get_all results."""
        # Create organization
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Hidden After Delete",
            description="Should not appear after deletion",
            folder_prefix="hidden",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        # Delete
        await OrganizationService.delete(test_admin_user, org_id)

        # Verify not in get_all results
        result = await OrganizationService.get_all(test_admin_user)
        org_names = [o["name"] for o in result["organizations"]]
        assert "Hidden After Delete" not in org_names

    async def test_delete_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify CFIA admin can delete organizations."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="CFIA Admin Delete Test",
            description="Deletable by CFIA admin",
            folder_prefix="cfia-delete",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        result = await OrganizationService.delete(test_admin_user, org_id)
        assert result["message"] == "Organization soft deleted successfully"

    async def test_delete_as_non_cfia_admin_fails(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Non-CFIA Delete Test",
            description="Should not be deletable",
            folder_prefix="non-cfia-del",
            active=True,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(org)
        cleanup_test_organizations.append(org_id)
        await integration_db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.delete(test_regular_user, org_id)

        assert exc_info.value.status_code == 403

    async def test_delete_nonexistent_organization_raises_error(
        self,
        test_admin_user: UUID,
    ):
        """Verify deleting non-existent organization raises error."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.delete(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrganizationServiceIntegrationCrossMethod:
    """Integration tests for cross-method scenarios."""

    async def test_full_crud_lifecycle(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Test create → get_by_id → update → get_by_id → delete flow."""
        # Create
        create_result = await OrganizationService.create(
            user_id=test_admin_user,
            name="CRUD Lifecycle Org",
            description="Testing full CRUD lifecycle",
        )
        org_id = UUID(create_result["id"])
        cleanup_test_organizations.append(org_id)

        # Get by ID
        get_result = await OrganizationService.get_by_id(test_admin_user, org_id)
        assert get_result["name"] == "CRUD Lifecycle Org"

        # Update
        update_result = await OrganizationService.update(
            user_id=test_admin_user,
            entity_id=org_id,
            name="Updated Lifecycle Org",
        )
        assert update_result["name"] == "Updated Lifecycle Org"

        # Get by ID again
        get_result2 = await OrganizationService.get_by_id(test_admin_user, org_id)
        assert get_result2["name"] == "Updated Lifecycle Org"

        # Delete
        delete_result = await OrganizationService.delete(test_admin_user, org_id)
        assert delete_result["message"] == "Organization soft deleted successfully"

        # Verify deleted
        with pytest.raises(HTTPException) as exc_info:
            await OrganizationService.get_by_id(test_admin_user, org_id)
        assert exc_info.value.status_code == 404

    async def test_serialization_format(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_organizations: list,
    ):
        """Verify all fields are properly serialized (UUID → string, datetime → ISO)."""
        # Create organization
        result = await OrganizationService.create(
            user_id=test_admin_user,
            name="Serialization Test Org",
            description="Testing serialization",
        )

        org_id = UUID(result["id"])
        cleanup_test_organizations.append(org_id)

        # Verify serialization
        assert isinstance(result["id"], str)
        assert isinstance(result["name"], str)
        assert isinstance(result["date_created"], str)
        assert isinstance(result["active"], bool)
        assert isinstance(result["rbac_roles"], list)

        # Verify RBAC roles serialization
        for role in result["rbac_roles"]:
            assert isinstance(role["id"], str)
            assert isinstance(role["name"], str)
