"""
Integration tests for DBOS workflow with real Azurite blob storage.

These tests use the local Azurite container (not mocked) to test the complete
image processing pipeline with actual Azure Blob Storage operations.

Prerequisites:
- Azurite container must be running: docker compose up -d nachet-blob
- Test environment variables must be configured in .env.test.local
- Database must be initialized with test schema

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_dbos_azurite_integration.py -v
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from uuid6 import uuid7
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

from app.db.model import ImageProcessingState, Folder, Picture
from app.service.constants import ProcessingStatus
from app.blob.azure.storage import AzureBlobStorage
from app.api.config import get_settings
from tests.fixtures.test_images import get_test_seed_image

# Load test environment variables
if not os.getenv("BLOB_STORAGE_PROVIDER"):
    load_dotenv(".env.test.local")


def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()

    # If blob storage is configured in settings, use it
    if settings.blob_storage_name and settings.blob_storage_key:
        return settings.blob_storage_config

    raise ValueError("No Azure Storage configuration found in settings")


@pytest_asyncio.fixture
async def test_folder(
    integration_db_session: AsyncSession,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
):
    """Create a test folder for image uploads."""
    folder = Folder(
        id=uuid4(),
        name="Test Folder Azurite",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-azurite",
        description="Test folder for DBOS Azurite integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    yield folder.id
    # Cleanup handled by conftest.py cleanup fixtures


@pytest_asyncio.fixture
async def azure_storage():
    """Create a real AzureBlobStorage instance connected to Azurite."""
    config = get_test_config()
    storage = AzureBlobStorage(config)
    yield storage
    # Cleanup: Delete test containers if they exist
    try:
        # List and clean up test containers
        containers_result = await storage.list_containers()
        for container in containers_result.get("containers", []):
            container_name = container.get("name", "")
            if container_name.startswith("nachet-") and "-test" in container_name:
                # Clean up test blobs
                try:
                    blobs_result = await storage.list_blobs(container_name)
                    for blob in blobs_result.get("blobs", []):
                        blob_name = blob.get("name")
                        if blob_name:
                            await storage.delete_blob(container_name, blob_name)
                except Exception:
                    pass  # Container might not exist
    except Exception:
        pass  # Cleanup is best-effort


class TestAzuriteBlobOperations:
    """Test blob operations with real Azurite storage."""

    @pytest.mark.asyncio
    async def test_upload_to_azure_blob_azurite(self, azure_storage):
        """Test successful blob upload to Azurite."""
        # Arrange
        image_id = uuid7()
        file_bytes = get_test_seed_image()
        genus = "avena"
        species = "fatua"
        org_name = "cfia-org"

        # Create test container
        container_name = "nachet-original-test"
        await azure_storage.create_container(container_name)

        # Act - Upload using the actual blob storage
        blob_name = f"{org_name}/{genus}-{species}/{image_id}.png"
        result = await azure_storage.upload_blob(
            container=container_name,
            name=blob_name,
            data=file_bytes,
            overwrite=True,
        )

        # Assert
        assert result is not None
        assert result.get("name") == blob_name
        assert result.get("container") == container_name

        # Verify blob exists
        exists = await azure_storage.blob_exists(container_name, blob_name)
        assert exists is True

        # Verify blob properties
        properties = await azure_storage.get_blob_properties(container_name, blob_name)
        assert properties.get("name") == blob_name
        assert properties.get("size") > 0

        # Clean up
        await azure_storage.delete_blob(container_name, blob_name)

    @pytest.mark.asyncio
    async def test_list_blobs_azurite(self, azure_storage):
        """Test listing blobs in Azurite container."""
        # Arrange
        container_name = "nachet-test-list"
        await azure_storage.create_container(container_name)

        # Upload test blobs
        test_blobs = []
        for i in range(3):
            blob_name = f"test-folder/test-blob-{i}.txt"
            test_data = f"Test data {i}".encode("utf-8")
            await azure_storage.upload_blob(container_name, blob_name, test_data)
            test_blobs.append(blob_name)

        # Act
        result = await azure_storage.list_blobs(container_name)

        # Assert
        assert "blobs" in result
        assert len(result["blobs"]) >= 3
        blob_names = [blob["name"] for blob in result["blobs"]]
        for test_blob in test_blobs:
            assert test_blob in blob_names

        # Clean up
        for blob_name in test_blobs:
            await azure_storage.delete_blob(container_name, blob_name)

    @pytest.mark.asyncio
    async def test_download_blob_azurite(self, azure_storage):
        """Test downloading blob from Azurite."""
        # Arrange
        container_name = "nachet-test-download"
        await azure_storage.create_container(container_name)

        blob_name = "test-download.txt"
        test_data = b"This is test data for download"
        await azure_storage.upload_blob(container_name, blob_name, test_data)

        # Act
        downloaded_data = await azure_storage.download_blob(container_name, blob_name)

        # Assert
        assert downloaded_data == test_data

        # Clean up
        await azure_storage.delete_blob(container_name, blob_name)

    @pytest.mark.asyncio
    async def test_copy_blob_azurite(self, azure_storage):
        """Test copying blob within Azurite."""
        # Arrange
        container_name = "nachet-test-copy"
        await azure_storage.create_container(container_name)

        source_blob = "source/test.txt"
        dest_blob = "dest/test.txt"
        test_data = b"Test data for copy operation"

        await azure_storage.upload_blob(container_name, source_blob, test_data)

        # Act
        result = await azure_storage.copy_blob(
            source_container=container_name,
            source_name=source_blob,
            dest_container=container_name,
            dest_name=dest_blob,
        )

        # Assert
        assert result is not None
        dest_exists = await azure_storage.blob_exists(container_name, dest_blob)
        assert dest_exists is True

        # Verify content matches
        downloaded = await azure_storage.download_blob(container_name, dest_blob)
        assert downloaded == test_data

        # Clean up
        await azure_storage.delete_blob(container_name, source_blob)
        await azure_storage.delete_blob(container_name, dest_blob)

    @pytest.mark.asyncio
    async def test_move_blob_azurite(self, azure_storage):
        """Test moving blob within Azurite."""
        # Arrange
        container_name = "nachet-test-move"
        await azure_storage.create_container(container_name)

        source_blob = "source/test-move.txt"
        dest_blob = "dest/test-move.txt"
        test_data = b"Test data for move operation"

        await azure_storage.upload_blob(container_name, source_blob, test_data)

        # Act
        result = await azure_storage.move_blob(
            source_container=container_name,
            source_name=source_blob,
            dest_container=container_name,
            dest_name=dest_blob,
        )

        # Assert
        assert result is not None

        # Source should not exist
        source_exists = await azure_storage.blob_exists(container_name, source_blob)
        assert source_exists is False

        # Destination should exist
        dest_exists = await azure_storage.blob_exists(container_name, dest_blob)
        assert dest_exists is True

        # Verify content
        downloaded = await azure_storage.download_blob(container_name, dest_blob)
        assert downloaded == test_data

        # Clean up
        await azure_storage.delete_blob(container_name, dest_blob)

    @pytest.mark.asyncio
    async def test_blob_metadata_azurite(self, azure_storage):
        """Test blob metadata operations with Azurite."""
        # Arrange
        container_name = "nachet-test-metadata"
        await azure_storage.create_container(container_name)

        blob_name = "test-metadata.txt"
        test_data = b"Test data with metadata"
        metadata = {
            "project": "nachet",
            "environment": "test",
            "version": "1.0",
        }

        # Upload with metadata
        await azure_storage.upload_blob(
            container=container_name,
            name=blob_name,
            data=test_data,
            metadata=metadata,
        )

        # Act - Get properties to verify metadata
        properties = await azure_storage.get_blob_properties(container_name, blob_name)

        # Assert
        assert properties.get("metadata") is not None
        retrieved_metadata = properties.get("metadata")
        assert retrieved_metadata.get("project") == "nachet"
        assert retrieved_metadata.get("environment") == "test"
        assert retrieved_metadata.get("version") == "1.0"

        # Clean up
        await azure_storage.delete_blob(container_name, blob_name)

    @pytest.mark.asyncio
    async def test_container_operations_azurite(self, azure_storage):
        """Test container create/delete operations with Azurite."""
        # Arrange
        container_name = "nachet-test-container-ops"

        # Act - Create container
        await azure_storage.create_container(container_name)

        # Assert - Container exists
        exists = await azure_storage.container_exists(container_name)
        assert exists is True

        # Act - List containers should include our test container
        containers_result = await azure_storage.list_containers()
        container_names = [c["name"] for c in containers_result["containers"]]
        assert container_name in container_names

        # Act - Delete container
        await azure_storage.delete_container(container_name)

        # Assert - Container no longer exists
        exists_after = await azure_storage.container_exists(container_name)
        assert exists_after is False


class TestAzuriteImageProcessingWorkflow:
    """Test complete image processing workflow with Azurite."""

    @pytest.mark.asyncio
    async def test_image_upload_workflow_azurite(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_folder: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage,
    ):
        """Test complete image upload workflow using Azurite."""
        # Arrange
        image_id = uuid7()
        container_name = "nachet-original-test"
        await azure_storage.create_container(container_name)

        # Create Picture record
        picture = Picture(
            id=image_id,
            folder_id=test_folder,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="test_seed_azurite.png",
            blob_url_original=f"http://localhost:12434/devstoreaccount1/{container_name}/test/{image_id}.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_sha256_hash_azurite",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()

        # Create processing state
        processing_state = ImageProcessingState(
            picture_id=image_id,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Act - Upload blob
        file_bytes = get_test_seed_image()
        blob_name = f"cfia-org/avena-fatua/{image_id}.png"
        upload_result = await azure_storage.upload_blob(
            container=container_name,
            name=blob_name,
            data=file_bytes,
            overwrite=True,
        )

        # Update processing state
        processing_state.status = ProcessingStatus.UPLOADED
        processing_state.progress_percentage = 25
        processing_state.uploaded_at = datetime.now(timezone.utc)
        processing_state.blob_url_original = (
            f"http://localhost:12434/devstoreaccount1/{container_name}/{blob_name}"
        )
        await integration_db_session.commit()

        # Assert - Verify upload
        assert upload_result is not None
        blob_exists = await azure_storage.blob_exists(container_name, blob_name)
        assert blob_exists is True

        # Verify database state
        await integration_db_session.refresh(processing_state)
        assert processing_state.status == ProcessingStatus.UPLOADED
        assert processing_state.blob_url_original is not None

        # Clean up
        await azure_storage.delete_blob(container_name, blob_name)
        await integration_db_session.delete(processing_state)
        await integration_db_session.delete(picture)
        await integration_db_session.commit()

    @pytest.mark.asyncio
    async def test_full_pipeline_stages_azurite(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_folder: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        azure_storage,
    ):
        """Test all pipeline stages with Azurite storage."""
        # Arrange
        image_id = uuid7()
        original_container = "nachet-original-test"
        sanitized_container = "nachet-sanitized-test"

        await azure_storage.create_container(original_container)
        await azure_storage.create_container(sanitized_container)

        # Create Picture record
        picture = Picture(
            id=image_id,
            folder_id=test_folder,
            user_id=test_user,
            org_user_role_id=test_org_user_role,
            org_admin_role_id=test_org_admin_role,
            name="test_pipeline.png",
            blob_url_original=f"http://localhost:12434/devstoreaccount1/{original_container}/test/{image_id}.png",
            width=100,
            height=100,
            format="png",
            size_on_disk_original=1024.0,
            sha256="test_pipeline_hash",
        )
        integration_db_session.add(picture)
        await integration_db_session.commit()

        # Create processing state
        processing_state = ImageProcessingState(
            picture_id=image_id,
            status=ProcessingStatus.PENDING,
            progress_percentage=0,
            created_at=datetime.now(timezone.utc),
        )
        integration_db_session.add(processing_state)
        await integration_db_session.commit()

        # Act - Stage 1: Upload to original container
        file_bytes = get_test_seed_image()
        original_blob_name = f"cfia-org/avena-fatua/{image_id}.png"

        await azure_storage.upload_blob(
            container=original_container,
            name=original_blob_name,
            data=file_bytes,
            overwrite=True,
        )

        processing_state.status = ProcessingStatus.UPLOADED
        processing_state.progress_percentage = 25
        processing_state.uploaded_at = datetime.now(timezone.utc)
        processing_state.blob_url_original = f"http://localhost:12434/devstoreaccount1/{original_container}/{original_blob_name}"
        await integration_db_session.commit()

        # Stage 2: Simulate sanitization (copy to sanitized container)
        sanitized_blob_name = f"avena/fatua/{image_id}.png"

        await azure_storage.copy_blob(
            source_container=original_container,
            source_name=original_blob_name,
            dest_container=sanitized_container,
            dest_name=sanitized_blob_name,
        )

        processing_state.status = ProcessingStatus.SANITIZED
        processing_state.progress_percentage = 90
        processing_state.sanitization_completed_at = datetime.now(timezone.utc)
        processing_state.blob_url_sanitized = f"http://localhost:12434/devstoreaccount1/{sanitized_container}/{sanitized_blob_name}"
        await integration_db_session.commit()

        # Stage 3: Complete
        processing_state.status = ProcessingStatus.COMPLETED
        processing_state.progress_percentage = 100
        processing_state.completed_at = datetime.now(timezone.utc)
        await integration_db_session.commit()

        # Assert - Verify all stages
        await integration_db_session.refresh(processing_state)

        assert processing_state.status == ProcessingStatus.COMPLETED
        assert processing_state.progress_percentage == 100
        assert processing_state.uploaded_at is not None
        assert processing_state.sanitization_completed_at is not None
        assert processing_state.completed_at is not None
        assert processing_state.blob_url_original is not None
        assert processing_state.blob_url_sanitized is not None

        # Verify both blobs exist
        original_exists = await azure_storage.blob_exists(
            original_container, original_blob_name
        )
        sanitized_exists = await azure_storage.blob_exists(
            sanitized_container, sanitized_blob_name
        )

        assert original_exists is True
        assert sanitized_exists is True

        # Verify we can download both
        original_data = await azure_storage.download_blob(
            original_container, original_blob_name
        )
        sanitized_data = await azure_storage.download_blob(
            sanitized_container, sanitized_blob_name
        )

        assert len(original_data) > 0
        assert len(sanitized_data) > 0
        assert (
            original_data == sanitized_data
        )  # Should be identical (no actual sanitization)

        # Clean up
        await azure_storage.delete_blob(original_container, original_blob_name)
        await azure_storage.delete_blob(sanitized_container, sanitized_blob_name)
        await integration_db_session.delete(processing_state)
        await integration_db_session.delete(picture)
        await integration_db_session.commit()
