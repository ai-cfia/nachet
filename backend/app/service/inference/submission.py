"""
Inference Submission Module

This module handles image submission for processing and inference,
including validation, deduplication, and workflow orchestration.
"""

from uuid import UUID
from datetime import datetime, timezone
from beartype.typing import Dict, Any
from uuid6 import uuid7
from dbos import DBOS

from app.model.inference import InferenceRequest, ImageSubmissionResponse
from app.service import DirectoryService, PipelineService, ImageService
from app.service.rbac import RbacService
from app.service.constants import ProcessingStatus
from app.exceptions import (
    InvalidImageError,
    FolderNotFoundError,
    PipelineNotFoundError,
    ImageProcessingError,
)
from app.db.utils import sessionmanager
from app.service.inference.image_validation import preprocess_image
from app.service.inference.state_management import create_processing_state
from app.service.inference.queues import image_processing_queue
from app.service.inference.workflows import image_processing_and_inference_workflow
from app.service.inference.workflow_management import get_processing_status


async def submit_inference_request(
    request: InferenceRequest,
    user_id: UUID,
) -> ImageSubmissionResponse:
    """
    Submit an image for async processing (MVP: upload → scan → sanitize).

    This is the async version of the legacy /inf endpoint.
    Returns immediately with UUID while processing continues in background.

    Request body matches legacy API format:
    {
        "pipeline_id": "pipeline uuid",
        "folder_id": "folder uuid",
        "imageDims": [1920, 1080],
        "image": "data:image/png;base64,...",
        "area_ratio": 0.5,
        "color_format": "hex"
    }

    Response format:
    {
        "request_id": "uuid",
        "workflow_id": "workflow-uuid",
        "status": "pending",
        "message": "Image submitted for processing"
    }

    Frontend should poll GET /inf/{image_id}/status for progress.

    Coordinates all the steps needed to submit an image for processing:
    1. Lookup folder by ID
    2. Get user's organization
    3. Validate folder exists in DB
    4. Decode and validate image
    5. Create Picture and ImageProcessingState records
    6. Enqueue DBOS workflow for background processing

    Manages database session and logging internally.

    Args:
        request: InferenceRequest with image data and metadata
        user_id: UUID of requesting user

    Returns:
        ImageSubmissionResponse with image_id, workflow_id, status

    Raises:
        ValueError: If folder not found or validation fails
        InvalidImageError: If image validation fails
        FolderNotFoundError: If folder doesn't exist in DB
        ImageProcessingError: If submission fails
    """
    from app.service.logs import LogService

    logger = LogService.get_logger()

    logger.debug(
        "Processing inference request",
        user_id=str(user_id),
        folder_name=request.folder_name,
    )

    try:
        # Get user's organization and roles in single DB call
        user_org_roles = await RbacService.get_user_org_roles(user_id)

        # Parse folder_id from string to UUID
        folder_id = UUID(request.folder_id)

        # Verify folder exists and belongs to user's organization
        _folder_prefix = await DirectoryService.check_folder_exists(
            folder_id=folder_id,
            user_role_id=user_org_roles.org_user_role_id,
        )

        # Verify the pipeline exists
        pipeline_id = await PipelineService.pipeline_exists(
            request.pipeline_id, user_id
        )

        # Validate and preprocess the image
        info = await preprocess_image(
            image_base64=request.image, user_role_id=user_org_roles.org_user_role_id
        )

        image_id = uuid7() if not info.duplicate_uuid else info.duplicate_uuid

        # Only create Picture if it's not a duplicate
        if not info.duplicate_uuid:
            # Construct blob URL using org_prefix and image_id
            blob_url_original = f"{user_org_roles.org_prefix}/{image_id}.png"

            _picture_data = await ImageService.create(
                requester_id=user_id,
                id=image_id,
                active=True,
                folder_id=folder_id,
                org_user_role_id=user_org_roles.org_user_role_id,
                org_admin_role_id=user_org_roles.org_admin_role_id,
                name=image_id,  # from the parsed image info
                width=info.width,
                height=info.height,
                format=info.mime_type,  # Changed from info.format to info.mime_type
                size_on_disk_original=info.size_bytes,
                sha256=info.sha256_hash,
                blob_url_original=blob_url_original,
            )
        else:
            logger.info(
                f"Duplicate image detected: {image_id}",
                user_id=str(user_id),
                sha256=info.sha256_hash,
            )

        # Start workflow in background using DBOS queue
        # For duplicates, skip preprocessing but still allow inference
        # Queue handles rate limiting and concurrency
        workflow_handle = await image_processing_queue.enqueue_async(
            image_processing_and_inference_workflow,
            image_id=image_id,
            file_bytes=info.image_bytes
            if not info.duplicate_uuid
            else None,  # No file bytes for duplicates
            user_id=user_id,
            org_prefix=user_org_roles.org_prefix,
            pipeline_id=pipeline_id,
            imageDims=[info.width, info.height],
            org_user_role_id=user_org_roles.org_user_role_id,
            org_admin_role_id=user_org_roles.org_admin_role_id,
            skip_preprocessing=bool(
                info.duplicate_uuid
            ),  # Skip preprocessing for duplicates
        )
        workflow_id = workflow_handle.get_workflow_id()

        # Only create processing state for new images, not duplicates
        if not info.duplicate_uuid:
            _processing_state = await create_processing_state(
                picture_id=image_id,
                user_id=user_id,
                org_user_role_id=user_org_roles.org_user_role_id,
                org_admin_role_id=user_org_roles.org_admin_role_id,
                status=ProcessingStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                progress_percentage=5,
                workflow_id=workflow_id,
            )

            DBOS.logger.info(
                f"Image {image_id} submitted for processing. Workflow: {workflow_id}"
            )

            logger.info(
                f"Image submitted for processing: {image_id}",
                user_id=str(user_id),
                workflow_id=workflow_id,
            )
        else:
            logger.info(
                f"Duplicate image submitted for inference (skipping preprocessing): {image_id}",
                user_id=str(user_id),
                workflow_id=workflow_id,
            )

        return ImageSubmissionResponse(
            image_id=str(image_id),
            workflow_id=workflow_id,
            status=ProcessingStatus.PENDING,
            message="Image submitted for processing"
            if not info.duplicate_uuid
            else "Duplicate image submitted (preprocessing skipped)",
        )

    except (
        ValueError,
        InvalidImageError,
        FolderNotFoundError,
        PipelineNotFoundError,
    ):
        raise
    except Exception as e:
        logger.error(
            f"Failed to submit inference: {str(e)}",
            user_id=str(user_id),
            error_type=type(e).__name__,
        )
        raise ImageProcessingError(f"Failed to submit inference: {str(e)}") from e


async def get_inference_status(
    image_id: UUID,
    user_id: UUID,
) -> Dict[str, Any]:
    """
    Get processing status for an image.

    Manages database session and logging internally.
    Could add additional business logic here if needed (caching, auth checks, etc.)

    Args:
        image_id: UUID of the image
        user_id: UUID of requesting user (for logging/auth)

    Returns:
        Dict with status information

    Raises:
        ImageProcessingError: If status retrieval fails
    """
    from app.service.logs import LogService

    logger = LogService.get_logger()

    logger.debug(
        f"Getting status for image {image_id}",
        user_id=str(user_id),
        image_id=str(image_id),
    )

    try:
        async with sessionmanager.get_session() as session:
            return await get_processing_status(
                session=session,
                image_id=image_id,
            )
    except Exception as e:
        logger.error(
            f"Failed to get status for image {image_id}: {str(e)}",
            user_id=str(user_id),
            image_id=str(image_id),
            error_type=type(e).__name__,
        )
        raise ImageProcessingError(f"Failed to get inference status: {str(e)}") from e
