"""
State Management Module

This module handles creation and management of database state records
for image processing and inference workflows.
"""

from typing import no_type_check, Any
from uuid import UUID
from datetime import datetime
from beartype.typing import Optional

from dbos import DBOS
from app.db.model import ImageProcessingState, InferenceRequestState
from app.db.utils import sessionmanager
from app.service.constants import ProcessingStatus
from app.exceptions import ImageProcessingError


async def create_processing_state(
    workflow_id: str,
    picture_id: UUID,
    user_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    status: ProcessingStatus,
    created_at: datetime,
    progress_percentage: int = 0,
) -> ImageProcessingState:
    """
    Create a new ImageProcessingState record with ownership tracking.

    Args:
        workflow_id: DBOS workflow ID for tracking (now required and primary key)
        picture_id: UUID of the picture being processed
        user_id: User who initiated the workflow
        org_user_role_id: User's role in their organization
        org_admin_role_id: Admin role for cross-org access
        status: Initial processing status
        created_at: Timestamp when processing state was created
        progress_percentage: Initial progress percentage (default 0)

    Returns:
        ImageProcessingState: Created processing state record

    Raises:
        ImageProcessingError: If creation fails
    """
    try:
        async with sessionmanager.get_session() as session:
            processing_state = ImageProcessingState(
                workflow_id=workflow_id,
                picture_id=picture_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                status=status,
                created_at=created_at,
                progress_percentage=progress_percentage,
            )
            session.add(processing_state)
            await session.commit()
            await session.refresh(processing_state)
            return processing_state
    except Exception as e:
        raise ImageProcessingError(
            f"Failed to create processing state: {str(e)}"
        ) from e


async def create_inference_request_state(
    picture_id: UUID,
    pipeline_id: UUID,
    user_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    workflow_id: str,
    request_payload: dict,
) -> InferenceRequestState:
    """
    Create a new InferenceRequestState record for inference workflow tracking.

    Args:
        picture_id: UUID of the picture being processed
        pipeline_id: UUID of the pipeline being used
        user_id: User who initiated the inference request
        org_user_role_id: User's role in their organization
        org_admin_role_id: Admin role for cross-org access
        workflow_id: DBOS workflow ID for tracking
        request_payload: Payload sent for inference request

    Returns:
        InferenceRequestState: Created inference request state record

    Raises:
        ImageProcessingError: If creation fails
    """
    try:
        async with sessionmanager.get_session() as session:
            inference_state = InferenceRequestState(
                picture_id=picture_id,
                pipeline_id=pipeline_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                workflow_id=workflow_id,
                request_payload=request_payload,
                status="pending",
            )
            session.add(inference_state)
            await session.commit()
            await session.refresh(inference_state)
            return inference_state
    except Exception as e:
        raise ImageProcessingError(
            f"Failed to create inference request state: {str(e)}"
        ) from e


# ============================================================================
# DBOS Step Functions for State Updates
# ============================================================================


