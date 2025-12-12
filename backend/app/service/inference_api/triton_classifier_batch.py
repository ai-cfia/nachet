"""
Batch Triton classifier that sends up to 6 image classification requests in parallel.

This module provides parallel inference using the SWIN model via Triton v2 protocol,
improving throughput by processing multiple images concurrently.
"""

import asyncio
import json
import time

import httpx
from pydantic import ValidationError

from .exceptions import ModelAPIError
from .triton_classifier import process_swin_result
from app.model.inference import (
    SwinClassificationAPIResponse,
    TritonInferenceInput,
    TritonInferenceRequest,
    TritonInferenceResponse,
    ParsedPredictions,
)
from . import (
    ModelDispatchInfo,
    ModelInferenceDetectorResult,
    ModelInferenceClassifierResult,
)

MAX_CONCURRENT_REQUESTS = 6


class SwinBatchModelAPIError(ModelAPIError):
    pass


async def classify_single_image(
    client: httpx.AsyncClient,
    model: ModelDispatchInfo,
    img_b64: str,
    idx: int,
    semaphore: asyncio.Semaphore,
    logger,
) -> tuple[int, SwinClassificationAPIResponse, float]:
    """
    Classify a single image with concurrency limiting.

    Args:
        client: Shared httpx async client for connection pooling.
        model: Model configuration with endpoint and API key.
        img_b64: Base64 encoded image string.
        idx: Image index for ordering results.
        semaphore: Semaphore to limit concurrent requests.
        logger: Logger instance for structured logging.

    Returns:
        Tuple of (index, validated classification response, api call duration in ms).

    Raises:
        httpx.HTTPStatusError: If the HTTP request fails.
        ValidationError: If the response doesn't match expected schema.
    """
    async with semaphore:
        # Create Triton v2 inference request using Pydantic model
        request_data = TritonInferenceRequest(
            inputs=[
                TritonInferenceInput(
                    name="IMAGE", shape=[1, 1], datatype="BYTES", data=[img_b64]
                )
            ]
        )

        headers = {
            "Content-Type": "application/json",
        }

        # Add authorization if API key is provided
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"

        logger.debug(
            "Triton SWIN batch API request",
            model_name=model.name,
            endpoint=model.endpoint,
            image_index=idx + 1,
            input_name=request_data.inputs[0].name,
            input_shape=request_data.inputs[0].shape,
            image_data_length=len(img_b64),
        )

        api_call_start = time.time()
        response = await client.post(
            model.endpoint,
            headers=headers,
            json=request_data.model_dump(),
            timeout=30.0,
        )
        response.raise_for_status()
        api_call_ms = (time.time() - api_call_start) * 1000

        result_dict = response.json()

        logger.debug(
            "Triton SWIN batch raw API response",
            model_name=model.name,
            image_index=idx + 1,
            response=result_dict,
        )

        # Validate the Triton v2 response structure
        triton_response = TritonInferenceResponse(**result_dict)

        # Extract predictions from Triton wrapper (outputs[0].data[0] contains JSON string)
        predictions_json = triton_response.outputs[0].data[0]
        parsed_predictions = ParsedPredictions(predictions=json.loads(predictions_json))

        # Extract first batch to get list[PredictionLabelScore]
        predictions_list = parsed_predictions.predictions[0]

        # Create SwinClassificationAPIResponse from the predictions list
        validated_classification = SwinClassificationAPIResponse(predictions_list)

        logger.debug(
            "Triton SWIN batch classification result",
            model_name=model.name,
            image_index=idx + 1,
            predictions=len(validated_classification.predictions),
            api_call_duration_ms=round(api_call_ms, 2),
        )

        return (idx, validated_classification, api_call_ms)


async def request_triton_classifier_batch(
    model: ModelDispatchInfo, previous_result: ModelInferenceDetectorResult
) -> ModelInferenceClassifierResult:
    """
    Perform parallel inference using the SWIN model on cropped seed images via Triton v2 protocol.

    Sends up to 6 classification requests in parallel for improved throughput.
    Takes the output from the seed detector (which includes cropped images and bounding boxes),
    classifies each cropped image using a Triton inference server, and merges the classification
    results back into the boxes.

    Args:
        model: The SWIN model configuration to use for inference.
        previous_result: The detection result from seed detector containing result and images.

    Returns:
        ModelInferenceClassifierResult: Dataclass containing enhanced detection boxes with
        classification labels, scores, and topN predictions.

    Raises:
        SwinBatchModelAPIError: If an error occurs while processing the request or communicating
                                with the Triton server.
    """
    from app.service.logs import LogService

    logger = LogService.get_logger()

    image_count = len(previous_result.images)

    logger.debug(
        "Requesting Triton SWIN batch classification",
        model_name=model.name,
        endpoint=model.endpoint,
        image_count=image_count,
        max_concurrent=MAX_CONCURRENT_REQUESTS,
    )

    start_time = time.time()

    try:
        # Get the validated detection response from previous step
        detection_response = previous_result.result

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        # Prepare images as base64 strings
        images_b64 = [
            img.decode("utf-8") if isinstance(img, bytes) else img
            for img in previous_result.images
        ]

        # Execute all classification requests in parallel (limited by semaphore)
        async with httpx.AsyncClient() as client:
            tasks = [
                classify_single_image(client, model, img_b64, idx, semaphore, logger)
                for idx, img_b64 in enumerate(images_b64)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for exceptions and collect results in order
        classification_results: list[SwinClassificationAPIResponse] = [
            None
        ] * image_count  # type: ignore
        total_api_time_ms = 0.0

        for result in results:
            if isinstance(result, BaseException):
                # Re-raise the first exception encountered
                raise result
            # At this point, result is guaranteed to be a tuple
            result_tuple: tuple[int, SwinClassificationAPIResponse, float] = result
            idx, classification, api_call_ms = result_tuple
            classification_results[idx] = classification
            total_api_time_ms += api_call_ms

        logger.debug(
            "Triton SWIN batch API calls completed",
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
            "Triton SWIN batch classification completed",
            model_name=model.name,
            classified_boxes=len(enhanced_result.boxes),
            merge_duration_ms=round(merge_ms, 2),
            total_duration_ms=round(elapsed_ms, 2),
        )

        return ModelInferenceClassifierResult(result=enhanced_result)

    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Triton SWIN batch validation error",
            model_name=model.name,
            error=str(error),
            error_type="ValidationError",
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinBatchModelAPIError(
            f"Invalid data structure from Triton SWIN API:\n {str(error)}"
        ) from error
    except httpx.HTTPStatusError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Triton SWIN batch HTTP error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinBatchModelAPIError(
            f"HTTP error while communicating with Triton server:\n {str(error)}"
        ) from error
    except httpx.RequestError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Triton SWIN batch request error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinBatchModelAPIError(
            f"Request error while communicating with Triton server:\n {str(error)}"
        ) from error
    except (
        TypeError,
        IndexError,
        AttributeError,
        json.JSONDecodeError,
    ) as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Triton SWIN batch processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SwinBatchModelAPIError(
            f"An error occurred while processing Triton SWIN batch request:\n {str(error)}"
        ) from error
