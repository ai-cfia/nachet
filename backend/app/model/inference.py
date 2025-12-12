"""
Pydantic models for image inference and processing endpoints.
"""

import re
from enum import Enum
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from beartype.typing import Optional
from uuid import UUID


class TrayCode(str, Enum):
    """Valid tray codes for sample identification."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class PredictionLabelScore(BaseModel):
    """
    Universal prediction model for all inference results.

    Represents a single prediction with a label (species name) and confidence score.
    Used across all model types: SWIN classifiers, Triton inference, and ensemble models.

    Consolidates TopNPredictionAPI, TopNPredictionCleaned, and SeedPrediction.
    """

    label: str = Field(description="Classification label or species name")
    score: float = Field(
        ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )


class InferenceRequest(BaseModel):
    """
    Request model for POST /inf endpoint.

    Matches legacy API format for backwards compatibility.
    Includes required image metadata fields sent by frontend.
    """

    pipeline_id: str
    folder_name: str
    folder_id: str  # UUID as string
    image_dims: list[int] = Field(
        ...,
        description="Image dimensions as [width, height]",
        min_length=2,
        max_length=2,
    )
    image: str  # base64 with data URL prefix
    area_ratio: float = 0.5
    color_format: str = "hex"

    # Required image metadata fields (from frontend ImageMetadata)
    image_name: str = Field(
        ...,
        description="Human-readable name for the image",
        max_length=100,
    )
    image_description: str = Field(
        ...,
        description="Description or notes about the image",
        max_length=500,
    )
    device_model_id: UUID = Field(
        ...,
        description="UUID of the device model used to capture the image",
    )
    device_lens_id: UUID = Field(
        ...,
        description="UUID of the lens used to capture the image",
    )
    tray_code: TrayCode = Field(
        ..., description="Sample tray identification code (A-E only)"
    )
    magnification: float = Field(
        ..., description="Magnification level used when capturing the image"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_validator("image_name")
    @classmethod
    def validate_image_name(cls, v: str) -> str:
        """
        Validate imageName: alphanumeric and hyphens only, max 100 chars.

        Matches frontend SampleMetadataFields normalization pattern.
        """
        if not v or not v.strip():
            raise ValueError("Image name cannot be empty")

        # Check character set: only alphanumeric and hyphens allowed
        if not re.match(r"^[a-zA-Z0-9-]+$", v):
            raise ValueError(
                "Image name can only contain letters, numbers, and hyphens"
            )

        if len(v) > 100:
            raise ValueError("Image name exceeds 100 characters")

        return v

    @field_validator("image_description")
    @classmethod
    def validate_image_description(cls, v: str) -> str:
        """
        Validate imageDescription: alphanumeric, periods, spaces only, max 500 chars.

        Matches frontend SampleMetadataFields normalization pattern.
        """
        # Description can be empty, so only validate if non-empty
        if v:
            # Check character set: only alphanumeric, periods, and spaces allowed
            if not re.match(r"^[a-zA-Z0-9. ]*$", v):
                raise ValueError(
                    "Image description can only contain letters, numbers, periods, and spaces"
                )

            if len(v) > 500:
                raise ValueError("Image description exceeds 500 characters")

        return v


class ImageSubmissionResponse(BaseModel):
    """Response model for image submission to processing pipeline."""

    image_id: str
    workflow_id: str
    status: str
    message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class SanitizationCallbackRequest(BaseModel):
    """
    Request model for sanitization completion callback.

    Sent by Azure Function when image sanitization is complete.
    """

    image_id: str  # UUID as string
    status: str  # "success" or "failed"
    sanitized_blob_url: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# ML Model API Request/Response Models
# ============================================================================


class AzureMLInputData(BaseModel):
    """
    Input data structure for Azure ML endpoints.

    This is the standard Azure ML input format used across all model types.
    """

    columns: list[str] = Field(
        default=["image"], description="Column names for the input data"
    )
    index: list[int] = Field(default=[0], description="Index values for the input data")
    data: list[str] = Field(description="Base64 encoded image data")


class SeedDetectorAPIRequest(BaseModel):
    """
    Request model for seed detector model API.

    Used to send base64 encoded images to the Azure ML seed detector endpoint.
    """

    input_data: AzureMLInputData

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input_data": {
                    "columns": ["image"],
                    "index": [0],
                    "data": ["base64_encoded_image_string"],
                }
            }
        }
    )


class BoundingBoxAPI(BaseModel):
    """
    Bounding box coordinates from seed detector API response.

    Coordinates are normalized (0.0 to 1.0) relative to image dimensions.
    """

    topX: float = Field(
        ge=0.0, le=1.0, description="Top-left X coordinate (normalized)"
    )
    topY: float = Field(
        ge=0.0, le=1.0, description="Top-left Y coordinate (normalized)"
    )
    bottomX: float = Field(
        ge=0.0, le=1.0, description="Bottom-right X coordinate (normalized)"
    )
    bottomY: float = Field(
        ge=0.0, le=1.0, description="Bottom-right Y coordinate (normalized)"
    )


class DetectionBoxAPI(BaseModel):
    """
    Single detection box from detector API response.

    Supports both regular seed detectors and SAM3 segmentation.
    Mask fields are optional and populated only by SAM3 segmentation model.
    """

    box: BoundingBoxAPI
    label: str = Field(description="Detected object label (e.g., 'seed')")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score for detection")

    # Optional SAM3 mask fields (None for regular detectors)
    mask_available: Optional[bool] = Field(
        default=None,
        description="Indicates if segmentation mask exists (SAM3 only)",
    )
    mask_id: Optional[int] = Field(
        default=None,
        ge=0,
        description="Mask index for retrieval (SAM3 only)",
    )
    mask: Optional[str] = Field(
        default=None,
        description="Base64-encoded PNG mask data (SAM3 with RETURN_MASKS=true)",
    )


class SeedDetectorAPIResponse(BaseModel):
    """
    Response model from seed detector API.

    Returns a list of detected bounding boxes with labels and confidence scores.
    """

    boxes: list[DetectionBoxAPI]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "boxes": [
                    {
                        "box": {
                            "topX": 0.1,
                            "topY": 0.2,
                            "bottomX": 0.3,
                            "bottomY": 0.4,
                        },
                        "label": "seed",
                        "score": 0.95,
                    }
                ]
            }
        }
    )


class SwinClassificationAPIResponse(RootModel[list[PredictionLabelScore]]):
    """
    Response model from SWIN classifier API for a single image.

    Returns a list of top-N predictions for the classified seed.
    The API returns this as a direct list where each prediction
    contains the label (with index prefix like "0 Species Name") and score.

    Example response from API:
    [
        {"label": "0 Avena fatua", "score": 0.87},
        {"label": "1 Avena sativa", "score": 0.10}
    ]
    """

    @property
    def predictions(self) -> list[PredictionLabelScore]:
        """Convenience property to access the root list."""
        return self.root


# ============================================================================
# Enhanced Classification Result Models (Post-Processing)
# ============================================================================


class ClassifiedBox(BaseModel):
    """
    Detection box enhanced with classification results.

    Combines the original bounding box from detection with the
    classification label, score, and top-N predictions from SWIN.
    """

    box: BoundingBoxAPI
    label: str = Field(description="Primary classification label (cleaned)")
    score: float = Field(
        ge=0.0, le=1.0, description="Confidence score for primary classification"
    )
    topN: list[PredictionLabelScore] = Field(
        description="Top-N classification predictions"
    )


class PixelBoundingBox(BaseModel):
    """
    Bounding box coordinates in pixel values.

    Used after converting from normalized coordinates (0.0-1.0)
    to absolute pixel positions.
    """

    topX: int = Field(description="Top-left X coordinate (pixels)")
    topY: int = Field(description="Top-left Y coordinate (pixels)")
    bottomX: int = Field(description="Bottom-right X coordinate (pixels)")
    bottomY: int = Field(description="Bottom-right Y coordinate (pixels)")


class ProcessedClassifiedBox(BaseModel):
    """
    Classified box with additional processing information.

    Extends ClassifiedBox with overlapping detection, color assignment,
    and pixel coordinates (converted from normalized coordinates).
    """

    box: PixelBoundingBox  # Coordinates in pixel values
    label: str = Field(description="Primary classification label")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    topN: list[PredictionLabelScore] = Field(description="Top-N predictions")
    overlapping: bool = Field(description="Whether this box overlaps with others")
    overlappingIndices: list[int] = Field(
        description="Indices of boxes that overlap with this one"
    )
    color: str = Field(description="Assigned color for visualization (hex or rgb)")


class ProcessedInferenceResult(BaseModel):
    """
    Complete processed inference result with all post-processing applied.

    This includes overlapping detection, color assignment, pixel coordinate conversion,
    and summary statistics.
    """

    boxes: list[ProcessedClassifiedBox]
    labelOccurrence: dict[str, int] = Field(
        description="Count of each label in the results"
    )
    totalBoxes: int = Field(description="Total number of boxes")
    filename: str = Field(description="Image filename")


class EnhancedClassificationResult(BaseModel):
    """
    Complete classification result with enhanced detection boxes.

    This is the final output structure after merging detection boxes
    with classification results from the SWIN model.
    """

    boxes: list[ClassifiedBox]
    filename: str = Field(default="default_filename")


class ApiReadyInferenceResult(BaseModel):
    """
    API-ready inference result with normalized coordinates.

    Similar to ProcessedInferenceResult but maintains normalized coordinates (0.0-1.0)
    for API responses. Includes overlapping detection, colors, and summary statistics.
    Uses ApiInferenceBox to match frontend schema exactly.
    """

    boxes: list["ApiInferenceBox"]
    labelOccurrence: dict[str, int] = Field(
        description="Count of each label in the results"
    )
    totalBoxes: int = Field(description="Total number of boxes")
    filename: str = Field(description="Image filename")


# ============================================================================
# API Response Models for Frontend Compatibility
# ============================================================================


class ModelInfo(BaseModel):
    """Model information for API response."""

    name: str
    version: str


class ApiInferenceBox(BaseModel):
    """
    Inference box matching frontend InferenceBoxApiSchema.

    This is the exact format expected by the frontend for each box in the inference results.
    Includes all required fields for frontend visualization and interaction.

    Note: Frontend expects PIXEL coordinates, not normalized coordinates!
    """

    box: PixelBoundingBox  # Frontend expects pixel coordinates for rendering
    label: str = Field(description="Primary classification label")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    topN: list[PredictionLabelScore] = Field(description="Top-N predictions")
    classId: str = Field(description="Unique identifier for this classification")
    object_type_id: str = Field(description="Type identifier for the detected object")
    box_id: str = Field(description="Unique identifier for this bounding box")
    overlapping: bool = Field(description="Whether this box overlaps with others")
    overlappingIndices: int = Field(
        description="Index of overlapping box (if any), -1 if none"
    )
    is_verified: bool = Field(
        default=False, description="Whether this box has been verified by user"
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ApiInferenceResponse(BaseModel):
    """
    Complete inference response matching frontend ApiInferenceDataSchema.

    This is the format expected by the frontend for inference results.
    Used by /inf-direct endpoint.
    """

    filename: str
    image_id: str = Field(..., description="Image UUID or identifier")
    inference_id: str = Field(..., description="Inference UUID or identifier")
    boxes: list[ApiInferenceBox]
    label_occurrence: dict[str, int] = Field(
        ..., description="Count of each label found in the image"
    )
    total_boxes: int = Field(..., description="Total number of detected boxes")
    models: list[ModelInfo] = Field(..., description="Models used for inference")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


# ============================================================================
# Request Models (Triton v2 Inference Protocol)
# ============================================================================


class TritonInferenceInput(BaseModel):
    """
    Single input tensor for Triton inference request.

    For the 27spp model, this represents the IMAGE input containing
    base64-encoded image data.
    """

    name: str = Field(
        ...,
        description="Name of the input tensor. Must be 'IMAGE' for the 27spp model.",
    )
    shape: list[int] = Field(
        ..., description="Shape of the input tensor. For single image: [1, 1]"
    )
    datatype: str = Field(
        ...,
        description="Data type of the input. Must be 'BYTES' for base64-encoded images.",
    )
    data: list[str] = Field(
        ..., description="Array containing base64-encoded image data"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v != "IMAGE":
            raise ValueError("Input name must be 'IMAGE'")
        return v

    @field_validator("datatype")
    @classmethod
    def validate_datatype(cls, v: str) -> str:
        if v.upper() != "BYTES":
            raise ValueError("Datatype must be 'BYTES' for image data")
        return v.upper()


class TritonInferenceRequest(BaseModel):
    """
    Triton v2 inference request for the 27spp seed classification model.

    Example:
        {
            "inputs": [
                {
                    "name": "IMAGE",
                    "shape": [1, 1],
                    "datatype": "BYTES",
                    "data": ["<base64-encoded-image>"]
                }
            ]
        }
    """

    inputs: list[TritonInferenceInput] = Field(
        ..., description="Array of input tensors (single IMAGE input for 27spp model)"
    )

    @field_validator("inputs")
    @classmethod
    def validate_single_input(
        cls, v: list[TritonInferenceInput]
    ) -> list[TritonInferenceInput]:
        if len(v) != 1:
            raise ValueError("27spp model expects exactly one input (IMAGE)")
        return v


# ============================================================================
# Response Models (Triton v2 Inference Protocol)
# ============================================================================


class TritonInferenceOutput(BaseModel):
    """
    Single output tensor from Triton inference response.

    For the 27spp model, this represents the PREDICTIONS output containing
    JSON-encoded top-5 predictions.
    """

    name: str = Field(
        ..., description="Name of the output tensor. 'PREDICTIONS' for 27spp model."
    )
    shape: list[int] = Field(
        ..., description="Shape of the output tensor. [1] for single prediction result."
    )
    datatype: str = Field(
        ..., description="Data type of the output. 'BYTES' for JSON string."
    )
    data: list[str] = Field(
        ..., description="Array containing JSON-encoded prediction results"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v != "PREDICTIONS":
            raise ValueError("Output name must be 'PREDICTIONS'")
        return v


class TritonInferenceResponse(BaseModel):
    """
    Triton v2 inference response for the 27spp seed classification model.

    Example:
        {
            "outputs": [
                {
                    "name": "PREDICTIONS",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ["[[{\"label\": \"000 Brassica napus\", \"score\": 0.9234}, ...]]"]
                }
            ]
        }
    """

    outputs: list[TritonInferenceOutput] = Field(
        ...,
        description="Array of output tensors (single PREDICTIONS output for 27spp model)",
    )

    @field_validator("outputs")
    @classmethod
    def validate_single_output(
        cls, v: list[TritonInferenceOutput]
    ) -> list[TritonInferenceOutput]:
        if len(v) != 1:
            raise ValueError("27spp model returns exactly one output (PREDICTIONS)")
        return v


class ParsedPredictions(BaseModel):
    """
    Parsed prediction results from the model output.

    This is the result after parsing the JSON string from the PREDICTIONS output.
    Contains a batch of predictions, where each batch item has top-5 predictions.

    Example:
        {
            "predictions": [
                [
                    {"label": "000 Brassica napus", "score": 0.9234},
                    {"label": "001 Brassica junsea", "score": 0.0456},
                    {"label": "002 Cirsium arvense", "score": 0.0123},
                    {"label": "003 Solanum nigrum", "score": 0.0089},
                    {"label": "004 Ambrosia artemisiifolia", "score": 0.0067}
                ]
            ]
        }
    """

    predictions: list[list[PredictionLabelScore]] = Field(
        ...,
        description="Batch of predictions. Each batch item contains top-5 seed predictions.",
    )

    @field_validator("predictions")
    @classmethod
    def validate_predictions(
        cls, v: list[list[PredictionLabelScore]]
    ) -> list[list[PredictionLabelScore]]:
        for batch_idx, batch in enumerate(v):
            if len(batch) != 5:
                raise ValueError(
                    f"Batch {batch_idx}: Expected exactly 5 predictions (top-5), got {len(batch)}"
                )
        return v


# ============================================================================
# Detector Models (Triton v2 Inference Protocol)
# ============================================================================


class TritonDetectorOutput(BaseModel):
    """
    Single output tensor from Triton detector inference response.

    For the seed-detector-rcnn model, this represents the DETECTIONS output
    containing JSON-encoded bounding box predictions.

    Example:
        {
            "name": "DETECTIONS",
            "shape": [1],
            "datatype": "BYTES",
            "data": ["{\"boxes\": [...]}"]
        }
    """

    name: str = Field(
        ..., description="Name of the output tensor. 'DETECTIONS' for detector models."
    )
    shape: list[int] = Field(
        ..., description="Shape of the output tensor. [1] for single detection result."
    )
    datatype: str = Field(
        ..., description="Data type of the output. 'BYTES' for JSON string."
    )
    data: list[str] = Field(
        ..., description="Array containing JSON-encoded detection results"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v != "DETECTIONS":
            raise ValueError("Output name must be 'DETECTIONS' for detector models")
        return v

    @field_validator("datatype")
    @classmethod
    def validate_datatype(cls, v: str) -> str:
        if v.upper() != "BYTES":
            raise ValueError("Datatype must be 'BYTES' for detection data")
        return v.upper()


class TritonDetectorResponse(BaseModel):
    """
    Triton v2 inference response for seed detector models.

    Includes model metadata and detection outputs in Triton protocol format.

    Example:
        {
            "model_name": "seed-detector-rcnn",
            "model_version": "1",
            "outputs": [
                {
                    "name": "DETECTIONS",
                    "shape": [1],
                    "datatype": "BYTES",
                    "data": ["{\"boxes\": [{\"box\": {...}, \"label\": \"Seed\", \"score\": 0.99}]}"]
                }
            ]
        }
    """

    model_name: str = Field(..., description="Name of the detector model")
    model_version: str = Field(..., description="Version of the detector model")
    outputs: list[TritonDetectorOutput] = Field(
        ..., description="Array of output tensors (single DETECTIONS output)"
    )

    @field_validator("outputs")
    @classmethod
    def validate_single_output(
        cls, v: list[TritonDetectorOutput]
    ) -> list[TritonDetectorOutput]:
        if len(v) != 1:
            raise ValueError("Detector model returns exactly one output (DETECTIONS)")
        return v


# ============================================================================
# Helper Models for Application Integration
# ============================================================================


class ModelEndpoint(BaseModel):
    """
    Configuration for connecting to the Triton model endpoint.
    """

    base_url: str = Field(
        ...,
        description="Base URL of the Triton server (e.g., 'http://localhost:28000')",
    )
    model_name: str = Field(
        default="27spp_model_1", description="Name of the model to use for inference"
    )
    timeout_seconds: int = Field(
        default=30, ge=1, description="Request timeout in seconds"
    )

    @property
    def inference_url(self) -> str:
        """Get the full inference endpoint URL."""
        return f"{self.base_url}/v2/models/{self.model_name}/infer"

    @property
    def health_url(self) -> str:
        """Get the health check endpoint URL."""
        return f"{self.base_url}/v2/health/ready"

    @property
    def metadata_url(self) -> str:
        """Get the model metadata endpoint URL."""
        return f"{self.base_url}/v2/models/{self.model_name}"


# ============================================================================
# Example Usage
# ============================================================================

# if __name__ == "__main__":
#     import json

#     # Example: Create an inference request
#     request = TritonInferenceRequest(
#         inputs=[
#             TritonInferenceInput(
#                 name="IMAGE",
#                 shape=[1, 1],
#                 datatype="BYTES",
#                 data=["<base64-encoded-image-here>"],
#             )
#         ]
#     )
#     print("Request:")
#     print(request.model_dump_json(indent=2))
#     print()

#     # Example: Parse an inference response
#     response_json = {
#         "outputs": [
#             {
#                 "name": "PREDICTIONS",
#                 "shape": [1],
#                 "datatype": "BYTES",
#                 "data": [
#                     json.dumps(
#                         [
#                             [
#                                 {"label": "000 Brassica napus", "score": 0.9234},
#                                 {"label": "001 Brassica junsea", "score": 0.0456},
#                                 {"label": "002 Cirsium arvense", "score": 0.0123},
#                                 {"label": "003 Solanum nigrum", "score": 0.0089},
#                                 {
#                                     "label": "004 Ambrosia artemisiifolia",
#                                     "score": 0.0067,
#                                 },
#                             ]
#                         ]
#                     )
#                 ],
#             }
#         ]
#     }

#     response = TritonInferenceResponse(**response_json)
#     print("Response:")
#     print(response.model_dump_json(indent=2))
#     print()

#     # Parse the predictions from the response
#     predictions_json = json.loads(response.outputs[0].data[0])
#     parsed = ParsedPredictions(predictions=predictions_json)
#     print("Parsed Predictions:")
#     print(parsed.model_dump_json(indent=2))
#     print()

#     # Show top prediction
#     top_pred = parsed.predictions[0][0]
#     print(f"Top prediction: {top_pred.label} ({top_pred.score:.2%} confidence)")
