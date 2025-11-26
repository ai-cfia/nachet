"""
This file contains the function that requests the inference and processes the data from
the swin model.
"""

import json
from pydantic import ValidationError

from urllib.error import URLError
from urllib.request import Request, urlopen
from .exceptions import ModelAPIError
from app.model.inference import (
    SeedDetectorAPIResponse,
    SwinClassificationAPIResponse,
    EnhancedClassificationResult,
    ClassifiedBox,
    PredictionLabelScore,
    BoundingBoxAPI,
)
from . import (
    ModelDispatchInfo,
    ModelInferenceDetectorResult,
    ModelInferenceClassifierResult,
)


class SwinModelAPIError(ModelAPIError):
    pass


def correct_model_label(label: str) -> str:
    """
    Temporary shim to correct known spelling mistakes from ML models.

    TODO: Remove this once model API is fixed.

    Known corrections:
    - "Brassica junsea" → "Brassica juncea"

    Args:
        label: Raw label from ML model

    Returns:
        Corrected label
    """
    # Case-insensitive correction for known spelling mistakes
    if label.lower() == "brassica junsea":
        return "Brassica juncea"
    return label


def process_swin_result(
    detection_response: SeedDetectorAPIResponse,
    classification_results: list[SwinClassificationAPIResponse],
) -> EnhancedClassificationResult:
    """
    Process SWIN classification results and merge them with detection boxes.

    Takes the detection boxes from the seed detector and enriches them with
    classification labels, scores, and top-N predictions from the SWIN classifier.

    Args:
        detection_response: The validated detection results from seed detector.
        classification_results: List of validated SWIN classification results, one per detected box.

    Returns:
        EnhancedClassificationResult: Pydantic model containing enhanced detection boxes with
        classification data and filename.
    """
    # Create the enhanced result structure
    enhanced_boxes = []

    for detection_box, classification in zip(
        detection_response.boxes, classification_results
    ):
        # Get the top prediction (first in the list)
        top_prediction = classification.predictions[0]

        # Remove the index prefix from label if present (e.g., "0 Avena fatua" -> "Avena fatua")
        # Check if first part is a digit (index prefix) before removing it
        def clean_label(label: str) -> str:
            parts = label.split(" ", 1)  # Split only on first space
            if len(parts) > 1 and parts[0].isdigit():
                cleaned = parts[1]  # Remove numeric index prefix
            else:
                cleaned = label  # No index prefix, return as-is
            # Apply spelling corrections (temporary shim)
            return correct_model_label(cleaned)

        cleaned_label = clean_label(top_prediction.label)

        # Build topN predictions with cleaned labels using Pydantic model
        top_n_predictions = [
            PredictionLabelScore(label=clean_label(pred.label), score=pred.score)
            for pred in classification.predictions
        ]

        # Create enhanced box using Pydantic model
        enhanced_box = ClassifiedBox(
            box=BoundingBoxAPI(
                topX=detection_box.box.topX,
                topY=detection_box.box.topY,
                bottomX=detection_box.box.bottomX,
                bottomY=detection_box.box.bottomY,
            ),
            label=cleaned_label,
            score=top_prediction.score,
            topN=top_n_predictions,
        )
        enhanced_boxes.append(enhanced_box)

    # Return the enhanced result as Pydantic model
    return EnhancedClassificationResult(
        boxes=enhanced_boxes, filename="default_filename"
    )


async def request_inference_from_swin(
    model: ModelDispatchInfo, previous_result: ModelInferenceDetectorResult
) -> ModelInferenceClassifierResult:
    """
    Perform inference using the SWIN model on a list of cropped seed images.

    Takes the output from the seed detector (which includes cropped images and bounding boxes),
    classifies each cropped image, and merges the classification results back into the boxes.

    Args:
        model: The SWIN model configuration to use for inference.
        previous_result: The detection result from seed detector containing result_json and images.

    Returns:
        ModelInferenceClassifierResult: Dataclass containing enhanced detection boxes with
        classification labels, scores, and topN predictions.

    Raises:
        SwinModelAPIError: If an error occurs while processing the request.
    """
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    image_count = len(previous_result.images)

    logger.debug(
        "Requesting SWIN classification",
        model_name=model.name,
        endpoint=model.endpoint,
        image_count=image_count,
    )

    start_time = time.time()

    try:
        # Get the validated detection response from previous step
        detection_response = previous_result.result

        # Perform classification on each cropped image
        classification_results = []
        total_api_time_ms = 0

        for idx, img in enumerate(previous_result.images):
            headers = {
                "Content-Type": model.content_type,
                "Authorization": ("Bearer " + model.api_key),
                model.deployment_platform: model.name,
            }
            body = img

            # Log request details (excluding full base64 image)
            logger.debug(
                "SWIN API request",
                model_name=model.name,
                endpoint=model.endpoint,
                image_index=idx + 1,
                request_body_size=len(body),
            )

            req = Request(model.endpoint, body, headers, method="POST")
            # req = Request("http://192.168.x.x:12390/score", body, headers, method="POST")

            api_call_start = time.time()
            response = urlopen(req)
            result = response.read()
            api_call_ms = (time.time() - api_call_start) * 1000
            total_api_time_ms += api_call_ms

            result_list = json.loads(result.decode("utf8"))

            # Log the raw model response for debugging
            logger.debug(
                "SWIN raw API response",
                model_name=model.name,
                image_index=idx + 1,
                response=result_list,
            )

            # Validate the SWIN API response
            validated_classification = SwinClassificationAPIResponse(result_list)

            logger.debug(
                "SWIN classification result",
                model_name=model.name,
                image_index=idx + 1,
                predictions=len(validated_classification.predictions),
                api_call_duration_ms=round(api_call_ms, 2),
            )

            classification_results.append(validated_classification)

        logger.debug(
            "SWIN API calls completed",
            model_name=model.name,
            total_classifications=len(classification_results),
            total_api_time_ms=round(total_api_time_ms, 2),
            avg_per_image_ms=round(total_api_time_ms / image_count, 2)
            if image_count > 0
            else 0,
        )

        # Merge detection boxes with classification results
        merge_start = time.time()
        enhanced_result = process_swin_result(
            detection_response, classification_results
        )
        merge_ms = (time.time() - merge_start) * 1000

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(
            "SWIN classification completed",
            model_name=model.name,
            classified_boxes=len(enhanced_result.boxes),
            merge_duration_ms=round(merge_ms, 2),
            total_duration_ms=round(elapsed_ms, 2),
        )

        return ModelInferenceClassifierResult(result=enhanced_result)

    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "SWIN validation error",
            model_name=model.name,
            error=str(error),
            error_type="ValidationError",
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinModelAPIError(
            f"Invalid data structure from SWIN API:\n {str(error)}"
        ) from error
    except (
        TypeError,
        IndexError,
        AttributeError,
        URLError,
        json.JSONDecodeError,
    ) as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "SWIN processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinModelAPIError(
            f"An error occurred while processing the request:\n {str(error)}"
        ) from error
