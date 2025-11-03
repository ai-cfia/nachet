"""
Pydantic models for system health and status endpoints.

This module defines response models for health checks, version info,
and system status endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class HealthResponse(BaseModel):
    """
    Response model for GET /health and GET /ready endpoints.

    Simple health check response indicating the service is operational.
    """

    status: str = Field(..., description="Health status (e.g., 'ok', 'ready')")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class VersionResponse(BaseModel):
    """
    Response model for GET /version endpoint.

    Returns the current API version.
    """

    version: str = Field(..., description="API version string")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class RateLimitTestResponse(BaseModel):
    """
    Response model for GET /rate-limit-test endpoint.

    Tests rate limiting functionality.
    """

    message: str = Field(..., description="Response message")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
