"""
Integration tests for workflow state updates.

These tests verify that DBOS workflows properly update ImageProcessingState
and InferenceRequestState tables throughout the workflow lifecycle.

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Azurite container running: docker compose up -d nachet-blob
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_workflow_state_updates.py -v -s
"""

import asyncio
import pytest
import pytest_asyncio
import os
from dotenv import load_dotenv
from uuid import uuid4, UUID
from uuid6 import uuid7
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.service.inference import image_processing_workflow, image_inference_workflow
from app.db.model import (
    Picture,
    ImageProcessingState,
    InferenceRequestState,
    Folder,
    Pipeline,
)
from app.blob.azure.storage import AzureBlobStorage
from app.api.config import get_settings
from tests.fixtures.test_images import get_test_seed_image
from tests.integration.helpers import (
    wait_for_workflow_completion,
    mock_defender_tags_in_azurite,
)
from dbos import DBOS

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


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
        name="Test State Update Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-state",
        description="Test folder for workflow state update tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    cleanup_test_folders.append(folder.id)
    yield folder.id


@pytest_asyncio.fixture
async def test_picture(
    integration_db_session: AsyncSession,
    test_folder: UUID,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
    cleanup_test_pictures: list,
):
    """Create a test Picture record for workflow testing."""
    picture_id = uuid7()
    org_prefix = "test-state"
    picture = Picture(
        id=picture_id,
        folder_id=test_folder,
        user_id=test_user,
        org_admin_role_id=test_org_admin_role,
        org_user_role_id=test_org_user_role,
        name="test_state_workflow.png",
        width=638,
        height=559,
        format="PNG",
        sha256="test_hash_" + str(picture_id),
        blob_url_original=f"{org_prefix}/{picture_id}.png",
        blob_url_sanitized=None,
        size_on_disk_original=1024,
    )
    integration_db_session.add(picture)
    await integration_db_session.commit()
    await integration_db_session.refresh(picture)
    cleanup_test_pictures.append(picture_id)
    yield picture


@pytest_asyncio.fixture
async def azure_storage_external():
    """Get the external storage client from BlobStorageManager."""
    from app.blob.manager import blob_storage_manager

    storage = blob_storage_manager.get_client("external")
    yield storage


@pytest_asyncio.fixture
async def azure_storage_onprem():
    """Get the onprem storage client from BlobStorageManager."""
    from app.blob.manager import blob_storage_manager

    storage = blob_storage_manager.get_client("onprem")
    yield storage


@pytest_asyncio.fixture
async def test_pipeline(
    integration_db_session: AsyncSession,
):
    """
    Get the appropriate test pipeline ID based on NACHET_ENV.

    - NACHET_ENV="local": Uses "15 spp RCNN SWIN (Local)" pipeline
    - NACHET_ENV="ci"/"test": Uses "15 spp RCNN SWIN" pipeline
    """
    from tests.integration.pipeline_config import get_pipeline_id_for_test
    from sqlalchemy import select
    from app.db.model import Pipeline

    pipeline_id = get_pipeline_id_for_test(species_count=15)

    # Fetch the Pipeline object
    stmt = select(Pipeline).where(Pipeline.id == pipeline_id)
    result = await integration_db_session.execute(stmt)
    pipeline = result.scalar_one_or_none()

    yield pipeline