@no_type_check
@DBOS.step()
async def update_processing_state_step(
    workflow_id: str,
    status: Optional[str] = None,
    uploaded_at: Optional[datetime] = None,
    defender_scan_started_at: Optional[datetime] = None,
    defender_scan_completed_at: Optional[datetime] = None,
    defender_scan_result: Optional[dict] = None,
    malware_detected: Optional[bool] = None,
    sanitization_started_at: Optional[datetime] = None,
    sanitization_completed_at: Optional[datetime] = None,
    blob_url_original: Optional[str] = None,
    blob_url_sanitized: Optional[str] = None,
    completed_at: Optional[datetime] = None,
    progress_percentage: Optional[int] = None,
) -> dict[str, Any]:
    """
    DBOS Step: Update ImageProcessingState record with new field values.

    This function updates only the provided fields, allowing for flexible
    partial updates throughout the workflow. It is idempotent and safe for
    DBOS replay.

    Args:
        workflow_id: DBOS workflow ID (primary key)
        status: Processing status (uploaded, defender_scanning, etc.)
        uploaded_at: Timestamp when upload completed
        defender_scan_started_at: Timestamp when defender scan started
        defender_scan_completed_at: Timestamp when defender scan completed
        defender_scan_result: Defender scan result JSON
        malware_detected: Whether malware was detected
        sanitization_started_at: Timestamp when sanitization started
        sanitization_completed_at: Timestamp when sanitization completed
        blob_url_original: URL to original blob
        blob_url_sanitized: URL to sanitized blob
        completed_at: Timestamp when processing completed
        progress_percentage: Current progress percentage (0-100)

    Returns:
        Dict with updated state fields

    Raises:
        ImageProcessingError: If update fails
    """
    from app.service.logs import LogService
    from sqlalchemy import select

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Query ImageProcessingState by workflow_id (primary key)
            stmt = select(ImageProcessingState).where(
                ImageProcessingState.workflow_id == workflow_id
            )
            result = await session.execute(stmt)
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                error_msg = (
                    f"ImageProcessingState not found for workflow_id {workflow_id}"
                )
                logger.error(error_msg)
                raise ImageProcessingError(error_msg)

            # Update only provided fields
            if status is not None:
                processing_state.status = status
            if uploaded_at is not None:
                processing_state.uploaded_at = uploaded_at
            if defender_scan_started_at is not None:
                processing_state.defender_scan_started_at = defender_scan_started_at
            if defender_scan_completed_at is not None:
                processing_state.defender_scan_completed_at = defender_scan_completed_at
            if defender_scan_result is not None:
                processing_state.defender_scan_result = defender_scan_result
            if malware_detected is not None:
                processing_state.malware_detected = malware_detected
            if sanitization_started_at is not None:
                processing_state.sanitization_started_at = sanitization_started_at
            if sanitization_completed_at is not None:
                processing_state.sanitization_completed_at = sanitization_completed_at
            if blob_url_original is not None:
                processing_state.blob_url_original = blob_url_original
            if blob_url_sanitized is not None:
                processing_state.blob_url_sanitized = blob_url_sanitized
            if completed_at is not None:
                processing_state.completed_at = completed_at
            if progress_percentage is not None:
                processing_state.progress_percentage = progress_percentage

            await session.commit()
            await session.refresh(processing_state)

            logger.debug(
                f"Updated ImageProcessingState (workflow_id={workflow_id}, status={status}, progress_percentage={progress_percentage})"
            )

            return {
                "workflow_id": workflow_id,
                "picture_id": str(processing_state.picture_id),
                "status": processing_state.status,
                "progress_percentage": processing_state.progress_percentage,
            }

    except Exception as e:
        logger.error(
            f"Failed to update processing state for workflow_id={workflow_id}: {str(e)} (error_type={type(e).__name__})"
        )
        # Don't crash the workflow - log and return empty dict
        return {"error": str(e)}


@no_type_check
@DBOS.step()
async def update_inference_state_step(
    inference_request_state_id: UUID,
    status: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    response_payload: Optional[dict] = None,
) -> dict[str, Any]:
    """
    DBOS Step: Update InferenceRequestState record with new field values.

    This function updates only the provided fields, allowing for flexible
    partial updates throughout the workflow. It is idempotent and safe for
    DBOS replay.

    Args:
        inference_request_state_id: UUID of the inference request state
        status: Inference status (pending, in_progress, completed, failed)
        started_at: Timestamp when inference started
        completed_at: Timestamp when inference completed
        response_payload: Response payload JSON

    Returns:
        Dict with updated state fields

    Raises:
        ImageProcessingError: If update fails
    """
    from app.service.logs import LogService
    from sqlalchemy import select

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Query InferenceRequestState by id
            stmt = select(InferenceRequestState).where(
                InferenceRequestState.id == inference_request_state_id
            )
            result = await session.execute(stmt)
            inference_state = result.scalar_one_or_none()

            if not inference_state:
                error_msg = f"InferenceRequestState not found for id {inference_request_state_id}"
                logger.error(error_msg)
                raise ImageProcessingError(error_msg)

            # Update only provided fields
            if status is not None:
                inference_state.status = status
            if started_at is not None:
                inference_state.started_at = started_at
            if completed_at is not None:
                inference_state.completed_at = completed_at
            if response_payload is not None:
                inference_state.response_payload = response_payload

            await session.commit()
            await session.refresh(inference_state)

            logger.debug(
                "Updated InferenceRequestState",
                inference_request_state_id=str(inference_request_state_id),
                status=status,
            )

            return {
                "inference_request_state_id": str(inference_state.id),
                "status": inference_state.status,
            }

    except Exception as e:
        logger.error(
            f"Failed to update inference state: {str(e)}",
            inference_request_state_id=str(inference_request_state_id),
            error_type=type(e).__name__,
        )
        # Don't crash the workflow - log and return empty dict
        return {"error": str(e)}


