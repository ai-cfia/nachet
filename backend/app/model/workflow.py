"""
Pydantic models for workflow status and management endpoints.

This module defines response models for DBOS workflow tracking,
including comprehensive status for image processing and inference workflows.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Dict, Any


class WorkflowAuthorization(BaseModel):
    """Authorization metadata for workflow access."""

    user_id: str
    is_owner: bool
    is_cfia_admin: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ParentWorkflowStatus(BaseModel):
    """Status information for parent (orchestrator) workflow."""

    workflow_id: str
    status: str
    progress_percentage: int | None = None
    created_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    error_message: str | None = None
    malware_detected: bool | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProcessingStages(BaseModel):
    """Processing pipeline stages completion status."""

    uploaded: bool
    defender_scanning: bool
    defender_scanned: bool
    sanitizing: bool
    sanitized: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProcessingTimestamps(BaseModel):
    """Timestamps for each processing stage."""

    uploaded_at: str | None = None
    defender_scan_started_at: str | None = None
    defender_scan_completed_at: str | None = None
    sanitization_started_at: str | None = None
    sanitization_completed_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class BlobUrls(BaseModel):
    """Blob storage URLs for original and sanitized images."""

    original: str | None = None
    sanitized: str | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProcessingWorkflowStatus(BaseModel):
    """Detailed status for image processing workflow."""

    status: str
    stages: ProcessingStages
    timestamps: ProcessingTimestamps
    defender_scan_result: str | None = None
    blob_urls: BlobUrls
    error_message: str | None = None
    error_details: str | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class InferenceWorkflowStatus(BaseModel):
    """Status information for ML inference workflow."""

    workflow_id: str
    status: str
    pipeline_id: str
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    error_message: str | None = None
    request_payload: Dict[str, Any] | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class WorkflowStatusResponse(BaseModel):
    """
    Comprehensive workflow status response.

    Returned by GET /workflow/{workflow_id}/status endpoint.
    Provides complete status tracking for image processing and inference workflows.

    The response includes:
    - Overall workflow status and type
    - Parent workflow orchestration status
    - Image processing pipeline details and timestamps
    - ML inference workflow status
    - Authorization metadata
    """

    workflow_id: str = Field(..., description="The queried workflow ID")
    workflow_type: str = Field(
        ..., description="Workflow type: 'parent', 'processing', or 'inference'"
    )
    image_id: str = Field(..., description="Associated picture UUID")
    overall_status: str = Field(
        ...,
        description="High-level status: 'pending', 'in_progress', 'completed', 'failed'",
    )
    authorization: WorkflowAuthorization = Field(
        ..., description="Authorization metadata"
    )

    # Optional workflow details (depend on workflow type and state)
    parent_workflow: ParentWorkflowStatus | None = Field(
        None, description="Parent workflow status (if exists)"
    )
    processing_workflow: ProcessingWorkflowStatus | None = Field(
        None, description="Processing workflow details (if exists)"
    )
    inference_workflow: InferenceWorkflowStatus | None = Field(
        None, description="Inference workflow details (if exists)"
    )

    # Error details (if failed)
    error_message: str | None = Field(None, description="Error message (if failed)")
    error_details: str | None = Field(
        None, description="Detailed error info (if failed)"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class WorkflowEventsResponse(BaseModel):
    """
    Workflow events response for DBOS event tracking.

    Returned by GET /test/dbos/workflow/{workflow_id}/events endpoint.
    Shows progress tracking events published by the workflow.
    """

    workflow_id: str = Field(..., description="Workflow UUID")
    events: Dict[str, Any] = Field(..., description="Event data published by workflow")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
