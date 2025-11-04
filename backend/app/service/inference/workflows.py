"""
DBOS Workflows and Steps for Image Processing and Inference

This module contains all DBOS workflow definitions and steps for:
- Image processing pipeline (upload → scan → sanitize)
- Inference pipeline (download → execute models → save results)
- Parent workflow orchestration

DBOS ARCHITECTURE:
-----------------
The workflows are broken down into DBOS steps to ensure durability and proper recovery.
Each step handles a nondeterministic operation that accesses external services.

WORKFLOW CONSTRAINTS:
--------------------
- Steps cannot call, start, or enqueue workflows
- Steps can call other steps, but they become part of the same step execution
- Workflow can call steps and other workflows
- @no_type_check required due to DBOS decorator conflicts with beartype
"""

from typing import no_type_check, Any
from beartype.typing import Dict
from uuid import UUID
from datetime import datetime, timezone

from dbos import DBOS
from app.model.inference import ApiInferenceResponse
from app.service import PipelineService
from app.service.annotation import AnnotationService
from app.service.image_objects import ImageObjectsService
from app.service.seed import SeedService
from app.exceptions import ImageProcessingError
from app.service.constants import BlobAccount
from app.service.blob_operations import (
    upload_to_azure_blob,
    # wait_for_defender_scan,
)
from app.service.sanitization import trigger_sanitization_function_local
from app.service.inference.state_management import (
    update_processing_state_step,
    update_inference_state_step,
    mark_processing_failed_step,
    mark_inference_failed_step,
)


# ============================================================================
# DBOS Steps for Inference Workflow
# ============================================================================


@no_type_check
@DBOS.step()
async def create_inference_request_state_step(
    picture_id: UUID,
    pipeline_id: UUID,
    user_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    workflow_id: str,
    image_dims: list[int],
) -> dict[str, Any]:
    """
    DBOS Step: Create InferenceRequestState record for tracking.

    This is a nondeterministic operation because it writes to the database.
    DBOS will record the result and replay it on workflow recovery.

    Args:
        picture_id: UUID of the picture
        pipeline_id: UUID of the pipeline
        user_id: User who initiated the request
        org_user_role_id: User's organization role
        org_admin_role_id: Admin role for cross-org access
        workflow_id: DBOS workflow ID for this inference workflow
        image_dims: Image dimensions [width, height]

    Returns:
        Dict with inference_request_state_id
    """
    from app.service.inference.state_management import create_inference_request_state

    request_payload = {
        "picture_id": str(picture_id),
        "pipeline_id": str(pipeline_id),
        "image_dims": image_dims,
        "workflow_id": workflow_id,
    }

    state = await create_inference_request_state(
        picture_id=picture_id,
        pipeline_id=pipeline_id,
        user_id=user_id,
        org_user_role_id=org_user_role_id,
        org_admin_role_id=org_admin_role_id,
        workflow_id=workflow_id,
        request_payload=request_payload,
    )

    return {
        "inference_request_state_id": str(state.id),
        "status": state.status,
    }


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
            f"{error_msg} (available_pipelines={PipelineService.get_cached_pipeline_names()})"
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
        InferenceDispatchService,
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


