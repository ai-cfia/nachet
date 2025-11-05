"""
This file contains the function that requests the inference and processes the data from
the seed detector model.
"""

import io
import base64
import json
from urllib.error import URLError
from pydantic import ValidationError

from PIL import Image
from urllib.request import Request, urlopen
from .exceptions import ModelAPIError
from app.model.inference import SeedDetectorAPIRequest, SeedDetectorAPIResponse
from . import ModelDispatchInfo, ModelInferenceDetectorResult


class SeedDetectorModelAPIError(ModelAPIError):
    pass


def process_image_slicing(
    image_bytes: str | bytes, detection_response: SeedDetectorAPIResponse
) -> list[bytes]:
    """
    Slices the original image into cropped images based on detected bounding boxes.

    Takes the validated API response with bounding boxes and creates individual
    cropped images for each detected seed.

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


async def request_inference_from_seed_detector(
    model: ModelDispatchInfo, previous_result: str
) -> ModelInferenceDetectorResult:
    """
    Requests inference from the seed detector model using the previously provided result.

    Args:
        model: The seed detector model configuration
        previous_result: The previous result used for inference (base64 encoded image).

    Returns:
        ModelInferenceDetectorResult: A dataclass containing:
            - result: SeedDetectorAPIResponse - Validated detection results with boxes, labels, and scores
            - images: list[bytes] - Base64 encoded cropped images for each detected box

    Raises:
        SeedDetectorModelAPIError: If an error occurs while processing the request.
    """
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    logger.debug(
        "Requesting seed detector inference",
        model_name=model.name,
        endpoint=model.endpoint,
        image_size_b64=len(previous_result),
    )

    start_time = time.time()

    try:
        # Create and validate request using Pydantic model
        from app.model.inference import AzureMLInputData

        request_data = SeedDetectorAPIRequest(
            input_data=AzureMLInputData(
                columns=["image"],
                index=[0],
                data=[previous_result],
            )
        )

        headers = {
            "Content-Type": model.content_type,
            "Authorization": ("Bearer " + model.api_key),
            model.deployment_platform: model.name,
        }

        # Serialize request to JSON
        body = str.encode(request_data.model_dump_json())
        req = Request(model.endpoint, body, headers, method="POST")
        # req = Request("http://192.168.x.x:12380/score", body, headers, method="POST")

        api_call_start = time.time()
        response = urlopen(req)
        api_call_ms = (time.time() - api_call_start) * 1000

        # Parse and validate response using Pydantic model
        result = response.read()
        result_dict = json.loads(result.decode("utf8"))

        # Validate the API response structure
        validated_response = SeedDetectorAPIResponse(**result_dict)

        logger.debug(
            "Seed detector API response received",
            model_name=model.name,
            detected_boxes=len(validated_response.boxes),
            api_call_duration_ms=round(api_call_ms, 2),
        )

        # Create cropped images from detected boxes using Pydantic model
        slicing_start = time.time()
        cropped_images = process_image_slicing(previous_result, validated_response)
        slicing_ms = (time.time() - slicing_start) * 1000

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(
            "Seed detector inference completed",
            model_name=model.name,
            detected_boxes=len(validated_response.boxes),
            cropped_images=len(cropped_images),
            slicing_duration_ms=round(slicing_ms, 2),
            total_duration_ms=round(elapsed_ms, 2),
        )

        # Return structured dataclass with Pydantic model
        return ModelInferenceDetectorResult(
            result=validated_response, images=cropped_images
        )
    except ValidationError as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Seed detector validation error",
            model_name=model.name,
            error=str(error),
            error_type="ValidationError",
            duration_ms=round(elapsed_ms, 2),
        )
        raise SeedDetectorModelAPIError(
            f"Invalid data structure from seed detector API:\n {str(error)}"
        ) from error
    except (
        KeyError,
        TypeError,
        IndexError,
        ValueError,
        URLError,
        json.JSONDecodeError,
    ) as error:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Seed detector processing error",
            model_name=model.name,
            error=str(error),
            error_type=type(error).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise SeedDetectorModelAPIError(
            f"Error while processing inference results:\n {str(error)}"
        ) from error
