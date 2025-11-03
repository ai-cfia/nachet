"""
Pydantic models for user and authentication endpoints.

This module defines response models for user management and authentication status.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class UserIdResponse(BaseModel):
    """
    Response model for POST /get-user-id endpoint.

    Returns the authenticated user's ID.
    """

    user_id: str = Field(
        ..., description="User's unique identifier (OID from Azure AD)"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class RegistrationStatusResponse(BaseModel):
    """
    Response model for GET /is-registered endpoint.

    Checks if the user is registered in the system.
    """

    is_registered: bool = Field(
        ..., description="Whether the user is registered in the system"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