@no_type_check
@DBOS.step()
async def save_inference_results_step(
    user_id: UUID,
    image_id: UUID,
    pipeline_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    api_response: ApiInferenceResponse,
    parent_workflow_id: UUID,
) -> dict[str, Any]:
    """
    DBOS Step: Save inference results to database (Annotation + Objects).

    This is a nondeterministic operation because it writes to database.
    DBOS will record the result and replay it on workflow recovery.

    Args:
        user_id: User who submitted the inference request
        image_id: UUID of the image
        pipeline_id: UUID of the pipeline used
        org_user_role_id: Organization user role ID for RBAC
        org_admin_role_id: Organization admin role ID for RBAC
        api_response: Complete API response with boxes and metadata
        parent_workflow_id: Parent workflow ID (used as annotation ID)

    Returns:
        dict with annotation_id and list of created object_ids

    Raises:
        Exception: If species label not found in seed database (critical error)
        ImageProcessingError: If database operations fail
    """
    from app.service.logs import LogService

    logger = LogService.get_logger()

    try:
        # Step 1: Get seed lookup cache with both name_code and species name mappings
        seed_data = await SeedService.get_seed_data()
        seed_lookup: dict[str, UUID] = {}

        for seed in seed_data["seeds"]:
            seed_id = (
                seed["seed_id"]
                if isinstance(seed["seed_id"], UUID)
                else UUID(seed["seed_id"])
            )
            # Map by name_code (e.g., "AMBRO_PSI")
            seed_lookup[seed["name_code"]] = seed_id

            # Also map by full species name for ML models that return full names
            # Format: "Genus species" (e.g., "Ambrosia psilostachya")
            genus = seed.get("genus", "").strip()
            species = seed.get("species", "").strip()
            if genus and species:
                full_species_name = f"{genus} {species}"
                seed_lookup[full_species_name] = seed_id

        logger.debug(
            f"Loaded {len(seed_data['seeds'])} seeds with {len(seed_lookup)} lookup keys (name_code + species names)",
            image_id=str(image_id),
        )

        # Step 2: Create Annotation record with parent workflow ID as annotation ID
        annotation_id = parent_workflow_id
        raw_data = api_response.model_dump()

        annotation = await AnnotationService.create(
            requester_id=user_id,
            id=annotation_id,  # Use parent workflow ID as annotation ID
            org_admin_role_id=org_admin_role_id,
            org_user_role_id=org_user_role_id,
            picture_id=image_id,
            pipeline_id=pipeline_id,
            raw_data=raw_data,
        )

        logger.info(
            f"Created annotation record with ID {annotation_id}",
            image_id=str(image_id),
            annotation_id=str(annotation_id),
        )

        # Step 3: Create Object records for each detected box
        created_object_ids = []

        for box in api_response.boxes:
            # Map species label to seed ID
            # The label format is typically like "Avena fatua" or "0 Avena fatua"
            label = box.label.strip()

            # Try to find seed by name_code
            top_id = seed_lookup.get(label)

            if top_id is None:
                # Critical error - species not found in database
                error_msg = (
                    f"CRITICAL: Species label '{label}' not found in seed database. "
                    f"Available seeds: {list(seed_lookup.keys())[:10]}... "
                    f"This must be fixed immediately."
                )
                logger.error(
                    f"{error_msg} (image_id={image_id}, label={label}, available_seed_count={len(seed_lookup)})"
                )
                raise Exception(error_msg)

            # Get top-N predictions
            top_id_2 = None
            top_score_2 = None
            top_id_3 = None
            top_score_3 = None

            if len(box.topN) > 1:
                second_label = box.topN[1].label.strip()
                top_id_2 = seed_lookup.get(second_label)
                if top_id_2 is None:
                    logger.error(
                        f"CRITICAL: Species label '{second_label}' (2nd prediction) not found in seed database (image_id={image_id}, label={second_label})"
                    )
                    raise Exception(
                        f"CRITICAL: Species label '{second_label}' not found in seed database"
                    )
                top_score_2 = box.topN[1].score

            if len(box.topN) > 2:
                third_label = box.topN[2].label.strip()
                top_id_3 = seed_lookup.get(third_label)
                if top_id_3 is None:
                    logger.error(
                        f"CRITICAL: Species label '{third_label}' (3rd prediction) not found in seed database (image_id={image_id}, label={third_label})"
                    )
                    raise Exception(
                        f"CRITICAL: Species label '{third_label}' not found in seed database"
                    )
                top_score_3 = box.topN[2].score

            # Create Object record
            image_object = await ImageObjectsService.create(
                requester_id=user_id,
                user_id=user_id,
                org_admin_role_id=org_admin_role_id,
                org_user_role_id=org_user_role_id,
                inference_id=annotation_id,
                picture_id=image_id,
                pipeline_id=pipeline_id,
                valid=True,
                top_x_abs=box.box.topX,
                top_y_abs=box.box.topY,
                bot_x_abs=box.box.bottomX,
                bot_y_abs=box.box.bottomY,
                top_id=top_id,
                top_score=box.score,
                top_id_2=top_id_2,
                top_score_2=top_score_2,
                top_id_3=top_id_3,
                top_score_3=top_score_3,
            )

            created_object_ids.append(image_object["id"])

        logger.info(
            f"Created {len(created_object_ids)} object records for annotation {annotation_id}",
            image_id=str(image_id),
            annotation_id=str(annotation_id),
            object_count=len(created_object_ids),
        )

        return {
            "annotation_id": str(annotation["id"]),
            "object_ids": created_object_ids,
            "object_count": len(created_object_ids),
        }

    except Exception as e:
        logger.error(
            f"Failed to save inference results to database for image_id={image_id}, parent_workflow_id={parent_workflow_id}: {str(e)} (error_type={type(e).__name__})"
        )
        raise