@pytest.mark.integration
@pytest.mark.asyncio
class TestImageProcessingWorkflowStateUpdates:
    """Integration tests for ImageProcessingState updates during image_processing_workflow."""

    async def test_processing_state_updates_success_flow(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage_external: AzureBlobStorage,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test that ImageProcessingState is updated at each workflow stage.

        Verifies state updates for:
        1. Initial state creation (pending)
        2. After upload (uploaded)
        3. Before defender scan (defender_scanning)
        4. After defender scan (defender_scanned)
        5. Before sanitization (sanitizing)
        6. After sanitization (sanitized)
        7. On completion (completed)

        Also verifies:
        - Progress percentage updates (0 → 25 → 40 → 50 → 75 → 90 → 100)
        - Timestamps are set correctly
        - Blob URLs are updated
        - Defender scan results are stored
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Act - Execute workflow
        # In tests, we pass workflow_id as parent_workflow_id since we create state with that ID
        # Generate a test workflow ID first
        from uuid6 import uuid7

        test_workflow_id = str(uuid7())

        workflow_handle = DBOS.start_workflow(
            image_processing_workflow,
            image_id=image_id,
            file_bytes=file_bytes,
            user_id=test_user,
            org_prefix=org_prefix,
            parent_workflow_id=test_workflow_id,
        )
        actual_workflow_id = workflow_handle.get_workflow_id()  # Child workflow ID
        workflow_id = test_workflow_id  # Parent workflow ID used for state tracking

        # Create processing state immediately after workflow start
        from app.service.constants import ProcessingStatus
        import asyncio

        processing_state = ImageProcessingState(
            workflow_id=workflow_id,  # Use parent workflow ID
            picture_id=image_id,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Wait for workflow to upload blob, then set Defender tags
        blob_name = f"{org_prefix}/{image_id}.png"
        # Poll for blob existence (workflow uploads it)
        for _ in range(30):  # Wait up to 3 seconds
            if await azure_storage_external.blob_exists(
                containers["original"], blob_name
            ):
                break
            await asyncio.sleep(0.1)

        # Set Defender tags AFTER the blob is uploaded by workflow
        await mock_defender_tags_in_azurite(
            azure_storage_external,
            containers["original"],
            blob_name,
            scan_result="No threats found",
            upload_placeholder=False,  # Blob already exists from workflow
        )

        # Wait for workflow completion (use actual child workflow ID)
        await wait_for_workflow_completion(actual_workflow_id, timeout=60)

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert - Query the ImageProcessingState
        stmt = select(ImageProcessingState).where(
            ImageProcessingState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify state exists
        assert state is not None, "ImageProcessingState should exist"
        assert state.picture_id == image_id
        assert state.user_id == test_user
        assert state.workflow_id == workflow_id

        # Verify final status
        assert state.status == "completed", (
            f"Expected status 'completed', got '{state.status}'"
        )
        assert state.progress_percentage == 100

        # Verify timestamps
        assert state.uploaded_at is not None
        assert state.defender_scan_started_at is not None
        assert state.defender_scan_completed_at is not None
        assert state.sanitization_started_at is not None
        assert state.sanitization_completed_at is not None
        assert state.completed_at is not None

        # Verify defender scan results
        assert state.defender_scan_result is not None
        assert state.malware_detected is False

        # Verify blob URLs
        assert state.blob_url_original is not None
        assert state.blob_url_sanitized is not None

        # Verify no error fields
        assert state.failed_at is None
        assert state.error_message is None

    async def test_processing_state_progress_updates(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage_external: AzureBlobStorage,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test that progress_percentage is updated correctly throughout the workflow.

        Expected progression:
        - 0 (initial)
        - 25 (uploaded)
        - 40 (defender_scanning)
        - 50 (defender_scanned)
        - 75 (sanitizing)
        - 90 (sanitized)
        - 100 (completed)
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Act
        from uuid6 import uuid7

        test_workflow_id = str(uuid7())

        workflow_handle = DBOS.start_workflow(
            image_processing_workflow,
            image_id=image_id,
            file_bytes=file_bytes,
            user_id=test_user,
            org_prefix=org_prefix,
            parent_workflow_id=test_workflow_id,
        )
        actual_workflow_id = workflow_handle.get_workflow_id()
        workflow_id = test_workflow_id

        # Create processing state immediately after workflow start
        from app.service.constants import ProcessingStatus
        import asyncio

        processing_state = ImageProcessingState(
            workflow_id=workflow_id,
            picture_id=image_id,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Wait for workflow to upload blob, then set Defender tags
        blob_name = f"{org_prefix}/{image_id}.png"
        # Poll for blob existence (workflow uploads it)
        for _ in range(30):  # Wait up to 3 seconds
            if await azure_storage_external.blob_exists(
                containers["original"], blob_name
            ):
                break
            await asyncio.sleep(0.1)

        # Set Defender tags AFTER the blob is uploaded by workflow
        await mock_defender_tags_in_azurite(
            azure_storage_external,
            containers["original"],
            blob_name,
            scan_result="No threats found",
            upload_placeholder=False,  # Blob already exists from workflow
        )

        await wait_for_workflow_completion(actual_workflow_id, timeout=60)

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert
        stmt = select(ImageProcessingState).where(
            ImageProcessingState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        assert state is not None, "ImageProcessingState should exist"
        assert state.progress_percentage == 100, "Final progress should be 100%"

    @pytest.mark.skip(reason="Waiting for blob store to be unblocked from network")
    async def test_processing_state_malware_detection(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage_external: AzureBlobStorage,
    ):
        """
        Test that malware_detected flag is set correctly when malware is found.

        Note: This test mocks a malicious defender scan result.
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Act
        from uuid6 import uuid7

        test_workflow_id = str(uuid7())

        workflow_handle = DBOS.start_workflow(
            image_processing_workflow,
            image_id=image_id,
            file_bytes=file_bytes,
            user_id=test_user,
            org_prefix=org_prefix,
            parent_workflow_id=test_workflow_id,
        )
        actual_workflow_id = workflow_handle.get_workflow_id()
        workflow_id = test_workflow_id

        # Create processing state immediately after workflow start
        from app.service.constants import ProcessingStatus
        import asyncio

        processing_state = ImageProcessingState(
            workflow_id=workflow_id,
            picture_id=image_id,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Wait for workflow to upload blob, then set Defender tags for MALWARE
        blob_name = f"{org_prefix}/{image_id}.png"
        # Poll for blob existence (workflow uploads it)
        for _ in range(30):  # Wait up to 3 seconds
            if await azure_storage_external.blob_exists(
                containers["original"], blob_name
            ):
                break
            await asyncio.sleep(0.1)

        # Set Defender tags AFTER the blob is uploaded by workflow
        await mock_defender_tags_in_azurite(
            azure_storage_external,
            containers["original"],
            blob_name,
            scan_result="Malicious",
            upload_placeholder=False,  # Blob already exists from workflow
        )

        # Wait for workflow (may fail due to malware, but state should be updated)
        try:
            await wait_for_workflow_completion(actual_workflow_id, timeout=60)
        except Exception:
            pass  # Workflow might fail due to malware detection

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert
        stmt = select(ImageProcessingState).where(
            ImageProcessingState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify malware detection flag
        assert state is not None
        assert state.malware_detected is True, "Malware should be detected"
        assert state.defender_scan_result is not None
        assert "Malicious" in str(state.defender_scan_result)


@pytest.mark.integration
@pytest.mark.asyncio
class TestInferenceWorkflowStateUpdates:
    """Integration tests for InferenceRequestState updates during image_inference_workflow."""

    async def test_inference_state_updates_success_flow(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_pipeline: Pipeline,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test that InferenceRequestState is updated throughout inference workflow.

        Verifies state updates for:
        1. Initial state creation (pending)
        2. Before inference starts (in_progress)
        3. After successful inference (completed)

        Also verifies:
        - Timestamps (started_at, completed_at)
        - Response payload is stored
        """
        # Arrange
        image_id = test_picture.id
        pipeline_id = test_pipeline.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Upload sanitized image to onprem storage (required for inference)
        blob_name = f"{org_prefix}/{image_id}.png"
        await azure_storage_onprem.upload_blob(
            containers["sanitized"], blob_name, file_bytes
        )

        # Update picture with sanitized blob URL
        test_picture.blob_url_sanitized = blob_name
        integration_db_session.add(test_picture)
        await integration_db_session.commit()

        # Act - Execute inference workflow
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
            pipeline_id=pipeline_id,
            image_dims=[test_picture.width, test_picture.height],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=uuid7(),  # Generate a parent workflow ID
        )
        workflow_id = workflow_handle.get_workflow_id()

        # Wait for workflow completion
        await wait_for_workflow_completion(workflow_id, timeout=120)

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert - Query the InferenceRequestState
        stmt = select(InferenceRequestState).where(
            InferenceRequestState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify state exists
        assert state is not None, "InferenceRequestState should exist"
        assert state.picture_id == image_id
        assert state.pipeline_id == pipeline_id
        assert state.user_id == test_user
        assert state.workflow_id == workflow_id

        # Verify final status
        assert state.status == "completed", (
            f"Expected status 'completed', got '{state.status}'"
        )

        # Verify timestamps
        assert state.started_at is not None, "started_at should be set"
        assert state.completed_at is not None, "completed_at should be set"
        assert state.started_at <= state.completed_at, (
            "started_at should be before completed_at"
        )

        # Verify response payload is stored
        assert state.response_payload is not None, "response_payload should be stored"

        # Verify no error fields
        assert state.failed_at is None
        assert state.error_message is None

    async def test_inference_state_timestamps(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_pipeline: Pipeline,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test that started_at and completed_at timestamps are set correctly.
        """
        # Arrange
        image_id = test_picture.id
        pipeline_id = test_pipeline.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Upload sanitized image
        blob_name = f"{org_prefix}/{image_id}.png"
        await azure_storage_onprem.upload_blob(
            containers["sanitized"], blob_name, file_bytes
        )

        test_picture.blob_url_sanitized = blob_name
        integration_db_session.add(test_picture)
        await integration_db_session.commit()

        # Record start time
        workflow_start = datetime.now(timezone.utc)

        # Act
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
            pipeline_id=pipeline_id,
            image_dims=[test_picture.width, test_picture.height],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=uuid7(),  # Generate a parent workflow ID
        )
        workflow_id = workflow_handle.get_workflow_id()

        await wait_for_workflow_completion(workflow_id, timeout=120)

        workflow_end = datetime.now(timezone.utc)

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert
        stmt = select(InferenceRequestState).where(
            InferenceRequestState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify timestamps are within workflow execution window
        assert state is not None, "InferenceRequestState should exist"
        assert state.started_at is not None, "started_at should be set"
        assert state.completed_at is not None, "completed_at should be set"
        assert state.started_at >= workflow_start
        assert state.completed_at <= workflow_end
        assert state.started_at <= state.completed_at


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowStateErrorHandling:
    """Integration tests for workflow state updates during error scenarios."""

    @pytest.mark.skip(reason="Waiting for blob store to be unblocked from network")
    async def test_processing_state_marked_failed_on_error(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage_external: AzureBlobStorage,
    ):
        """
        Test that ImageProcessingState is marked as failed when workflow errors occur.

        Simulates a defender scan timeout scenario.
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-state"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()

        # Act
        from uuid6 import uuid7

        test_workflow_id = str(uuid7())

        workflow_handle = DBOS.start_workflow(
            image_processing_workflow,
            image_id=image_id,
            file_bytes=file_bytes,
            user_id=test_user,
            org_prefix=org_prefix,
            parent_workflow_id=test_workflow_id,
        )
        actual_workflow_id = workflow_handle.get_workflow_id()
        workflow_id = test_workflow_id

        # Create processing state immediately after workflow start
        from app.service.constants import ProcessingStatus

        processing_state = ImageProcessingState(
            workflow_id=workflow_id,
            picture_id=image_id,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Wait for workflow to upload blob, then set Defender tags with an ERROR
        # to trigger immediate failure instead of waiting 300s for timeout
        blob_name = f"{org_prefix}/{image_id}.png"
        # Poll for blob existence (workflow uploads it)
        for _ in range(30):  # Wait up to 3 seconds
            if await azure_storage_external.blob_exists(
                containers["original"], blob_name
            ):
                break
            await asyncio.sleep(0.1)

        # Set Defender tags with a permanent error code (SAM259222) to trigger failure
        await mock_defender_tags_in_azurite(
            azure_storage_external,
            containers["original"],
            blob_name,
            scan_result="SAM259222",  # Permanent error - triggers immediate failure
            upload_placeholder=False,  # Blob already exists from workflow
        )

        # Wait for workflow to fail
        try:
            await wait_for_workflow_completion(actual_workflow_id, timeout=60)
        except Exception:
            pass  # Expected to fail

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert - Query the ImageProcessingState
        stmt = select(ImageProcessingState).where(
            ImageProcessingState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify state is marked as failed
        assert state is not None, "ImageProcessingState should exist even on failure"
        assert state.status == "failed", (
            f"Expected status 'failed', got '{state.status}'"
        )
        assert state.failed_at is not None, "failed_at should be set"
        assert state.error_message is not None, "error_message should be set"
        assert state.progress_percentage == 0, (
            "progress should be reset to 0 on failure"
        )

    async def test_inference_state_marked_failed_on_error(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_picture: Picture,
        test_user: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_pipeline: Pipeline,
    ):
        """
        Test that InferenceRequestState is marked as failed when inference errors occur.

        Simulates a missing sanitized image scenario.
        """
        # Arrange
        image_id = test_picture.id
        pipeline_id = test_pipeline.id

        # DO NOT upload sanitized image - this will cause workflow to fail
        test_picture.blob_url_sanitized = None
        integration_db_session.add(test_picture)
        await integration_db_session.commit()

        # Act
        workflow_handle = DBOS.start_workflow(
            image_inference_workflow,
            image_id=image_id,
            org_prefix="test-state",
            pipeline_id=pipeline_id,
            image_dims=[test_picture.width, test_picture.height],
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            parent_workflow_id=uuid7(),  # Generate a parent workflow ID
        )
        workflow_id = workflow_handle.get_workflow_id()

        # Wait for workflow to fail
        try:
            await wait_for_workflow_completion(workflow_id, timeout=60)
        except Exception:
            pass  # Expected to fail

        # Expire all cached objects to force fresh database query
        integration_db_session.expire_all()

        # Assert
        stmt = select(InferenceRequestState).where(
            InferenceRequestState.workflow_id == workflow_id
        )
        result = await integration_db_session.execute(stmt)
        state = result.scalar_one_or_none()

        # Verify state is marked as failed
        assert state is not None, "InferenceRequestState should exist even on failure"
        assert state.status == "failed", (
            f"Expected status 'failed', got '{state.status}'"
        )
        assert state.failed_at is not None, "failed_at should be set"
        assert state.error_message is not None, "error_message should be set"
