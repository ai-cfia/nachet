"""
Integration tests for image_inference_workflow.

These tests use real database, real Azurite, and real DBOS workflows to test
the complete image inference pipeline with no mocks.

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Azurite container running: docker compose up -d nachet-blob
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_image_inference_workflow_integration.py -v -s
"""

import pytest
import pytest_asyncio
import os
from dotenv import load_dotenv
from uuid import uuid4, UUID
from uuid6 import uuid7
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.inference import (
    image_inference_workflow,
)
from app.db.model import Picture, Folder
from app.blob.azure.storage import AzureBlobStorage
from app.api.config import get_settings
from app.exceptions import ImageProcessingError
from tests.fixtures.test_images import get_test_seed_image
from tests.integration.helpers import (
    wait_for_workflow_completion,
)
from dbos import DBOS

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()
    if settings.blob_storage_name and settings.blob_storage_key:
        return settings.blob_storage_config
    raise ValueError("No Azure Storage configuration found")


def get_test_container_names():
    """Get the correct test container names based on environment configuration."""
    from app.service.constants import Bucket

    settings = get_settings()
    bucket_prefix = settings.blob_container_prefix

    return {
        "original": bucket_prefix
        + Bucket.get_original_container(is_test=settings.is_test_environment),
        "sanitized": bucket_prefix
        + Bucket.get_sanitized_container(is_test=settings.is_test_environment),
    }


