"""
Pydantic models for logging endpoints.

This module defines request models for frontend log submission,
ensuring structured data and preventing abuse through validation.
"""

import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from typing import Literal, Optional


class FrontendLogRequest(BaseModel):
    """
    Request model for frontend log submission.

    Frontend sends error logs to backend for centralized logging.
    All fields are validated to prevent abuse (e.g., extremely long strings).
    """

    level: Literal["ERROR", "WARNING", "INFO"] = Field(
        default="ERROR", description="Log level"
    )
    message: str = Field(..., max_length=1000, description="Log message")
    error_type: Optional[str] = Field(
        None, max_length=200, description="Error type or name"
    )
    stack_trace: Optional[str] = Field(
        None, max_length=5000, description="Stack trace for errors"
    )
    url: Optional[str] = Field(
        None, max_length=500, description="URL where error occurred"
    )
    correlation_id: Optional[str] = Field(
        None, max_length=100, description="Correlation ID for request tracing"
    )
    session_id: Optional[str] = Field(
        None, max_length=100, description="Frontend session ID"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("message", "error_type", "url", "stack_trace")
    @classmethod
    def sanitize_log_fields(cls, v: Optional[str]) -> Optional[str]:
        """
        Sanitize log fields by removing control characters.

        Control characters (null bytes, etc.) can cause issues in log systems.
        We remove them while preserving newlines in stack traces.
        """
        if v is None:
            return v

        # Remove null bytes and other problematic control characters
        # Keep newlines (\n, 0x0A) and tabs (\t, 0x09) for readability
        sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", v)

        return sanitized


class LogSubmissionResponse(BaseModel):
    """
    Response model for frontend log submission.

    Confirms that the log was received and processed.
    """

    status: str = Field(
        ..., description="Processing status (e.g., 'success', 'logged')"
    )
    message: Optional[str] = Field(None, description="Optional response message")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
