"""
Tests for camelCase alias support in response models.

Tests verify that:
- Response models serialize to camelCase (for frontend)
- Backend can use snake_case internally
- model_dump(by_alias=True) produces camelCase
- populate_by_name=True works for input
"""

from uuid import uuid4
from app.model.batch_upload import BatchUploadInitResponse, BatchUploadImageResponse
from app.model.directory import UpdateFolderResponse
from app.model.inference import (
    ImageSubmissionResponse,
    ApiInferenceResponse,
    ApiInferenceBox,
    ModelInfo,
    PixelBoundingBox,
)
from app.api.test_dbos import ToyWorkflowResponse, WorkflowStatusResponse


class TestBatchUploadInitResponseAliases:
    """Test camelCase serialization for BatchUploadInitResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize to camelCase for frontend."""
        session_id = str(uuid4())
        response = BatchUploadInitResponse(session_id=session_id)

        dumped = response.model_dump(by_alias=True)
        assert "sessionId" in dumped
        assert dumped["sessionId"] == session_id
        # snake_case should not be in output
        assert "session_id" not in dumped

    def test_response_accepts_snake_case_input(self):
        """Backend can construct response with snake_case."""
        session_id = str(uuid4())
        response = BatchUploadInitResponse(session_id=session_id)
        assert response.session_id == session_id


class TestBatchUploadImageResponseAliases:
    """Test camelCase serialization for BatchUploadImageResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize to camelCase for frontend."""
        response = BatchUploadImageResponse(
            success=True,
            picture_id="picture-123",
            workflow_id="workflow-456",
            error=None,
        )

        dumped = response.model_dump(by_alias=True, exclude_none=True)
        assert "success" in dumped
        assert "pictureId" in dumped
        assert "workflowId" in dumped
        # snake_case should not be in output
        assert "picture_id" not in dumped
        assert "workflow_id" not in dumped

    def test_response_with_error(self):
        """Error responses should also use camelCase."""
        response = BatchUploadImageResponse(
            success=False,
            picture_id=None,
            workflow_id=None,
            error="Upload failed",
        )

        dumped = response.model_dump(by_alias=True, exclude_none=True)
        assert dumped["success"] is False
        assert dumped["error"] == "Upload failed"


class TestUpdateFolderResponseAliases:
    """Test camelCase serialization for UpdateFolderResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize with aliases."""
        response = UpdateFolderResponse(
            id="folder-123",
            message="Folder updated successfully",
        )

        dumped = response.model_dump(by_alias=True)
        assert "id" in dumped
        assert "message" in dumped
        assert dumped["id"] == "folder-123"


class TestImageSubmissionResponseAliases:
    """Test camelCase serialization for ImageSubmissionResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize to camelCase for frontend."""
        response = ImageSubmissionResponse(
            image_id="image-123",
            workflow_id="workflow-456",
            status="processing",
            message="Image submitted successfully",
        )

        dumped = response.model_dump(by_alias=True)
        assert "imageId" in dumped
        assert "workflowId" in dumped
        assert "status" in dumped
        assert "message" in dumped
        # snake_case should not be in output
        assert "image_id" not in dumped
        assert "workflow_id" not in dumped

    def test_response_accepts_snake_case_input(self):
        """Backend can construct response with snake_case."""
        response = ImageSubmissionResponse(
            image_id="image-123",
            workflow_id="workflow-456",
            status="processing",
            message="Success",
        )
        assert response.image_id == "image-123"
        assert response.workflow_id == "workflow-456"


