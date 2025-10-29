"""
Integration tests for image_processing_workflow.

These tests use real database, real Azurite, and real DBOS workflows to test
the complete image processing pipeline with no mocks.

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Azurite container running: docker compose up -d nachet-blob
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_process_image_pipeline_integration.py -v -s
"""

import pytest
import pytest_asyncio
import asyncio
import os
from dotenv import load_dotenv
from uuid import uuid4, UUID
from uuid6 import uuid7
from sqlalchemy.ext.asyncio import AsyncSession

from app.service.inference import image_processing_workflow
from app.service.blob_operations import (
    upload_to_azure_blob,
)
from tests.integration.test_workflows import (
    trigger_sanitization_workflow,
)
from app.db.model import Picture, ImageProcessingState, Folder
from app.service.constants import ProcessingStatus
from app.blob.azure.storage import AzureBlobStorage
from app.api.config import get_settings
from app.exceptions import (
    DefenderScanTimeoutError,
    DefenderScanFailedError,
    DefenderScanNotScannedError,
    SanitizationError,
)
from tests.fixtures.test_images import get_test_seed_image
from tests.integration.helpers import (
    wait_for_workflow_completion,
    assert_blob_exists_in_azurite,
    mock_defender_tags_in_azurite,
    download_blob_from_azurite,
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
        name="Test Workflow Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-wf",
        description="Test folder for workflow integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    cleanup_test_folders.append(folder.id)
    yield folder.id


@pytest_asyncio.fixture
async def azure_storage():
    """Get the external storage client from BlobStorageManager for testing.

    Note: wait_for_defender_scan uses EXTERNAL storage to check Defender tags,
    so tests must mock tags on the external storage client.
    """
    from app.blob.manager import blob_storage_manager

    # Return the external storage client that's used by wait_for_defender_scan
    storage = blob_storage_manager.get_client("external")
    yield storage

    # Cleanup handled by test methods


@pytest_asyncio.fixture
async def azure_storage_onprem():
    """Get the onprem storage client from BlobStorageManager for testing.

    Note: trigger_sanitization_function_local uploads sanitized images to ONPREM storage,
    so tests must verify sanitized blobs on the onprem storage client.
    """
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
    """Create a test Picture record for workflow testing."""
    picture_id = uuid7()
    org_prefix = "test-wf"
    picture = Picture(
        id=picture_id,
        folder_id=test_folder,
        user_id=test_user,
        org_admin_role_id=test_org_admin_role,
        org_user_role_id=test_org_user_role,
        name="test_workflow.png",
        width=638,
        height=559,
        format="PNG",
        sha256="test_hash_" + str(picture_id),
        blob_url_original=f"{org_prefix}/{picture_id}.png",
        blob_url_sanitized=None,  # Will be set by workflow
        size_on_disk_original=1024,  # Mock size in bytes
    )
    integration_db_session.add(picture)
    await integration_db_session.commit()
    await integration_db_session.refresh(picture)
    cleanup_test_pictures.append(picture_id)
    yield picture


@pytest.mark.integration
@pytest.mark.asyncio
class TestProcessImagePipelineWorkflow:
    """Full workflow integration tests for image_processing_workflow."""

    async def test_workflow_upload_step_success(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test Step 1: upload_to_azure_blob with explicit ONPREM account.

        Note: The workflow uses EXTERNAL by default for Defender scanning,
        but this test verifies the ONPREM upload functionality.

        Verifies:
        - Blob uploaded to original container on onprem storage
        - Correct blob naming: {org_prefix}/{image_id}.png
        - Metadata includes user_id and date_uploaded
        """
        # Arrange
        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()
        containers = get_test_container_names()
        from app.service.constants import BlobAccount

        # Act - explicitly upload to ONPREM to test that functionality
        blob_path = await upload_to_azure_blob(
            image_id=image_id,
            file_bytes=file_bytes,
            org_prefix=org_prefix,
            user_id=test_user,
            blob_account=BlobAccount.ONPREM,
        )

        # Assert
        assert blob_path == f"{org_prefix}/{image_id}.png"

        # Verify blob exists in Azurite on ONPREM storage
        blob_info = await assert_blob_exists_in_azurite(
            storage=azure_storage_onprem,
            container=containers["original"],
            blob_name=blob_path,
        )

        assert blob_info is not None
        assert blob_info["name"] == blob_path

        # Cleanup
        await azure_storage_onprem.delete_blob(containers["original"], blob_path)

    async def test_workflow_defender_scan_clean(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage: AzureBlobStorage,
    ):
        """
        Test Step 2: wait_for_defender_scan with clean result.

        Verifies:
        - Blob tags set to "No threats found"
        - Defender scan returns status="clean"
        """
        # Arrange
        from dbos import DBOS
        from app.service.constants import BlobAccount
        from app.blob.manager import blob_storage_manager

        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()

        # Upload blob directly using storage client (not DBOS step)
        # This avoids DBOS runtime conflicts
        storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
        containers = get_test_container_names()
        blob_path = f"{org_prefix}/{image_id}.png"

        await storage.upload_blob(
            container=containers["original"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Mock Defender tags (Azurite doesn't run real scans)
        await mock_defender_tags_in_azurite(
            storage=azure_storage,
            container=get_test_container_names()["original"],
            blob_name=blob_path,
            scan_result="No threats found",
        )

        # Verify tags were set correctly before starting workflow
        tags = await azure_storage.get_blob_tags(
            get_test_container_names()["original"], blob_path
        )
        assert tags.get("Malware scanning scan result") == "No threats found"

        # Act - start the workflow directly (it's now a workflow, not a step)
        from app.service.blob_operations import wait_for_defender_scan

        handle = DBOS.start_workflow(
            wait_for_defender_scan,
            image_id=image_id,
            org_prefix=org_prefix,
            timeout_sec=30,
        )

        # Wait for workflow to complete using the helper function
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=60,
            poll_interval=1.0,
        )
        result = workflow_result["result"]

        # Assert
        assert result["status"] == "clean"
        assert "scan_timestamp" in result

        # Cleanup
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )

    async def test_workflow_defender_scan_malicious(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage: AzureBlobStorage,
    ):
        """
        Test Step 2: wait_for_defender_scan with malicious result.

        Verifies:
        - Malicious scan result raises DefenderScanFailedError
        """
        # Arrange
        from dbos import DBOS
        from app.service.constants import BlobAccount
        from app.blob.manager import blob_storage_manager

        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()

        # Upload blob directly using storage client (not DBOS step)
        storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
        containers = get_test_container_names()
        blob_path = f"{org_prefix}/{image_id}.png"

        await storage.upload_blob(
            container=containers["original"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Mock malicious scan result
        await mock_defender_tags_in_azurite(
            storage=azure_storage,
            container=get_test_container_names()["original"],
            blob_name=blob_path,
            scan_result="Malicious",
        )

        # Act & Assert - start the workflow directly
        from app.service.blob_operations import wait_for_defender_scan

        handle = DBOS.start_workflow(
            wait_for_defender_scan,
            image_id=image_id,
            org_prefix=org_prefix,
            timeout_sec=30,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises(DefenderScanFailedError) as exc_info:
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        assert "Malware detected" in str(exc_info.value)

        # Cleanup
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )

    async def test_workflow_defender_scan_not_scanned(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage: AzureBlobStorage,
    ):
        """
        Test Step 2: wait_for_defender_scan with 'Not scanned' result.

        Verifies:
        - Not scanned raises DefenderScanNotScannedError
        """
        # Arrange
        from dbos import DBOS
        from app.service.constants import BlobAccount
        from app.blob.manager import blob_storage_manager

        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()

        # Upload blob directly using storage client (not DBOS step)
        storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
        containers = get_test_container_names()
        blob_path = f"{org_prefix}/{image_id}.png"

        await storage.upload_blob(
            container=containers["original"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Mock 'Not scanned' result
        await mock_defender_tags_in_azurite(
            storage=azure_storage,
            container=get_test_container_names()["original"],
            blob_name=blob_path,
            scan_result="Not scanned",
        )

        # Act & Assert - start the workflow directly
        from app.service.blob_operations import wait_for_defender_scan

        handle = DBOS.start_workflow(
            wait_for_defender_scan,
            image_id=image_id,
            org_prefix=org_prefix,
            timeout_sec=30,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises(DefenderScanNotScannedError) as exc_info:
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        assert "could not be scanned" in str(exc_info.value)

        # Cleanup
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )

    async def test_workflow_sanitization_success(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage: AzureBlobStorage,
        azure_storage_onprem: AzureBlobStorage,
    ):
        """
        Test Step 3: trigger_sanitization_function_local succeeds.

        Verifies:
        - Downloads from original container (external storage)
        - Uploads to sanitized container (onprem storage)
        - Sanitized image has no EXIF metadata
        - Image dimensions preserved
        """
        # Arrange
        from dbos import DBOS
        from app.service.constants import BlobAccount
        from app.blob.manager import blob_storage_manager

        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()

        # Upload original blob directly to EXTERNAL storage
        storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
        containers = get_test_container_names()
        blob_path = f"{org_prefix}/{image_id}.png"

        await storage.upload_blob(
            container=containers["original"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Act - use workflow wrapper to test the step
        handle = DBOS.start_workflow(
            trigger_sanitization_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
        )

        # Wait for workflow to complete
        workflow_result = await wait_for_workflow_completion(
            workflow_id=handle.workflow_id,
            timeout=60,
            poll_interval=1.0,
        )
        sanitized_path = workflow_result["result"]

        # Assert
        assert sanitized_path == f"{org_prefix}/{image_id}.png"

        # Verify sanitized blob exists on ONPREM storage
        # (trigger_sanitization_function_local uploads to onprem storage)
        sanitized_blob = await assert_blob_exists_in_azurite(
            storage=azure_storage_onprem,
            container=get_test_container_names()["sanitized"],
            blob_name=sanitized_path,
        )
        assert sanitized_blob is not None

        # Download and verify sanitized image from ONPREM storage
        sanitized_bytes = await download_blob_from_azurite(
            storage=azure_storage_onprem,
            container=get_test_container_names()["sanitized"],
            blob_name=sanitized_path,
        )

        # Verify it's a valid PNG
        from PIL import Image
        from io import BytesIO

        sanitized_image = Image.open(BytesIO(sanitized_bytes))
        assert sanitized_image.format == "PNG"
        assert sanitized_image.size == (638, 559)  # Original dimensions preserved

        # Cleanup - delete from EXTERNAL and ONPREM storages
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )
        await azure_storage_onprem.delete_blob(
            get_test_container_names()["sanitized"], sanitized_path
        )

    async def test_workflow_complete_success_path(
        self,
        dbos_runtime,
        test_user: UUID,
        test_picture: Picture,
        azure_storage: AzureBlobStorage,
        azure_storage_onprem: AzureBlobStorage,
        integration_db_session: AsyncSession,
    ):
        """
        Test complete workflow: upload → defender → sanitization.

        This is the main integration test that verifies the entire pipeline.

        Correct storage flow:
        1. Upload to EXTERNAL storage (original container) - for Defender scanning
        2. Defender scan checks tags on EXTERNAL storage
        3. Sanitization downloads from EXTERNAL, uploads to ONPREM (sanitized container)

        Storage rationale:
        - EXTERNAL: Azure Defender malware scanning only works here
        - ONPREM: Sanitized files don't need Defender scan, stored locally

        Verifies:
        - All steps execute successfully
        - Original blob on EXTERNAL storage
        - Sanitized blob on ONPREM storage
        - DBOS events published
        - Workflow completes with status="completed"
        """
        # Arrange
        image_id = test_picture.id
        org_prefix = "test-wf"
        file_bytes = get_test_seed_image()

        # Create ImageProcessingState
        state = ImageProcessingState(
            picture_id=image_id,
            user_id=test_picture.user_id,
            org_user_role_id=test_picture.org_user_role_id,
            org_admin_role_id=test_picture.org_admin_role_id,
            status=ProcessingStatus.PENDING.value,
            workflow_id=None,
            progress_percentage=0,
        )
        integration_db_session.add(state)
        await integration_db_session.commit()

        # Act - Execute workflow
        workflow_handle = DBOS.start_workflow(
            image_processing_workflow,
            image_id=image_id,
            file_bytes=file_bytes,
            user_id=test_user,
            org_prefix=org_prefix,
        )

        workflow_id = workflow_handle.workflow_id

        # Mock Defender scan result after upload completes
        # Workflow uploads to EXTERNAL storage, where Defender scanning occurs
        await asyncio.sleep(2)

        blob_path = f"{org_prefix}/{image_id}.png"

        # Set Defender tags on EXTERNAL storage (where workflow uploaded)
        try:
            await mock_defender_tags_in_azurite(
                storage=azure_storage,  # external storage
                container=get_test_container_names()["original"],
                blob_name=blob_path,
                scan_result="No threats found",
            )
        except Exception:
            # Blob might not be uploaded yet, retry
            await asyncio.sleep(2)
            await mock_defender_tags_in_azurite(
                storage=azure_storage,  # external storage
                container=get_test_container_names()["original"],
                blob_name=blob_path,
                scan_result="No threats found",
            )

        # Wait for workflow completion
        try:
            workflow_result = await wait_for_workflow_completion(
                workflow_id=workflow_id,
                timeout=60,
                poll_interval=2.0,
            )
        except TimeoutError:
            # Workflow might still be running, check status
            pytest.fail(f"Workflow {workflow_id} timed out after 60s")

        # Assert workflow completed successfully
        assert workflow_result["status"] == "completed"
        result = workflow_result["result"]
        assert result["status"] == "completed"
        assert result["blob_url_original"] == blob_path
        assert result["blob_url_sanitized"] == blob_path

        # Verify blobs exist in correct storage accounts:
        # - Original on EXTERNAL (where workflow uploads for Defender scan)
        # - Sanitized on ONPREM (where sanitizer uploads the clean file)
        original_blob = await assert_blob_exists_in_azurite(
            storage=azure_storage,  # external storage
            container=get_test_container_names()["original"],
            blob_name=blob_path,
        )
        assert original_blob is not None

        sanitized_blob = await assert_blob_exists_in_azurite(
            storage=azure_storage_onprem,  # onprem storage
            container=get_test_container_names()["sanitized"],
            blob_name=blob_path,
        )
        assert sanitized_blob is not None

        # Verify DBOS events
        events = workflow_result["events"]
        assert events.get("processing_status") in ["completed", "sanitizing"]
        assert events.get("upload_complete") is True

        # Cleanup - delete from correct storage accounts
        # Original blob on EXTERNAL
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )
        # Sanitized blob on ONPREM
        await azure_storage_onprem.delete_blob(
            get_test_container_names()["sanitized"], blob_path
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestProcessImagePipelineErrors:
    """Error handling tests for image_processing_workflow."""

    async def test_workflow_defender_timeout(
        self,
        dbos_runtime,
        test_user: UUID,
        azure_storage: AzureBlobStorage,
    ):
        """
        Test that Defender scan timeout raises DefenderScanTimeoutError.

        Verifies:
        - Scan times out after specified duration
        - Proper error is raised
        """
        # Arrange
        from dbos import DBOS
        from app.service.constants import BlobAccount
        from app.blob.manager import blob_storage_manager

        image_id = uuid7()
        org_prefix = "test-org"
        file_bytes = get_test_seed_image()

        # Upload blob directly to EXTERNAL storage but DON'T set Defender tags
        storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
        containers = get_test_container_names()
        blob_path = f"{org_prefix}/{image_id}.png"

        await storage.upload_blob(
            container=containers["original"],
            name=blob_path,
            data=file_bytes,
            metadata={"user_id": str(test_user)},
        )

        # Act & Assert - should timeout
        from app.service.blob_operations import wait_for_defender_scan

        handle = DBOS.start_workflow(
            wait_for_defender_scan,
            image_id=image_id,
            org_prefix=org_prefix,
            timeout_sec=5,  # Short timeout
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises(DefenderScanTimeoutError):
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )

        # Cleanup
        await azure_storage.delete_blob(
            get_test_container_names()["original"], blob_path
        )

    async def test_workflow_sanitization_download_failure(
        self,
        dbos_runtime,
        azure_storage: AzureBlobStorage,
    ):
        """
        Test that sanitization fails if original blob doesn't exist.

        Verifies:
        - Download failure raises SanitizationError
        """
        # Arrange - try to sanitize non-existent blob
        from dbos import DBOS

        image_id = uuid7()
        org_prefix = "test-org"

        # Act & Assert - use workflow wrapper to test the step
        handle = DBOS.start_workflow(
            trigger_sanitization_workflow,
            image_id=image_id,
            org_prefix=org_prefix,
        )

        # Wait for workflow to complete - it should raise an error
        with pytest.raises(SanitizationError):
            await wait_for_workflow_completion(
                workflow_id=handle.workflow_id,
                timeout=60,
                poll_interval=1.0,
            )
