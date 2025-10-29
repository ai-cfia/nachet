"""
Inference Service

Business logic layer for image inference and processing API endpoints.
Coordinates between DirectoryService, blob operations, DBOS workflows, and other services.
Consolidates image processing pipeline, queue, and inference operations.

IMPORTANT: DBOS decorators wrap async functions in a way that conflicts with
beartype's automatic type checking. Use @no_type_check to exclude these functions
from automatic beartype decoration applied by beartype_this_package().
"""

# import base64
from beartype.typing import Dict, Any, Optional
from typing import no_type_check
from uuid import UUID
from datetime import datetime, timezone
from dataclasses import dataclass
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
    PipelineService,
    RbacService,
    ImageService,
)
from app.service.constants import MAX_BASE64_LENGTH
from app.exceptions import (
    ImageProcessingError,
    InvalidImageError,
    FolderNotFoundError,
    PipelineNotFoundError,
)
from app.db.utils import sessionmanager
from app.service.inference_api import (
    InferenceDispatchService,
    process_api_ready_classification_result,
)
from app.datastore.image import ImageDataService
from app.db.model import ImageProcessingState
from app.service.constants import ProcessingStatus
from app.service.blob_operations import (
    upload_to_azure_blob,
    wait_for_defender_scan,
)
from app.service.sanitization import (
    trigger_sanitization_function_local,
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
# DBOS Steps for Inference Workflow
# ============================================================================
#
# WORKFLOW ARCHITECTURE:
# ----------------------
# The image_inference_workflow is broken down into DBOS steps to ensure
# durability and proper recovery. Each step handles a nondeterministic
# operation that accesses external services.
#
# EXECUTION FLOW:
# ---------------
# 1. download_image_from_blob_step(org_prefix, image_id)
#    → Downloads image from Azure Blob Storage
#    → Returns: bytes
#
# 2. [WORKFLOW] base64 encoding (deterministic)
#    → Encodes image bytes to base64 string
#
# 3. get_pipeline_configuration_step(pipeline_id)
#    → Retrieves pipeline steps from cache/database
#    → Returns: list[dict[str, str]]
#
# 4. FOR EACH pipeline step:
#    execute_inference_step(step_config, previous_result)
#    → Calls external ML inference endpoint
#    → Returns: dict[str, Any] (serialized inference result)
#    → Each iteration is a separate DBOS step for durability
#
# 5. [WORKFLOW] Reconstruct ModelInferenceClassifierResult (deterministic)
#    → Converts dict back to typed object
#
# 6. [WORKFLOW] process_api_ready_classification_result(...) (deterministic)
#    → Pure computation: overlapping detection, color assignment, etc.
#    → Remains in workflow as it's deterministic
#
# 7. [WORKFLOW] Build final API response (deterministic)
#
# ERROR HANDLING:
# ---------------
# - Exceptions in steps: Propagate to workflow, DBOS handles retries
# - Workflow-level try/catch: Wraps all operations for final error handling
# - max_recovery_attempts=5: DBOS will retry workflow up to 5 times
# - Each step records its result - on recovery, completed steps are replayed
#   from recorded results, not re-executed
#
# WHY STEPS ARE NEEDED:
# ---------------------
# - download_image_from_blob_step: Accesses Azure Blob Storage (external service)
# - get_pipeline_configuration_step: Accesses database/cache (external data store)
# - execute_inference_step: Calls ML model HTTP endpoints (external API)
# - process_api_ready_classification_result: NOT a step (deterministic computation)
#
# DBOS CONSTRAINTS:
# -----------------
# - Steps cannot call, start, or enqueue workflows
# - Steps can call other steps, but they become part of the same step execution
# - Workflow can call steps and other workflows
# - @no_type_check required due to DBOS decorator conflicts with beartype
#
# ============================================================================


@no_type_check
@DBOS.step()
async def download_image_from_blob_step(
    org_prefix: str,
    image_id: UUID,
) -> str:
    """
    DBOS Step: Download sanitized image from Azure Blob Storage.

    This is a nondeterministic operation because it accesses an external service.
    DBOS will record the result and replay it on workflow recovery.

    Args:
        org_prefix: Organization prefix for blob path
        image_id: UUID of the image to download

    Returns:
        str: Base64-encoded string of the raw image data

    Raises:
        BlobDownloadError: If download fails
    """
    import base64
    from app.service.blob_operations import download_sanitized_blob

    image_bytes = await download_sanitized_blob(image_id, org_prefix)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    if not image_base64:
        raise ImageProcessingError("Image not found")

    return image_base64


@no_type_check
@DBOS.step()
async def get_pipeline_configuration_step(
    pipeline_id: UUID,
) -> list[dict[str, Any]]:
    """
    DBOS Step: Retrieve pipeline configuration from cache/database.

    This is a nondeterministic operation because it accesses an external data store.
    DBOS will record the result and replay it on workflow recovery.

    Args:
        pipeline_id: UUID of the pipeline

    Returns:
        list[dict[str, Any]]: Pipeline steps configuration

    Raises:
        ValueError: If pipeline not found
    """
    pipeline_steps = await PipelineService.get_pipeline_steps(str(pipeline_id))

    if not pipeline_steps:
        from app.service.logs import LogService

        logger = LogService.get_logger()
        error_msg = f"Pipeline '{pipeline_id}' not found in cache"
        logger.error(
            error_msg,
            pipeline_id=pipeline_id,
            available_pipelines=PipelineService.get_cached_pipeline_names(),
        )
        raise ValueError(error_msg)

    return pipeline_steps


@no_type_check
@DBOS.step()
async def execute_inference_step(
    step_config: dict[str, Any],
    previous_result: str | dict[str, Any],
) -> dict[str, Any]:
    """
    DBOS Step: Execute a single inference step by calling external ML model endpoint.

    This is a nondeterministic operation because it calls an external API.
    DBOS will record the result and replay it on workflow recovery.

    Args:
        step_config: Model configuration dict with endpoint, api_key, etc.
        previous_result: Result from previous step (base64 string or inference result dict)

    Returns:
        dict[str, Any]: Inference result from the model

    Raises:
        ValueError: If inference returns unexpected type
    """
    from app.service.inference_api import (
        ModelInferenceDetectorResult,
        ModelInferenceClassifierResult,
    )

    # Reconstruct typed objects from dict if needed
    if isinstance(previous_result, dict):
        # Determine type based on dict structure and reconstruct
        if "images" in previous_result and "result" in previous_result:
            # Check if result field has boxes (detector) or filename (classifier)
            result_field = previous_result.get("result")
            if isinstance(result_field, dict):
                if "boxes" in result_field and "filename" not in result_field:
                    # This is a detector result - reconstruct SeedDetectorAPIResponse
                    from app.model.inference import (
                        SeedDetectorAPIResponse as SeedDetectorAPIResponseModel,
                    )

                    result_obj = SeedDetectorAPIResponseModel(**result_field)
                    previous_result = ModelInferenceDetectorResult(
                        result=result_obj, images=previous_result["images"]
                    )
                elif "filename" in result_field and "boxes" in result_field:
                    # This is a classifier result - reconstruct EnhancedClassificationResult
                    from app.model.inference import (
                        EnhancedClassificationResult as EnhancedClassificationResultModel,
                    )

                    result_obj = EnhancedClassificationResultModel(**result_field)
                    previous_result = ModelInferenceClassifierResult(
                        result=result_obj, images=previous_result.get("images")
                    )
            # else: result field is already a Pydantic model instance, use as-is
            elif hasattr(result_field, "boxes"):
                # Already a proper object, reconstruct the wrapper dataclass
                previous_result = (
                    ModelInferenceDetectorResult(**previous_result)
                    if not hasattr(result_field, "filename")
                    else ModelInferenceClassifierResult(**previous_result)
                )

    # Dispatch to inference service
    step_result = await InferenceDispatchService.dispatch(
        model=step_config,
        previous_result=previous_result,
    )

    # Type guard: dispatch returns only valid result types
    if not isinstance(
        step_result,
        (str, ModelInferenceDetectorResult, ModelInferenceClassifierResult),
    ):
        raise ValueError(f"Pipeline step returned unexpected type: {type(step_result)}")

    # Convert to dict for DBOS serialization
    if isinstance(
        step_result, (ModelInferenceDetectorResult, ModelInferenceClassifierResult)
    ):
        return step_result.__dict__

    return {"base64_result": step_result}


# ============================================================================
# DBOS Workflow for Inference
# ============================================================================


@no_type_check
@DBOS.workflow(max_recovery_attempts=5)
async def image_inference_workflow(
    image_id: UUID,
    org_prefix: str,
    pipeline_id: UUID,
    imageDims: list[int],
) -> ApiInferenceResponse:
    """
    Main image inference workflow.

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Args:
        image_id: UUID v7 of the image
        user_id: Submitting user UUID
        org_prefix: Organization prefix (normalized, max 10 chars)

    Returns:
        ApiInferenceResponse containing inference results

    Raises:
        ImageProcessingError: If inference fails
    """
    from app.service.logs import LogService
    from app.service.inference_api import ModelInferenceClassifierResult
    from app.model.inference import ModelInfo

    logger = LogService.get_logger()

    logger.debug(
        "Processing direct pipeline inference request",
        pipeline_id=pipeline_id,
    )

    try:
        # Publish initial inference events
        await DBOS.set_event_async("inference_status", "started")
        await DBOS.set_event_async(
            "inference_timestamps", {"started": datetime.now(timezone.utc).isoformat()}
        )

        # DBOS Step 1: Download image from sanitized blob storage and encode to base64
        DBOS.logger.info(f"[{image_id}] Step 1: Downloading image from blob storage")
        image_base64 = await download_image_from_blob_step(org_prefix, image_id)
        await DBOS.set_event_async("inference_status", "image_downloaded")

        # DBOS Step 2: Get pipeline configuration
        DBOS.logger.info(f"[{image_id}] Step 2: Retrieving pipeline configuration")
        pipeline_steps = await get_pipeline_configuration_step(pipeline_id)
        await DBOS.set_event_async("inference_status", "pipeline_loaded")

        logger.info(
            f"Found pipeline with {len(pipeline_steps)} steps",
            pipeline_id=pipeline_id,
            steps=[s["model_name"] for s in pipeline_steps],
        )

        # Execute pipeline steps sequentially - each as a separate DBOS step
        await DBOS.set_event_async("inference_status", "running_models")
        await DBOS.set_event_async("inference_model_progress", {})

        previous_result: str | dict[str, Any] = image_base64

        for step_idx, step in enumerate(pipeline_steps, start=1):
            logger.debug(
                f"Executing pipeline step {step_idx}/{len(pipeline_steps)}",
                step=step["step"],
                model_name=step["model_name"],
                request_function=step["request_function"],
            )

            # DBOS Step 3+: Execute each inference step
            DBOS.logger.info(
                f"[{image_id}] Step {step_idx + 2}: Executing inference with {step['model_name']}"
            )
            step_result_dict = await execute_inference_step(
                step_config=step,
                previous_result=previous_result,
            )

            # Update previous_result for next step
            previous_result = step_result_dict

            # Track model completion
            workflow_id = DBOS.workflow_id
            if workflow_id:
                all_events = await DBOS.get_all_events_async(workflow_id)
                model_progress = all_events.get("inference_model_progress", {})
                model_progress[step["model_name"]] = True
                await DBOS.set_event_async("inference_model_progress", model_progress)

            logger.debug(
                f"Completed pipeline step {step_idx}/{len(pipeline_steps)}",
                model_name=step["model_name"],
            )

        # Reconstruct final classification result from dict
        # The last result should be the classification result
        if "base64_result" in previous_result:
            raise ValueError(
                "Pipeline did not return classification result. Got base64 string instead."
            )

        # Reconstruct ModelInferenceClassifierResult from dict
        classification_result = ModelInferenceClassifierResult(**previous_result)

        logger.info(
            "Direct pipeline inference request processed successfully",
            pipeline_id=pipeline_id,
            steps_executed=len(pipeline_steps),
        )

        # Deterministic operation: process the classification result
        # This remains in workflow as it's pure computation
        api_result = await process_api_ready_classification_result(
            result=classification_result.result,
            imageDims=imageDims,
        )

        # Build model info list from pipeline steps

        models = [
            ModelInfo(name=step["model_name"], version=step.get("version", "1"))
            for step in pipeline_steps
        ]

        # Publish completion events
        await DBOS.set_event_async("inference_status", "completed")
        workflow_id = DBOS.workflow_id
        if workflow_id:
            all_events = await DBOS.get_all_events_async(workflow_id)
            await DBOS.set_event_async(
                "inference_timestamps",
                {
                    **all_events.get("inference_timestamps", {}),
                    "completed": datetime.now(timezone.utc).isoformat(),
                },
            )

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

    except Exception as e:
        # Publish error events for all exceptions
        await DBOS.set_event_async("inference_status", "failed")
        await DBOS.set_event_async(
            "inference_error_details",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.error(
            f"Failed to submit direct pipeline inference: {str(e)}",
            pipeline_id=pipeline_id,
            error_type=type(e).__name__,
        )

        # Re-raise ValueError as-is, convert others to ImageProcessingError
        if isinstance(e, ValueError):
            raise
        raise ImageProcessingError(
            f"Failed to submit direct pipeline inference: {str(e)}"
        ) from e


# ============================================================================
# DBOS Workflow for Image Processing Pipeline
# ============================================================================


@no_type_check
@DBOS.workflow(max_recovery_attempts=5)
async def image_processing_and_inference_workflow(
    image_id: UUID,
    file_bytes: bytes | None,
    user_id: UUID,
    org_prefix: str,
    pipeline_id: UUID,
    imageDims: list[int],
    skip_preprocessing: bool = False,
) -> Dict[str, Any]:
    """
    Parent workflow that orchestrates image processing and inference.

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Steps:
    1. Run image_processing_workflow (upload → scan → sanitize)
    2. Run image_inference_workflow (ML inference)

    Args:
        image_id: UUID v7 of the image
        file_bytes: Raw image bytes (None for duplicates)
        user_id: Submitting user UUID
        org_prefix: Organization prefix (normalized, max 10 chars)
        skip_preprocessing: If True, skip upload/scan/sanitize (for duplicate images)
        inference_request: InferenceRequest for ML inference (required)

    Returns:
        Dict containing processing results, blob URLs, and inference results

    Raises:
        Various exceptions for different failure modes (defender, sanitization, inference)
    """
    try:
        DBOS.logger.info(
            f"Starting parent workflow for {image_id} (skip_preprocessing={skip_preprocessing})"
        )

        # Track workflow IDs
        processing_workflow_id = None
        inference_workflow_id = None

        # Step 1: Process image (upload → scan → sanitize)
        processing_result = None
        if not skip_preprocessing:
            # Get the child workflow ID before executing
            processing_workflow_id = (
                DBOS.workflow_id
            )  # This will be set by DBOS when child runs

            processing_result = await image_processing_workflow(
                image_id=image_id,
                file_bytes=file_bytes,
                user_id=user_id,
                org_prefix=org_prefix,
            )

            # Publish processing workflow ID
            await DBOS.set_event_async("processing_workflow_id", processing_workflow_id)

        DBOS.logger.info(f"[{image_id}] Processing complete, starting inference")

        # Step 2: Run inference on the processed image (if pipeline_id provided)
        inference_result = None
        if pipeline_id:
            # Get the child workflow ID before executing
            inference_workflow_id = DBOS.workflow_id

            inference_result = await image_inference_workflow(
                image_id=image_id,
                org_prefix=org_prefix,
                pipeline_id=pipeline_id,
                imageDims=imageDims,
            )

            # Publish inference workflow ID
            await DBOS.set_event_async("inference_workflow_id", inference_workflow_id)
            DBOS.logger.info(f"[{image_id}] Inference complete")

        # Publish both workflow IDs together for easy retrieval
        await DBOS.set_event_async(
            "workflow_ids",
            {
                "parent_workflow_id": DBOS.workflow_id,
                "processing_workflow_id": processing_workflow_id,
                "inference_workflow_id": inference_workflow_id,
            },
        )

        return {
            "processing_result": processing_result,
            "inference_result": inference_result,
            "workflow_ids": {
                "parent": DBOS.workflow_id,
                "processing": processing_workflow_id,
                "inference": inference_workflow_id,
            },
        }

    except Exception as e:
        DBOS.logger.error(f"[{image_id}] Parent workflow failed: {str(e)}")
        raise


@no_type_check
@DBOS.workflow(max_recovery_attempts=5)
async def image_processing_workflow(
    image_id: UUID,
    file_bytes: bytes | None,
    user_id: UUID,
    org_prefix: str,
) -> Dict[str, Any]:
    """
    Main image processing workflow (MVP).

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Args:
        image_id: UUID v7 of the image
        file_bytes: Raw image bytes (None for duplicates)
        user_id: Submitting user UUID
        org_prefix: Organization prefix (normalized, max 10 chars)
        skip_preprocessing: If True, skip upload/scan/sanitize (for duplicate images)

    Returns:
        Dict containing processing results and blob URLs

    Raises:
        Various exceptions for different failure modes (defender, sanitization)
    """
    try:
        DBOS.logger.info(f"Starting image processing pipeline for {image_id})")

        # Publish initial progress event
        await DBOS.set_event_async("processing_status", "started")
        await DBOS.set_event_async(
            "timestamps", {"started": datetime.now(timezone.utc).isoformat()}
        )

        # Step 1: Upload to Azure Blob Storage (nachet-original on EXTERNAL)
        # Must upload to EXTERNAL account for Azure Defender malware scanning
        from app.service.constants import BlobAccount

        DBOS.logger.info(
            f"[{image_id}] Step 1: Uploading to nachet-original on EXTERNAL storage"
        )
        blob_url_original = await upload_to_azure_blob(
            image_id=image_id,
            file_bytes=file_bytes,
            org_prefix=org_prefix,
            user_id=user_id,
            blob_account=BlobAccount.EXTERNAL,
        )
        await DBOS.set_event_async("upload_complete", True)
        await DBOS.set_event_async("processing_status", "uploaded")
        await DBOS.set_event_async("blob_url_original", blob_url_original)

        # Step 2: Wait for Azure Defender scan
        DBOS.logger.info(f"[{image_id}] Step 2: Waiting for Defender scan")
        await DBOS.set_event_async("processing_status", "defender_scanning")
        defender_result = await wait_for_defender_scan(
            image_id=image_id,
            org_prefix=org_prefix,
            timeout_sec=300,
        )
        await DBOS.set_event_async("defender_scan_complete", True)
        await DBOS.set_event_async("processing_status", "defender_scanned")
        await DBOS.set_event_async("defender_result", defender_result)

        # Step 3: Trigger sanitization Azure Function
        DBOS.logger.info(f"[{image_id}] Step 3: Triggering sanitization function")
        await DBOS.set_event_async("processing_status", "sanitizing")
        blob_url_sanitized = await trigger_sanitization_function_local(
            image_id=image_id,
            org_prefix=org_prefix,
        )

        # Step 4: Wait for sanitization callback
        # DBOS.logger.info(f"[{image_id}] Step 4: Waiting for sanitization callback")
        # sanitized_blob_url = await wait_for_sanitization_callback(
        #     image_id=image_id,
        #     timeout_sec=600,
        # )
        # await DBOS.set_event_async("sanitization_complete", True)
        # await DBOS.set_event_async("processing_status", "sanitized")
        # await DBOS.set_event_async("blob_url_sanitized", blob_url_sanitized)

        # Publish completion
        await DBOS.set_event_async("processing_status", "completed")
        workflow_id = DBOS.workflow_id
        if workflow_id is None:
            raise ValueError("DBOS workflow_id is None")
        all_events = await DBOS.get_all_events_async(workflow_id)
        await DBOS.set_event_async(
            "timestamps",
            {
                **all_events.get("timestamps", {}),
                "completed": datetime.now(timezone.utc).isoformat(),
            },
        )

        DBOS.logger.info(f"[{image_id}] Pipeline completed successfully")

        return {
            "image_id": str(image_id),
            "status": "completed",
            "blob_url_original": blob_url_original,
            "blob_url_sanitized": blob_url_sanitized,
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        raise


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PreprocessedImageData:
    """
    Dataclass containing validated image data and metadata from preprocessing.

    Attributes:
        image_bytes: Decoded binary image data
        width: Image width in pixels
        height: Image height in pixels
        mime_type: MIME type of the image (e.g., "image/png")
        size_bytes: Size of the image in bytes
        sha256_hash: SHA-256 hash of the image bytes
        duplicate_uuid: UUID of existing image with same hash, if found
    """

    image_bytes: bytes
    width: int
    height: int
    mime_type: str
    size_bytes: int
    sha256_hash: str
    duplicate_uuid: Optional[UUID] = None


# ============================================================================
# InferenceService Class
# ============================================================================


class InferenceService:
    """Service layer for inference-related business logic."""

    @staticmethod
    async def _preprocess_image(
        image_base64: str, user_role_id: UUID
    ) -> PreprocessedImageData:
        """
        Validate the uploaded image file. Decode from base64 and check type, size, dimensions.
        Issue #229 #231

        Args:
            image_base64: Base64-encoded image data

        Returns:
            PreprocessedImageData: Dataclass containing validated image data and metadata

        Raises:
            ValueError: If validation fails
            ImageProcessingError: If hash computation or duplicate check fails
        """
        import base64
        import magic
        import hashlib

        # validate size (max 10MB)
        if len(image_base64) > MAX_BASE64_LENGTH:
            raise InvalidImageError("Image size exceeds maximum limit of 10MB")

        # Strip data URL prefix if present before further validation
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]

        # Check minimum size (but be lenient - very small images will fail dimension check anyway)
        if len(image_base64.strip()) < 100:
            raise InvalidImageError("Image size is too small or empty")

        # Decode base64 to binary
        image_bytes = base64.b64decode(image_base64)

        # Validate image type using magic bytes (more reliable than mimetypes on base64)
        mime_type = magic.from_buffer(image_bytes, mime=True)
        if not mime_type.startswith("image/png"):
            raise InvalidImageError("Uploaded file is not a valid PNG image")

        # validate dimensions
        header = image_bytes[:24]
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        if width < 384 or height < 384:
            raise InvalidImageError(
                "Image dimensions are too small, minimum is 384x384 pixels"
            )
        if width > 1920 and height > 1080:
            raise InvalidImageError(
                "Image dimensions are too large, maximum is 1920x1080 pixels"
            )

        try:
            # Compute hash of the image
            image_hash = hashlib.sha256(image_bytes).hexdigest()

            # Check if image with this hash already exists in database
            async with sessionmanager.get_session() as session:
                image_service = ImageDataService(session)
                duplicate_uuid_result = await image_service.check_sha256_exists(
                    image_hash, user_role_id
                )
                # Cast to standard UUID type for compatibility
                duplicate_uuid: Optional[UUID] = (
                    UUID(str(duplicate_uuid_result)) if duplicate_uuid_result else None
                )

        except Exception as e:
            raise ImageProcessingError(f"Failed to compute image hash: {str(e)}") from e

        return PreprocessedImageData(
            image_bytes=image_bytes,
            width=width,
            height=height,
            mime_type=mime_type,
            size_bytes=len(image_bytes),
            sha256_hash=image_hash,
            duplicate_uuid=duplicate_uuid,
        )

    @staticmethod
    async def create_processing_state(
        picture_id: UUID,
        status: ProcessingStatus,
        created_at: datetime,
        progress_percentage: int = 0,
        workflow_id: Optional[str] = None,
    ) -> ImageProcessingState:
        """
        Create a new ImageProcessingState record.

        Args:
            picture_id: UUID of the picture being processed
            status: Initial processing status
            created_at: Timestamp when processing state was created
            progress_percentage: Initial progress percentage (default 0)
            workflow_id: Optional DBOS workflow ID for tracking

        Returns:
            ImageProcessingState: Created processing state record

        Raises:
            ImageProcessingError: If creation fails
        """
        try:
            async with sessionmanager.get_session() as session:
                processing_state = ImageProcessingState(
                    picture_id=picture_id,
                    status=status,
                    created_at=created_at,
                    progress_percentage=progress_percentage,
                    workflow_id=workflow_id,
                )
                session.add(processing_state)
                await session.commit()
                await session.refresh(processing_state)
                return processing_state
        except Exception as e:
            raise ImageProcessingError(
                f"Failed to create processing state: {str(e)}"
            ) from e

    @staticmethod
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
        from uuid6 import uuid7
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
            info = await InferenceService._preprocess_image(
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
                skip_preprocessing=bool(
                    info.duplicate_uuid
                ),  # Skip preprocessing for duplicates
            )
            workflow_id = workflow_handle.get_workflow_id()

            # Only create processing state for new images, not duplicates
            if not info.duplicate_uuid:
                _processing_state = await InferenceService.create_processing_state(
                    picture_id=image_id,
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
    # Helper Methods for Image Validation and Metadata Extraction
    # ========================================================================

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

            if workflow_id is None:
                raise ImageProcessingError(f"No workflow ID found for image {image_id}")

            # Resume the workflow from last completed step
            DBOS.resume_workflow(workflow_id)

            # Update processing state
            processing_state.retry_count += 1
            processing_state.last_retry_at = datetime.now(timezone.utc)
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

    # @staticmethod
    # async def handle_sanitization_callback(
    #     image_id: str,
    #     status: str,
    #     sanitized_blob_url: Optional[str],
    #     error: Optional[str],
    #     function_key: Optional[str] = None,
    # ) -> Dict[str, Any]:
    #     """
    #     Handle sanitization completion callback from Azure Function.

    #     Validates the function key, validates the request, and sends a DBOS message
    #     to the waiting workflow using the DBOS messaging system (recv/send pattern).

    #     Args:
    #         image_id: UUID string of the image
    #         status: "success" or "failed"
    #         sanitized_blob_url: URL to sanitized blob (if successful)
    #         error: Error message (if failed)
    #         function_key: Azure Function authentication key (optional)

    #     Returns:
    #         Dict with confirmation message

    #     Raises:
    #         ValueError: If image_id is invalid UUID or function key is invalid
    #         ImageProcessingError: If message send fails or config error
    #     """
    #     from app.api.config import get_settings

    #     try:
    #         # Validate function key if provided
    #         if function_key is not None:
    #             settings = get_settings()
    #             expected_key = settings.azure_sanitization_function_key

    #             if not expected_key:
    #                 raise ImageProcessingError(
    #                     "Sanitization function key not configured"
    #                 )

    #             if function_key != expected_key:
    #                 DBOS.logger.warning(
    #                     f"Invalid function key in sanitization callback for image {image_id}"
    #                 )
    #                 raise ValueError("Invalid function key")

    #         # Validate image_id is valid UUID
    #         try:
    #             _image_uuid = UUID(image_id)
    #         except ValueError as e:
    #             raise ValueError(f"Invalid image_id format: {image_id}") from e

    #         # Prepare message for workflow
    #         message = {
    #             "status": status,
    #             "sanitized_blob_url": sanitized_blob_url,
    #             "error": error,
    #         }

    #         # Send message to waiting workflow using DBOS messaging
    #         # Topic format matches what workflow is listening on: "sanitization-{image_id}"
    #         topic = f"sanitization-{image_id}"

    #         await DBOS.send_async(
    #             destination_id=topic,
    #             message=message,
    #             topic=topic,
    #         )

    #         DBOS.logger.info(
    #             f"Sanitization callback processed for image {image_id}: {status}"
    #         )

    #         return {
    #             "message": "Callback received and workflow notified",
    #             "image_id": image_id,
    #             "status": status,
    #         }

    #     except ValueError:
    #         raise
    #     except ImageProcessingError:
    #         raise
    #     except Exception as e:
    #         DBOS.logger.error(
    #             f"Failed to process sanitization callback: {str(e)}",
    #             exc_info=True,
    #         )
    #         raise ImageProcessingError(
    #             f"Failed to process sanitization callback: {str(e)}"
    #         ) from e

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
        from app.service.rbac import RbacService

        await RbacService.verify_user_is_cfia_admin(user_id)  # type: ignore[arg-type]

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
            from app.service.inference_api import (
                ModelInferenceDetectorResult,
                ModelInferenceClassifierResult,
            )

            previous_result: (
                str | ModelInferenceDetectorResult | ModelInferenceClassifierResult
            ) = image_base64

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
                # Type guard: dispatch returns only valid result types
                if not isinstance(
                    step_result,
                    (str, ModelInferenceDetectorResult, ModelInferenceClassifierResult),
                ):
                    raise ValueError(
                        f"Pipeline step returned unexpected type: {type(step_result)}"
                    )
                previous_result = step_result

                logger.debug(
                    f"Completed pipeline step {step_idx}/{len(pipeline_steps)}",
                    model_name=step["model_name"],
                )

            # The last result should be the classification result
            # Type check: ensure the last step returned a classification result
            from app.service.inference_api import ModelInferenceClassifierResult

            if not isinstance(previous_result, ModelInferenceClassifierResult):
                raise ValueError(
                    f"Pipeline did not return classification result. Got: {type(previous_result)}"
                )

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
            from app.model.inference import ModelInfo

            models = [
                ModelInfo(name=step["model_name"], version=step.get("version", "1"))
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
            from app.service.inference_api import ModelInferenceDetectorResult

            detection_result_raw = await InferenceDispatchService.dispatch(
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

            # Type check: ensure detector returned detector result
            if not isinstance(detection_result_raw, ModelInferenceDetectorResult):
                raise ValueError(
                    f"Detector did not return expected result type. Got: {type(detection_result_raw)}"
                )

            detection_result: ModelInferenceDetectorResult = detection_result_raw

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

            # Type check: ensure we got a classification result
            from app.service.inference_api import ModelInferenceClassifierResult

            if not isinstance(classification_result, ModelInferenceClassifierResult):
                raise ValueError(
                    f"Classification step did not return expected result type. Got: {type(classification_result)}"
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
            from app.model.inference import ModelInfo

            return ApiInferenceResponse(
                filename=api_result.filename,
                imageId="direct-inference",  # No DB storage for direct inference
                inference_id="direct-inference",  # No DB storage for direct inference
                boxes=api_result.boxes,
                labelOccurrence=api_result.labelOccurrence,
                totalBoxes=api_result.totalBoxes,
                models=[
                    ModelInfo(name="rcnn_seed_detector", version="1"),
                    ModelInfo(name="swin_classifier_model", version="1"),
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
