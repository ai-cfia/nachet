"""
Integration tests for submit_inference_request.

These tests use real database and real Azurite (no mocks) to test the complete
image submission and workflow enqueuing process.

Prerequisites:
- PostgreSQL with nachet-backend-test schema
- Azurite container running: docker compose up -d nachet-blob
- Test environment variables in .env.test.local
- DBOS initialized

Usage:
    cd backend/
    export $(grep -v '^#' .env.test.local | xargs)
    uv run pytest tests/integration/test_submit_inference_integration.py -v
"""

import pytest
import pytest_asyncio
import base64
import os
from dotenv import load_dotenv
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.service.inference import InferenceService
from app.db.model import Picture, ImageProcessingState, Folder
from app.service.constants import ProcessingStatus
from app.model.inference import InferenceRequest, TrayCode
from app.exceptions import InvalidImageError, FolderNotFoundError, ImageProcessingError
from app.blob.azure.storage import AzureBlobStorage
from app.api.config import get_settings
from tests.fixtures.test_images import get_test_seed_image

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


def get_test_config():
    """Get blob storage config for testing."""
    settings = get_settings()
    if settings.blob_storage_name and settings.blob_storage_key:
        return settings.blob_storage_config
    raise ValueError("No Azure Storage configuration found in settings")


@pytest_asyncio.fixture()
async def test_folder(
    integration_db_session: AsyncSession,
    test_user: UUID,
    test_org_admin_role: UUID,
    test_org_user_role: UUID,
    cleanup_test_folders: list,
):
    """Create a test folder for image submissions."""
    folder = Folder(
        id=uuid4(),
        name="Test Submission Folder",
        user_id=test_user,
        org_user_role_id=test_org_user_role,
        org_admin_role_id=test_org_admin_role,
        folder_prefix="test-submit",
        description="Test folder for submit_inference_request integration tests",
        active=True,
    )
    integration_db_session.add(folder)
    await integration_db_session.commit()
    await integration_db_session.refresh(folder)
    cleanup_test_folders.append(folder.id)
    yield folder.id


@pytest.fixture()
def test_image_base64():
    """Load test PNG image as base64 with data URL prefix."""
    image_bytes = get_test_seed_image()
    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{base64_str}"


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


@pytest.fixture()
def test_inference_request(
    test_folder: UUID,
    test_image_base64: str,
    test_pipeline_id: UUID,
    test_device_model: UUID,
    test_device_lens: UUID,
):
    """Create valid InferenceRequest for testing."""
    return InferenceRequest(
        pipeline_id=str(test_pipeline_id),
        folder_name="Test Submission Folder",
        folder_id=str(test_folder),
        image_dims=[638, 559],  # Dimensions of test seed image
        image=test_image_base64,
        area_ratio=0.5,
        color_format="hex",
        # Required metadata fields (must match validation rules)
        image_name="Test-Seed-Image",  # Alphanumeric + hyphens only
        image_description="Integration test image for inference request",
        device_model_id=test_device_model,
        device_lens_id=test_device_lens,
        tray_code=TrayCode.A,  # Must be A, B, C, D, or E
        magnification=40.0,
    )


