"""
Inference Service

Business logic layer for image inference and processing API endpoints.
Coordinates between ImageProcessingService, DirectoryService, and other services.
"""

from typing import Dict, Any
from uuid import UUID

from app.model.inference import InferenceRequest, ImageSubmissionResponse, ApiInferenceResponse
from app.service import ImageProcessingService, DirectoryService, SeedService, PipelineService
from app.service.organization import OrganizationService
from app.service.constants import get_cfia_admin_role_id
from app.exceptions import ImageProcessingError
from app.db.utils import sessionmanager
from app.service.inference_api import InferenceDispatchService, process_api_ready_classification_result


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
            raise ImageProcessingError(f"Failed to submit direct pipeline inference: {str(e)}") from e


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
            raise ImageProcessingError(f"Failed to submit direct inference: {str(e)}") from e

    @staticmethod
    async def submit_inference_request(
        request: InferenceRequest,
        user_id: UUID,
    ) -> ImageSubmissionResponse:
        """
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
                    raise ValueError(f"Folder '{request.folder_name}' not found for user")

                # Extract filename from image data (use folder_name as fallback)
                filename = f"{request.folder_name}.png"

                # Get genus/species from folder metadata or use defaults
                # TODO: Extract from folder metadata, seed database, or image metadata
                genus = SeedService.normalize_taxonomic_name("unknown")
                species = SeedService.normalize_taxonomic_name("unknown")

                # Get user role IDs
                # TODO: Get actual role IDs from user/organization
                org_admin_role_id = get_cfia_admin_role_id()
                org_user_role_id = get_cfia_admin_role_id()  # TODO: Get actual user role

                # Convert imageDims from list [width, height] to dict format
                image_metadata = {
                    "width": request.imageDims[0],
                    "height": request.imageDims[1],
                }

                # Submit image for processing
                result = await ImageProcessingService.submit_image_for_processing(
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
                return await ImageProcessingService.get_processing_status(
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
