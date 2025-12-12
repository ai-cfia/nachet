"""
This file contains the function that requests the inference and processes the data from
the SAM3 segmentation model using Triton v2 inference protocol.

SAM3 (Segment Anything Model 3) is a segmentation model that detects objects and optionally
returns segmentation masks. It supports optional text prompts for targeted detection.
"""

import io
import base64
import json
import requests
from pydantic import ValidationError

from PIL import Image
from .exceptions import ModelAPIError
from app.model.inference import (
    SeedDetectorAPIResponse,
    TritonDetectorResponse,
)
from . import ModelDispatchInfo, ModelInferenceDetectorResult


class Sam3SegmentationModelAPIError(ModelAPIError):
    pass


def process_image_slicing(
    image_bytes: str | bytes, detection_response: SeedDetectorAPIResponse
) -> list[bytes]:
    """
    Slices the original image into cropped images based on detected bounding boxes.

    Takes the validated API response with bounding boxes and creates individual
    cropped images for each detected object.

    Args:
        image_bytes: Base64 encoded original image (as string or bytes)
        detection_response: Validated Pydantic model containing detection boxes

    Returns:
        List of base64 encoded cropped images, one for each detected box
    """
    # Handle both str and bytes input
    if isinstance(image_bytes, str):
        image_data = base64.b64decode(image_bytes)
    else:
        image_data = base64.b64decode(image_bytes)

    # Decode the base64 image
    image_io_byte = io.BytesIO(image_data)
    image_io_byte.seek(0)
    image = Image.open(image_io_byte)

    format = image.format

    # Pre-allocate list for cropped images
    cropped_images = [bytes(0) for _ in detection_response.boxes]

    # Crop each detected box from the original image
    for i, detection_box in enumerate(detection_response.boxes):
        # Convert normalized coordinates to pixel coordinates
        topX = int(detection_box.box.topX * image.width)
        topY = int(detection_box.box.topY * image.height)
        bottomX = int(detection_box.box.bottomX * image.width)
        bottomY = int(detection_box.box.bottomY * image.height)

        # Crop the image using the bounding box
        img = image.crop((topX, topY, bottomX, bottomY))

        # Convert cropped image to base64
        buffered = io.BytesIO()
        img.save(buffered, format)
        cropped_images[i] = base64.b64encode(buffered.getvalue())

    return cropped_images


async def request_triton_sam3_segmentation(
    model: ModelDispatchInfo,
    previous_result: str,
    prompt: str | None = None,
    return_masks: bool = False,
) -> ModelInferenceDetectorResult:
    """
    Requests inference from the SAM3 segmentation model using Triton v2 inference protocol.

    Sends a base64-encoded image to a Triton inference server and receives bounding box
    predictions with optional segmentation masks. The response is wrapped in Triton v2
    protocol format.

    Args:
        model: The SAM3 model configuration (endpoint should be full Triton inference URL)
        previous_result: Base64 encoded image for inference
        prompt: Optional text prompt for targeted detection (e.g., "seed", "foreground object")
        return_masks: Whether to return PNG base64-encoded masks (~10-20 KB per mask)

    Returns:
        ModelInferenceDetectorResult: A dataclass containing:
            - result: SeedDetectorAPIResponse - Validated detection results with boxes,
              labels, scores, and optional mask metadata (compatible with classifiers)
            - images: list[bytes] - Base64 encoded cropped images for each detected box

    Raises:
        Sam3SegmentationModelAPIError: If an error occurs while processing the request
            or communicating with the Triton server.
    """
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    logger.debug(
        "Requesting SAM3 segmentation inference",
        model_name=model.name,
        endpoint=model.endpoint,
        image_size_b64=len(previous_result),
        prompt=prompt,
        return_masks=return_masks,
    )

    start_time = time.time()

    try:
        # Build inputs list dynamically based on provided parameters
        # IMAGE is always required
        inputs = [
            {
                "name": "IMAGE",
                "shape": [1, 1],  # [batch_size, 1] - batch dim required
                "datatype": "BYTES",
                "data": [previous_result],
            }
        ]

        # Add optional PROMPT input if provided
        if prompt is not None:
            inputs.append(
                {
                    "name": "PROMPT",
                    "shape": [1, 1],
                    "datatype": "BYTES",
                    "data": [prompt],
                }
            )

        # Add optional RETURN_MASKS input if True
        if return_masks:
            inputs.append(
                {
                    "name": "RETURN_MASKS",
                    "shape": [1, 1],
                    "datatype": "BOOL",
                    "data": [return_masks],
                }
            )

        request_data = {"inputs": inputs}

        headers = {
            "Content-Type": "application/json",
        }

        # Add authorization if API key is provided
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"

        # Log request details (excluding full base64 image)
        logger.debug(
            "Triton SAM3 API request",
            model_name=model.name,
            endpoint=model.endpoint,
            input_count=len(inputs),
            input_names=[inp["name"] for inp in inputs],
            image_data_length=len(previous_result),
        )

        api_call_start = time.time()
        response = requests.post(
            model.endpoint, headers=headers, json=request_data, timeout=120
        )
        response.raise_for_status()
        api_call_ms = (time.time() - api_call_start) * 1000

        # Parse and validate response using Pydantic model
        result_dict = response.json()

        # Log the raw Triton response for debugging
        logger.debug(
            "Triton SAM3 raw API response",
            model_name=model.name,
            response=result_dict,
        )

        # Validate the Triton v2 response structure
        triton_response = TritonDetectorResponse(**result_dict)

        # Extract detections from Triton wrapper (outputs[0].data[0] contains JSON string)
        detections_json = triton_response.outputs[0].data[0]
        validated_response = SeedDetectorAPIResponse(**json.loads(detections_json))

        logger.debug(
            "Triton SAM3 API response received",
            model_name=model.name,
            triton_model_name=triton_response.model_name,
            triton_model_version=triton_response.model_version,
            detected_boxes=len(validated_response.boxes),
            api_call_duration_ms=round(api_call_ms, 2),
        )

        # Create cropped images from detected boxes using Pydantic model
        slicing_start = time.time()
        cropped_images = process_image_slicing(previous_result, validated_response)
        slicing_ms = (time.time() - slicing_start) * 1000

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(
            "Triton SAM3 segmentation inference completed",
            model_name=model.name,
            triton_model_name=triton_response.model_name,
            triton_model_version=triton_response.model_version,
            detected_boxes=len(validated_response.boxes),
            cropped_images=len(cropped_images),
            slicing_duration_ms=round(slicing_ms, 2),
            total_duration_ms=round(elapsed_ms, 2),
        )

        # Return structured dataclass with Pydantic model
        # Uses ModelInferenceDetectorResult for compatibility with downstream classifiers
        return ModelInferenceDetectorResult(
            result=validated_response, images=cropped_images
        )
    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "SAM3 segmentation validation error",
            model_name=model.name,
            error=str(error),
            error_type="ValidationError",
            duration_ms=round(elapsed_ms, 2),
        )
        raise Sam3SegmentationModelAPIError(
            f"Invalid data structure from SAM3 API:\n {str(error)}"
        ) from error
    except requests.exceptions.RequestException as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Triton SAM3 HTTP error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise Sam3SegmentationModelAPIError(
            f"HTTP error while communicating with Triton server:\n {str(error)}"
        ) from error
    except (
        KeyError,
        TypeError,
        IndexError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "SAM3 segmentation processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise Sam3SegmentationModelAPIError(
            f"Error while processing inference results:\n {str(error)}"
        ) from error
