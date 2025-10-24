"""
Inference Service

Business logic layer for image inference and processing API endpoints.
Coordinates between DirectoryService, blob operations, DBOS workflows, and other services.
Consolidates image processing pipeline, queue, and inference operations.
"""

import base64
import hashlib
import io
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dbos import DBOS, Queue
from app.model.inference import (
    InferenceRequest,
    ImageSubmissionResponse,
    ApiInferenceResponse,
)
from app.service import (
    DirectoryService,
    SeedService,
    PipelineService,
)
from app.service.organization import OrganizationService
from app.service.constants import get_cfia_admin_role_id, MAX_BASE64_LENGTH
from app.exceptions import (
    ImageProcessingError,
    InvalidImageError,
    FolderNotFoundError,
)
from app.db.utils import sessionmanager
from app.service.inference_api import (
    InferenceDispatchService,
    process_api_ready_classification_result,
)
from app.datastore.image import ImageDataService
from app.db.model import Picture, Folder, ImageProcessingState
from app.service.constants import ProcessingStatus
from app.service.blob_operations import (
    upload_to_azure_blob,
    wait_for_defender_scan,
)
from app.service.sanitization import (
    trigger_sanitization_function,
    wait_for_sanitization_callback,
)


# ============================================================================
# DBOS Queue Configuration
# ============================================================================

# Image processing queue with concurrency and rate limits
image_processing_queue = Queue(
    name="image-processing",
    concurrency=10,  # Max 10 concurrent workflows globally
    limiter={
        "limit": 50,  # Max 50 workflow starts
        "period": 60,  # Per 60 seconds
    },
    worker_concurrency=5,  # Max 5 concurrent per worker process
    partition_queue=True,  # Enable partitioning by org_id
)


# ============================================================================
# DBOS Workflow for Image Processing Pipeline
# ============================================================================