class TestApiInferenceResponseAliases:
    """Test camelCase serialization for ApiInferenceResponse."""

    def test_response_serializes_to_camelcase(self):
        """Complete inference response should serialize to camelCase."""
        pixel_box = PixelBoundingBox(topX=10, topY=20, bottomX=100, bottomY=200)

        box = ApiInferenceBox(
            box=pixel_box,
            label="species-a",
            score=0.95,
            topN=[],  # Required
            classId="class-1",  # Required
            object_type_id="obj-type-1",  # Required
            box_id="box-1",
            overlapping=False,  # Required
            overlappingIndices=-1,  # Required
            is_verified=False,
        )

        model = ModelInfo(name="test-model", version="1.0")

        response = ApiInferenceResponse(
            filename="test.png",
            image_id="image-123",
            inference_id="inference-456",
            boxes=[box],
            label_occurrence={"species-a": 1},
            total_boxes=1,
            models=[model],
        )

        dumped = response.model_dump(by_alias=True)

        # Check camelCase keys
        assert "filename" in dumped
        assert "imageId" in dumped
        assert "inferenceId" in dumped
        assert "boxes" in dumped
        assert "labelOccurrence" in dumped
        assert "totalBoxes" in dumped
        assert "models" in dumped

        # Verify values
        assert dumped["imageId"] == "image-123"
        assert dumped["inferenceId"] == "inference-456"
        assert dumped["totalBoxes"] == 1
        assert dumped["labelOccurrence"] == {"species-a": 1}

        # snake_case should not be in output
        assert "image_id" not in dumped
        assert "inference_id" not in dumped
        assert "label_occurrence" not in dumped
        assert "total_boxes" not in dumped

    def test_response_accepts_snake_case_input(self):
        """Backend can construct response with snake_case fields."""
        pixel_box = PixelBoundingBox(topX=10, topY=20, bottomX=100, bottomY=200)

        box = ApiInferenceBox(
            box=pixel_box,
            label="species-a",
            score=0.95,
            topN=[],  # Required
            classId="class-1",  # Required
            object_type_id="obj-type-1",  # Required
            box_id="box-1",
            overlapping=False,  # Required
            overlappingIndices=-1,  # Required
            is_verified=False,
        )

        model = ModelInfo(name="test-model", version="1.0")

        response = ApiInferenceResponse(
            filename="test.png",
            image_id="image-123",
            inference_id="inference-456",
            boxes=[box],
            label_occurrence={"species-a": 1},
            total_boxes=1,
            models=[model],
        )

        # snake_case field access works internally
        assert response.image_id == "image-123"
        assert response.inference_id == "inference-456"
        assert response.label_occurrence == {"species-a": 1}
        assert response.total_boxes == 1


class TestToyWorkflowResponseAliases:
    """Test camelCase serialization for ToyWorkflowResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize to camelCase."""
        response = ToyWorkflowResponse(
            workflow_id="workflow-123",
            message="Workflow submitted",
        )

        dumped = response.model_dump(by_alias=True)
        assert "workflowId" in dumped
        assert "message" in dumped
        # snake_case should not be in output
        assert "workflow_id" not in dumped


class TestWorkflowStatusResponseAliases:
    """Test camelCase serialization for WorkflowStatusResponse."""

    def test_response_serializes_to_camelcase(self):
        """Response should serialize to camelCase."""
        response = WorkflowStatusResponse(
            workflow_id="workflow-123",
            status="SUCCESS",
            result={"output": "test"},
            error=None,
        )

        dumped = response.model_dump(by_alias=True, exclude_none=True)
        assert "workflowId" in dumped
        assert "status" in dumped
        assert "result" in dumped
        # snake_case should not be in output
        assert "workflow_id" not in dumped

    def test_response_with_error(self):
        """Error responses should use camelCase."""
        response = WorkflowStatusResponse(
            workflow_id="workflow-123",
            status="ERROR",
            result=None,
            error="Workflow failed",
        )

        dumped = response.model_dump(by_alias=True, exclude_none=True)
        assert dumped["workflowId"] == "workflow-123"
        assert dumped["status"] == "ERROR"
        assert dumped["error"] == "Workflow failed"


class TestCrossResponseConsistency:
    """Test that all response models follow consistent patterns."""

    def test_all_responses_serialize_to_camelcase(self):
        """All responses should serialize to camelCase with by_alias=True."""
        # BatchUploadInitResponse
        batch_init = BatchUploadInitResponse(session_id=str(uuid4()))
        batch_init_dumped = batch_init.model_dump(by_alias=True)
        assert "sessionId" in batch_init_dumped

        # BatchUploadImageResponse
        batch_image = BatchUploadImageResponse(
            success=True,
            picture_id="pic-1",
            workflow_id="wf-1",
            error=None,
        )
        batch_image_dumped = batch_image.model_dump(by_alias=True, exclude_none=True)
        assert "pictureId" in batch_image_dumped
        assert "workflowId" in batch_image_dumped

        # ImageSubmissionResponse
        image_sub = ImageSubmissionResponse(
            image_id="img-1",
            workflow_id="wf-1",
            status="processing",
            message="Success",
        )
        image_sub_dumped = image_sub.model_dump(by_alias=True)
        assert "imageId" in image_sub_dumped
        assert "workflowId" in image_sub_dumped

        # ToyWorkflowResponse
        toy = ToyWorkflowResponse(workflow_id="wf-1", message="Test")
        toy_dumped = toy.model_dump(by_alias=True)
        assert "workflowId" in toy_dumped
