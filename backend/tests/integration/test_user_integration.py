"""
Integration tests for UserService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only

System Invariants verified:
- Each user must be associated with an organization
- Soft delete maintains referential integrity
- Organization relationship is eagerly loaded
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

from app.service.user import UserService
from app.db.model import Users
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationGetAll:
    """Integration tests for UserService.get_all method."""

    async def test_get_all_returns_active_users_only(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify that get_all returns only active users, excluding soft-deleted ones."""
        # Create active user
        active_user = Users(
            id=uuid4(),
            email="active.user@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(active_user)
        cleanup_test_users.append(active_user.id)

        # Create inactive user
        inactive_user = Users(
            id=uuid4(),
            email="inactive.user@test.com",
            organization=test_organization,
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_user)
        cleanup_test_users.append(inactive_user.id)

        await integration_db_session.commit()

        # Call service - should only return active user
        result = await UserService.get_all(test_user)

        # Verify
        assert "items" in result
        user_emails = [u["email"] for u in result["items"]]
        assert "active.user@test.com" in user_emails
        assert "inactive.user@test.com" not in user_emails

    async def test_get_all_includes_organization_relationship(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify that get_all includes organization details via eager loading."""
        # Create user with organization
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="org.test@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)

        await integration_db_session.commit()

        # Call service
        result = await UserService.get_all(test_user)

        # Verify organization details are included
        test_user_data = next(
            (u for u in result["items"] if u["email"] == "org.test@test.com"),
            None,
        )
        assert test_user_data is not None
        assert "organization_id" in test_user_data
        assert "organization_name" in test_user_data
        assert test_user_data["organization_id"] == str(test_organization)

    async def test_get_all_pagination_works(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify pagination with offset and limit works correctly."""
        # Create 10 test users
        for i in range(10):
            user = Users(
                id=uuid4(),
                email=f"pagination.user{i:02d}@test.com",
                organization=test_organization,
                active=True,
                date_created=datetime.now(timezone.utc),
                date_updated=datetime.now(timezone.utc),
            )
            integration_db_session.add(user)
            cleanup_test_users.append(user.id)

        await integration_db_session.commit()

        # Test first page
        page1 = await UserService.get_all(test_user, offset=0, limit=5)
        assert len(page1["items"]) == 5
        assert page1["offset"] == 0
        assert page1["limit"] == 5
        assert page1["has_more"] is True

        # Test second page
        page2 = await UserService.get_all(test_user, offset=5, limit=5)
        assert len(page2["items"]) == 5
        assert page2["offset"] == 5

        # Verify all our test users exist
        all_users = await UserService.get_all(test_user, limit=1000)
        user_emails = [u["email"] for u in all_users["items"]]
        for i in range(10):
            assert f"pagination.user{i:02d}@test.com" in user_emails

    async def test_get_all_filtering_by_email(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify filtering by email works correctly."""
        # Create users with specific emails
        user1 = Users(
            id=uuid4(),
            email="filter.alpha@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        user2 = Users(
            id=uuid4(),
            email="filter.beta@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user1)
        integration_db_session.add(user2)
        cleanup_test_users.extend([user1.id, user2.id])

        await integration_db_session.commit()

        # Filter by email
        result = await UserService.get_all(
            test_user, filters={"email": "filter.alpha@test.com"}
        )

        # Verify
        user_emails = [u["email"] for u in result["items"]]
        assert "filter.alpha@test.com" in user_emails
        assert "filter.beta@test.com" not in user_emails

    async def test_get_all_ordering_by_email_asc(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify ordering by email in ascending order."""
        # Create users with specific emails
        user_z = Users(
            id=uuid4(),
            email="zzz.order@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        user_a = Users(
            id=uuid4(),
            email="aaa.order@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user_z)
        integration_db_session.add(user_a)
        cleanup_test_users.extend([user_z.id, user_a.id])

        await integration_db_session.commit()

        # Get all with ordering by email ascending
        result = await UserService.get_all(
            test_user, order_by="email", order_direction="asc", limit=1000
        )

        # Verify order
        user_emails = [u["email"] for u in result["items"]]
        aaa_index = user_emails.index("aaa.order@test.com")
        zzz_index = user_emails.index("zzz.order@test.com")
        assert aaa_index < zzz_index

    async def test_get_all_as_authenticated_user_succeeds(
        self,
        test_user: UUID,
    ):
        """Verify that any authenticated user can retrieve users."""
        # Call service as regular authenticated user
        result = await UserService.get_all(test_user)

        # Verify successful response
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "total" in result
        assert "offset" in result
        assert "limit" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationGetById:
    """Integration tests for UserService.get_by_id method."""

    async def test_get_by_id_retrieves_user_with_organization(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify get_by_id retrieves user with full details including organization."""
        # Create user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="getbyid.test@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)

        await integration_db_session.commit()

        # Call service
        result = await UserService.get_by_id(test_user, user_id)

        # Verify
        assert result["id"] == str(user_id)
        assert result["email"] == "getbyid.test@test.com"
        assert result["organization_id"] == str(test_organization)
        assert "organization_name" in result
        assert result["active"] is True
        assert "date_created" in result
        assert "date_updated" in result

    async def test_get_by_id_nonexistent_user_raises_error(
        self,
        test_user: UUID,
    ):
        """Verify get_by_id raises error for non-existent user."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_by_id(test_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_inactive_user_raises_error(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify get_by_id raises error for soft-deleted (inactive) user."""
        # Create inactive user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="inactive@test.com",
            organization=test_organization,
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)

        await integration_db_session.commit()

        # Call service
        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_by_id(test_user, user_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_as_authenticated_user_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify any authenticated user can retrieve user details."""
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="auth.test@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)

        await integration_db_session.commit()

        # Should succeed without raising
        result = await UserService.get_by_id(test_user, user_id)
        assert result["id"] == str(user_id)


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationCreate:
    """Integration tests for UserService.create method."""

    async def test_create_successfully_creates_user(
        self,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify create successfully creates user with required fields."""
        # Call service
        result = await UserService.create(
            user_id=test_admin_user,
            email="newuser@test.com",
            organization=test_organization,
        )

        # Track for cleanup
        user_id = UUID(result["id"])
        cleanup_test_users.append(user_id)

        # Verify response
        assert result["email"] == "newuser@test.com"
        assert result["organization_id"] == str(test_organization)
        assert result["active"] is True
        assert "date_created" in result
        assert "date_updated" in result

    async def test_create_with_optional_default_folder_id(
        self,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify optional default_folder_id is handled correctly."""
        # Create without default_folder_id
        result = await UserService.create(
            user_id=test_admin_user,
            email="nofolder@test.com",
            organization=test_organization,
        )

        user_id = UUID(result["id"])
        cleanup_test_users.append(user_id)

        # Verify default_folder_id is None
        assert result["default_folder_id"] is None

    async def test_create_organization_ref_is_loaded(
        self,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify organization_ref is eagerly loaded in response."""
        result = await UserService.create(
            user_id=test_admin_user,
            email="orgref@test.com",
            organization=test_organization,
        )

        user_id = UUID(result["id"])
        cleanup_test_users.append(user_id)

        # Verify organization details are present
        assert "organization_id" in result
        assert "organization_name" in result
        assert result["organization_id"] == str(test_organization)

    async def test_create_as_cfia_admin_succeeds(
        self,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify CFIA admin can create users."""
        result = await UserService.create(
            user_id=test_admin_user,
            email="admin.created@test.com",
            organization=test_organization,
        )

        user_id = UUID(result["id"])
        cleanup_test_users.append(user_id)

        assert result["email"] == "admin.created@test.com"

    async def test_create_as_non_cfia_admin_fails(
        self,
        test_regular_user: UUID,
        test_organization: UUID,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        with pytest.raises(HTTPException) as exc_info:
            await UserService.create(
                user_id=test_regular_user,
                email="unauthorized@test.com",
                organization=test_organization,
            )

        assert exc_info.value.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationUpdate:
    """Integration tests for UserService.update method."""

    async def test_update_successfully_updates_fields(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify update successfully updates email."""
        # Create user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="original@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        # Update
        result = await UserService.update(
            user_id=test_admin_user,
            entity_id=user_id,
            email="updated@test.com",
        )

        # Verify
        assert result["email"] == "updated@test.com"

    async def test_update_partial_updates_work(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify partial updates work (only updating some fields)."""
        # Create user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="partial@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        # Update only active status
        result = await UserService.update(
            user_id=test_admin_user,
            entity_id=user_id,
            active=False,
        )

        # Verify email unchanged but active updated
        assert result["email"] == "partial@test.com"
        assert result["active"] is False

    async def test_update_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify CFIA admin can update users."""
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="admin.update@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        result = await UserService.update(
            user_id=test_admin_user,
            entity_id=user_id,
            email="admin.updated@test.com",
        )

        assert result["email"] == "admin.updated@test.com"

    async def test_update_as_non_cfia_admin_fails(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="no.update@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await UserService.update(
                user_id=test_regular_user,
                entity_id=user_id,
                email="should.fail@test.com",
            )

        assert exc_info.value.status_code == 403

    async def test_update_nonexistent_user_raises_error(
        self,
        test_admin_user: UUID,
    ):
        """Verify updating non-existent user raises error."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await UserService.update(
                user_id=test_admin_user,
                entity_id=nonexistent_id,
                email="does.not.exist@test.com",
            )

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationDelete:
    """Integration tests for UserService.delete method."""

    async def test_delete_soft_deletes_user(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify delete soft deletes user (sets active=False)."""
        # Create user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="delete.test@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        # Delete
        result = await UserService.delete(test_admin_user, user_id)

        assert result["message"] == "User soft deleted successfully"

        # Verify soft delete in database
        integration_db_session.expire_all()
        stmt = select(Users).where(Users.id == user_id)
        db_result = await integration_db_session.execute(stmt)
        deleted_user = db_result.scalar_one_or_none()

        assert deleted_user is not None
        assert deleted_user.active is False

    async def test_delete_does_not_appear_in_get_all(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify deleted users don't appear in get_all results."""
        # Create user
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="hidden.after.delete@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        # Delete
        await UserService.delete(test_admin_user, user_id)

        # Verify not in get_all results
        result = await UserService.get_all(test_admin_user)
        user_emails = [u["email"] for u in result["items"]]
        assert "hidden.after.delete@test.com" not in user_emails

    async def test_delete_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify CFIA admin can delete users."""
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="admin.delete@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        result = await UserService.delete(test_admin_user, user_id)
        assert result["message"] == "User soft deleted successfully"

    async def test_delete_as_non_cfia_admin_fails(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify non-CFIA admin gets 403 Forbidden."""
        user_id = uuid4()
        user = Users(
            id=user_id,
            email="no.delete@test.com",
            organization=test_organization,
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        cleanup_test_users.append(user_id)
        await integration_db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await UserService.delete(test_regular_user, user_id)

        assert exc_info.value.status_code == 403

    async def test_delete_nonexistent_user_raises_error(
        self,
        test_admin_user: UUID,
    ):
        """Verify deleting non-existent user raises error."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await UserService.delete(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestUserServiceIntegrationCrossMethod:
    """Integration tests for cross-method scenarios."""

    async def test_full_crud_lifecycle(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Test create → get_by_id → update → get_by_id → delete flow."""
        # Create
        create_result = await UserService.create(
            user_id=test_admin_user,
            email="lifecycle@test.com",
            organization=test_organization,
        )
        user_id = UUID(create_result["id"])
        cleanup_test_users.append(user_id)

        # Get by ID
        get_result = await UserService.get_by_id(test_admin_user, user_id)
        assert get_result["email"] == "lifecycle@test.com"

        # Update
        update_result = await UserService.update(
            user_id=test_admin_user,
            entity_id=user_id,
            email="lifecycle.updated@test.com",
        )
        assert update_result["email"] == "lifecycle.updated@test.com"

        # Get by ID again
        get_result2 = await UserService.get_by_id(test_admin_user, user_id)
        assert get_result2["email"] == "lifecycle.updated@test.com"

        # Delete
        delete_result = await UserService.delete(test_admin_user, user_id)
        assert delete_result["message"] == "User soft deleted successfully"

        # Verify deleted
        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_by_id(test_admin_user, user_id)
        assert exc_info.value.status_code == 404

    async def test_serialization_format(
        self,
        test_admin_user: UUID,
        test_organization: UUID,
        cleanup_test_users: list,
    ):
        """Verify all fields are properly serialized (UUID → string, datetime → ISO)."""
        # Create user
        result = await UserService.create(
            user_id=test_admin_user,
            email="serialize@test.com",
            organization=test_organization,
        )

        user_id = UUID(result["id"])
        cleanup_test_users.append(user_id)

        # Verify serialization
        assert isinstance(result["id"], str)
        assert isinstance(result["email"], str)
        assert isinstance(result["organization_id"], str)
        assert isinstance(result["date_created"], str)
        assert isinstance(result["date_updated"], str)
        assert isinstance(result["active"], bool)
        
        # Verify organization_name is included
        assert "organization_name" in result