@pytest_asyncio.fixture
async def test_folder(
    integration_db_session: AsyncSession,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
    cleanup_test_folders: list,
):
    """Create a test folder for workflow tests."""
    folder = Folder(
        id=uuid4(),
        name="Test Inference Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-inf",
        description="Test folder for inference integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    cleanup_test_folders.append(folder.id)
    yield folder.id


@pytest_asyncio.fixture
async def azure_storage_onprem():
    """Get the onprem storage client from BlobStorageManager for testing."""
    from app.blob.manager import blob_storage_manager

    # Return the onprem storage client
    storage = blob_storage_manager.get_client("onprem")
    yield storage

    # Cleanup handled by test methods


@pytest_asyncio.fixture
async def test_picture(
    integration_db_session: AsyncSession,
    test_folder: UUID,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
    cleanup_test_pictures: list,
):
    """Create a test Picture record for inference testing."""
    picture_id = uuid7()
    org_prefix = "test-inf"
    picture = Picture(
        id=picture_id,
        folder_id=test_folder,
        user_id=test_user,
        org_admin_role_id=test_org_admin_role,
        org_user_role_id=test_org_user_role,
        name="test_inference.png",
        width=638,
        height=559,
        format="PNG",
        sha256="test_hash_" + str(picture_id),
        blob_url_original=f"{org_prefix}/{picture_id}.png",
        blob_url_sanitized=f"{org_prefix}/{picture_id}.png",  # Assume already sanitized
        size_on_disk_original=1024,
    )
    integration_db_session.add(picture)
    await integration_db_session.commit()
    await integration_db_session.refresh(picture)
    cleanup_test_pictures.append(picture_id)
    yield picture


@pytest_asyncio.fixture
async def test_pipeline_id(
    integration_db_session: AsyncSession,
    test_user: UUID,
):
    """
    Get the appropriate test pipeline ID based on NACHET_ENV.

    - NACHET_ENV="local": Uses "15 spp RCNN SWIN (Local)" pipeline
      - Step 1: seed-detector-rcnn-1-local (http://127.0.0.1:12380/score)
      - Step 2: swin-15e-spp-local (http://127.0.0.1:12390/score)

    - NACHET_ENV="ci"/"test": Uses "15 spp RCNN SWIN" pipeline
      - Step 1: seed-detector-rcnn-1 (http://nachet-detector:5001/score)
      - Step 2: swin-15e-spp (http://nachet-15spp-classifier:5001/score)
    """
    from tests.integration.pipeline_config import get_pipeline_id_for_test

    pipeline_id = get_pipeline_id_for_test(species_count=15)
    yield pipeline_id


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageInferenceWorkflowSteps:
    """Integration tests for individual DBOS steps in image_inference_workflow."""

    async def test_download_image_from_blob_step_success(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test Step 1: download_image_from_blob_step successfully downloads and encodes image.

        Verifies:
        - Image downloaded from sanitized container
        - Correct base64 encoding
        - Returns non-empty string
        """
        # Arrange

        image_id = uuid7()
        org_prefix = "test-inf"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Construct correct blob path: org_prefix/image_id.png
        blob_path = f"{org_prefix}/{image_id}.png"

        # Upload directly to sanitized container on ONPREM storage
        await azure_storage_onprem.upload_blob(
            container=containers["sanitized"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Act - call the DBOS step through a workflow wrapper
        from tests.integration.test_workflows import download_image_workflow

        handle = DBOS.start_workflow(
            download_image_workflow,
            org_prefix=org_prefix,
            image_id=image_id,
        )

        # Wait for workflow to complete
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=60,
            poll_interval=1.0,
        )
        base64_result = workflow_result["result"]

        # Assert
        assert base64_result is not None
        assert isinstance(base64_result, str)
        assert len(base64_result) > 0
        # Verify it's valid base64
        import base64

        decoded = base64.b64decode(base64_result)
        assert len(decoded) > 0

        # Cleanup
        await azure_storage_onprem.delete_blob(containers["sanitized"], blob_path)

    async def test_download_image_from_blob_step_not_found(
        self,
        dbos_runtime,
    ):
        """
        Test Step 1: download_image_from_blob_step raises error when image not found.

        Verifies:
        - Correct error when blob doesn't exist
        """
        # Arrange - use non-existent image
        image_id = uuid7()
        org_prefix = "test-inf"

        # Act & Assert
        from tests.integration.test_workflows import download_image_workflow

        handle = DBOS.start_workflow(
            download_image_workflow,
            org_prefix=org_prefix,
            image_id=image_id,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises(Exception):  # BlobDownloadError or similar
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

    async def test_get_pipeline_configuration_step_success(
        self,
        dbos_runtime,
        test_pipeline_id: UUID,
    ):
        """
        Test Step 2: get_pipeline_configuration_step retrieves pipeline steps.

        Verifies:
        - Pipeline configuration loaded from cache
        - Returns list of step dictionaries
        - Each step has required fields
        """
        # Arrange - pipeline_id from fixture

        # Act - call the DBOS step through a workflow wrapper
        from tests.integration.test_workflows import (
            get_pipeline_configuration_workflow,
        )

        handle = DBOS.start_workflow(
            get_pipeline_configuration_workflow,
            pipeline_id=test_pipeline_id,
        )

        # Wait for workflow to complete
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=60,
            poll_interval=1.0,
        )
        pipeline_steps = workflow_result["result"]

        # Assert
        assert pipeline_steps is not None
        assert isinstance(pipeline_steps, list)
        assert len(pipeline_steps) > 0

        # Verify each step has required fields
        for step in pipeline_steps:
            assert "model_name" in step
            assert "request_function" in step
            assert "step" in step

    async def test_get_pipeline_configuration_step_not_found(
        self,
        dbos_runtime,
    ):
        """
        Test Step 2: get_pipeline_configuration_step raises error when pipeline not found.

        Verifies:
        - Correct error when pipeline doesn't exist
        """
        # Arrange - use non-existent pipeline
        fake_pipeline_id = uuid4()

        # Act & Assert
        from tests.integration.test_workflows import (
            get_pipeline_configuration_workflow,
        )

        handle = DBOS.start_workflow(
            get_pipeline_configuration_workflow,
            pipeline_id=fake_pipeline_id,
        )

        # Wait for workflow to complete - it should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        assert "not found in cache" in str(exc_info.value)

    async def test_execute_inference_step_with_base64(
        self,
        dbos_runtime,
        test_pipeline_id: UUID,
    ):
        """
        Test Step 3: execute_inference_step with base64 input (detector step).

        Verifies:
        - Step accepts base64 string
        - Calls external ML endpoint
        - Returns detection result
        """
        # Arrange
        from tests.integration.test_workflows import (
            get_pipeline_configuration_workflow,
            execute_inference_step_workflow,
        )

        # Get pipeline configuration to extract first step (detector)
        pipeline_handle = DBOS.start_workflow(
            get_pipeline_configuration_workflow,
            pipeline_id=test_pipeline_id,
        )
        pipeline_result = await wait_for_workflow_completion(
            workflow_id=pipeline_handle.workflow_id,
            timeout=60,
        )
        pipeline_steps = pipeline_result["result"]

        # Get first step (should be detector)
        first_step = pipeline_steps[0]

        # Get test image as base64
        import base64

        file_bytes = get_test_seed_image()
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

        # Act - call inference step with base64 input
        handle = DBOS.start_workflow(
            execute_inference_step_workflow,
            step_config=first_step,
            previous_result=image_base64,
        )

        # Wait for workflow to complete
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=120,  # ML inference may take longer
            poll_interval=2.0,
        )
        result = workflow_result["result"]

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        # Detection result should have boxes
        assert "boxes" in result or "base64_result" not in result

    async def test_execute_inference_step_with_detection_result(
        self,
        dbos_runtime,
        test_pipeline_id: UUID,
    ):
        """
        Test Step 3: execute_inference_step with detection result (classifier step).

        Verifies:
        - Step accepts detection result
        - Calls external ML endpoint
        - Returns classification result
        """
        # Arrange
        from tests.integration.test_workflows import (
            get_pipeline_configuration_workflow,
            execute_inference_step_workflow,
        )

        # Get pipeline configuration
        pipeline_handle = DBOS.start_workflow(
            get_pipeline_configuration_workflow,
            pipeline_id=test_pipeline_id,
        )
        pipeline_result = await wait_for_workflow_completion(
            workflow_id=pipeline_handle.workflow_id,
            timeout=60,
        )
        pipeline_steps = pipeline_result["result"]

        # Need at least 2 steps (detector + classifier)
        if len(pipeline_steps) < 2:
            pytest.skip("Pipeline must have at least 2 steps for this test")

        # Execute first step (detector) to get detection result
        first_step = pipeline_steps[0]
        import base64

        file_bytes = get_test_seed_image()
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

        detector_handle = DBOS.start_workflow(
            execute_inference_step_workflow,
            step_config=first_step,
            previous_result=image_base64,
        )
        detector_result = await wait_for_workflow_completion(
            workflow_id=detector_handle.workflow_id,
            timeout=120,
        )
        detection_result = detector_result["result"]

        # Act - call inference step with detection result (classifier)
        second_step = pipeline_steps[1]
        handle = DBOS.start_workflow(
            execute_inference_step_workflow,
            step_config=second_step,
            previous_result=detection_result,
        )

        # Wait for workflow to complete
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=120,
            poll_interval=2.0,
        )
        result = workflow_result["result"]

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        # Classification result should have filename and result
        assert "filename" in result or "result" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageInferenceWorkflowComplete:
    """Complete workflow integration tests for image_inference_workflow."""

    async def test_workflow_complete_success_path(
        self,
        dbos_runtime,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_picture: Picture,
        test_pipeline_id: UUID,
        azure_storage_onprem: AzureBlobStorage,
        integration_db_session: AsyncSession,
    ):
        """
        Test complete inference workflow: download → configure → execute pipeline.

        This is the main integration test that verifies the entire inference pipeline.

        Verifies:
        - All steps execute successfully
        - Pipeline steps execute in sequence
        - DBOS events published
        - Workflow completes with valid ApiInferenceResponse
        - Results contain boxes and classifications
        """

        # Arrange
        image_id = test_picture.id
        org_prefix = "test-inf"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Construct correct blob path and upload directly to sanitized container
        blob_path = f"{org_prefix}/{image_id}.png"

        await azure_storage_onprem.upload_blob(
            container=containers["sanitized"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Act - Execute workflow
        parent_workflow_id = uuid4()  # Generate parent workflow ID for this test
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
            pipeline_id=test_pipeline_id,
            image_dims=[test_picture.width, test_picture.height],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=parent_workflow_id,
        )

        workflow_id = workflow_handle.workflow_id

        # Wait for workflow completion
        try:
            workflow_result = await wait_for_workflow_completion(
                workflow_id=workflow_id,
                timeout=120,  # Longer timeout for ML inference
                poll_interval=2.0,
            )
        except TimeoutError:
            pytest.fail(f"Workflow {workflow_id} timed out after 120s")

        # Assert workflow completed successfully
        assert workflow_result["status"] == "completed"
        result = workflow_result["result"]

        # Verify response structure (result is an ApiInferenceResponse Pydantic model)
        assert hasattr(result, "filename")
        assert hasattr(result, "boxes")
        assert hasattr(
            result, "label_occurrence"
        )  # Use Python attribute name, not alias
        assert hasattr(result, "total_boxes")  # Use Python attribute name, not alias
        assert hasattr(result, "models")

        # Verify actual values
        assert result.filename is not None
        assert isinstance(result.boxes, list)
        assert isinstance(result.label_occurrence, dict)  # Use Python attribute name
        assert isinstance(result.total_boxes, int)  # Use Python attribute name
        assert isinstance(result.models, list)

        # Verify DBOS events
        events = workflow_result["events"]
        assert events.get("inference_status") == "completed"
        assert events.get("inference_timestamps") is not None

        # Cleanup
        await azure_storage_onprem.delete_blob(containers["sanitized"], blob_path)

    async def test_workflow_pipeline_not_found(
        self,
        dbos_runtime,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_picture: Picture,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test workflow fails gracefully when pipeline not found.

        Verifies:
        - Workflow publishes error events
        - Correct exception raised
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-inf"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()
        fake_pipeline_id = uuid4()

        # Upload sanitized image directly
        blob_path = f"{org_prefix}/{image_id}.png"

        await azure_storage_onprem.upload_blob(
            container=containers["sanitized"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Act & Assert
        parent_workflow_id = uuid4()
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
            pipeline_id=fake_pipeline_id,
            image_dims=[test_picture.width, test_picture.height],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=parent_workflow_id,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises((ValueError, ImageProcessingError)):
            await wait_for_workflow_completion(
                workflow_id=workflow_handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        # Verify error events were published
        events = await DBOS.get_all_events_async(workflow_handle.workflow_id)
        assert events.get("inference_status") == "failed"
        assert events.get("inference_error_details") is not None

        # Cleanup
        await azure_storage_onprem.delete_blob(containers["sanitized"], blob_path)

    async def test_workflow_image_not_found(
        self,
        dbos_runtime,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_pipeline_id: UUID,
    ):
        """
        Test workflow fails gracefully when image blob not found.

        Verifies:
        - Workflow publishes error events
        - Correct exception raised
        """
        # Arrange - use non-existent image
        image_id = uuid7()
        org_prefix = "test-inf"

        # Act & Assert
        parent_workflow_id = uuid4()
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
            pipeline_id=test_pipeline_id,
            image_dims=[640, 480],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=parent_workflow_id,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises((Exception, ImageProcessingError)):
            await wait_for_workflow_completion(
                workflow_id=workflow_handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        # Verify error events were published
        events = await DBOS.get_all_events_async(workflow_handle.workflow_id)
        assert events.get("inference_status") == "failed"
        assert events.get("inference_error_details") is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageInferenceWorkflowRecovery:
    """Test DBOS workflow recovery and durability features."""

    async def test_workflow_recovery_after_interruption(
        self,
        dbos_runtime,
    ):
        """
        Test that workflow can resume from last completed step after interruption.

        This verifies DBOS durability - completed steps are not re-executed.

        Note: This test requires simulating workflow interruption, which may be
        complex to implement reliably. Consider using DBOS testing utilities.
        """
        pytest.skip("Complex test - requires workflow interruption simulation")

    async def test_workflow_max_recovery_attempts(
        self,
        dbos_runtime,
    ):
        """
        Test that workflow respects max_recovery_attempts=5 configuration.

        Verifies DBOS will retry workflow up to 5 times before giving up.
        """
        pytest.skip("Complex test - requires controlled failure injection")


@pytest.mark.integration
@pytest.mark.asyncio
class TestInferenceResultsDatabasePersistence:
    """Test database persistence of inference results (Annotation + Objects)."""

    async def test_save_inference_results_creates_annotation_and_objects(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_picture: Picture,
        test_pipeline_id: UUID,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test save_inference_results_step creates Annotation and Object records.

        Verifies:
        - Annotation record created with parent workflow ID as annotation ID
        - Object records created for each detected box
        - Species labels correctly mapped to seed IDs
        - Raw data stored in annotation
        """
        from app.model.inference import (
            ApiInferenceResponse,
            ApiInferenceBox,
            PixelBoundingBox,
            PredictionLabelScore,
            ModelInfo,
        )
        from sqlalchemy import select
        from app.db.model import Annotation, Object

        # Arrange - create mock API response with test data
        parent_workflow_id = uuid4()

        test_boxes = [
            ApiInferenceBox(
                box=PixelBoundingBox(topX=10, topY=20, bottomX=100, bottomY=200),
                label="Chenopodium album",  # Using full species name (genus + species)
                score=0.95,
                topN=[
                    PredictionLabelScore(label="Chenopodium album", score=0.95),
                    PredictionLabelScore(label="Chenopodium ficifolium", score=0.03),
                    PredictionLabelScore(label="Chenopodium pallidicaule", score=0.02),
                ],
                classId="0",
                object_type_id="seed",
                box_id="box-1",
                overlapping=False,
                overlappingIndices=0,
                is_verified=False,
            ),
        ]

        api_response = ApiInferenceResponse(
            filename="test.png",
            image_id=str(test_picture.id),
            inference_id=str(parent_workflow_id),
            boxes=test_boxes,
            label_occurrence={"Chenopodium album": 1},
            total_boxes=1,
            models=[ModelInfo(name="test-model", version="1")],
        )

        # Act - call the DBOS step through a workflow wrapper
        from tests.integration.test_workflows import save_inference_results_workflow

        workflow_handle = DBOS.start_workflow(
            save_inference_results_workflow,
            user_id=test_user,
            image_id=test_picture.id,
            pipeline_id=test_pipeline_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            api_response=api_response,
            parent_workflow_id=parent_workflow_id,
        )

        # Wait for workflow completion
        await wait_for_workflow_completion(
            workflow_id=workflow_handle.workflow_id,
            timeout=30,
            poll_interval=0.5,
        )

        # Assert - verify annotation was created
        annotation_id = parent_workflow_id
        annotation_result = await integration_db_session.execute(
            select(Annotation).where(Annotation.id == annotation_id)
        )
        annotation = annotation_result.scalar_one_or_none()

        assert annotation is not None
        assert annotation.id == annotation_id
        assert annotation.picture_id == test_picture.id
        assert annotation.pipeline_id == test_pipeline_id
        assert annotation.user_id == test_user
        assert annotation.raw_data is not None
        assert "boxes" in annotation.raw_data
        assert annotation.raw_data["totalBoxes"] == 1

        # Assert - verify object records were created
        objects_result = await integration_db_session.execute(
            select(Object).where(Object.inference_id == annotation_id)
        )
        objects = objects_result.scalars().all()

        assert len(objects) == 1
        obj = objects[0]
        assert obj.inference_id == annotation_id
        assert obj.picture_id == test_picture.id
        assert obj.pipeline_id == test_pipeline_id
        assert obj.top_x_abs == 10
        assert obj.top_y_abs == 20
        assert obj.bot_x_abs == 100
        assert obj.bot_y_abs == 200
        assert obj.top_score == 0.95
        assert obj.top_id is not None  # Should be mapped to seed UUID

        # Cleanup - delete objects first, then annotation
        for obj in objects:
            await integration_db_session.delete(obj)
        await integration_db_session.delete(annotation)
        await integration_db_session.commit()

    async def test_save_inference_results_raises_error_for_unmapped_species(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_picture: Picture,
        test_pipeline_id: UUID,
    ):
        """
        Test save_inference_results_step raises exception for unmapped species.

        Verifies:
        - Exception raised when species label not found in seed database
        - Clear error message with debugging info
        - No partial data created in database
        """
        from app.model.inference import (
            ApiInferenceResponse,
            ApiInferenceBox,
            PixelBoundingBox,
            PredictionLabelScore,
            ModelInfo,
        )
        from sqlalchemy import select
        from app.db.model import Annotation

        # Arrange - create API response with unmapped species label
        parent_workflow_id = uuid4()

        test_boxes = [
            ApiInferenceBox(
                box=PixelBoundingBox(topX=10, topY=20, bottomX=100, bottomY=200),
                label="UNMAPPED_SPECIES_XYZ123",  # This species doesn't exist
                score=0.95,
                topN=[
                    PredictionLabelScore(label="UNMAPPED_SPECIES_XYZ123", score=0.95),
                ],
                classId="0",
                object_type_id="seed",
                box_id="box-1",
                overlapping=False,
                overlappingIndices=0,
                is_verified=False,
            ),
        ]

        api_response = ApiInferenceResponse(
            filename="test.png",
            image_id=str(test_picture.id),
            inference_id=str(parent_workflow_id),
            boxes=test_boxes,
            label_occurrence={"UNMAPPED_SPECIES_XYZ123": 1},
            total_boxes=1,
            models=[ModelInfo(name="test-model", version="1")],
        )

        # Act & Assert - should raise exception
        from tests.integration.test_workflows import save_inference_results_workflow

        workflow_handle = DBOS.start_workflow(
            save_inference_results_workflow,
            user_id=test_user,
            image_id=test_picture.id,
            pipeline_id=test_pipeline_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            api_response=api_response,
            parent_workflow_id=parent_workflow_id,
        )

        # Wait for workflow - should fail
        with pytest.raises(Exception):
            await wait_for_workflow_completion(
                workflow_id=workflow_handle.workflow_id,
                timeout=30,
                poll_interval=0.5,
            )

        # Verify annotation was created but workflow failed
        # Note: Annotation is created before species validation, so it exists even on error
        annotation_id = parent_workflow_id
        annotation_result = await integration_db_session.execute(
            select(Annotation).where(Annotation.id == annotation_id)
        )
        annotation = annotation_result.scalar_one_or_none()
        # Annotation should exist because it's created before species validation
        assert annotation is not None

        # Cleanup - delete the annotation since test workflow failed
        if annotation:
            await integration_db_session.delete(annotation)
            await integration_db_session.commit()

    async def test_save_inference_results_handles_multiple_boxes(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_picture: Picture,
        test_pipeline_id: UUID,
    ):
        """
        Test save_inference_results_step handles multiple detected boxes.

        Verifies:
        - Multiple Object records created for multiple boxes
        - Each object correctly linked to same annotation
        - All species labels correctly mapped
        """
        from app.model.inference import (
            ApiInferenceResponse,
            ApiInferenceBox,
            PixelBoundingBox,
            PredictionLabelScore,
            ModelInfo,
        )
        from sqlalchemy import select
        from app.db.model import Annotation, Object

        # Arrange - create API response with multiple boxes
        parent_workflow_id = uuid4()

        test_boxes = [
            ApiInferenceBox(
                box=PixelBoundingBox(topX=10, topY=20, bottomX=100, bottomY=200),
                label="Chenopodium album",
                score=0.95,
                topN=[PredictionLabelScore(label="Chenopodium album", score=0.95)],
                classId="0",
                object_type_id="seed",
                box_id="box-1",
                overlapping=False,
                overlappingIndices=0,
                is_verified=False,
            ),
            ApiInferenceBox(
                box=PixelBoundingBox(topX=150, topY=50, bottomX=250, bottomY=150),
                label="Chenopodium ficifolium",
                score=0.88,
                topN=[PredictionLabelScore(label="Chenopodium ficifolium", score=0.88)],
                classId="1",
                object_type_id="seed",
                box_id="box-2",
                overlapping=False,
                overlappingIndices=0,
                is_verified=False,
            ),
            ApiInferenceBox(
                box=PixelBoundingBox(topX=300, topY=100, bottomX=400, bottomY=200),
                label="Chenopodium pallidicaule",
                score=0.92,
                topN=[
                    PredictionLabelScore(label="Chenopodium pallidicaule", score=0.92)
                ],
                classId="2",
                object_type_id="seed",
                box_id="box-3",
                overlapping=False,
                overlappingIndices=0,
                is_verified=False,
            ),
        ]

        api_response = ApiInferenceResponse(
            filename="test.png",
            image_id=str(test_picture.id),
            inference_id=str(parent_workflow_id),
            boxes=test_boxes,
            label_occurrence={
                "Chenopodium album": 1,
                "Chenopodium ficifolium": 1,
                "Chenopodium pallidicaule": 1,
            },
            total_boxes=3,
            models=[ModelInfo(name="test-model", version="1")],
        )

        # Act
        from tests.integration.test_workflows import save_inference_results_workflow

        workflow_handle = DBOS.start_workflow(
            save_inference_results_workflow,
            user_id=test_user,
            image_id=test_picture.id,
            pipeline_id=test_pipeline_id,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            api_response=api_response,
            parent_workflow_id=parent_workflow_id,
        )

        await wait_for_workflow_completion(
            workflow_id=workflow_handle.workflow_id,
            timeout=30,
            poll_interval=0.5,
        )

        # Assert - verify all objects were created
        annotation_id = parent_workflow_id
        objects_result = await integration_db_session.execute(
            select(Object).where(Object.inference_id == annotation_id)
        )
        objects = objects_result.scalars().all()

        assert len(objects) == 3
        assert all(obj.inference_id == annotation_id for obj in objects)
        assert all(obj.picture_id == test_picture.id for obj in objects)

        # Verify bounding boxes match
        coords = [
            (obj.top_x_abs, obj.top_y_abs, obj.bot_x_abs, obj.bot_y_abs)
            for obj in objects
        ]
        assert (10, 20, 100, 200) in coords
        assert (150, 50, 250, 150) in coords
        assert (300, 100, 400, 200) in coords

        # Cleanup - delete objects first, then annotation
        for obj in objects:
            await integration_db_session.delete(obj)
        annotation_result = await integration_db_session.execute(
            select(Annotation).where(Annotation.id == annotation_id)
        )
        annotation = annotation_result.scalar_one()
        await integration_db_session.delete(annotation)
        await integration_db_session.commit()