# ============================================================================
# DBOS Workflow for Inference
# ============================================================================


@no_type_check
@DBOS.workflow(max_recovery_attempts=5)
async def image_inference_workflow(
    image_id: UUID,
    org_prefix: str,
    pipeline_id: UUID,
    image_dims: list[int],
    user_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    parent_workflow_id: UUID,
) -> ApiInferenceResponse:
    """
    Main image inference workflow.

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Args:
        image_id: UUID v7 of the image
        org_prefix: Organization prefix (normalized, max 10 chars)
        pipeline_id: UUID of the pipeline to execute
        imageDims: Image dimensions [width, height]
        user_id: Submitting user UUID
        org_user_role_id: Organization user role ID for RBAC
        org_admin_role_id: Organization admin role ID for RBAC
        parent_workflow_id: Parent workflow ID (for annotation tracking)

    Returns:
        ApiInferenceResponse containing inference results

    Raises:
        ImageProcessingError: If inference fails
    """
    from app.service.logs import LogService
    from app.service.inference_api import (
        ModelInferenceClassifierResult,
        process_api_ready_classification_result,
    )
    from app.model.inference import ModelInfo

    logger = LogService.get_logger()

    logger.debug(
        "Processing direct pipeline inference request",
        pipeline_id=pipeline_id,
    )

    # Initialize inference_state_id to None for error handling
    inference_state_id = None

    try:
        # Publish initial inference events
        await DBOS.set_event_async("inference_status", "started")
        await DBOS.set_event_async(
            "inference_timestamps", {"started": datetime.now(timezone.utc).isoformat()}
        )

        # DBOS Step 0: Create InferenceRequestState record for tracking
        DBOS.logger.info(f"[{image_id}] Step 0: Creating inference request state")
        _inference_state = await create_inference_request_state_step(
            picture_id=image_id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            org_user_role_id=org_user_role_id,
            org_admin_role_id=org_admin_role_id,
            workflow_id=DBOS.workflow_id,
            image_dims=image_dims,
        )
        inference_state_id = UUID(_inference_state["inference_request_state_id"])
        logger.info(
            "Created inference request state",
            inference_request_state_id=str(inference_state_id),
        )

        # Update inference state before starting inference
        await update_inference_state_step(
            inference_request_state_id=inference_state_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
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
            imageDims=image_dims,
        )

        # Build model info list from pipeline steps
        models = [
            ModelInfo(name=step["model_name"], version=step.get("version", "1"))
            for step in pipeline_steps
        ]

        # Build complete API response
        api_response = ApiInferenceResponse(
            filename=api_result.filename,
            image_id=str(image_id),
            inference_id=str(
                parent_workflow_id
            ),  # Use parent workflow ID as inference ID
            boxes=api_result.boxes,
            label_occurrence=api_result.labelOccurrence,
            total_boxes=api_result.totalBoxes,
            models=models,
        )

        # DBOS Step: Save annotation and object records to database
        DBOS.logger.info(f"[{image_id}] Saving inference results to database")
        save_result = await save_inference_results_step(
            user_id=user_id,
            image_id=image_id,
            pipeline_id=pipeline_id,
            org_user_role_id=org_user_role_id,
            org_admin_role_id=org_admin_role_id,
            api_response=api_response,
            parent_workflow_id=parent_workflow_id,
        )

        logger.info(
            f"Saved inference results to database: {save_result['object_count']} objects",
            annotation_id=save_result["annotation_id"],
            object_count=save_result["object_count"],
        )

        # Update inference state after successful completion
        await update_inference_state_step(
            inference_request_state_id=inference_state_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            response_payload=api_response.model_dump(),
        )

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

        # Return validated API response
        return api_response

    except Exception as e:
        # Update inference state on error (only if state was created)
        if inference_state_id is not None:
            await mark_inference_failed_step(
                inference_request_state_id=inference_state_id,
                error_message=str(e),
            )

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
            f"Failed to submit direct pipeline inference for pipeline_id={pipeline_id}: {str(e)} (error_type={type(e).__name__})"
        )

        # Re-raise ValueError as-is, convert others to ImageProcessingError
        if isinstance(e, ValueError):
            raise
        raise ImageProcessingError(
            f"Failed to submit direct pipeline inference: {str(e)}"
        ) from e


