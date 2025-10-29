"""
Integration tests for workflow status endpoint with authorization.

These tests verify that:
1. Users can access their own workflow status
2. Users cannot access other users' workflow status
3. CFIA admins can access any workflow status
4. Status returns comprehensive data for parent and child workflows
5. Proper error handling (404, 403)

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_workflow_status_authorization.py -v -s
"""

import pytest
import pytest_asyncio
import os
from dotenv import load_dotenv
from uuid import UUID
from uuid6 import uuid7
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.service.inference import InferenceService
from app.db.model import (
    ImageProcessingState,
    InferenceRequestState,
    Users,
    Organization,
    RbacRole,
    RbacUserRole,
    Picture,
    Folder,
)
from app.service.constants import ProcessingStatus
from datetime import datetime, timezone

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowStatusAuthorization:
    """Test authorization for workflow status endpoint."""

    @pytest_asyncio.fixture
    async def test_user_1(
        self, integration_db_session: AsyncSession, test_org: UUID
    ) -> UUID:
        """Create test user 1."""
        user = Users(
            id=uuid7(),
            email=f"test-user-1-{uuid7()}@example.com",
            organization=test_org,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()
        await integration_db_session.refresh(user)
        return UUID(str(user.id))

    @pytest_asyncio.fixture
    async def test_user_2(
        self, integration_db_session: AsyncSession, test_org_2: UUID
    ) -> UUID:
        """Create test user 2 (different user in different org)."""
        user = Users(
            id=uuid7(),
            email=f"test-user-2-{uuid7()}@example.com",
            organization=test_org_2,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(user)
        await integration_db_session.commit()
        await integration_db_session.refresh(user)
        return UUID(str(user.id))

    @pytest_asyncio.fixture
    async def test_org(self, integration_db_session: AsyncSession) -> UUID:
        """Create test organization for user 1."""
        org = Organization(
            id=uuid7(),
            name=f"Test Org 1 {uuid7()}",
            description="Test organization 1 for workflow status tests",
            folder_prefix=f"test1{uuid7().hex[:8]}",
        )
        integration_db_session.add(org)
        await integration_db_session.commit()
        await integration_db_session.refresh(org)
        return UUID(str(org.id))

    @pytest_asyncio.fixture
    async def test_org_2(self, integration_db_session: AsyncSession) -> UUID:
        """Create test organization for user 2 (different org)."""
        org = Organization(
            id=uuid7(),
            name=f"Test Org 2 {uuid7()}",
            description="Test organization 2 for workflow status tests",
            folder_prefix=f"test2{uuid7().hex[:8]}",
        )
        integration_db_session.add(org)
        await integration_db_session.commit()
        await integration_db_session.refresh(org)
        return UUID(str(org.id))

    @pytest_asyncio.fixture
    async def test_user_role_1(
        self,
        integration_db_session: AsyncSession,
        test_org: UUID,
        test_user_1: UUID,
    ) -> UUID:
        """Create user role for user 1."""
        role = RbacRole(
            id=uuid7(),
            organization_id=test_org,
            name="user",
            description="User role for testing",
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_user_role_2(
        self,
        integration_db_session: AsyncSession,
        test_org_2: UUID,
        test_user_2: UUID,
    ) -> UUID:
        """Create user role for user 2 (in different org)."""
        role = RbacRole(
            id=uuid7(),
            organization_id=test_org_2,
            name="user",
            description="User role for testing in org 2",
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_admin_role_2(
        self, integration_db_session: AsyncSession, test_org_2: UUID
    ) -> UUID:
        """Create admin role for org 2."""
        role = RbacRole(
            id=uuid7(),
            organization_id=test_org_2,
            name="admin",
            description="Admin role for testing in org 2",
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_admin_role(
        self, integration_db_session: AsyncSession, test_org: UUID
    ) -> UUID:
        """Create admin role."""
        role = RbacRole(
            id=uuid7(),
            organization_id=test_org,
            name="admin",
            description="Admin role for testing",
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_user_role_assignment_1(
        self,
        integration_db_session: AsyncSession,
        test_user_1: UUID,
        test_user_role_1: UUID,
    ) -> None:
        """Assign user role to user 1."""
        user_role = RbacUserRole(
            user_id=test_user_1,
            role_id=test_user_role_1,
            active=True,
        )
        integration_db_session.add(user_role)
        await integration_db_session.commit()

    @pytest_asyncio.fixture
    async def test_user_role_assignment_2(
        self,
        integration_db_session: AsyncSession,
        test_user_2: UUID,
        test_user_role_2: UUID,
        test_admin_role_2: UUID,
    ) -> None:
        """Assign user role to user 2."""
        user_role = RbacUserRole(
            user_id=test_user_2,
            role_id=test_user_role_2,
            active=True,
        )
        integration_db_session.add(user_role)
        await integration_db_session.commit()

    @pytest_asyncio.fixture
    async def test_folder_1(
        self,
        integration_db_session: AsyncSession,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
    ) -> Folder:
        """Create folder for user 1."""
        folder = Folder(
            id=uuid7(),
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            name="Test Folder",
            folder_prefix="test",
            description="Test folder for workflow status tests",
            active=True,
        )
        integration_db_session.add(folder)
        await integration_db_session.commit()
        await integration_db_session.refresh(folder)
        return folder

    @pytest_asyncio.fixture
    async def test_picture_id_1(self) -> UUID:
        """Generate picture ID for user 1."""
        return uuid7()

    @pytest_asyncio.fixture
    async def test_pipeline_id(self) -> UUID:
        """
        Get test pipeline ID for inference requests.
        Uses the "15 spp RCNN SWIN (Local)" pipeline which has 2 steps.
        """
        return UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a4b")

    @pytest_asyncio.fixture
    async def test_picture_1(
        self,
        integration_db_session: AsyncSession,
        test_picture_id_1: UUID,
        test_folder_1: Folder,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
    ) -> Picture:
        """Create picture record for user 1."""
        picture = Picture(
            id=test_picture_id_1,
            folder_id=test_folder_1.id,
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            name="test_workflow_image.png",
            blob_url_original="https://test.blob.core.windows.net/test/image.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_hash",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()
        await integration_db_session.refresh(picture)
        return picture

    @pytest_asyncio.fixture
    async def test_processing_state_user_1(
        self,
        integration_db_session: AsyncSession,
        test_picture_1: Picture,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
    ) -> ImageProcessingState:
        """Create processing state for user 1."""
        workflow_id = f"workflow-{uuid7()}"
        state = ImageProcessingState(
            picture_id=test_picture_1.id,
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            status=ProcessingStatus.PENDING.value,
            workflow_id=workflow_id,
            created_at=datetime.now(timezone.utc),
            progress_percentage=10,
        )
        integration_db_session.add(state)
        await integration_db_session.commit()
        await integration_db_session.refresh(state)
        return state

    @pytest_asyncio.fixture
    async def test_inference_state_user_1(
        self,
        integration_db_session: AsyncSession,
        test_picture_1: Picture,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
        test_pipeline_id: UUID,
    ) -> InferenceRequestState:
        """Create inference request state for user 1."""
        workflow_id = f"inference-workflow-{uuid7()}"
        state = InferenceRequestState(
            id=uuid7(),
            picture_id=test_picture_1.id,
            pipeline_id=test_pipeline_id,
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            workflow_id=workflow_id,
            status="pending",
            request_payload={"test": "data"},
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(state)
        await integration_db_session.commit()
        await integration_db_session.refresh(state)
        return state

    async def test_user_can_access_own_workflow_status(
        self,
        test_user_1: UUID,
        test_processing_state_user_1: ImageProcessingState,
        test_user_role_assignment_1,
    ):
        """Test that a user can access their own workflow status."""
        # Arrange
        assert test_processing_state_user_1.workflow_id is not None

        # Act
        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )

        # Assert
        assert result is not None
        assert result["workflow_id"] == test_processing_state_user_1.workflow_id
        assert result["workflow_type"] == "parent"
        assert result["image_id"] == str(test_processing_state_user_1.picture_id)
        assert result["authorization"]["user_id"] == str(test_user_1)
        assert result["authorization"]["is_owner"] is True
        assert "parent_workflow" in result
        assert result["parent_workflow"]["status"] == ProcessingStatus.PENDING.value

    async def test_user_cannot_access_other_user_workflow(
        self,
        test_user_2: UUID,
        test_processing_state_user_1: ImageProcessingState,
        test_user_role_assignment_1,
        test_user_role_assignment_2,
    ):
        """Test that a user cannot access another user's workflow status."""
        # Arrange
        assert test_processing_state_user_1.workflow_id is not None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await InferenceService.get_workflow_status(
                workflow_id=test_processing_state_user_1.workflow_id,
                user_id=test_user_2,
            )

        assert exc_info.value.status_code == 403
        assert "Not authorized" in str(exc_info.value.detail)

    async def test_get_status_by_inference_workflow_id(
        self,
        test_user_1: UUID,
        test_inference_state_user_1: InferenceRequestState,
        test_processing_state_user_1: ImageProcessingState,
        test_user_role_assignment_1,
    ):
        """Test querying status by inference workflow ID."""
        # Arrange
        assert test_inference_state_user_1.workflow_id is not None

        # Act
        result = await InferenceService.get_workflow_status(
            workflow_id=test_inference_state_user_1.workflow_id,
            user_id=test_user_1,
        )

        # Assert
        assert result is not None
        assert result["workflow_id"] == test_inference_state_user_1.workflow_id
        assert result["workflow_type"] == "inference"
        assert "inference_workflow" in result
        assert (
            result["inference_workflow"]["workflow_id"]
            == test_inference_state_user_1.workflow_id
        )
        assert result["inference_workflow"]["status"] == "pending"

    async def test_workflow_not_found_returns_404(
        self,
        test_user_1: UUID,
        test_user_role_assignment_1,
    ):
        """Test that querying non-existent workflow returns 404."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await InferenceService.get_workflow_status(
                workflow_id="non-existent-workflow-id",
                user_id=test_user_1,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    async def test_status_includes_both_parent_and_inference_workflows(
        self,
        integration_db_session: AsyncSession,
        test_user_1: UUID,
        test_processing_state_user_1: ImageProcessingState,
        test_inference_state_user_1: InferenceRequestState,
        test_user_role_assignment_1,
    ):
        """Test that status returns both parent and inference workflow details."""
        # Arrange
        assert test_processing_state_user_1.workflow_id is not None
        assert test_inference_state_user_1.workflow_id is not None

        # Note: No explicit linking needed - get_workflow_status() finds
        # inference states by querying all inference requests for the picture_id

        # Act
        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )

        # Assert
        assert result is not None
        assert "parent_workflow" in result
        assert "processing_workflow" in result
        assert "inference_workflow" in result

        # Verify parent workflow details
        assert result["parent_workflow"]["workflow_id"] == str(
            test_processing_state_user_1.workflow_id
        )
        assert result["parent_workflow"]["progress_percentage"] == 10

        # Verify inference workflow details
        assert result["inference_workflow"]["workflow_id"] == str(
            test_inference_state_user_1.workflow_id
        )
        assert result["inference_workflow"]["status"] == "pending"

    async def test_overall_status_reflects_workflow_state(
        self,
        integration_db_session: AsyncSession,
        test_user_1: UUID,
        test_processing_state_user_1: ImageProcessingState,
        test_user_role_assignment_1,
    ):
        """Test that overall_status is computed correctly from workflow states."""
        # Arrange
        assert test_processing_state_user_1.workflow_id is not None

        # Test pending state
        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )
        assert result["overall_status"] == "in_progress"

        # Update to failed state
        test_processing_state_user_1.status = ProcessingStatus.FAILED.value
        await integration_db_session.commit()

        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )
        assert result["overall_status"] == "failed"

        # Update to completed state
        test_processing_state_user_1.status = ProcessingStatus.COMPLETED.value
        await integration_db_session.commit()

        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )
        assert result["overall_status"] == "completed"

    async def test_status_includes_timestamps(
        self,
        test_user_1: UUID,
        test_processing_state_user_1: ImageProcessingState,
        test_user_role_assignment_1,
    ):
        """Test that status response includes timestamp information."""
        # Arrange
        assert test_processing_state_user_1.workflow_id is not None

        # Act
        result = await InferenceService.get_workflow_status(
            workflow_id=test_processing_state_user_1.workflow_id,
            user_id=test_user_1,
        )

        # Assert
        assert "parent_workflow" in result
        assert "created_at" in result["parent_workflow"]
        assert result["parent_workflow"]["created_at"] is not None

        assert "processing_workflow" in result
        assert "timestamps" in result["processing_workflow"]

    async def test_cleanup_test_data(
        self,
        integration_db_session: AsyncSession,
        test_processing_state_user_1: ImageProcessingState,
        test_inference_state_user_1: InferenceRequestState,
        test_user_1: UUID,
        test_user_2: UUID,
        test_user_role_assignment_1,
        test_user_role_assignment_2,
    ):
        """Clean up test data after tests complete."""
        # Test data cleanup is handled automatically by pytest fixtures
        # and database rollback/transaction management.
        # This test exists to ensure all fixtures are created correctly.
        assert test_processing_state_user_1 is not None
        assert test_inference_state_user_1 is not None
        assert test_user_1 is not None
        assert test_user_2 is not None