@no_type_check
@DBOS.step()
async def mark_processing_failed_step(
    workflow_id: str,
    error_message: str,
    error_details: Optional[dict] = None,
    malware_detected: Optional[bool] = None,
    defender_scan_result: Optional[dict] = None,
) -> dict[str, Any]:
    """
    DBOS Step: Mark ImageProcessingState as failed with error details.

    Args:
        workflow_id: DBOS workflow ID (primary key)
        error_message: Error message string
        error_details: Optional error details dict
        malware_detected: Optional flag indicating if malware was detected
        defender_scan_result: Optional Defender scan result dict

    Returns:
        Dict with updated state fields

    Raises:
        ImageProcessingError: If update fails
    """
    from app.service.logs import LogService
    from datetime import timezone
    from sqlalchemy import select

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Query ImageProcessingState by workflow_id (primary key)
            stmt = select(ImageProcessingState).where(
                ImageProcessingState.workflow_id == workflow_id
            )
            result = await session.execute(stmt)
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                error_msg = (
                    f"ImageProcessingState not found for workflow_id {workflow_id}"
                )
                logger.error(error_msg)
                raise ImageProcessingError(error_msg)

            # Mark as failed
            processing_state.status = "failed"
            processing_state.failed_at = datetime.now(timezone.utc)
            processing_state.error_message = error_message
            processing_state.error_details = error_details
            processing_state.progress_percentage = 0

            # Set malware-related fields if provided
            if malware_detected is not None:
                processing_state.malware_detected = malware_detected
            if defender_scan_result is not None:
                processing_state.defender_scan_result = defender_scan_result
                processing_state.defender_scan_completed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(processing_state)

            logger.error(
                f"Marked ImageProcessingState as failed (workflow_id={workflow_id}, error_message={error_message})"
            )

            return {
                "workflow_id": workflow_id,
                "picture_id": str(processing_state.picture_id),
                "status": "failed",
                "error_message": error_message,
            }

    except Exception as e:
        logger.error(
            f"Failed to mark processing state as failed for workflow_id={workflow_id}: {str(e)} (error_type={type(e).__name__})"
        )
        # Don't crash the workflow - log and return empty dict
        return {"error": str(e)}


@no_type_check
@DBOS.step()
async def mark_inference_failed_step(
    inference_request_state_id: UUID,
    error_message: str,
) -> dict[str, Any]:
    """
    DBOS Step: Mark InferenceRequestState as failed with error message.

    Args:
        inference_request_state_id: UUID of the inference request state
        error_message: Error message string

    Returns:
        Dict with updated state fields

    Raises:
        ImageProcessingError: If update fails
    """
    from app.service.logs import LogService
    from datetime import timezone
    from sqlalchemy import select

    logger = LogService.get_logger()

    try:
        async with sessionmanager.get_session() as session:
            # Query InferenceRequestState by id
            stmt = select(InferenceRequestState).where(
                InferenceRequestState.id == inference_request_state_id
            )
            result = await session.execute(stmt)
            inference_state = result.scalar_one_or_none()

            if not inference_state:
                error_msg = f"InferenceRequestState not found for id {inference_request_state_id}"
                logger.error(error_msg)
                raise ImageProcessingError(error_msg)

            # Mark as failed
            inference_state.status = "failed"
            inference_state.failed_at = datetime.now(timezone.utc)
            inference_state.error_message = error_message

            await session.commit()
            await session.refresh(inference_state)

            logger.error(
                "Marked InferenceRequestState as failed",
                inference_request_state_id=str(inference_request_state_id),
                error_message=error_message,
            )

            return {
                "inference_request_state_id": str(inference_state.id),
                "status": "failed",
                "error_message": error_message,
            }

    except Exception as e:
        logger.error(
            f"Failed to mark inference state as failed: {str(e)}",
            inference_request_state_id=str(inference_request_state_id),
            error_type=type(e).__name__,
        )
        # Don't crash the workflow - log and return empty dict
        return {"error": str(e)}
