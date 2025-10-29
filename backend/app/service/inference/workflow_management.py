"""
Workflow Management Module

This module handles workflow status retrieval, cancellation, retry operations,
and progress calculation for image processing and inference workflows.
"""

from uuid import UUID
from datetime import datetime, timezone
from beartype.typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dbos import DBOS
from app.db.model import ImageProcessingState, InferenceRequestState
from app.db.utils import sessionmanager
from app.service.rbac import RbacService
from app.service.constants import ProcessingStatus
from app.exceptions import ImageProcessingError


async def get_workflow_status(
    workflow_id: str,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Get comprehensive workflow status with authorization check.

    Accepts any workflow_id (parent, processing child, or inference child)
    and returns status for all related workflows.

    Authorization: User must own the workflow OR be a CFIA admin.

    Args:
        workflow_id: DBOS workflow UUID (parent, processing, or inference)
        user_id: User requesting the status

    Returns:
        Dict containing:
        - workflow_id: The queried workflow ID
        - workflow_type: "parent"|"processing"|"inference"
        - image_id: Associated picture UUID
        - overall_status: High-level status
        - parent_workflow: Parent workflow details
        - processing_workflow: Processing child workflow details (if exists)
        - inference_workflow: Inference child workflow details (if exists)
        - authorization: Authorization metadata

    Raises:
        HTTPException: 404 if workflow not found, 403 if unauthorized
        ImageProcessingError: If query fails
    """
    from fastapi import HTTPException, status
    from app.service.logs import LogService

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Step 1: Find which state table contains this workflow_id
            # Check ImageProcessingState (parent workflow only)
            processing_result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.workflow_id == workflow_id
                )
            )
            processing_state = processing_result.scalar_one_or_none()

            # Check InferenceRequestState (inference child workflow)
            inference_result = await session.execute(
                select(InferenceRequestState).where(
                    InferenceRequestState.workflow_id == workflow_id
                )
            )
            inference_state = inference_result.scalar_one_or_none()

            # If not found in either table, return 404
            if not processing_state and not inference_state:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found",
                )

            # Step 2: Determine workflow type and get all related state records
            if inference_state:
                # Queried by inference workflow ID
                workflow_type = "inference"
                image_id = inference_state.picture_id
                auth_user_id = inference_state.user_id
                auth_org_admin_role_id = inference_state.org_admin_role_id

                # Get parent processing state using picture_id
                if not processing_state:
                    proc_result = await session.execute(
                        select(ImageProcessingState).where(
                            ImageProcessingState.picture_id == image_id
                        )
                    )
                    processing_state = proc_result.scalar_one_or_none()

            elif processing_state and processing_state.workflow_id == workflow_id:
                # Queried by parent workflow ID
                workflow_type = "parent"
                image_id = processing_state.picture_id
                auth_user_id = processing_state.user_id
                auth_org_admin_role_id = processing_state.org_admin_role_id

                # Get all inference states for this picture
                # Note: There can be multiple inference runs per image
                if not inference_state:
                    inf_result = await session.execute(
                        select(InferenceRequestState).where(
                            InferenceRequestState.picture_id == image_id
                        )
                    )
                    # Get all inference states, return the most recent one for now
                    inference_states = inf_result.scalars().all()
                    if inference_states:
                        # Sort by created_at descending, get most recent
                        inference_state = sorted(
                            inference_states,
                            key=lambda x: x.created_at,
                            reverse=True,
                        )[0]

            else:
                # Should not reach here - already checked that one of the states exists
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected state: no processing state found",
                )

            # Step 3: Authorization check
            user_org_roles = await RbacService.get_user_org_roles(user_id)
            is_owner = auth_user_id == user_id

            # TODO: Get CFIA admin role ID from config/env
            # For now, check if user's admin role matches the workflow's admin role
            is_cfia_admin = user_org_roles.org_admin_role_id == auth_org_admin_role_id

            if not (is_owner or is_cfia_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this workflow",
                )

            # Step 4: Build comprehensive status response
            response: dict[str, Any] = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "image_id": str(image_id),
                "authorization": {
                    "user_id": str(user_id),
                    "is_owner": is_owner,
                    "is_cfia_admin": is_cfia_admin,
                },
            }

            # Add parent/processing workflow status
            if processing_state:
                response["parent_workflow"] = {
                    "workflow_id": processing_state.workflow_id,
                    "status": processing_state.status,
                    "progress_percentage": processing_state.progress_percentage,
                    "created_at": (
                        processing_state.created_at.isoformat()
                        if processing_state.created_at
                        else None
                    ),
                    "completed_at": (
                        processing_state.completed_at.isoformat()
                        if processing_state.completed_at
                        else None
                    ),
                    "failed_at": (
                        processing_state.failed_at.isoformat()
                        if processing_state.failed_at
                        else None
                    ),
                    "error_message": processing_state.error_message,
                    "malware_detected": processing_state.malware_detected,
                }

                # Add processing stages
                response["processing_workflow"] = {
                    "status": processing_state.status,
                    "stages": {
                        "uploaded": processing_state.uploaded_at is not None,
                        "defender_scanning": processing_state.defender_scan_started_at
                        is not None,
                        "defender_scanned": processing_state.defender_scan_completed_at
                        is not None,
                        "sanitizing": processing_state.sanitization_started_at
                        is not None,
                        "sanitized": processing_state.sanitization_completed_at
                        is not None,
                    },
                    "timestamps": {
                        "uploaded_at": (
                            processing_state.uploaded_at.isoformat()
                            if processing_state.uploaded_at
                            else None
                        ),
                        "defender_scan_started_at": (
                            processing_state.defender_scan_started_at.isoformat()
                            if processing_state.defender_scan_started_at
                            else None
                        ),
                        "defender_scan_completed_at": (
                            processing_state.defender_scan_completed_at.isoformat()
                            if processing_state.defender_scan_completed_at
                            else None
                        ),
                        "sanitization_started_at": (
                            processing_state.sanitization_started_at.isoformat()
                            if processing_state.sanitization_started_at
                            else None
                        ),
                        "sanitization_completed_at": (
                            processing_state.sanitization_completed_at.isoformat()
                            if processing_state.sanitization_completed_at
                            else None
                        ),
                    },
                    "defender_scan_result": processing_state.defender_scan_result,
                    "blob_urls": {
                        "original": processing_state.blob_url_original,
                        "sanitized": processing_state.blob_url_sanitized,
                    },
                }

            # Add inference workflow status
            if inference_state:
                response["inference_workflow"] = {
                    "workflow_id": inference_state.workflow_id,
                    "status": inference_state.status,
                    "pipeline_id": str(inference_state.pipeline_id),
                    "created_at": (
                        inference_state.created_at.isoformat()
                        if inference_state.created_at
                        else None
                    ),
                    "started_at": (
                        inference_state.started_at.isoformat()
                        if inference_state.started_at
                        else None
                    ),
                    "completed_at": (
                        inference_state.completed_at.isoformat()
                        if inference_state.completed_at
                        else None
                    ),
                    "failed_at": (
                        inference_state.failed_at.isoformat()
                        if inference_state.failed_at
                        else None
                    ),
                    "error_message": inference_state.error_message,
                    "request_payload": inference_state.request_payload,
                }

            # Determine overall status
            if processing_state:
                if processing_state.status == "failed":
                    response["overall_status"] = "failed"
                elif processing_state.status == "completed" and (
                    not inference_state or inference_state.status == "completed"
                ):
                    response["overall_status"] = "completed"
                elif inference_state and inference_state.status == "failed":
                    response["overall_status"] = "failed"
                else:
                    response["overall_status"] = "in_progress"
            else:
                response["overall_status"] = (
                    inference_state.status if inference_state else "unknown"
                )

            logger.info(
                "Retrieved workflow status",
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                user_id=str(user_id),
                overall_status=response["overall_status"],
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get workflow status: {str(e)}",
            workflow_id=workflow_id,
            user_id=str(user_id),
        )
        raise ImageProcessingError(f"Failed to get workflow status: {str(e)}") from e


async def get_workflow_results(
    workflow_id: str,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Get formatted inference results for a completed workflow.

    Retrieves the Annotation record (stored with annotation_id == parent workflow_id)
    and formats it as ApiInferenceResponse for frontend consumption.

    Authorization: User must own the workflow OR be a CFIA admin.

    Args:
        workflow_id: Parent DBOS workflow UUID (from POST /inf response)
        user_id: User requesting the results

    Returns:
        Dict containing ApiInferenceResponse fields:
        - filename: Image filename
        - imageId: Image UUID
        - inference_id: Annotation UUID (equals workflow_id)
        - boxes: List of detected objects with classifications
        - labelOccurrence: Count of each label
        - totalBoxes: Total number of detected boxes
        - models: Model metadata used for inference

    Raises:
        HTTPException: 404 if results not found, 403 if unauthorized
        ImageProcessingError: If retrieval fails
    """
    from fastapi import HTTPException, status as http_status
    from app.service.logs import LogService
    from app.db.model import Annotation
    from app.model.inference import ApiInferenceResponse

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Step 1: Try to find Annotation by workflow_id
            # The annotation_id equals the parent workflow_id
            try:
                annotation_uuid = UUID(workflow_id)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid workflow_id format: {workflow_id}",
                )

            annotation_result = await session.execute(
                select(Annotation).where(Annotation.id == annotation_uuid)
            )
            annotation = annotation_result.scalar_one_or_none()

            if not annotation:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"No results found for workflow {workflow_id}. "
                    "Workflow may not be completed yet or results may not have been saved.",
                )

            # Step 2: Authorization check
            user_org_roles = await RbacService.get_user_org_roles(user_id)
            is_owner = annotation.user_id == user_id
            is_cfia_admin = (
                user_org_roles.org_admin_role_id == annotation.org_admin_role_id
            )

            if not (is_owner or is_cfia_admin):
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access these results",
                )

            # Step 3: Parse raw_data and return as ApiInferenceResponse
            # The raw_data field contains the full ApiInferenceResponse structure
            if not annotation.raw_data:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"No inference data found in annotation {workflow_id}",
                )

            # Validate and parse the raw_data as ApiInferenceResponse
            try:
                # raw_data is already a dict (stored as JSON in database)
                inference_response = ApiInferenceResponse(**annotation.raw_data)
            except Exception as e:
                logger.error(
                    f"Failed to parse annotation raw_data as ApiInferenceResponse: {str(e)}",
                    workflow_id=workflow_id,
                    annotation_id=str(annotation.id),
                )
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to parse inference results: {str(e)}",
                )

            logger.info(
                "Retrieved workflow results",
                workflow_id=workflow_id,
                annotation_id=str(annotation.id),
                user_id=str(user_id),
                total_boxes=inference_response.totalBoxes,
            )

            # Return as dict for FastAPI serialization
            return inference_response.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get workflow results: {str(e)}",
            workflow_id=workflow_id,
            user_id=str(user_id),
        )
        raise ImageProcessingError(f"Failed to get workflow results: {str(e)}") from e


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
                "sanitization": processing_state.sanitization_completed_at is not None,
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
