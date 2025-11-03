"""
Pydantic models for data retrieval endpoints.

This module defines response models for core data endpoints that provide
reference data (pipelines, seeds, devices, directories, model metadata).
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic.alias_generators import to_camel
from typing import Dict, Any, List


class PipelinesResponse(BaseModel):
    """
    Response model for GET /pipelines endpoint.

    Returns available ML pipelines for seed classification.
    """

    pipelines: List[Dict[str, Any]] = Field(
        ..., description="List of available pipeline configurations"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SeedDataResponse(RootModel[Dict[str, Any]]):
    """
    Response model for GET /seeds endpoint.

    Returns seed species data for frontend selection.
    Uses RootModel since the response is a direct dict structure.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DevicesResponse(RootModel[Dict[str, Any]]):
    """
    Response model for GET /devices endpoint.

    Returns device information (brands, models, lenses) for image metadata.
    Uses RootModel since the response is a direct dict structure.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DirectoriesResponse(RootModel[Dict[str, Any]]):
    """
    Response model for GET /get-directories endpoint.

    Returns user's directory/folder tree structure.
    Uses RootModel since the response is a direct dict structure.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ModelEndpointsMetadataResponse(RootModel[Dict[str, Any]]):
    """
    Response model for GET /model-endpoints-metadata endpoint.

    Returns ML model endpoint configuration metadata.
    Uses RootModel since the response is a direct dict structure.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
