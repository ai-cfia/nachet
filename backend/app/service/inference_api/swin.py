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
    TopNPredictionCleaned,
    BoundingBoxAPI
)
from . import (
    ModelDispatchInfo,
    ModelInferenceDetectorResult,
    ModelInferenceClassifierResult
)

class SwinModelAPIError(ModelAPIError) :
    pass

def process_swin_result(
    detection_response: SeedDetectorAPIResponse,
    classification_results: list[SwinClassificationAPIResponse]
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

    for detection_box, classification in zip(detection_response.boxes, classification_results):
        # Get the top prediction (first in the list)
        top_prediction = classification.predictions[0]

        # Remove the index prefix from label if present (e.g., "0 Avena fatua" -> "Avena fatua")
        # Check if first part is a digit (index prefix) before removing it
        def clean_label(label: str) -> str:
            parts = label.split(" ", 1)  # Split only on first space
            if len(parts) > 1 and parts[0].isdigit():
                return parts[1]  # Remove numeric index prefix
            return label  # No index prefix, return as-is

        cleaned_label = clean_label(top_prediction.label)

        # Build topN predictions with cleaned labels using Pydantic model
        top_n_predictions = [
            TopNPredictionCleaned(
                label=clean_label(pred.label),
                score=pred.score
            )
            for pred in classification.predictions
        ]

        # Create enhanced box using Pydantic model
        enhanced_box = ClassifiedBox(
            box=BoundingBoxAPI(
                topX=detection_box.box.topX,
                topY=detection_box.box.topY,
                bottomX=detection_box.box.bottomX,
                bottomY=detection_box.box.bottomY
            ),
            label=cleaned_label,
            score=top_prediction.score,
            topN=top_n_predictions
        )
        enhanced_boxes.append(enhanced_box)

    # Return the enhanced result as Pydantic model
    return EnhancedClassificationResult(
        boxes=enhanced_boxes,
        filename="default_filename"
    )


async def request_inference_from_swin(
    model: ModelDispatchInfo,
    previous_result: ModelInferenceDetectorResult
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
    try:
        # Get the validated detection response from previous step
        detection_response = previous_result.result

        # Perform classification on each cropped image
        classification_results = []
        for idx, img in enumerate(previous_result.images):
            headers = {
                "Content-Type": model.content_type,
                "Authorization": ("Bearer " + model.api_key),
                model.deployment_platform: model.name
            }
            body = img
            req = Request(model.endpoint, body, headers, method="POST")
            # req = Request("http://192.168.x.x:12390/score", body, headers, method="POST")
            response = urlopen(req)
            result = response.read()
            result_list = json.loads(result.decode("utf8"))

            # Validate the SWIN API response
            validated_classification = SwinClassificationAPIResponse(result_list)

            print(f"Result for image {idx + 1}: \n {json.dumps([p.model_dump() for p in validated_classification.predictions], indent=4)}")
            classification_results.append(validated_classification)

        print(f"Total classifications: {len(classification_results)}")  # TODO Transform into logging

        # Merge detection boxes with classification results
        enhanced_result = process_swin_result(detection_response, classification_results)
        # print(json.dumps(enhanced_result, indent=4))

        return ModelInferenceClassifierResult(result=enhanced_result)

    except ValidationError as error:
        print(f"Pydantic validation error: {error}")
        raise SwinModelAPIError(
            f"Invalid data structure from SWIN API:\n {str(error)}"
        ) from error
    except (TypeError, IndexError, AttributeError, URLError, json.JSONDecodeError) as error:
        print(error)
        raise SwinModelAPIError(f"An error occurred while processing the request:\n {str(error)}") from error
