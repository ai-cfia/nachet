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


SPECIES_LIST = [
    "ambrosia artemisiifolia",
    "ambrosia trifida",
    "ambrosia psilostachya",
]


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

        # Extract label and score from the classification result
        # Apply spelling corrections (temporary shim)
        label = correct_model_label(top_prediction.label)
        score = top_prediction.score

        # Build topN predictions with cleaned labels using Pydantic model
        # Apply spelling corrections to all predictions (temporary shim)
        top_n_predictions = [
            PredictionLabelScore(
                label=correct_model_label(pred.label), score=pred.score
            )
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
            label=label,
            score=score,
            topN=top_n_predictions,
        )
        enhanced_boxes.append(enhanced_box)

    # Return the enhanced result as Pydantic model
    return EnhancedClassificationResult(
        boxes=enhanced_boxes, filename="default_filename"
    )


async def request_inference_ensemble_a(
    model: ModelDispatchInfo, previous_result: ModelInferenceDetectorResult
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
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    image_count = len(previous_result.images)

    logger.debug(
        "Requesting ensemble_a inference",
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
                "Ensemble_a API request",
                model_name=model.name,
                endpoint=model.endpoint,
                image_index=idx + 1,
                request_body_size=len(body),
            )

            api_call_start = time.time()
            req = Request(model.endpoint, body, headers, method="POST")
            response = urlopen(req)
            inf_result = response.read()
            api_call_ms = (time.time() - api_call_start) * 1000
            total_api_time_ms += api_call_ms

            inf_result_json = json.loads(inf_result.decode("utf8"))

            # Log the raw model response for debugging
            logger.debug(
                "Ensemble_a raw API response",
                model_name=model.name,
                image_index=idx + 1,
                response=inf_result_json,
            )

            # Validate the SWIN API response
            validated_classification = SwinClassificationAPIResponse(inf_result_json)

            logger.debug(
                "Ensemble_a classification result",
                model_name=model.name,
                image_index=idx + 1,
                predictions=len(validated_classification.predictions),
                api_call_duration_ms=round(api_call_ms, 2),
            )

            classification_results.append(validated_classification)

        logger.debug(
            "Ensemble_a API calls completed",
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
            "Ensemble_a inference completed",
            model_name=model.name,
            classified_boxes=len(enhanced_result.boxes),
            merge_duration_ms=round(merge_ms, 2),
            total_duration_ms=round(elapsed_ms, 2),
        )

        # Return result with images for potential use in ensemble pipelines
        return ModelInferenceClassifierResult(
            result=enhanced_result, images=previous_result.images
        )

    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Ensemble_a validation error",
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
            "Ensemble_a processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinModelAPIError(
            f"An error occurred while processing the request:\n {str(error)}"
        ) from error


async def request_inference_ensemble_b(
    model: ModelDispatchInfo, previous_result: ModelInferenceClassifierResult
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
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    total_boxes = len(previous_result.result.boxes)

    logger.debug(
        "Requesting ensemble_b inference",
        model_name=model.name,
        endpoint=model.endpoint,
        total_boxes=total_boxes,
    )

    start_time = time.time()

    try:
        # Deep copy the result to avoid modifying the original
        amended_result = deepcopy(previous_result.result)

        # Ensure images are available
        if previous_result.images is None:
            raise SwinModelAPIError(
                "Images are required for ensemble_b but were not provided in previous_result"
            )

        # Process each box and re-classify if it matches the species list
        matched_boxes = 0
        total_api_time_ms = 0

        for idx, box in enumerate(amended_result.boxes):
            if box.label.lower().strip() in SPECIES_LIST:
                matched_boxes += 1
                headers = {
                    "Content-Type": model.content_type,
                    "Authorization": ("Bearer " + model.api_key),
                    model.deployment_platform: model.name,
                }
                body = previous_result.images[idx]

                # Log request details (excluding full base64 image)
                logger.debug(
                    "Ensemble_b API request",
                    model_name=model.name,
                    endpoint=model.endpoint,
                    box_index=idx + 1,
                    original_label=box.label,
                    request_body_size=len(body),
                )

                api_call_start = time.time()
                req = Request(model.endpoint, body, headers, method="POST")
                response = urlopen(req)
                inf_result = response.read()
                api_call_ms = (time.time() - api_call_start) * 1000
                total_api_time_ms += api_call_ms

                inf_result_json = json.loads(inf_result.decode("utf8"))

                # Log the raw model response for debugging
                logger.debug(
                    "Ensemble_b raw API response",
                    model_name=model.name,
                    box_index=idx + 1,
                    response=inf_result_json,
                )

                # Validate the SWIN API response
                validated_classification = SwinClassificationAPIResponse(
                    inf_result_json
                )

                # Get the top prediction
                top_prediction = validated_classification.predictions[0]

                # The older models return labels with leading numbers, so we need to adjust for that
                # detect and remove leading numbers if present
                corrected_label = top_prediction.label
                if top_prediction.label.split(" ")[0].isdigit():
                    corrected_label = " ".join(top_prediction.label.split(" ")[1:])

                # Apply spelling corrections (temporary shim)
                corrected_label = correct_model_label(corrected_label)

                logger.debug(
                    "Ensemble_b reclassification result",
                    model_name=model.name,
                    box_index=idx + 1,
                    original_label=box.label,
                    new_label=corrected_label,
                    new_score=top_prediction.score,
                    api_call_duration_ms=round(api_call_ms, 2),
                )

                # Build topN predictions with cleaned labels
                # Apply spelling corrections to all predictions (temporary shim)
                top_n_predictions = [
                    PredictionLabelScore(
                        label=correct_model_label(
                            " ".join(pred.label.split(" ")[1:])
                            if pred.label.split(" ")[0].isdigit()
                            else pred.label
                        ),
                        score=pred.score,
                    )
                    for pred in validated_classification.predictions
                ]

                # Update only the classification fields (label, score, topN), keep the same bounding box
                # Use model_copy to create a new instance with updated fields (Pydantic models are immutable)
                amended_result.boxes[idx] = box.model_copy(
                    update={
                        "label": corrected_label,
                        "score": top_prediction.score,
                        "topN": top_n_predictions,
                    }
                )

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(
            "Ensemble_b inference completed",
            model_name=model.name,
            total_boxes=total_boxes,
            matched_boxes=matched_boxes,
            amended_boxes=matched_boxes,
            total_api_time_ms=round(total_api_time_ms, 2),
            avg_per_box_ms=round(total_api_time_ms / matched_boxes, 2)
            if matched_boxes > 0
            else 0,
            total_duration_ms=round(elapsed_ms, 2),
        )

        # Return wrapped in dataclass for consistency with other inference functions
        return ModelInferenceClassifierResult(
            result=amended_result, images=previous_result.images
        )

    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Ensemble_b validation error",
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
            "Ensemble_b processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinModelAPIError(
            f"An error occurred while processing the request:\n {str(error)}"
        ) from error
