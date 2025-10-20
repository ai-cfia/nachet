"""
Pydantic models for image inference and processing endpoints.
"""

from pydantic import BaseModel
from typing import Optional


class InferenceRequest(BaseModel):
    """
    Request model for POST /inf endpoint.

    Matches legacy API format for backwards compatibility.
    """
    model_name: str
    folder_name: str
    imageDims: dict
    image: str  # base64 with data URL prefix
    area_ratio: float = 0.5
    color_format: str = "hex"


class ImageSubmissionResponse(BaseModel):
    """Response model for image submission to processing pipeline."""
    image_id: str
    workflow_id: str
    status: str
    message: str


class SanitizationCallbackRequest(BaseModel):
    """
    Request model for sanitization completion callback.

    Sent by Azure Function when image sanitization is complete.
    """
    image_id: str  # UUID as string
    status: str  # "success" or "failed"
    sanitized_blob_url: Optional[str] = None
    error: Optional[str] = None
