"""
Pydantic models for batch upload endpoints.

This module defines request/response models for the batch upload feature,
which allows users to upload multiple images in a session with consistent
folder organization and security scanning.
"""

import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from typing import Literal


class BatchUploadInitRequest(BaseModel):
    """
    Initialize batch upload session.

    The folder must exist before batch upload starts.
    Returns a session_id for subsequent upload requests.
    Sessions expire after 24 hours and support up to 1000 files.
    """

    folder_id: str = Field(..., description="UUID of existing folder")
    file_count: int = Field(
        ..., gt=0, le=1000, description="Number of files to upload (max 1000)"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("folder_id")
    @classmethod
    def validate_folder_id(cls, v: str) -> str:
        """Validate folder_id is a valid UUID format."""
        from uuid import UUID

        try:
            UUID(v)
        except ValueError:
            raise ValueError("folder_id must be a valid UUID")
        return v


class BatchUploadInitResponse(BaseModel):
    """
    Response from batch initialization.

    Session expires after 24 hours and accepts up to file_count uploads.
    """

    session_id: str = Field(..., description="UUID of created session")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class BatchUploadImageRequest(BaseModel):
    """
    Upload single image in batch.

    This request is submitted for each image in the batch session.
    The image goes through the full security pipeline (Defender scan + sanitization).
    Duplicate images (same SHA256 hash) are tracked but not saved.
    """

    # Session
    session_id: str = Field(..., description="Session UUID from /new-batch-import")

    # Seed identification
    seed_id: str = Field(..., description="UUID of existing seed record")

    # Sample metadata
    tray_code: Literal["A", "B", "C", "D", "E"]
    sample_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Becomes picture.name",
    )
    image_description: str = Field(
        ...,
        max_length=500,
        description="Description for the image",
    )

    # Device metadata
    device_brand_id: str  # UUID
    device_model_id: str  # UUID
    device_lens_id: str  # UUID
    magnification: float = Field(..., gt=0.1, lt=1000)

    # Image
    image: str = Field(..., description="Base64 data URL")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("sample_id")
    @classmethod
    def validate_sample_id(cls, v: str) -> str:
        """
        Validate sample_id: alphanumeric and hyphens only, cannot end with dash.

        Matches frontend normalizeSampleIdPrefix pattern.
        """
        if not v or not v.strip():
            raise ValueError("Sample ID cannot be empty")

        # Match frontend normalization pattern [a-zA-Z0-9-]
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError("Sample ID can only contain letters, numbers, and hyphens")

        # Match frontend validation: cannot end with dash
        if v.endswith("-"):
            raise ValueError("Sample ID cannot end with a hyphen")

        return v

    @field_validator("image_description")
    @classmethod
    def validate_image_description(cls, v: str) -> str:
        """
        Validate imageDescription: alphanumeric, periods, spaces only, max 500 chars.

        Matches InferenceRequest validation and frontend normalizeSampleDescription pattern.
        """
        if v:  # Only validate if non-empty (empty string allowed, auto-generated in service)
            # Check character set: only alphanumeric, periods, and spaces allowed
            if not re.match(r"^[a-zA-Z0-9. ]*$", v):
                raise ValueError(
                    "Image description can only contain letters, numbers, periods, and spaces"
                )

            if len(v) > 500:
                raise ValueError("Image description exceeds 500 characters")

        return v

    @field_validator(
        "session_id", "seed_id", "device_brand_id", "device_model_id", "device_lens_id"
    )
    @classmethod
    def validate_uuid_fields(cls, v: str) -> str:
        """Validate UUID format for ID fields."""
        from uuid import UUID

        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")
        return v


class BatchUploadImageResponse(BaseModel):
    """
    Response from image upload - ASYNC WORKFLOW PATTERN.

    The image is queued for processing in the background.
    Frontend must poll GET /workflow/{workflow_id}/status for completion.
    """

    success: bool
    picture_id: str | None = None
    workflow_id: str | None = Field(None, description="For status polling")
    error: str | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
