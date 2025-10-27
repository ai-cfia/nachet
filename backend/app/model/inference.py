"""
Pydantic models for image inference and processing endpoints.
"""

from pydantic import BaseModel, Field, RootModel, ConfigDict
from beartype.typing import Optional


class InferenceRequest(BaseModel):
    """
    Request model for POST /inf endpoint.

    Matches legacy API format for backwards compatibility.
    """

    pipeline_id: str
    folder_name: str
    folder_id: str  # UUID as string
    imageDims: list[int] = Field(
        description="Image dimensions as [width, height]", min_length=2, max_length=2
    )
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
    Single detection box from seed detector API response.
    """

    box: BoundingBoxAPI
    label: str = Field(description="Detected object label (e.g., 'seed')")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score for detection")


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


class TopNPredictionAPI(BaseModel):
    """
    A single prediction in the top-N classification results from SWIN API.
    """

    label: str = Field(description="Classification label (species name)")
    score: float = Field(
        ge=0.0, le=1.0, description="Confidence score for this classification"
    )


class SwinClassificationAPIResponse(RootModel[list[TopNPredictionAPI]]):
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
    def predictions(self) -> list[TopNPredictionAPI]:
        """Convenience property to access the root list."""
        return self.root


# ============================================================================
# Enhanced Classification Result Models (Post-Processing)
# ============================================================================


class TopNPredictionCleaned(BaseModel):
    """
    Top-N prediction with cleaned label (index prefix removed).
    """

    label: str = Field(description="Classification label without index prefix")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")


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
    topN: list[TopNPredictionCleaned] = Field(
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
    topN: list[TopNPredictionCleaned] = Field(description="Top-N predictions")
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
    topN: list[TopNPredictionCleaned] = Field(description="Top-N predictions")
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


class ApiInferenceResponse(BaseModel):
    """
    Complete inference response matching frontend ApiInferenceDataSchema.

    This is the format expected by the frontend for inference results.
    Used by /inf-direct endpoint.
    """

    filename: str
    imageId: str = Field(description="Image UUID or identifier")
    inference_id: str = Field(description="Inference UUID or identifier")
    boxes: list[ApiInferenceBox]
    labelOccurrence: dict[str, int] = Field(
        description="Count of each label found in the image"
    )
    totalBoxes: int = Field(description="Total number of detected boxes")
    models: list[ModelInfo] = Field(description="Models used for inference")