# ============================================================================
# DBOS Step for Updating Picture Table
# ============================================================================


@no_type_check
@DBOS.step()
async def update_picture_blob_url_step(
    picture_id: UUID,
    blob_url_sanitized: str,
) -> dict[str, Any]:
    """
    DBOS Step: Update Picture table with sanitized blob URL.

    This maintains compatibility with legacy code that reads from Picture table.

    Args:
        picture_id: UUID of the picture
        blob_url_sanitized: URL to sanitized blob

    Returns:
        Dict with updated picture info
    """
    from app.db.utils import sessionmanager
    from app.db.model import Picture
    from sqlalchemy import select

    async with sessionmanager.get_session() as session:
        stmt = select(Picture).where(Picture.id == picture_id)
        result = await session.execute(stmt)
        picture = result.scalar_one_or_none()

        if picture:
            picture.blob_url_sanitized = blob_url_sanitized
            await session.commit()
            await session.refresh(picture)

            return {
                "picture_id": str(picture.id),
                "blob_url_sanitized": picture.blob_url_sanitized,
            }
        else:
            return {"error": f"Picture not found: {picture_id}"}


# ============================================================================
# DBOS Workflow for Waiting on Sanitization (handles duplicate race condition)
# ============================================================================


@no_type_check
@DBOS.step()
async def check_sanitization_status(image_id: UUID) -> dict[str, Any]:
    """
    Step to check if image sanitization is complete.

    Returns dict with:
    - sanitized: bool (True if sanitized blob exists)
    - blob_url_sanitized: str or None
    """
    from app.db.utils import sessionmanager
    from app.db.model import Picture
    from sqlalchemy import select

    async with sessionmanager.get_session() as session:
        stmt = select(Picture.blob_url_sanitized).where(Picture.id == image_id)
        result = await session.execute(stmt)
        blob_url = result.scalar_one_or_none()

        return {
            "sanitized": blob_url is not None,
            "blob_url_sanitized": blob_url,
        }


