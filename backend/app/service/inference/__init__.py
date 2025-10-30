"""
Inference Package

This package contains modules for image inference and processing workflows.

Public API:
-----------
From workflows:
    - image_processing_workflow
    - image_inference_workflow
    - image_processing_and_inference_workflow

From queues:
    - image_processing_queue

From submission:
    - submit_inference_request
    - get_inference_status

From workflow_management:
    - get_workflow_status
    - get_processing_status
    - cancel_processing
    - retry_failed_processing
    - calculate_progress_percentage

From state_management:
    - create_processing_state
    - create_inference_request_state

From image_validation:
    - preprocess_image
    - PreprocessedImageData

From test_endpoints (DISABLE IN PROD):
    - submit_direct_pipeline_inference_request_test
    - submit_direct_inference_request_test
"""

from uuid import UUID

# Export workflows
from app.service.inference.workflows import (
    image_processing_workflow,
    image_inference_workflow,
    image_processing_and_inference_workflow,
    # Export DBOS steps for testing
    download_image_from_blob_step,
    get_pipeline_configuration_step,
    execute_inference_step,
    save_inference_results_step,
    create_inference_request_state_step,
)

# Export queue
from app.service.inference.queues import image_processing_queue

# Export submission functions
from app.service.inference.submission import (
    submit_inference_request,
    get_inference_status,
)

# Export workflow management functions
from app.service.inference.workflow_management import (
    get_workflow_status,
    get_workflow_results,
    get_processing_status,
    cancel_processing,
    retry_failed_processing,
    calculate_progress_percentage,
)

# Export state management functions
from app.service.inference.state_management import (
    create_processing_state,
    create_inference_request_state,
    update_processing_state_step,
    update_inference_state_step,
    mark_processing_failed_step,
    mark_inference_failed_step,
)

# Export image validation
from app.service.inference.image_validation import (
    preprocess_image,
    PreprocessedImageData,
)

# Export test endpoints (DISABLE IN PROD)
from app.service.inference.test_endpoints import (
    submit_direct_pipeline_inference_request_test,
    submit_direct_inference_request_test,
)

# ==============================================================================
# InferenceService Facade Class
# ==============================================================================


class InferenceService:
    """
    Service layer for inference-related business logic.

    This class provides a unified API that delegates to specialized modules
    in the inference package. All methods are static to maintain backward
    compatibility with the original implementation.
    """

    # ========================================================================
    # Image Validation and Preprocessing
    # ========================================================================

    @staticmethod
    async def _preprocess_image(
        image_base64: str, user_role_id: UUID
    ) -> PreprocessedImageData:
        """Validate the uploaded image file. Decode from base64 and check type, size, dimensions."""
        return await preprocess_image(image_base64, user_role_id)

    # ========================================================================
    # State Management
    # ========================================================================

    @staticmethod
    async def create_processing_state(
        workflow_id: str,
        picture_id: UUID,
        user_id: UUID,
        org_user_role_id: UUID,
        org_admin_role_id: UUID,
        status,
        created_at,
        progress_percentage: int = 0,
    ):
        """Create a new ImageProcessingState record with ownership tracking."""
        return await create_processing_state(
            workflow_id=workflow_id,
            picture_id=picture_id,
            user_id=user_id,
            org_user_role_id=org_user_role_id,
            org_admin_role_id=org_admin_role_id,
            status=status,
            created_at=created_at,
            progress_percentage=progress_percentage,
        )

    @staticmethod
    async def create_inference_request_state(
        picture_id: UUID,
        pipeline_id: UUID,
        user_id: UUID,
        org_user_role_id: UUID,
        org_admin_role_id: UUID,
        workflow_id: str,
        request_payload: dict,
    ):
        """Create a new InferenceRequestState record for inference workflow tracking."""
        return await create_inference_request_state(
            picture_id=picture_id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            org_user_role_id=org_user_role_id,
            org_admin_role_id=org_admin_role_id,
            workflow_id=workflow_id,
            request_payload=request_payload,
        )

    # ========================================================================
    # Workflow Management
    # ========================================================================

    @staticmethod
    async def get_workflow_status(workflow_id: str, user_id: UUID):
        """Get comprehensive workflow status with authorization check."""
        return await get_workflow_status(workflow_id, user_id)

    @staticmethod
    async def get_workflow_results(workflow_id: str, user_id: UUID):
        """Get formatted inference results for a completed workflow."""
        return await get_workflow_results(workflow_id, user_id)

    @staticmethod
    async def get_processing_status(session, image_id: UUID):
        """Get current processing status of an image."""
        return await get_processing_status(session, image_id)

    @staticmethod
    async def cancel_processing(session, image_id: UUID, user_id: UUID):
        """Cancel an in-progress image processing workflow."""
        return await cancel_processing(session, image_id, user_id)

    @staticmethod
    async def retry_failed_processing(session, image_id: UUID, user_id: UUID):
        """Retry a failed image processing workflow."""
        return await retry_failed_processing(session, image_id, user_id)

    @staticmethod
    def calculate_progress_percentage(status):
        """Calculate progress percentage from processing status (MVP scope only)."""
        return calculate_progress_percentage(status)

    # ========================================================================
    # Submission and Status
    # ========================================================================

    @staticmethod
    async def submit_inference_request(request, user_id: UUID):
        """Submit an image for async processing (MVP: upload → scan → sanitize)."""
        return await submit_inference_request(request, user_id)

    @staticmethod
    async def get_inference_status(image_id: UUID, user_id: UUID):
        """Get processing status for an image."""
        return await get_inference_status(image_id, user_id)

    # ========================================================================
    # Test Endpoints (DISABLE IN PROD)
    # ========================================================================

    @staticmethod
    async def submit_direct_pipeline_inference_request_test(request, user_id: UUID):
        """DISABLE IN PROD - Process direct image inference submission request using cached pipeline steps."""
        return await submit_direct_pipeline_inference_request_test(request, user_id)

    @staticmethod
    async def submit_direct_inference_request_test(request, user_id: UUID):
        """DISABLE IN PROD - Process direct image inference submission request (bypass storage and workflow)."""
        return await submit_direct_inference_request_test(request, user_id)


__all__ = [
    # InferenceService Facade
    "InferenceService",
    # Workflows
    "image_processing_workflow",
    "image_inference_workflow",
    "image_processing_and_inference_workflow",
    # DBOS Steps (for testing)
    "download_image_from_blob_step",
    "get_pipeline_configuration_step",
    "execute_inference_step",
    "save_inference_results_step",
    "create_inference_request_state_step",
    # Queue
    "image_processing_queue",
    # Submission
    "submit_inference_request",
    "get_inference_status",
    # Workflow management
    "get_workflow_status",
    "get_workflow_results",
    "get_processing_status",
    "cancel_processing",
    "retry_failed_processing",
    "calculate_progress_percentage",
    # State management
    "create_processing_state",
    "create_inference_request_state",
    "update_processing_state_step",
    "update_inference_state_step",
    "mark_processing_failed_step",
    "mark_inference_failed_step",
    # Image validation
    "preprocess_image",
    "PreprocessedImageData",
    # Test endpoints (DISABLE IN PROD)
    "submit_direct_pipeline_inference_request_test",
    "submit_direct_inference_request_test",
]