@pytest_asyncio.fixture()
async def azure_storage_with_cleanup():
    """Create AzureBlobStorage instance with cleanup."""
    config = get_test_config()
    storage = AzureBlobStorage(config)
    yield storage

    # Cleanup: Remove test blobs
    try:
        containers_result = await storage.list_containers()
        for container in containers_result.get("containers", []):
            container_name = container.get("name", "")
            if container_name.startswith("nachet-") and "-test" in container_name:
                try:
                    blobs_result = await storage.list_blobs(container_name)
                    for blob in blobs_result.get("blobs", []):
                        blob_name = blob.get("name")
                        if blob_name and "test-" in blob_name:
                            await storage.delete_blob(container_name, blob_name)
                except Exception:
                    pass
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.asyncio
class TestSubmitInferenceRequestHappyPath:
    """Happy path tests for submit_inference_request."""

    async def test_submit_creates_picture_and_state(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_inference_request: InferenceRequest,
        cleanup_test_pictures: list,
    ):
        """
        Test successful image submission creates Picture and ImageProcessingState.

        This test verifies:
        - Picture record created with correct fields
        - ImageProcessingState created with PENDING status
        - Workflow ID stored
        - Response structure is correct
        """
        # Act
        response = await InferenceService.submit_inference_request(
            request=test_inference_request,
            user_id=test_user,
        )

        # Assert response structure
        assert response.image_id is not None
        assert response.workflow_id is not None
        assert response.status == ProcessingStatus.PENDING.value
        assert "submitted" in response.message.lower()

        # Track for cleanup
        image_id = UUID(response.image_id)
        cleanup_test_pictures.append(image_id)

        # Verify Picture record created
        picture_result = await integration_db_session.execute(
            select(Picture).where(Picture.id == image_id)
        )
        picture = picture_result.scalar_one()

        assert picture is not None
        assert picture.folder_id == UUID(test_inference_request.folder_id)
        assert picture.user_id == test_user
        assert picture.width == 638
        assert picture.height == 559
        assert picture.format == "image/png"  # MIME type format
        assert picture.sha256 is not None
        assert len(picture.sha256) == 64  # SHA256 is 64 hex chars

        # Verify ImageProcessingState created
        state_result = await integration_db_session.execute(
            select(ImageProcessingState).where(
                ImageProcessingState.picture_id == image_id
            )
        )
        state = state_result.scalar_one()

        assert state is not None
        assert state.status == ProcessingStatus.PENDING.value
        assert state.workflow_id == response.workflow_id
        assert state.created_at is not None
        assert state.progress_percentage == 5  # Initial progress is 5%

    async def test_submit_duplicate_image_reuses_id(
        self,
        dbos_runtime,
        integration_db_session: AsyncSession,
        test_user: UUID,
        test_folder: UUID,
        test_org_admin_role: UUID,
        test_org_user_role: UUID,
        test_inference_request: InferenceRequest,
        cleanup_test_pictures: list,
    ):
        """
        Test submitting duplicate image (same SHA256) reuses existing image_id.

        This verifies duplicate detection works correctly.
        """
        # First submission
        response1 = await InferenceService.submit_inference_request(
            request=test_inference_request,
            user_id=test_user,
        )

        image_id_1 = UUID(response1.image_id)
        cleanup_test_pictures.append(image_id_1)

        # Get SHA256 from first submission
        picture_result = await integration_db_session.execute(
            select(Picture).where(Picture.id == image_id_1)
        )
        picture1 = picture_result.scalar_one()
        sha256_hash = picture1.sha256

        # Second submission with same image
        response2 = await InferenceService.submit_inference_request(
            request=test_inference_request,
            user_id=test_user,
        )

        image_id_2 = UUID(response2.image_id)

        # Assert - should reuse same image_id (duplicate detection)
        assert image_id_1 == image_id_2, "Duplicate image should reuse same image_id"
        # For duplicates, a new workflow IS created (for inference), but preprocessing is skipped
        assert response2.workflow_id is not None, (
            "Duplicate should create workflow for inference"
        )
        assert response2.status == ProcessingStatus.PENDING.value
        assert (
            "preprocessing skipped" in response2.message.lower()
            or "duplicate" in response2.message.lower()
        )

        # Verify only one Picture record exists
        all_pictures_result = await integration_db_session.execute(
            select(Picture).where(Picture.sha256 == sha256_hash)
        )
        all_pictures = all_pictures_result.scalars().all()

        assert len(all_pictures) == 1, (
            "Should only have one Picture for duplicate submissions"
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestSubmitInferenceRequestValidation:
    """Validation and error handling tests."""

    async def test_submit_invalid_folder_id(
        self,
        test_user: UUID,
        test_image_base64: str,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """Test submission with non-existent folder raises error."""
        # Arrange
        fake_folder_id = str(uuid4())

        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Fake Folder",
            folder_id=fake_folder_id,
            image_dims=[640, 480],
            image=test_image_base64,
            area_ratio=0.5,
            color_format="hex",
            image_name="Test-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.B,
            magnification=40.0,
        )

        # Act & Assert
        with pytest.raises(
            (FolderNotFoundError, ValueError, ImageProcessingError)
        ) as exc_info:
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_user,
            )

        # Verify error message mentions folder
        assert "folder" in str(exc_info.value).lower()

    async def test_submit_invalid_image_size_too_large(
        self,
        test_user: UUID,
        test_folder: UUID,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """Test submission with >10MB image raises InvalidImageError."""
        # Arrange - create a large base64 string (>10MB)
        large_data = b"A" * (11 * 1024 * 1024)  # 11MB
        large_base64 = base64.b64encode(large_data).decode("utf-8")

        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Test Folder",
            folder_id=str(test_folder),
            image_dims=[640, 480],
            image=f"data:image/png;base64,{large_base64}",
            area_ratio=0.5,
            color_format="hex",
            image_name="Large-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.C,
            magnification=40.0,
        )

        # Act & Assert
        with pytest.raises(InvalidImageError) as exc_info:
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_user,
            )

        assert "10MB" in str(exc_info.value) or "size" in str(exc_info.value).lower()

    async def test_submit_invalid_image_dimensions_too_small(
        self,
        test_user: UUID,
        test_folder: UUID,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """Test submission with <384x384 image raises InvalidImageError."""
        # Arrange - create a small PNG image (but large enough to pass base64 size check)
        from PIL import Image
        from io import BytesIO

        # Use 383x383 to ensure it fails dimension check but has enough data
        small_image = Image.new("RGB", (383, 383), color="red")
        buffer = BytesIO()
        small_image.save(buffer, format="PNG")
        small_bytes = buffer.getvalue()
        small_base64 = base64.b64encode(small_bytes).decode("utf-8")

        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Test Folder",
            folder_id=str(test_folder),
            image_dims=[383, 383],
            image=f"data:image/png;base64,{small_base64}",
            area_ratio=0.5,
            color_format="hex",
            image_name="Small-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.D,
            magnification=40.0,
        )

        # Act & Assert
        with pytest.raises(InvalidImageError) as exc_info:
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_user,
            )

        assert (
            "384" in str(exc_info.value) or "dimension" in str(exc_info.value).lower()
        )

    async def test_submit_non_png_image(
        self,
        test_user: UUID,
        test_folder: UUID,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """Test submission with JPEG image raises InvalidImageError."""
        # Arrange - create a JPEG image
        from PIL import Image
        from io import BytesIO

        jpeg_image = Image.new("RGB", (640, 480), color="blue")
        buffer = BytesIO()
        jpeg_image.save(buffer, format="JPEG")
        jpeg_bytes = buffer.getvalue()
        jpeg_base64 = base64.b64encode(jpeg_bytes).decode("utf-8")

        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Test Folder",
            folder_id=str(test_folder),
            image_dims=[640, 480],
            image=f"data:image/jpeg;base64,{jpeg_base64}",
            area_ratio=0.5,
            color_format="hex",
            image_name="JPEG-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.E,
            magnification=40.0,
        )

        # Act & Assert
        with pytest.raises(InvalidImageError) as exc_info:
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_user,
            )

        assert (
            "png" in str(exc_info.value).lower()
            or "format" in str(exc_info.value).lower()
        )

    async def test_submit_corrupted_base64(
        self,
        test_user: UUID,
        test_folder: UUID,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """Test submission with corrupted base64 raises InvalidImageError."""
        # Arrange - corrupted base64
        corrupted_base64 = "data:image/png;base64,NOT_VALID_BASE64!!!"

        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Test Folder",
            folder_id=str(test_folder),
            image_dims=[640, 480],
            image=corrupted_base64,
            area_ratio=0.5,
            color_format="hex",
            image_name="Corrupted-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.A,
            magnification=40.0,
        )

        # Act & Assert
        with pytest.raises((InvalidImageError, ValueError)):
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_user,
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestSubmitInferenceRequestRbac:
    """RBAC and authorization tests."""

    async def test_submit_as_org_user_role(
        self,
        dbos_runtime,
        test_user: UUID,  # Has org user role
        test_inference_request: InferenceRequest,
        cleanup_test_pictures: list,
    ):
        """Test submission by organization user role succeeds."""
        # Act
        response = await InferenceService.submit_inference_request(
            request=test_inference_request,
            user_id=test_user,
        )

        # Assert
        assert response.image_id is not None
        assert response.status == ProcessingStatus.PENDING.value

        cleanup_test_pictures.append(UUID(response.image_id))

    async def test_submit_as_org_admin_role(
        self,
        dbos_runtime,
        test_admin_user: UUID,  # Has org admin role
        test_inference_request: InferenceRequest,
        cleanup_test_pictures: list,
    ):
        """Test submission by organization admin role succeeds."""
        # Act
        response = await InferenceService.submit_inference_request(
            request=test_inference_request,
            user_id=test_admin_user,
        )

        # Assert
        assert response.image_id is not None
        assert response.status == ProcessingStatus.PENDING.value

        cleanup_test_pictures.append(UUID(response.image_id))

    async def test_submit_folder_different_org(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,  # Different user without access
        test_folder: UUID,
        test_image_base64: str,
        test_pipeline_id: UUID,
        test_device_model: UUID,
        test_device_lens: UUID,
    ):
        """
        Test submission to folder from different organization is denied.

        Note: This test may need adjustment based on actual RBAC implementation.
        """
        # Arrange
        request = InferenceRequest(
            pipeline_id=str(test_pipeline_id),
            folder_name="Test Folder",
            folder_id=str(test_folder),
            image_dims=[638, 559],
            image=test_image_base64,
            area_ratio=0.5,
            color_format="hex",
            image_name="Test-Image",
            image_description="Test description",
            device_model_id=test_device_model,
            device_lens_id=test_device_lens,
            tray_code=TrayCode.B,
            magnification=40.0,
        )

        # Act & Assert - should raise authorization error
        with pytest.raises((FolderNotFoundError, ValueError, Exception)) as exc_info:
            await InferenceService.submit_inference_request(
                request=request,
                user_id=test_regular_user,
            )

        # Verify error mentions access or authorization
        error_msg = str(exc_info.value).lower()
        assert any(
            word in error_msg
            for word in ["folder", "access", "not found", "organization"]
        )
