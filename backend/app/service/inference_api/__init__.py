from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.model.inference import SeedDetectorAPIResponse, EnhancedClassificationResult


@dataclass
class ModelDispatchInfo:
    """
    Generic configuration for inference model endpoints.

    This dataclass is used across all model types (seed detector, SWIN, six seeds,
    torch ensemble, etc.) to provide a consistent interface for model endpoint configuration.

    Attributes:
        content_type: Content type for the HTTP request (e.g., "application/json")
        api_key: API key for authorization
        deployment_platform: Platform identifier (e.g., "azureml-model-deployment")
        name: Model name/identifier
        endpoint: Full URL of the model endpoint
    """

    content_type: str
    api_key: str
    deployment_platform: str
    name: str
    endpoint: str
    request_function: str


@dataclass
class ModelInferenceDetectorResult:
    """
    Structure for the result returned by the seed detector model.

    Attributes:
        result: The validated detection result from the API containing boxes with labels and scores.
        images: List of base64 encoded cropped images generated from the detected boxes.
    """

    result: "SeedDetectorAPIResponse"
    images: list[bytes]


@dataclass
class ModelInferenceClassifierResult:
    """
    Structure for the result returned by classification models (e.g., SWIN, six seeds).

    Contains enhanced detection boxes with classification labels, scores, and top-N predictions.

    Attributes:
        result: Validated enhanced classification result containing boxes and filename.
        images: Optional list of base64 encoded cropped images (needed for ensemble pipelines).
    """

    result: "EnhancedClassificationResult"
    images: list[bytes] | None = None


# Import after dataclass definitions to avoid circular imports
# ruff: noqa: E402
from .swin import request_inference_from_swin
from .seed_detector import request_inference_from_seed_detector
from .test import request_inference_from_test
from .inference import (
    process_enhanced_classification_result as process_enhanced_classification_result,
    process_api_ready_classification_result as process_api_ready_classification_result,
)
# from .torch_swin import request_inference_from_torch_swin
from .torch_ensemble import (
    request_inference_ensemble_a,
    request_inference_ensemble_b,
)


class InferenceDispatchService:
    @staticmethod
    def dispatch(model: dict[str, str], previous_result: str):
        # Convert dict to ModelDispatchInfo dataclass for type safety
        model_info = ModelDispatchInfo(
            content_type=model["content_type"],
            api_key=model["api_key"],
            deployment_platform=model["deployment_platform"],
            name=model["name"],
            endpoint=model["endpoint"],
            request_function=model["request_function"],
        )
        
        match model["request_function"]:
            case "rcnn_seed_detector":
                return request_inference_from_seed_detector(model_info, previous_result)
            case "swin_classifier":
                return request_inference_from_swin(model_info, previous_result)
            case "ensemble_a":
                return request_inference_ensemble_a(model_info, previous_result)
            case "ensemble_b":
                return request_inference_ensemble_b(model_info, previous_result)
            case "request_inference_from_test":
                return request_inference_from_test(model_info, previous_result)
            # case "request_inference_from_torch_swin":
            #     return request_inference_from_torch_swin(model_info, previous_result)
            case _:
                raise ValueError(
                    f"Unknown request function: {model['request_function']}"
                )
