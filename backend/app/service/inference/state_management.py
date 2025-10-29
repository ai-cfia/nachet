"""
State Management Module

This module handles creation and management of database state records
for image processing and inference workflows.
"""

from uuid import UUID
from datetime import datetime
from beartype.typing import Optional

from app.db.model import ImageProcessingState, InferenceRequestState
from app.db.utils import sessionmanager
from app.service.constants import ProcessingStatus
from app.exceptions import ImageProcessingError


async def create_processing_state(
    picture_id: UUID,
    user_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    status: ProcessingStatus,
    created_at: datetime,
    progress_percentage: int = 0,
    workflow_id: Optional[str] = None,
) -> ImageProcessingState:
    """
    Create a new ImageProcessingState record with ownership tracking.

    Args:
        picture_id: UUID of the picture being processed
        user_id: User who initiated the workflow
        org_user_role_id: User's role in their organization
        org_admin_role_id: Admin role for cross-org access
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
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
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
