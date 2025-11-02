"""
Integration tests for Batch Upload API endpoints.

These tests use real database, DBOS workflows, and blob storage (no mocks) to test
the complete batch upload flow end-to-end.

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Azurite container running: docker compose up -d nachet-blob
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_batch_upload_api.py -v -m integration
"""

import pytest
import pytest_asyncio
import base64
import os
from dotenv import load_dotenv
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.service.batch_upload import BatchUploadService
from app.db.model import (
    Picture,
    ImageProcessingState,
    Folder,
    BatchUploadSession,
    Seed,
)
from app.service.constants import ProcessingStatus
from app.model.batch_upload import (
    BatchUploadImageRequest,
)
from app.service.auth import User
from tests.fixtures.test_images import get_test_seed_image

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest_asyncio.fixture()
async def test_folder(
    integration_db_session: AsyncSession,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
    cleanup_test_folders: list,
):
    """Create a test folder for batch uploads."""
    folder = Folder(
        id=uuid4(),
        name="Batch Upload Test Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-batch",
        description="Test folder for batch upload integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    cleanup_test_folders.append(folder.id)
    yield folder.id


@pytest_asyncio.fixture()
async def test_seed(
    integration_db_session: AsyncSession,
    cleanup_test_seeds: list,
):
    """Create a test seed for batch uploads."""
    seed = Seed(
        id=uuid4(),
        family="Poaceae",
        genus="Triticum",
        species="aestivum",
        name_code="TRZAX",
        original_ista_2025="TRZAX",  # Required field
        active=True,
    )
    integration_db_session.add(seed)
    await integration_db_session.commit()
    await integration_db_session.refresh(seed)
    cleanup_test_seeds.append(seed.id)
    yield seed.id


@pytest.fixture()
def test_image_base64():
    """Load test PNG image as base64 with data URL prefix."""
    image_bytes = get_test_seed_image()
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"


def create_mock_user(user_id: UUID) -> User:
    """
    Create a mock User object for testing.

    The User object is a Pydantic model from app.service.auth
    that contains JWT claims and authentication info.
    """
    return User(
        aud="test-audience",
        iss="https://login.microsoftonline.com/test/v2.0",
        iat=int(datetime.now(timezone.utc).timestamp()),
        nbf=int(datetime.now(timezone.utc).timestamp()),
        exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        oid=str(user_id),
        sub=str(user_id),
        email="test@example.com",
        ver="2.0",
        claims={},
        access_token="mock-token",
        is_guest=False,
    )


@pytest_asyncio.fixture()
async def cleanup_test_sessions(integration_db_session: AsyncSession):
    """Cleanup fixture to track and remove test batch upload sessions."""
    created_session_ids = []

    yield created_session_ids

    # Cleanup: hard delete sessions
    if created_session_ids:
        from sqlalchemy import delete

        stmt = delete(BatchUploadSession).where(
            BatchUploadSession.id.in_(created_session_ids)
        )
        await integration_db_session.execute(stmt)
        await integration_db_session.flush()


@pytest_asyncio.fixture()
async def cleanup_test_pictures_and_states(integration_db_session: AsyncSession):
    """
    Cleanup fixture for pictures and their processing states.

    Deletes in proper order: ImageProcessingState → Picture
    """
    created_picture_ids = []

    yield created_picture_ids

    # Cleanup: delete in proper order
    if created_picture_ids:
        from sqlalchemy import delete

        # Delete processing states first
        stmt_states = delete(ImageProcessingState).where(
            ImageProcessingState.picture_id.in_(created_picture_ids)
        )
        await integration_db_session.execute(stmt_states)

        # Delete pictures
        stmt_pictures = delete(Picture).where(Picture.id.in_(created_picture_ids))
        await integration_db_session.execute(stmt_pictures)

        await integration_db_session.flush()


@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUploadAPIInitialize:
    """Integration tests for POST /new-batch-import endpoint."""

    async def test_initialize_success(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        cleanup_test_sessions: list,
    ):
        """
        Test successful batch session initialization.

        Verifies:
        - Session created in database
        - Returns session_id
        - Sets correct expiration (24h)
        - All fields populated correctly
        """
        # Act
        result = await BatchUploadService.initialize_batch_session(
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=10,
        )

        # Assert response
        assert "session_id" in result
        session_id = UUID(result["session_id"])
        cleanup_test_sessions.append(session_id)

        # Verify database record
        stmt = select(BatchUploadSession).where(BatchUploadSession.id == session_id)
        db_result = await integration_db_session.execute(stmt)
        session = db_result.scalar_one()

        assert session is not None
        assert session.user_id == test_admin_user
        assert session.folder_id == test_folder
        assert session.file_count == 10
        assert session.uploaded_count == 0
        assert session.duplicate_count == 0
        assert session.active is True

        # Verify 24-hour expiration
        now = datetime.now(timezone.utc)
        expected_expiration = now + timedelta(hours=24)
        time_diff = abs((session.expires_at - expected_expiration).total_seconds())
        assert time_diff < 10  # Within 10 seconds

    async def test_initialize_file_count_exceeds_limit(
        self,
        test_admin_user: UUID,
        test_folder: UUID,
    ):
        """Test that file_count > 1000 raises validation error."""
        with pytest.raises(ValueError) as exc_info:
            await BatchUploadService.initialize_batch_session(
                user_id=test_admin_user,
                folder_id=test_folder,
                file_count=1001,  # Exceeds limit
            )

        # After security fix (CWE-209), errors are sanitized
        assert "failed to initialize upload session" in str(exc_info.value).lower()

    async def test_initialize_folder_not_found(
        self,
        test_admin_user: UUID,
    ):
        """Test that non-existent folder raises error."""
        nonexistent_folder = uuid4()

        # After security fix (CWE-209), errors are sanitized to ValueError
        with pytest.raises(ValueError, match="Failed to initialize upload session"):
            await BatchUploadService.initialize_batch_session(
                user_id=test_admin_user,
                folder_id=nonexistent_folder,
                file_count=10,
            )

    async def test_initialize_folder_wrong_owner(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,  # Non-admin user
        test_admin_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        cleanup_test_folders: list,
    ):
        """Test that user cannot use another user's folder."""
        # Create folder owned by admin
        admin_folder_id = uuid4()
        admin_folder = Folder(
            id=admin_folder_id,
            name="Admin Only Folder",
            user_id=test_admin_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            folder_prefix="admin-only",
            description="Admin folder",
            active=True,
        )
        integration_db_session.add(admin_folder)
        await integration_db_session.commit()
        cleanup_test_folders.append(admin_folder_id)

        # Try to use admin's folder as regular user (should fail due to RBAC)
        # After security fix (CWE-209), errors are sanitized to ValueError
        with pytest.raises(ValueError, match="Failed to initialize upload session"):
            await BatchUploadService.initialize_batch_session(
                user_id=test_regular_user,
                folder_id=admin_folder_id,  # Use the UUID directly
                file_count=10,
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUploadAPIUpload:
    """Integration tests for POST /upload-picture endpoint."""

    async def test_upload_success_creates_picture_and_workflow(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_seed: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
        cleanup_test_pictures_and_states: list,
    ):
        """
        Test successful image upload in batch.

        Verifies:
        - Picture record created
        - ImageProcessingState created
        - DBOS workflow enqueued
        - Session counts updated
        - Returns workflow_id and picture_id
        """
        # Arrange: Create session
        session_result = await BatchUploadService.initialize_batch_session(
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=1,
        )
        session_id = UUID(session_result["session_id"])
        cleanup_test_sessions.append(session_id)

        # Create mock user object (required by service)
        user = create_mock_user(test_admin_user)

        # Create request
        request = BatchUploadImageRequest(
            session_id=str(session_id),
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="TEST-SAMPLE-001",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        # Act
        result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )

        # Assert response
        assert result["success"] is True
        assert "workflow_id" in result
        assert "picture_id" in result
        picture_id = UUID(result["picture_id"])
        cleanup_test_pictures_and_states.append(picture_id)

        # Verify Picture created
        picture_stmt = select(Picture).where(Picture.id == picture_id)
        picture_result = await integration_db_session.execute(picture_stmt)
        picture = picture_result.scalar_one()

        assert picture is not None
        assert picture.folder_id == test_folder
        assert picture.user_id == test_admin_user
        assert picture.name == "TEST-SAMPLE-001"  # sample_id becomes name
        assert picture.single_species_image == test_seed
        assert picture.width == 638
        assert picture.height == 559

        # Verify ImageProcessingState created
        state_stmt = select(ImageProcessingState).where(
            ImageProcessingState.picture_id == picture_id
        )
        state_result = await integration_db_session.execute(state_stmt)
        state = state_result.scalar_one()

        assert state is not None
        assert state.status == ProcessingStatus.PENDING.value
        assert state.user_id == test_admin_user

        # Verify session counts updated
        session_stmt = select(BatchUploadSession).where(
            BatchUploadSession.id == session_id
        )
        session_result = await integration_db_session.execute(session_stmt)
        session = session_result.scalar_one()

        assert session.uploaded_count == 1
        assert session.duplicate_count == 0
        assert session.active is False  # Should be inactive (1/1 uploaded)

    async def test_upload_session_not_found(
        self,
        test_admin_user: UUID,
        test_seed: UUID,
        test_image_base64: str,
    ):
        """Test that non-existent session returns error."""
        user = create_mock_user(test_admin_user)

        request = BatchUploadImageRequest(
            session_id=str(uuid4()),  # Non-existent
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="TEST",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )

        assert result["success"] is False
        assert "session" in result["error"].lower()

    async def test_upload_session_expired(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_seed: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
    ):
        """Test that expired session returns error."""
        # Create expired session (expires_at in the past)
        expired_session = BatchUploadSession(
            id=uuid4(),
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=10,
            uploaded_count=0,
            duplicate_count=0,
            active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(expired_session)
        await integration_db_session.commit()
        cleanup_test_sessions.append(expired_session.id)

        # Try to upload
        user = create_mock_user(test_admin_user)

        request = BatchUploadImageRequest(
            session_id=str(expired_session.id),
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="TEST",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )

        assert result["success"] is False
        assert "expired" in result["error"].lower()

    async def test_upload_session_inactive(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_seed: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
    ):
        """Test that inactive session returns error."""
        # Create inactive session
        inactive_session = BatchUploadSession(
            id=uuid4(),
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=10,
            uploaded_count=10,
            duplicate_count=0,
            active=False,  # Inactive
            expires_at=datetime.now(timezone.utc) + timedelta(hours=23),
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_session)
        await integration_db_session.commit()
        cleanup_test_sessions.append(inactive_session.id)

        # Try to upload
        user = create_mock_user(test_admin_user)

        request = BatchUploadImageRequest(
            session_id=str(inactive_session.id),
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="TEST",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )

        assert result["success"] is False
        assert "inactive" in result["error"].lower()

    async def test_upload_seed_not_found(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
    ):
        """Test that non-existent seed returns error."""
        # Create session
        session_result = await BatchUploadService.initialize_batch_session(
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=1,
        )
        session_id = UUID(session_result["session_id"])
        cleanup_test_sessions.append(session_id)

        # Try to upload with non-existent seed
        user = create_mock_user(test_admin_user)

        request = BatchUploadImageRequest(
            session_id=str(session_id),
            seed_id=str(uuid4()),  # Non-existent seed
            tray_code="A",
            sample_id="TEST",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )

        assert result["success"] is False
        # After security fix (CWE-209), errors are sanitized
        assert "failed to process image upload" in result["error"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUploadAPIDuplicateHandling:
    """Integration tests for duplicate image handling."""

    async def test_upload_duplicate_image_increments_counters(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_seed: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
        cleanup_test_pictures_and_states: list,
    ):
        """
        Test that uploading the same image twice:
        - Creates only ONE picture record
        - Increments both uploaded_count and duplicate_count
        - Returns error on second upload with existing picture_id
        """
        # Arrange: Create session with file_count=2
        session_result = await BatchUploadService.initialize_batch_session(
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=2,
        )
        session_id = UUID(session_result["session_id"])
        cleanup_test_sessions.append(session_id)

        user = create_mock_user(test_admin_user)

        # First upload (should succeed)
        request1 = BatchUploadImageRequest(
            session_id=str(session_id),
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="ORIGINAL-001",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        result1 = await BatchUploadService.upload_picture_batch(
            request=request1,
            user=user,
        )
        assert result1["success"] is True
        original_picture_id = UUID(result1["picture_id"])
        cleanup_test_pictures_and_states.append(original_picture_id)

        # Second upload (same image, should detect duplicate)
        request2 = BatchUploadImageRequest(
            session_id=str(session_id),
            seed_id=str(test_seed),
            tray_code="B",
            sample_id="DUPLICATE-002",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,  # Same image
        )

        result2 = await BatchUploadService.upload_picture_batch(
            request=request2,
            user=user,
        )

        # Assert duplicate detected
        assert result2["success"] is False
        assert "duplicate" in result2["error"].lower()
        assert str(original_picture_id) in result2["error"]

        # Verify session counts
        session_stmt = select(BatchUploadSession).where(
            BatchUploadSession.id == session_id
        )
        session_result = await integration_db_session.execute(session_stmt)
        session = session_result.scalar_one()

        assert session.uploaded_count == 2  # Both uploads counted
        assert session.duplicate_count == 1  # One duplicate
        assert session.active is False  # Completed (2/2)

        # Verify only ONE picture exists
        count_stmt = select(Picture).where(Picture.folder_id == test_folder)
        count_result = await integration_db_session.execute(count_stmt)
        pictures = count_result.scalars().all()
        assert len(pictures) == 1
        assert pictures[0].id == original_picture_id


@pytest.mark.integration
@pytest.mark.asyncio
class TestBatchUploadAPISessionLifecycle:
    """Integration tests for batch session lifecycle."""

    async def test_session_becomes_inactive_when_file_count_reached(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_folder: UUID,
        test_seed: UUID,
        test_image_base64: str,
        cleanup_test_sessions: list,
        cleanup_test_pictures_and_states: list,
    ):
        """
        Test that session becomes inactive when uploaded_count reaches file_count.
        """
        # Create session with file_count=1
        session_result = await BatchUploadService.initialize_batch_session(
            user_id=test_admin_user,
            folder_id=test_folder,
            file_count=1,
        )
        session_id = UUID(session_result["session_id"])
        cleanup_test_sessions.append(session_id)

        # Verify session is active
        stmt = select(BatchUploadSession).where(BatchUploadSession.id == session_id)
        result = await integration_db_session.execute(stmt)
        session = result.scalar_one()
        assert session.active is True

        # Upload one image
        user = create_mock_user(test_admin_user)

        request = BatchUploadImageRequest(
            session_id=str(session_id),
            seed_id=str(test_seed),
            tray_code="A",
            sample_id="TEST-001",
            device_brand_id="00000000-0000-0000-0000-000000000001",
            device_model_id="00000000-0000-0000-0000-000000000002",
            device_lens_id="00000000-0000-0000-0000-000000000003",
            magnification=10.0,
            image=test_image_base64,
        )

        upload_result = await BatchUploadService.upload_picture_batch(
            request=request,
            user=user,
        )
        assert upload_result["success"] is True
        cleanup_test_pictures_and_states.append(UUID(upload_result["picture_id"]))

        # Verify session is now inactive (need to refresh from DB)
        integration_db_session.expire_all()  # Clear cache (synchronous)
        result = await integration_db_session.execute(stmt)
        session = result.scalar_one()
        assert session.active is False
        assert session.uploaded_count == 1