@no_type_check
@DBOS.workflow()
async def wait_for_sanitization_workflow(
    image_id: UUID,
    timeout_sec: int = 300,
) -> dict[str, Any]:
    """
    Wait for image sanitization to complete (for duplicate images).

    This workflow handles the race condition where a duplicate image is submitted
    while the original upload is still being processed (upload → scan → sanitize).

    Polls the Picture table for blob_url_sanitized field every 5 seconds.
    Once sanitized, allows inference workflow to proceed.

    Args:
        image_id: UUID of the image (from duplicate detection)
        timeout_sec: Maximum time to wait (default 300s = 5 minutes)

    Returns:
        Dict with blob_url_sanitized

    Raises:
        ImageProcessingError: If sanitization doesn't complete within timeout
    """
    max_attempts = timeout_sec // 5  # Poll every 5 seconds

    for attempt in range(max_attempts):
        status = await check_sanitization_status(image_id)

        if status["sanitized"]:
            DBOS.logger.info(
                f"[{image_id}] Sanitization complete (attempt {attempt}): {status['blob_url_sanitized']}"
            )
            return status

        DBOS.logger.info(
            f"[{image_id}] Waiting for sanitization (attempt {attempt}/{max_attempts})"
        )

        # Durable sleep - survives crashes!
        await DBOS.sleep_async(5)

    # Timeout - sanitization didn't complete
    raise ImageProcessingError(
        f"Sanitization timeout: Image {image_id} not sanitized after {timeout_sec}s. "
        "The original upload may have failed."
    )


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
    image_dims: list[int],
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
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
        pipeline_id: UUID of the pipeline to execute
        imageDims: Image dimensions [width, height]
        org_user_role_id: Organization user role ID for RBAC
        org_admin_role_id: Organization admin role ID for RBAC
        skip_preprocessing: If True, skip upload/scan/sanitize (for duplicate images)

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
                parent_workflow_id=DBOS.workflow_id,
            )

            # Publish processing workflow ID
            await DBOS.set_event_async("processing_workflow_id", processing_workflow_id)
        else:
            # For duplicates, wait for sanitization to complete before inference
            # This handles race condition where duplicate submitted while first upload still processing
            DBOS.logger.info(
                f"[{image_id}] Duplicate image - waiting for sanitization to complete"
            )
            await wait_for_sanitization_workflow(image_id)
            DBOS.logger.info(
                f"[{image_id}] Sanitization complete, proceeding to inference"
            )

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
                image_dims=image_dims,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                parent_workflow_id=DBOS.workflow_id,  # Pass parent workflow ID
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
    parent_workflow_id: str,
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
        parent_workflow_id: Parent workflow ID for state tracking

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

        # Update processing state after upload
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="uploaded",
            uploaded_at=datetime.now(timezone.utc),
            blob_url_original=blob_url_original,
            progress_percentage=25,
        )

        # Step 2: Wait for Azure Defender scan
        DBOS.logger.info(f"[{image_id}] Step 2: Waiting for Defender scan")
        await DBOS.set_event_async("processing_status", "defender_scanning")

        # Update processing state before defender scan
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="defender_scanning",
            defender_scan_started_at=datetime.now(timezone.utc),
            progress_percentage=40,
        )

        # TODO: use the actual method when blob is unblocked
        defender_result = {
            "status": "clean",
            "scan_result": "No threats detected",
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        DBOS.logger.info(
            f"IMPORTANT: This is not for production use. Assuming clean scan for image {image_id}."
        )
        # defender_result = await wait_for_defender_scan(
        #     image_id=image_id,
        #     org_prefix=org_prefix,
        #     timeout_sec=300,
        # )
        await DBOS.set_event_async("defender_scan_complete", True)
        await DBOS.set_event_async("processing_status", "defender_scanned")
        await DBOS.set_event_async("defender_result", defender_result)

        # Update processing state after defender scan
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="defender_scanned",
            defender_scan_completed_at=datetime.now(timezone.utc),
            defender_scan_result=defender_result,
            malware_detected=defender_result.get("status") == "malicious",
            progress_percentage=50,
        )

        # Step 3: Trigger sanitization Azure Function
        DBOS.logger.info(f"[{image_id}] Step 3: Triggering sanitization function")
        await DBOS.set_event_async("processing_status", "sanitizing")

        # Update processing state before sanitization
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="sanitizing",
            sanitization_started_at=datetime.now(timezone.utc),
            progress_percentage=75,
        )

        blob_url_sanitized = await trigger_sanitization_function_local(
            image_id=image_id,
            org_prefix=org_prefix,
        )

        # Update Picture table with sanitized blob URL (for legacy compatibility)
        await update_picture_blob_url_step(
            picture_id=image_id,
            blob_url_sanitized=f"{org_prefix}/{image_id}.png",
        )

        # Update processing state after sanitization
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="sanitized",
            sanitization_completed_at=datetime.now(timezone.utc),
            blob_url_sanitized=blob_url_sanitized,
            progress_percentage=90,
        )

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

        # Update processing state on completion
        await update_processing_state_step(
            workflow_id=parent_workflow_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            progress_percentage=100,
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

        # Check if this is a malware detection error
        from app.exceptions import DefenderScanFailedError

        malware_detected = None
        defender_scan_result = None

        if isinstance(e, DefenderScanFailedError) and "Malware detected" in str(e):
            malware_detected = True
            defender_scan_result = {"status": "malicious", "scan_result": "Malicious"}

        # Update processing state on error
        await mark_processing_failed_step(
            workflow_id=parent_workflow_id,
            error_message=str(e),
            error_details={"error_type": type(e).__name__},
            malware_detected=malware_detected,
            defender_scan_result=defender_scan_result,
        )

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
