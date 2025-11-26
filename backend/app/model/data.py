"""
Pydantic models for data retrieval endpoints.

This module defines response models for core data endpoints that provide
reference data (pipelines, seeds, devices, directories, model metadata).
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic.alias_generators import to_camel
from typing import Dict, Any, List, Optional


class PipelineStep(BaseModel):
    """
    Individual model step in a pipeline.

    Represents a single ML model within a pipeline's execution sequence.
    """

    model_id: str = Field(..., description="UUID of the model")
    model_name: str = Field(..., description="Name of the model")
    version: str = Field(..., description="Model version")
    endpoint: str = Field(..., description="API endpoint URL")
    api_key: str = Field(..., description="API key for authentication")
    content_type: str = Field(..., description="Content type for requests")
    deployment_platform: str = Field(
        ..., description="Platform where model is deployed"
    )
    endpoint_name: str = Field(..., description="Endpoint identifier name")
    request_function: str = Field(..., description="Function used to make requests")
    step: int = Field(..., description="Step number in the pipeline sequence")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PipelineDetail(BaseModel):
    """
    Complete pipeline configuration with metadata and steps.

    Represents a single ML pipeline with all its models and metadata.
    """

    pipeline_id: str = Field(..., description="UUID of the pipeline")
    pipeline_name: str = Field(..., description="Pipeline name")
    created_by: Optional[str] = Field(None, description="Creator of the pipeline")
    creation_date: Optional[str] = Field(
        None, description="ISO formatted creation date"
    )
    description: Optional[str] = Field(None, description="Pipeline description")
    job_name: Optional[str] = Field(None, description="Job name for the pipeline")
    version: Optional[str] = Field(None, description="Pipeline version")
    dataset: Optional[str] = Field(None, description="Dataset used for training")
    identifiable: List[str] = Field(
        default_factory=list, description="List of identifiable classes"
    )
    metrics: List[Dict[str, Any]] = Field(
        default_factory=list, description="Performance metrics"
    )
    models: List[PipelineStep] = Field(
        ..., description="Ordered list of model steps in the pipeline"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PipelinesResponse(BaseModel):
    """
    Response model for GET /pipelines endpoint.

    Returns available ML pipelines for seed classification.
    """

    pipelines: List[PipelineDetail] = Field(
        ..., description="List of available pipeline configurations"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SeedItem(BaseModel):
    """
    Individual seed entry with taxonomic information.

    Represents a single seed species with identification metadata.
    """

    seed_id: str = Field(..., description="UUID of the seed")
    name_code: str = Field(..., description="Short code name for the seed")
    family: str = Field(..., description="Taxonomic family")
    genus: str = Field(..., description="Taxonomic genus")
    species: str = Field(..., description="Taxonomic species")
    subspecies: Optional[str] = Field(None, description="Taxonomic subspecies")
    variety: Optional[str] = Field(None, description="Taxonomic variety")
    synonyms: Optional[str] = Field(None, description="Taxonomic synonyms")
    author: Optional[str] = Field(None, description="Author citation")
    subspecies_author: Optional[str] = Field(
        None, description="Subspecies author citation"
    )
    variety_author: Optional[str] = Field(None, description="Variety author citation")
    url: Optional[str] = Field(None, description="Reference URL")
    seed_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional seed metadata"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SeedData(BaseModel):
    """Wrapper for seed data list."""

    seeds: List[SeedItem] = Field(..., description="List of seed species")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SeedDataResponse(RootModel[SeedData]):
    """
    Response model for GET /seeds endpoint.

    Returns seed species data for frontend selection.
    Uses RootModel wrapping SeedData for proper camelCase serialization.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DeviceModel(BaseModel):
    """Device model entry."""

    id: str = Field(..., description="UUID of the device model")
    name: str = Field(..., description="Model name")
    description: str = Field(..., description="Model description")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DeviceLens(BaseModel):
    """Device lens entry."""

    id: str = Field(..., description="UUID of the device lens")
    name: str = Field(..., description="Lens name")
    description: str = Field(..., description="Lens description")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DeviceBrand(BaseModel):
    """
    Device brand with associated models and lenses.

    Represents a manufacturer brand with its available models and lenses.
    """

    id: str = Field(..., description="UUID of the device brand")
    name: str = Field(..., description="Brand name")
    description: str = Field(..., description="Brand description")
    models: List[DeviceModel] = Field(..., description="List of models for this brand")
    lenses: List[DeviceLens] = Field(..., description="List of lenses for this brand")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DeviceData(BaseModel):
    """Wrapper for device data list."""

    devices: List[DeviceBrand] = Field(..., description="List of device brands")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DevicesResponse(RootModel[DeviceData]):
    """
    Response model for GET /devices endpoint.

    Returns device information (brands, models, lenses) for image metadata.
    Uses RootModel wrapping DeviceData for proper camelCase serialization.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DirectoryItem(BaseModel):
    """
    Individual directory/folder entry.

    Represents a user's folder with picture count and metadata.
    """

    id: str = Field(..., description="UUID of the directory")
    name: str = Field(..., description="Directory name")
    folder_prefix: str = Field(..., description="Organization prefix for the folder")
    description: str = Field(..., description="Directory description")
    picture_count: int = Field(..., description="Number of pictures in this directory")
    is_default_folder: bool = Field(
        ..., description="Whether this is the user's default folder"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DirectoryData(BaseModel):
    """Wrapper for directory data list."""

    directories: List[DirectoryItem] = Field(
        ..., description="List of user directories"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DirectoriesResponse(RootModel[DirectoryData]):
    """
    Response model for GET /get-directories endpoint.

    Returns user's directory/folder tree structure.
    Uses RootModel wrapping DirectoryData for proper camelCase serialization.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PipelineMetadata(BaseModel):
    """
    Model for individual pipeline metadata entry.

    Contains pipeline configuration, model information, and metadata.
    """

    created_by: str = Field(..., description="Creator of the pipeline")
    creation_date: str = Field(..., description="ISO formatted creation date")
    dataset: str = Field(..., description="Dataset used for training")
    description: str = Field(..., description="Pipeline description")
    identifiable: List[str] = Field(
        default_factory=list, description="List of identifiable classes"
    )
    job_name: str = Field(..., description="Job name for the pipeline")
    metrics: List[Dict[str, Any]] = Field(
        default_factory=list, description="Performance metrics"
    )
    model_name: str = Field(..., description="Model display name")
    models: List[str] = Field(..., description="List of model names in the pipeline")
    pipeline_name: str = Field(..., description="Pipeline name")
    pipeline_id: str = Field(..., description="Pipeline UUID")
    version: str = Field(..., description="Pipeline version")
    default: bool = Field(
        default=False, description="Whether this is the default pipeline"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ModelEndpointsMetadataResponse(RootModel[List[PipelineMetadata]]):
    """
    Response model for GET /model-endpoints-metadata endpoint.

    Returns ML model endpoint configuration metadata.
    Uses RootModel to return a list of PipelineMetadata objects.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )
