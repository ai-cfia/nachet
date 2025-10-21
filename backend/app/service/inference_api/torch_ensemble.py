"""
This file contains the function that requests the inference and processes the data from
the swin model.
"""

import json
from copy import deepcopy
from urllib.error import URLError
from urllib.request import Request, urlopen
from pydantic import ValidationError
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


class SwinModelAPIError(ModelAPIError):
    pass


SPECIES_LIST = [
    "ambrosia artemisiifolia",
    "ambrosia trifida",
    "ambrosia psilostachya",
]


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

        # Extract label and score from the classification result
        label = top_prediction.label
        score = top_prediction.score

        # Build topN predictions with cleaned labels using Pydantic model
        top_n_predictions = [
            TopNPredictionCleaned(
                label=pred.label,
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
            label=label,
            score=score,
            topN=top_n_predictions
        )
        enhanced_boxes.append(enhanced_box)

    # Return the enhanced result as Pydantic model
    return EnhancedClassificationResult(
        boxes=enhanced_boxes,
        filename="default_filename"
    )


async def request_inference_ensemble_a(
    model: ModelDispatchInfo,
    previous_result: ModelInferenceDetectorResult
) -> ModelInferenceClassifierResult:
    """
    Perform inference using the SWIN model on a list of cropped seed images.

    Takes the output from the seed detector (which includes cropped images and bounding boxes),
    classifies each cropped image, and merges the classification results back into the boxes.

    Args:
        model: The SWIN model configuration to use for inference.
        previous_result: The detection result from seed detector containing result and images.

    Returns:
        ModelInferenceClassifierResult: Dataclass containing enhanced detection boxes with
        classification labels, scores, and topN predictions.

    Raises:
        SwinModelAPIError: If an error occurs while processing the request.
    """
    try:
        print(f"Requesting inference from {model.name}")
        print(f"Endpoint: {model.endpoint}")

        # Get the validated detection response from previous step
        detection_response = previous_result.result

        # Perform classification on each cropped image
        classification_results = []
        for idx, img in enumerate(previous_result.images):
            headers = {
                "Content-Type": model.content_type,
                "Authorization": ("Bearer " + model.api_key),
                model.deployment_platform: model.name,
            }
            body = img

            print(f"Processing image {idx + 1}")
            req = Request(model.endpoint, body, headers, method="POST")
            response = urlopen(req)
            inf_result = response.read()
            inf_result_json = json.loads(inf_result.decode("utf8"))

            # Validate the SWIN API response
            validated_classification = SwinClassificationAPIResponse(inf_result_json)

            print(f"Result for image {idx + 1}: \n {json.dumps([p.model_dump() for p in validated_classification.predictions], indent=4)}")
            classification_results.append(validated_classification)

        print(f"Total classifications: {len(classification_results)}")  # TODO Transform into logging

        # Merge detection boxes with classification results
        enhanced_result = process_swin_result(detection_response, classification_results)

        # Return result with images for potential use in ensemble pipelines
        return ModelInferenceClassifierResult(
            result=enhanced_result,
            images=previous_result.images
        )

    except ValidationError as error:
        print(f"Pydantic validation error: {error}")
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
        print(error)
        raise SwinModelAPIError(
            f"An error occurred while processing the request:\n {str(error)}"
        ) from error


async def request_inference_ensemble_b(
    model: ModelDispatchInfo,
    previous_result: ModelInferenceClassifierResult
) -> ModelInferenceClassifierResult:
    """
    Perform secondary inference on images that match specific species in the species list.

    This function takes the initial classification results and performs additional
    classification using a different model for species that appear in the SPECIES_LIST.
    This allows for more accurate classification of specific species using specialized models.

    Args:
        model: The specialized model configuration to use for secondary inference.
        previous_result: The initial classification result containing enhanced boxes and images.

    Returns:
        ModelInferenceClassifierResult: Dataclass containing the enhanced result with amended
        labels for species in the species list, along with the images for potential further processing.

    Raises:
        SwinModelAPIError: If an error occurs while processing the request.
    """
    try:
        print(f"Requesting inference from {model.name}")
        print(f"Endpoint: {model.endpoint}")

        # Deep copy the result to avoid modifying the original
        amended_result = deepcopy(previous_result.result)

        # Ensure images are available
        if previous_result.images is None:
            raise SwinModelAPIError(
                "Images are required for ensemble_b but were not provided in previous_result"
            )

        # Process each box and re-classify if it matches the species list
        for idx, box in enumerate(amended_result.boxes):
            if box.label.lower().strip() in SPECIES_LIST:
                headers = {
                    "Content-Type": model.content_type,
                    "Authorization": ("Bearer " + model.api_key),
                    model.deployment_platform: model.name,
                }
                body = previous_result.images[idx]

                print(f"Box {idx + 1} matches species list: {box.label}")
                req = Request(model.endpoint, body, headers, method="POST")
                response = urlopen(req)
                inf_result = response.read()
                inf_result_json = json.loads(inf_result.decode("utf8"))

                # Validate the SWIN API response
                validated_classification = SwinClassificationAPIResponse(inf_result_json)

                print(f"Result for image {idx + 1}: \n {json.dumps([p.model_dump() for p in validated_classification.predictions], indent=4)}")

                # Get the top prediction
                top_prediction = validated_classification.predictions[0]

                # The older models return labels with leading numbers, so we need to adjust for that
                # detect and remove leading numbers if present
                corrected_label = top_prediction.label
                if top_prediction.label.split(" ")[0].isdigit():
                    corrected_label = " ".join(top_prediction.label.split(" ")[1:])

                # Build topN predictions with cleaned labels
                top_n_predictions = [
                    TopNPredictionCleaned(
                        label=" ".join(pred.label.split(" ")[1:]) if pred.label.split(" ")[0].isdigit() else pred.label,
                        score=pred.score
                    )
                    for pred in validated_classification.predictions
                ]

                # Update only the classification fields (label, score, topN), keep the same bounding box
                # Use model_copy to create a new instance with updated fields (Pydantic models are immutable)
                amended_result.boxes[idx] = box.model_copy(
                    update={
                        "label": corrected_label,
                        "score": top_prediction.score,
                        "topN": top_n_predictions
                    }
                )

        print(f"Amended result: {amended_result.model_dump_json(indent=4)}")  # TODO Transform into logging

        # Return wrapped in dataclass for consistency with other inference functions
        return ModelInferenceClassifierResult(
            result=amended_result,
            images=previous_result.images
        )

    except ValidationError as error:
        print(f"Pydantic validation error: {error}")
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
        print(error)
        raise SwinModelAPIError(
            f"An error occurred while processing the request:\n {str(error)}"
        ) from error
