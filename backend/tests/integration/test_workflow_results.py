"""
Integration tests for workflow results endpoint with authorization.

These tests verify that:
1. Users can access their own workflow results
2. Users cannot access other users' workflow results
3. Results are properly formatted as ApiInferenceResponse
4. Proper error handling (404, 403, 400)
5. Results endpoint only returns data for completed workflows

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_workflow_results.py -v -s
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
    Users,
    Organization,
    RbacRole,
    RbacUserRole,
    Picture,
    Folder,
    Annotation,
)
from datetime import datetime, timezone

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowResults:
    """Test workflow results endpoint with authorization."""

    @pytest_asyncio.fixture
    async def test_user_1(
        self, integration_db_session: AsyncSession, test_org: UUID
    ) -> UUID:
        """Create test user 1."""
        user = Users(
            id=uuid7(),
            email=f"test-user-results-1-{uuid7()}@example.com",
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
            email=f"test-user-results-2-{uuid7()}@example.com",
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
            name=f"Test Org Results 1 {uuid7()}",
            description="Test organization 1 for workflow results tests",
            folder_prefix=f"testres1{uuid7().hex[:8]}",
        )
        integration_db_session.add(org)
        await integration_db_session.commit()
        await integration_db_session.refresh(org)
        return UUID(str(org.id))

    @pytest_asyncio.fixture
    async def test_org_2(self, integration_db_session: AsyncSession) -> UUID:
        """Create test organization for user 2."""
        org = Organization(
            id=uuid7(),
            name=f"Test Org Results 2 {uuid7()}",
            description="Test organization 2 for workflow results tests",
            folder_prefix=f"testres2{uuid7().hex[:8]}",
        )
        integration_db_session.add(org)
        await integration_db_session.commit()
        await integration_db_session.refresh(org)
        return UUID(str(org.id))

    @pytest_asyncio.fixture
    async def test_admin_role(
        self, integration_db_session: AsyncSession, test_org: UUID
    ) -> UUID:
        """Create admin role for org 1."""
        role = RbacRole(
            id=uuid7(),
            name="admin",  # Must be exactly "admin" for get_user_org_roles()
            description="Test admin role",
            organization_id=test_org,
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
            name="admin",  # Must be exactly "admin" for get_user_org_roles()
            description="Test admin role 2",
            organization_id=test_org_2,
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_user_role_1(
        self, integration_db_session: AsyncSession, test_org: UUID
    ) -> UUID:
        """Create user role for org 1."""
        role = RbacRole(
            id=uuid7(),
            name="user",  # Must be exactly "user" for get_user_org_roles()
            description="Test user role",
            organization_id=test_org,
            active=True,
        )
        integration_db_session.add(role)
        await integration_db_session.commit()
        await integration_db_session.refresh(role)
        return UUID(str(role.id))

    @pytest_asyncio.fixture
    async def test_user_role_2(
        self, integration_db_session: AsyncSession, test_org_2: UUID
    ) -> UUID:
        """Create user role for org 2."""
        role = RbacRole(
            id=uuid7(),
            name="user",  # Must be exactly "user" for get_user_org_roles()
            description="Test user role 2",
            organization_id=test_org_2,
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
            name="Test Folder Results",
            folder_prefix="testres",
            description="Test folder for workflow results tests",
            active=True,
        )
        integration_db_session.add(folder)
        await integration_db_session.commit()
        await integration_db_session.refresh(folder)
        return folder

    @pytest_asyncio.fixture
    async def test_pipeline_id(self) -> UUID:
        """
        Get the appropriate test pipeline ID based on NACHET_ENV.

        - NACHET_ENV="local": Uses "15 spp RCNN SWIN (Local)" pipeline
        - NACHET_ENV="ci"/"test": Uses "15 spp RCNN SWIN" pipeline
        """
        from tests.integration.pipeline_config import get_pipeline_id_for_test

        return get_pipeline_id_for_test(species_count=15)

    @pytest_asyncio.fixture
    async def test_picture_1(
        self,
        integration_db_session: AsyncSession,
        test_folder_1: Folder,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
    ) -> Picture:
        """Create picture record for user 1."""
        picture = Picture(
            id=uuid7(),
            folder_id=test_folder_1.id,
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            name="test_results_image.png",
            blob_url_original="https://test.blob.core.windows.net/test/results.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_hash_results",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()
        await integration_db_session.refresh(picture)
        return picture

    @pytest_asyncio.fixture
    async def test_workflow_id_1(self) -> UUID:
        """Generate workflow ID for user 1 (this will be the annotation_id)."""
        return uuid7()

    @pytest_asyncio.fixture
    async def test_annotation_with_results(
        self,
        integration_db_session: AsyncSession,
        test_picture_1: Picture,
        test_user_1: UUID,
        test_user_role_1: UUID,
        test_admin_role: UUID,
        test_pipeline_id: UUID,
        test_workflow_id_1: UUID,
    ) -> Annotation:
        """Create annotation with inference results."""
        # Mock ApiInferenceResponse data - must match full schema
        mock_results = {
            "filename": "test_results_image.png",
            "imageId": str(test_picture_1.id),
            "inference_id": str(test_workflow_id_1),
            "boxes": [
                {
                    "box": {  # PixelBoundingBox
                        "topX": 10,
                        "topY": 20,
                        "bottomX": 30,
                        "bottomY": 40,
                    },
                    "label": "Seed Type A",
                    "score": 0.95,
                    "topN": [  # Top-N predictions
                        {"label": "Seed Type A", "score": 0.95},
                        {"label": "Seed Type B", "score": 0.03},
                    ],
                    "classId": "class_1",
                    "object_type_id": "obj_type_1",
                    "box_id": "box_1",
                    "overlapping": False,
                    "overlappingIndices": -1,
                    "is_verified": False,
                }
            ],
            "labelOccurrence": {"Seed Type A": 1},
            "totalBoxes": 1,
            "models": [
                {
                    "name": "Test Model",
                    "version": "1.0",
                    "endpoint": "https://test.model.com",
                }
            ],
        }

        annotation = Annotation(
            id=test_workflow_id_1,  # annotation_id == workflow_id
            user_id=test_user_1,
            org_user_role_id=test_user_role_1,
            org_admin_role_id=test_admin_role,
            picture_id=test_picture_1.id,
            pipeline_id=test_pipeline_id,
            raw_data=mock_results,
            date_created=datetime.now(timezone.utc),
        )
        integration_db_session.add(annotation)
        await integration_db_session.commit()
        await integration_db_session.refresh(annotation)
        return annotation

    async def test_get_results_for_completed_workflow(
        self,
        test_user_1: UUID,
        test_annotation_with_results: Annotation,
        test_user_role_assignment_1: None,
    ):
        """Test that user can retrieve results for their own completed workflow."""
        workflow_id = str(test_annotation_with_results.id)

        # Get results
        result = await InferenceService.get_workflow_results(workflow_id, test_user_1)

        # Verify response structure
        assert result is not None
        assert "filename" in result
        assert "imageId" in result
        assert "inference_id" in result
        assert "boxes" in result
        assert "labelOccurrence" in result
        assert "totalBoxes" in result
        assert "models" in result

        # Verify data matches
        assert result["filename"] == "test_results_image.png"
        assert result["totalBoxes"] == 1
        assert len(result["boxes"]) == 1
        assert result["boxes"][0]["label"] == "Seed Type A"
        assert result["boxes"][0]["score"] == 0.95
        assert result["boxes"][0]["box"]["topX"] == 10
        assert result["boxes"][0]["box"]["topY"] == 20

    async def test_get_results_unauthorized_user(
        self,
        test_user_2: UUID,
        test_annotation_with_results: Annotation,
        test_user_role_assignment_1: None,
        test_user_role_assignment_2: None,
        test_admin_role_2: UUID,  # Ensure admin role exists for org 2
    ):
        """Test that user cannot access another user's workflow results."""
        workflow_id = str(test_annotation_with_results.id)

        # Attempt to get results as different user
        with pytest.raises(HTTPException) as exc_info:
            await InferenceService.get_workflow_results(workflow_id, test_user_2)

        assert exc_info.value.status_code == 403
        assert "Not authorized" in str(exc_info.value.detail)

    async def test_get_results_workflow_not_found(
        self,
        test_user_1: UUID,
        test_user_role_assignment_1: None,
    ):
        """Test that 404 is returned when workflow/results not found."""
        non_existent_workflow_id = str(uuid7())

        with pytest.raises(HTTPException) as exc_info:
            await InferenceService.get_workflow_results(
                non_existent_workflow_id, test_user_1
            )

        assert exc_info.value.status_code == 404
        assert "No results found" in str(exc_info.value.detail)

    async def test_get_results_invalid_workflow_id_format(
        self,
        test_user_1: UUID,
        test_user_role_assignment_1: None,
    ):
        """Test that 400 is returned for invalid workflow_id format."""
        invalid_workflow_id = "not-a-valid-uuid"

        with pytest.raises(HTTPException) as exc_info:
            await InferenceService.get_workflow_results(
                invalid_workflow_id, test_user_1
            )

        assert exc_info.value.status_code == 400
        assert "Invalid workflow_id format" in str(exc_info.value.detail)

    async def test_get_results_response_format_validation(
        self,
        test_user_1: UUID,
        test_annotation_with_results: Annotation,
        test_user_role_assignment_1: None,
    ):
        """Test that results are properly formatted and validated."""
        workflow_id = str(test_annotation_with_results.id)

        result = await InferenceService.get_workflow_results(workflow_id, test_user_1)

        # Verify box structure
        assert isinstance(result["boxes"], list)
        box = result["boxes"][0]
        assert "box_id" in box
        assert "box" in box
        assert "topX" in box["box"]
        assert "topY" in box["box"]
        assert "bottomX" in box["box"]
        assert "bottomY" in box["box"]
        assert "label" in box
        assert "score" in box
        assert "topN" in box
        assert "classId" in box
        assert "object_type_id" in box
        assert "overlapping" in box
        assert "overlappingIndices" in box
        assert "is_verified" in box

        # Verify labelOccurrence is a dict
        assert isinstance(result["labelOccurrence"], dict)
        assert result["labelOccurrence"]["Seed Type A"] == 1

        # Verify models is a list
        assert isinstance(result["models"], list)
        assert len(result["models"]) == 1
        assert "name" in result["models"][0]
        assert "version" in result["models"][0]

    async def test_cleanup_test_data(
        self,
        integration_db_session: AsyncSession,
        test_annotation_with_results: Annotation,
        test_picture_1: Picture,
        test_folder_1: Folder,
        test_user_1: UUID,
        test_user_2: UUID,
        test_org: UUID,
        test_org_2: UUID,
        test_admin_role: UUID,
        test_admin_role_2: UUID,
        test_user_role_1: UUID,
        test_user_role_2: UUID,
    ):
        """Clean up test data after tests complete."""
        # Test data cleanup is handled automatically by pytest fixtures
        # and database rollback/transaction management.
        # This test exists to ensure all fixtures are created correctly.
        assert test_annotation_with_results is not None
        assert test_picture_1 is not None
        assert test_folder_1 is not None
        assert test_user_1 is not None
        assert test_user_2 is not None
        assert test_org is not None
        assert test_org_2 is not None
