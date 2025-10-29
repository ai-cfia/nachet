"""
Test and Debug Endpoints Module

This module contains test endpoints and commented-out code for review.
These functions are intended for testing/debugging and should be
DISABLED IN PRODUCTION.

Contents:
- submit_direct_pipeline_inference_request_test: Test endpoint for direct pipeline inference
- submit_direct_inference_request_test: Test endpoint for direct inference (hardcoded models)
- handle_sanitization_callback: Commented-out sanitization callback handler
"""

from uuid import UUID

from app.model.inference import InferenceRequest, ApiInferenceResponse
from app.service import PipelineService
from app.service.rbac import RbacService
from app.service.inference_api import (
    InferenceDispatchService,
    ModelInferenceDetectorResult,
    ModelInferenceClassifierResult,
    process_api_ready_classification_result,
)
from app.exceptions import ImageProcessingError


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

    await RbacService.verify_user_is_cfia_admin(user_id)  # type: ignore[arg-type]

    logger = LogService.get_logger()

    logger.debug(
        "Processing direct pipeline inference request",
        pipeline_id=request.pipeline_id,
        folder_name=request.folder_name,
    )

    try:
        # Get pipeline steps from cache
        pipeline_steps = await PipelineService.get_pipeline_steps(request.pipeline_id)

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


# ============================================================================
# COMMENTED OUT CODE FOR REVIEW
# ============================================================================
# The following code is commented out but preserved for review.
# It handles sanitization callbacks from Azure Functions.
# ============================================================================

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
#
#     Validates the function key, validates the request, and sends a DBOS message
#     to the waiting workflow using the DBOS messaging system (recv/send pattern).
#
#     Args:
#         image_id: UUID string of the image
#         status: "success" or "failed"
#         sanitized_blob_url: URL to sanitized blob (if successful)
#         error: Error message (if failed)
#         function_key: Azure Function authentication key (optional)
#
#     Returns:
#         Dict with confirmation message
#
#     Raises:
#         ValueError: If image_id is invalid UUID or function key is invalid
#         ImageProcessingError: If message send fails or config error
#     """
#     from app.api.config import get_settings
#     from dbos import DBOS
#
#     try:
#         # Validate function key if provided
#         if function_key is not None:
#             settings = get_settings()
#             expected_key = settings.azure_sanitization_function_key
#
#             if not expected_key:
#                 raise ImageProcessingError(
#                     "Sanitization function key not configured"
#                 )
#
#             if function_key != expected_key:
#                 DBOS.logger.warning(
#                     f"Invalid function key in sanitization callback for image {image_id}"
#                 )
#                 raise ValueError("Invalid function key")
#
#         # Validate image_id is valid UUID
#         try:
#             _image_uuid = UUID(image_id)
#         except ValueError as e:
#             raise ValueError(f"Invalid image_id format: {image_id}") from e
#
#         # Prepare message for workflow
#         message = {
#             "status": status,
#             "sanitized_blob_url": sanitized_blob_url,
#             "error": error,
#         }
#
#         # Send message to waiting workflow using DBOS messaging
#         # Topic format matches what workflow is listening on: "sanitization-{image_id}"
#         topic = f"sanitization-{image_id}"
#
#         await DBOS.send_async(
#             destination_id=topic,
#             message=message,
#             topic=topic,
#         )
#
#         DBOS.logger.info(
#             f"Sanitization callback processed for image {image_id}: {status}"
#         )
#
#         return {
#             "message": "Callback received and workflow notified",
#             "image_id": image_id,
#             "status": status,
#         }
#
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