@DBOS.workflow(max_recovery_attempts=5)
async def process_image_pipeline(
    image_id: UUID,
    file_bytes: bytes,
    filename: str,
    genus: str,
    species: str,
    org_name: str,
    user_id: UUID,
) -> Dict[str, Any]:
    """
    Main image processing workflow (MVP).

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Args:
        image_id: UUID v7 of the image
        file_bytes: Raw image bytes
        filename: Original filename
        genus: Genus name (normalized)
        species: Species name (normalized)
        org_name: Organization name (normalized, max 10 chars)
        user_id: Submitting user UUID

    Returns:
        Dict containing processing results and blob URLs

    Raises:
        Various exceptions for different failure modes (defender, sanitization)
    """
    try:
        DBOS.logger.info(f"Starting image processing pipeline for {image_id}")

        # Publish initial progress event
        await DBOS.set_event_async("processing_status", "started")
        await DBOS.set_event_async(
            "timestamps", {"started": datetime.utcnow().isoformat()}
        )

        # Step 1: Upload to Azure Blob Storage (nachet-original)
        DBOS.logger.info(f"[{image_id}] Step 1: Uploading to nachet-original")
        blob_url_original = await upload_to_azure_blob(
            image_id=image_id,
            file_bytes=file_bytes,
            filename=filename,
            genus=genus,
            species=species,
            org_name=org_name,
        )
        await DBOS.set_event_async("upload_complete", True)
        await DBOS.set_event_async("processing_status", "uploaded")
        await DBOS.set_event_async("blob_url_original", blob_url_original)

        # Step 2: Wait for Azure Defender scan
        DBOS.logger.info(f"[{image_id}] Step 2: Waiting for Defender scan")
        await DBOS.set_event_async("processing_status", "defender_scanning")
        defender_result = await wait_for_defender_scan(
            image_id=image_id,
            blob_url=blob_url_original,
            timeout_sec=300,
        )
        await DBOS.set_event_async("defender_scan_complete", True)
        await DBOS.set_event_async("processing_status", "defender_scanned")
        await DBOS.set_event_async("defender_result", defender_result)

        # Step 3: Trigger sanitization Azure Function
        DBOS.logger.info(f"[{image_id}] Step 3: Triggering sanitization function")
        await DBOS.set_event_async("processing_status", "sanitizing")
        await trigger_sanitization_function(
            image_id=image_id,
            genus=genus,
            species=species,
            blob_url_original=blob_url_original,
        )

        # Step 4: Wait for sanitization callback
        DBOS.logger.info(f"[{image_id}] Step 4: Waiting for sanitization callback")
        sanitized_blob_url = await wait_for_sanitization_callback(
            image_id=image_id,
            timeout_sec=600,
        )
        await DBOS.set_event_async("sanitization_complete", True)
        await DBOS.set_event_async("processing_status", "sanitized")
        await DBOS.set_event_async("blob_url_sanitized", sanitized_blob_url)

        # Publish completion
        await DBOS.set_event_async("processing_status", "completed")
        all_events = await DBOS.get_all_events_async(DBOS.workflow_id)
        await DBOS.set_event_async(
            "timestamps",
            {
                **all_events.get("timestamps", {}),
                "completed": datetime.utcnow().isoformat(),
            },
        )

        DBOS.logger.info(f"[{image_id}] Pipeline completed successfully")

        return {
            "image_id": str(image_id),
            "status": "completed",
            "blob_url_original": blob_url_original,
            "blob_url_sanitized": sanitized_blob_url,
        }

    except Exception as e:
        DBOS.logger.error(f"[{image_id}] Pipeline failed: {str(e)}")

        # Publish error event
        await DBOS.set_event_async("processing_status", "failed")
        await DBOS.set_event_async(
            "error_details",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        raise


# ============================================================================
# InferenceService Class
# ============================================================================


class InferenceService:
    """Service layer for inference-related business logic."""

    @staticmethod
    async def submit_direct_pipeline_inference_request_test(
        request: InferenceRequest,
        user_id: UUID,
    ) -> ApiInferenceResponse:
        """
        DISABLE IN PROD
        Process direct image inference submission request using cached pipeline steps.
        Coordinates all the steps needed to submit an image for direct inference:
        1. Validate request
        2. Lookup pipeline steps from cache
        3. Execute pipeline steps sequentially using InferenceDispatchService

        Logs yes, db no.

        Args:
            request: InferenceRequest with image data and metadata (including pipeline_id)
            user_id: UUID of requesting user
        Returns:
            ApiInferenceResponse with classification boxes and predictions
        Raises:
            ImageProcessingError: If submission fails
            ValueError: If pipeline not found in cache
        """
        from app.service.logs import LogService

        logger = LogService.get_logger()

        logger.debug(
            "Processing direct pipeline inference request",
            pipeline_id=request.pipeline_id,
            folder_name=request.folder_name,
        )

        try:
            # Get pipeline steps from cache
            pipeline_steps = await PipelineService.get_pipeline_steps(
                request.pipeline_id
            )

            if not pipeline_steps:
                error_msg = f"Pipeline '{request.pipeline_id}' not found in cache"
                logger.error(
                    error_msg,
                    pipeline_id=request.pipeline_id,
                    available_pipelines=PipelineService.get_cached_pipeline_names(),
                )
                raise ValueError(error_msg)

            logger.info(
                f"Found pipeline with {len(pipeline_steps)} steps",
                pipeline_id=request.pipeline_id,
                steps=[s["model_name"] for s in pipeline_steps],
            )

            # Extract base64 data from data URL (strip "data:image/png;base64," prefix)
            image_base64 = request.image
            if image_base64.startswith("data:"):
                # Strip data URL prefix to get just the base64 string
                image_base64 = image_base64.split(",", 1)[1]

            # Execute pipeline steps sequentially
            previous_result = image_base64

            for step_idx, step in enumerate(pipeline_steps, start=1):
                logger.debug(
                    f"Executing pipeline step {step_idx}/{len(pipeline_steps)}",
                    step=step["step"],
                    model_name=step["model_name"],
                    request_function=step["request_function"],
                )

                # Dispatch to inference service
                step_result = await InferenceDispatchService.dispatch(
                    model=step,
                    previous_result=previous_result,
                )

                # Update previous_result for next step
                previous_result = step_result

                logger.debug(
                    f"Completed pipeline step {step_idx}/{len(pipeline_steps)}",
                    model_name=step["model_name"],
                )

            # The last result should be the classification result
            classification_result = previous_result

            logger.info(
                "Direct pipeline inference request processed successfully",
                pipeline_id=request.pipeline_id,
                steps_executed=len(pipeline_steps),
            )

            # Process the classification result to add overlapping, colors, and label occurrence
            # Returns API-ready result with normalized coordinates
            api_result = await process_api_ready_classification_result(
                result=classification_result.result,
                imageDims=request.imageDims,
                area_ratio=request.area_ratio,
                color_format=request.color_format,
            )

            # Build model info list from pipeline steps
            models = [
                {"name": step["model_name"], "version": step.get("version", "1")}
                for step in pipeline_steps
            ]

            # Return validated API response using Pydantic model
            return ApiInferenceResponse(
                filename=api_result.filename,
                imageId="direct-inference",  # No DB storage for direct inference
                inference_id="direct-inference",  # No DB storage for direct inference
                boxes=api_result.boxes,
                labelOccurrence=api_result.labelOccurrence,
                totalBoxes=api_result.totalBoxes,
                models=models,
            )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to submit direct pipeline inference: {str(e)}",
                pipeline_id=request.pipeline_id,
                error_type=type(e).__name__,
            )
            raise ImageProcessingError(
                f"Failed to submit direct pipeline inference: {str(e)}"
            ) from e

    @staticmethod
    async def submit_direct_inference_request_test(
        request: InferenceRequest,
        user_id: UUID,
    ) -> ApiInferenceResponse:
        """
        DISABLE IN PROD
        Process direct image inference submission request (bypass storage and workflow).

        Coordinates all the steps needed to submit an image for direct inference:
        1. Validate request
        2. Submit to ImageProcessingService for direct inference

        Logs yes, db no.

        Args:
            request: InferenceRequest with image data and metadata
            user_id: UUID of requesting user

        Returns:
            ApiInferenceResponse with classification boxes and predictions

        Raises:
            ImageProcessingError: If submission fails
        """
        from app.service.logs import LogService

        logger = LogService.get_logger()

        logger.debug(
            "Processing direct inference request",
            folder_name=request.folder_name,
        )

        try:
            # Extract base64 data from data URL (strip "data:image/png;base64," prefix)
            image_base64 = request.image
            if image_base64.startswith("data:"):
                # Strip data URL prefix to get just the base64 string
                image_base64 = image_base64.split(",", 1)[1]

            # Directly submit image for inference without DB/storage
            detection_result = await InferenceDispatchService.dispatch(
                model={
                    "content_type": "application/json",
                    "api_key": "12345",
                    "deployment_platform": "local",
                    "request_function": "rcnn_seed_detector",
                    "name": "rcnn_seed_detector",
                    "endpoint": "http://nachet-detector:5001/score",
                },
                previous_result=image_base64,
            )

            classification_result = await InferenceDispatchService.dispatch(
                model={
                    "content_type": "application/json",
                    "api_key": "12345",
                    "deployment_platform": "local",
                    "request_function": "swin_classifier",
                    "name": "swin_classifier_model",
                    "endpoint": "http://nachet-15spp-classifier:5001/score",
                },
                previous_result=detection_result,
            )

            logger.info(
                "Direct inference request processed successfully",
            )

            # Process the classification result to add overlapping, colors, and label occurrence
            # Returns API-ready result with normalized coordinates
            api_result = await process_api_ready_classification_result(
                result=classification_result.result,
                imageDims=request.imageDims,
                area_ratio=request.area_ratio,
                color_format=request.color_format,
            )

            # Return validated API response using Pydantic model
            return ApiInferenceResponse(
                filename=api_result.filename,
                imageId="direct-inference",  # No DB storage for direct inference
                inference_id="direct-inference",  # No DB storage for direct inference
                boxes=api_result.boxes,
                labelOccurrence=api_result.labelOccurrence,
                totalBoxes=api_result.totalBoxes,
                models=[
                    {"name": "rcnn_seed_detector", "version": "1"},
                    {"name": "swin_classifier_model", "version": "1"},
                ],
            )

        except Exception as e:
            logger.error(
                f"Failed to submit direct inference: {str(e)}",
                error_type=type(e).__name__,
            )
            raise ImageProcessingError(
                f"Failed to submit direct inference: {str(e)}"
            ) from e

    @staticmethod
    def _url_to_binary(image_base64: str) -> bytes:
        """
        Validate the uploaded image file. Decode from base64 and check type, size, dimensions.
        Issue #229 #231

        Args:
            image_base64: Base64-encoded image data

        Returns:
            binary: Decoded binary image data

        Raises:
            ValueError: If validation fails
        """
        import base64
        import magic

        # validate size (max 10MB)
        if len(image_base64) > MAX_BASE64_LENGTH:
            raise ValueError("Image size exceeds maximum limit of 10MB")

        if len(image_base64.strip()) < 2049:
            raise ValueError("Image size is too small or empty")

        if image_base64.startswith("data:"):
            # Strip data URL prefix to get just the base64 string
            image_base64 = image_base64.split(",", 1)[1]
        # Decode base64 to binary
        image_bytes = base64.b64decode(image_base64)

        # Validate image type using magic bytes (more reliable than mimetypes on base64)
        mime_type = magic.from_buffer(image_bytes, mime=True)
        if not mime_type.startswith("image/png"):
            raise ValueError("Uploaded file is not a valid PNG image")

        # validate dimensions
        header = image_bytes[:24]
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        if width < 384 or height < 384:
            raise ValueError(
                "Image dimensions are too small, minimum is 384x384 pixels"
            )
        if width > 1920 and height > 1080:
            raise ValueError(
                "Image dimensions are too large, maximum is 1920x1080 pixels"
            )

        return image_bytes

    @staticmethod
    async def _get_hash(image_bytes: bytes) -> (str, UUID | None):
        """
        Returns the UUID of an existing image if a duplicate is found based on SHA256 hash.
        Issue #234

        Args:
            image_bytes: Binary image data

        Returns:
            str: SHA256 hash of the image
            UUID | None: UUID of the duplicate image if found, None otherwise

        Raises:
            ImageProcessingError: If duplicate check fails
        """
        import hashlib

        try:
            # Compute hash of the image
            image_hash = hashlib.sha256(image_bytes).hexdigest()

            # Check if image with this hash already exists in database
            async with sessionmanager.get_session() as session:
                image_service = ImageDataService(session)
                duplicate_uuid = await image_service.check_sha256_exists(image_hash)
                return image_hash, duplicate_uuid

        except Exception as e:
            raise ImageProcessingError(f"Failed to compute image hash: {str(e)}") from e

    @staticmethod
    async def submit_inference_request(
        request: InferenceRequest,
        user_id: UUID,
    ) -> ImageSubmissionResponse:
        """

        Submit an image for async processing (MVP: upload → scan → sanitize).

        This is the new async version of the legacy /inf endpoint.
        Returns immediately with UUID while processing continues in background.

        Request body matches legacy API format:
        {
            "pipeline_id": "pipeline-name",
            "folder_name": "folder-identifier",
            "imageDims": [1920, 1080],
            "image": "data:image/png;base64,...",
            "area_ratio": 0.5,
            "color_format": "hex"
        }

        Response (new format):
        {
            "request_id": "uuid",
            "workflow_id": "workflow-uuid",
            "status": "pending",
            "message": "Image submitted for processing"
        }

        Frontend should poll GET /inf/{image_id}/status for progress.

        Process image inference submission request (MVP: upload → scan → sanitize).

        Coordinates all the steps needed to submit an image for processing:
        1. Lookup/create folder
        2. Get user's organization
        3. Normalize names for blob storage
        4. Submit to ImageProcessingService

        Manages database session and logging internally.

        Args:
            request: InferenceRequest with image data and metadata
            user_id: UUID of requesting user

        Returns:
            ImageSubmissionResponse with image_id, workflow_id, status

        Raises:
            ValueError: If folder not found or validation fails
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
            async with sessionmanager.get_session() as session:
                # Get user's organization for org_name
                # TODO: Implement proper organization lookup from user
                # For now, use a default or extract from user metadata
                org_name = OrganizationService.normalize_org_name("default-org")

                # Get or create folder by folder_name
                directories = await DirectoryService.get_user_directories(user_id)
                folder_id = None

                # Find folder by name
                for directory in directories.get("directories", []):
                    if directory.get("name") == request.folder_name:
                        folder_id = UUID(directory.get("id"))
                        break

                if not folder_id:
                    # Folder not found - raise error
                    # TODO: Optionally create folder automatically
                    logger.error(
                        f"Folder not found: {request.folder_name}",
                        user_id=str(user_id),
                    )
                    raise ValueError(
                        f"Folder '{request.folder_name}' not found for user"
                    )

                # Extract filename from image data (use folder_name as fallback)
                filename = f"{request.folder_name}.png"

                # Get genus/species from folder metadata or use defaults
                # TODO: Extract from folder metadata, seed database, or image metadata
                genus = SeedService.normalize_taxonomic_name("unknown")
                species = SeedService.normalize_taxonomic_name("unknown")

                # Get user role IDs
                # TODO: Get actual role IDs from user/organization
                org_admin_role_id = get_cfia_admin_role_id()
                org_user_role_id = (
                    get_cfia_admin_role_id()
                )  # TODO: Get actual user role

                # Convert imageDims from list [width, height] to dict format
                image_metadata = {
                    "width": request.imageDims[0],
                    "height": request.imageDims[1],
                }

                # Submit image for processing
                result = await InferenceService.submit_image_for_processing(
                    session=session,
                    image_data=request.image,
                    filename=filename,
                    genus=genus,
                    species=species,
                    org_name=org_name,
                    user_id=user_id,
                    folder_id=folder_id,
                    org_user_role_id=org_user_role_id,
                    org_admin_role_id=org_admin_role_id,
                    image_metadata=image_metadata,
                )

                logger.info(
                    f"Image submitted for processing: {result['image_id']}",
                    user_id=str(user_id),
                    workflow_id=result["workflow_id"],
                )

                return ImageSubmissionResponse(**result)

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to submit inference: {str(e)}",
                user_id=str(user_id),
                error_type=type(e).__name__,
            )
            raise ImageProcessingError(f"Failed to submit inference: {str(e)}") from e

    @staticmethod
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
                return await InferenceService.get_processing_status(
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
            raise ImageProcessingError(
                f"Failed to get inference status: {str(e)}"
            ) from e

    # ========================================================================
    # Image Processing Service Methods (formerly ImageProcessingService)
    # ========================================================================

    @staticmethod
    async def submit_image_for_processing(
        session: AsyncSession,
        image_data: str,  # Base64 encoded string from frontend
        filename: str,
        genus: str,
        species: str,
        org_name: str,
        user_id: UUID,
        folder_id: UUID,
        org_user_role_id: UUID,
        org_admin_role_id: UUID,
        image_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit an image for async processing.

        Returns immediately with UUID v7 while processing continues in background.
        Accepts base64 encoded images from frontend and converts to binary.

        Args:
            session: Database session
            image_data: Base64 encoded image string from frontend
            filename: Original filename
            genus: Genus name (normalized: a-z, dashes only)
            species: Species name (normalized: a-z, dashes only)
            org_name: Organization name (normalized: a-z, 0-9, dashes, max 10 chars)
            user_id: Submitting user UUID
            folder_id: Target folder UUID
            org_user_role_id: Organization user role UUID
            org_admin_role_id: Organization admin role UUID
            image_metadata: Optional metadata (dimensions, format, etc.)

        Returns:
            Dict with image_id, status, and workflow_id

        Raises:
            InvalidImageError: If image validation fails
            FolderNotFoundError: If folder doesn't exist
            ImageProcessingError: If submission fails
        """
        try:
            # Generate UUIDv7 immediately
            from uuid_extensions import uuid7

            image_id = uuid7()

            # Validate folder exists
            folder = await session.get(Folder, folder_id)
            if not folder or not folder.active:
                raise FolderNotFoundError(f"Folder {folder_id} not found")

            # Decode base64 image to bytes
            try:
                # Handle data URL format: "data:image/png;base64,..."
                if image_data.startswith("data:"):
                    # Strip data URL prefix
                    image_data = image_data.split(",", 1)[1]

                file_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise InvalidImageError(f"Invalid base64 image data: {str(e)}") from e

            # Validate image (basic checks before workflow)
            InferenceService._validate_image_basic(file_bytes, filename)

            # Extract or validate metadata
            if not image_metadata:
                image_metadata = await InferenceService._extract_image_metadata(
                    file_bytes, filename
                )

            # Create minimal Picture record
            picture = Picture(
                id=image_id,
                active=True,
                folder_id=folder_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                name=filename,
                width=image_metadata.get("width", 0),
                height=image_metadata.get("height", 0),
                format=image_metadata.get("format", "unknown"),
                size_on_disk_original=len(file_bytes),
                sha256=image_metadata.get("sha256", ""),
                date_created=datetime.utcnow(),
            )

            session.add(picture)

            # Create separate processing state record
            processing_state = ImageProcessingState(
                picture_id=image_id,
                status=ProcessingStatus.PENDING,
                created_at=datetime.utcnow(),
                progress_percentage=5,
            )

            session.add(processing_state)
            await session.commit()

            # Start workflow in background using DBOS queue
            # Queue handles rate limiting and concurrency
            workflow_handle = await image_processing_queue.enqueue_async(
                process_image_pipeline,
                image_id=image_id,
                file_bytes=file_bytes,
                filename=filename,
                genus=genus,
                species=species,
                org_name=org_name,
                user_id=user_id,
            )
            workflow_id = workflow_handle.get_workflow_id()

            # Update processing state with workflow ID
            processing_state.workflow_id = workflow_id
            await session.commit()

            DBOS.logger.info(
                f"Image {image_id} submitted for processing. Workflow: {workflow_id}"
            )

            return {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": ProcessingStatus.PENDING,
                "message": "Image submitted for processing",
            }

        except (InvalidImageError, FolderNotFoundError):
            raise
        except Exception as e:
            raise ImageProcessingError(f"Failed to submit image: {str(e)}") from e

    @staticmethod
    async def get_processing_status(
        session: AsyncSession,
        image_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get current processing status of an image.

        Retrieves workflow status from DBOS and combines with database state
        from the ImageProcessingState table.

        Args:
            session: Database session
            image_id: Image UUID

        Returns:
            Dict with status, progress, events, and results if complete

        Raises:
            ImageProcessingError: If status retrieval fails
        """
        try:
            # Get processing state from database
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            workflow_id = processing_state.workflow_id

            # Retrieve workflow handle from DBOS if workflow exists
            if workflow_id:
                try:
                    workflow_handle = await DBOS.retrieve_workflow_async(workflow_id)
                    workflow_status = await workflow_handle.get_status()
                    # Get all events published by workflow
                    _events = await DBOS.get_all_events_async(workflow_id)

                    # Add workflow status to response if available
                    if workflow_status and workflow_status.status == "SUCCESS":
                        # Could add workflow results here if needed
                        pass
                except Exception:
                    # Workflow may not exist yet or already completed
                    pass

            response = {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": processing_state.status,
                "progress_percentage": processing_state.progress_percentage,
                "stages": {
                    "upload": processing_state.uploaded_at is not None,
                    "defender_scan": processing_state.defender_scan_completed_at
                    is not None,
                    "sanitization": processing_state.sanitization_completed_at
                    is not None,
                },
                "timestamps": {
                    "created": processing_state.created_at.isoformat()
                    if processing_state.created_at
                    else None,
                    "uploaded": processing_state.uploaded_at.isoformat()
                    if processing_state.uploaded_at
                    else None,
                    "defender_scan_started": processing_state.defender_scan_started_at.isoformat()
                    if processing_state.defender_scan_started_at
                    else None,
                    "defender_scan_completed": processing_state.defender_scan_completed_at.isoformat()
                    if processing_state.defender_scan_completed_at
                    else None,
                    "sanitization_started": processing_state.sanitization_started_at.isoformat()
                    if processing_state.sanitization_started_at
                    else None,
                    "sanitization_completed": processing_state.sanitization_completed_at.isoformat()
                    if processing_state.sanitization_completed_at
                    else None,
                    "completed": processing_state.completed_at.isoformat()
                    if processing_state.completed_at
                    else None,
                    "failed": processing_state.failed_at.isoformat()
                    if processing_state.failed_at
                    else None,
                },
                "blob_urls": {
                    "original": processing_state.blob_url_original,
                    "sanitized": processing_state.blob_url_sanitized,
                },
                "retry_count": processing_state.retry_count,
            }

            # Add malware detection info if available
            if processing_state.defender_scan_result:
                response["defender_scan"] = {
                    "malware_detected": processing_state.malware_detected,
                    "scan_result": processing_state.defender_scan_result,
                }

            # Add error details if failed
            if processing_state.status == ProcessingStatus.FAILED:
                response["error_message"] = processing_state.error_message
                response["error_details"] = processing_state.error_details

            return response

        except Exception as e:
            raise ImageProcessingError(f"Failed to get status: {str(e)}") from e

    @staticmethod
    async def cancel_processing(
        session: AsyncSession,
        image_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Cancel an in-progress image processing workflow.

        Args:
            session: Database session
            image_id: Image UUID
            user_id: Requesting user UUID (for authorization)

        Returns:
            Dict with cancellation status

        Raises:
            ImageProcessingError: If cancellation fails
        """
        try:
            # Get processing state
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            workflow_id = processing_state.workflow_id

            # Cancel the workflow in DBOS
            if workflow_id:
                DBOS.cancel_workflow(workflow_id)

            # Update processing state
            processing_state.status = ProcessingStatus.CANCELLED

            await session.commit()

            DBOS.logger.info(
                f"Image processing workflow {workflow_id} cancelled by user {user_id}"
            )

            return {
                "image_id": str(image_id),
                "status": ProcessingStatus.CANCELLED,
                "message": "Processing cancelled successfully",
            }

        except Exception as e:
            raise ImageProcessingError(f"Failed to cancel processing: {str(e)}") from e

    @staticmethod
    async def retry_failed_processing(
        session: AsyncSession,
        image_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Retry a failed image processing workflow.

        Args:
            session: Database session
            image_id: Image UUID
            user_id: Requesting user UUID (for authorization)

        Returns:
            Dict with retry status

        Raises:
            ImageProcessingError: If retry fails
        """
        try:
            # Get processing state
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            if processing_state.status != ProcessingStatus.FAILED:
                raise ImageProcessingError(
                    f"Cannot retry processing in status {processing_state.status}"
                )

            workflow_id = processing_state.workflow_id

            # Resume the workflow from last completed step
            DBOS.resume_workflow(workflow_id)

            # Update processing state
            processing_state.retry_count += 1
            processing_state.last_retry_at = datetime.utcnow()
            processing_state.error_message = None
            processing_state.error_details = None

            await session.commit()

            DBOS.logger.info(
                f"Image processing workflow {workflow_id} resumed by user {user_id}"
            )

            return {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": "retrying",
                "message": "Processing resumed successfully",
            }

        except Exception as e:
            raise ImageProcessingError(f"Failed to retry processing: {str(e)}") from e

    @staticmethod
    def _validate_image_basic(file_bytes: bytes, filename: str) -> None:
        """Perform basic image validation before workflow submission."""
        # Size validation
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_bytes) > max_size:
            raise InvalidImageError(f"Image size exceeds {max_size} bytes")

        if len(file_bytes) < 100:
            raise InvalidImageError("Image file too small")

        # Format validation (basic magic number check)
        valid_formats = {
            b"\xff\xd8\xff": "jpeg",
            b"\x89PNG\r\n\x1a\n": "png",
            b"GIF87a": "gif",
            b"GIF89a": "gif",
        }

        is_valid = any(file_bytes.startswith(magic) for magic in valid_formats.keys())
        if not is_valid:
            raise InvalidImageError("Unsupported image format")

    @staticmethod
    async def _extract_image_metadata(
        file_bytes: bytes, filename: str
    ) -> Dict[str, Any]:
        """Extract metadata from image bytes."""
        # Calculate SHA256
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Extract dimensions and format
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(file_bytes))
            width, height = image.size
            format_type = image.format.lower() if image.format else "unknown"
        except Exception:
            width, height, format_type = 0, 0, "unknown"

        return {
            "width": width,
            "height": height,
            "format": format_type,
            "sha256": sha256,
            "size": len(file_bytes),
        }

    @staticmethod
    def calculate_progress_percentage(status: ProcessingStatus) -> int:
        """
        Calculate progress percentage from processing status (MVP scope only).

        Used when updating ImageProcessingState.progress_percentage field.

        Note: Progress is for upload → scan → sanitize pipeline only.
        Inference progress is tracked separately.
        """
        progress_map = {
            ProcessingStatus.PENDING: 5,
            ProcessingStatus.UPLOADED: 25,
            ProcessingStatus.DEFENDER_SCANNING: 40,
            ProcessingStatus.DEFENDER_SCANNED: 50,
            ProcessingStatus.SANITIZING: 75,
            ProcessingStatus.SANITIZED: 90,
            ProcessingStatus.COMPLETED: 100,
            ProcessingStatus.FAILED: 0,
            ProcessingStatus.CANCELLED: 0,
        }
        return progress_map.get(status, 0)

    @staticmethod
    async def handle_sanitization_callback(
        image_id: str,
        status: str,
        sanitized_blob_url: Optional[str],
        error: Optional[str],
        function_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle sanitization completion callback from Azure Function.

        Validates the function key, validates the request, and sends a DBOS message
        to the waiting workflow using the DBOS messaging system (recv/send pattern).

        Args:
            image_id: UUID string of the image
            status: "success" or "failed"
            sanitized_blob_url: URL to sanitized blob (if successful)
            error: Error message (if failed)
            function_key: Azure Function authentication key (optional)

        Returns:
            Dict with confirmation message

        Raises:
            ValueError: If image_id is invalid UUID or function key is invalid
            ImageProcessingError: If message send fails or config error
        """
        from app.api.config import get_settings

        try:
            # Validate function key if provided
            if function_key is not None:
                settings = get_settings()
                expected_key = settings.azure_sanitization_function_key

                if not expected_key:
                    raise ImageProcessingError(
                        "Sanitization function key not configured"
                    )

                if function_key != expected_key:
                    DBOS.logger.warning(
                        f"Invalid function key in sanitization callback for image {image_id}"
                    )
                    raise ValueError("Invalid function key")

            # Validate image_id is valid UUID
            try:
                _image_uuid = UUID(image_id)
            except ValueError as e:
                raise ValueError(f"Invalid image_id format: {image_id}") from e

            # Prepare message for workflow
            message = {
                "status": status,
                "sanitized_blob_url": sanitized_blob_url,
                "error": error,
            }

            # Send message to waiting workflow using DBOS messaging
            # Topic format matches what workflow is listening on: "sanitization-{image_id}"
            topic = f"sanitization-{image_id}"

            await DBOS.send_async(
                destination_id=topic,
                message=message,
                topic=topic,
            )

            DBOS.logger.info(
                f"Sanitization callback processed for image {image_id}: {status}"
            )

            return {
                "message": "Callback received and workflow notified",
                "image_id": image_id,
                "status": status,
            }

        except ValueError:
            raise
        except ImageProcessingError:
            raise
        except Exception as e:
            DBOS.logger.error(
                f"Failed to process sanitization callback: {str(e)}",
                exc_info=True,
            )
            raise ImageProcessingError(
                f"Failed to process sanitization callback: {str(e)}"
            ) from e
