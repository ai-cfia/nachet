"""
This file contains the function that requests the inference and processes the data from
the seed detector model.
"""

import io
import base64
import json
from urllib.error import URLError

from PIL import Image
from collections import namedtuple
from urllib.request import Request, urlopen
from model.model_exceptions import ModelAPIError

class SeedDetectorModelAPIError(ModelAPIError) :
    pass

def process_image_slicing(image_bytes: bytes, result_json: dict) -> list:
    """
    This function takes the image bytes and the result_json from the model and
    returns a list of cropped images.
    The result_json is expected to be in the following format:
    {
        "boxes": [
            {
                "box": {
                    "topX": 0.0,
                    "topY": 0.0,
                    "bottomX": 0.0,
                    "bottomY": 0.0
                },
                "label": "string",
                "score": 0.0
            }
        ],
    }
    """
    boxes = result_json[0]['boxes']
    image_io_byte = io.BytesIO(base64.b64decode(image_bytes))
    image_io_byte.seek(0)
    image = Image.open(image_io_byte)

    format = image.format

    cropped_images = [bytes(0) for _ in boxes]

    for i, box in enumerate(boxes):
        topX = int(box['box']['topX'] * image.width)
        topY = int(box['box']['topY'] * image.height)
        bottomX = int(box['box']['bottomX'] * image.width)
        bottomY = int(box['box']['bottomY'] * image.height)

        img = image.crop((topX, topY, bottomX, bottomY))

        buffered = io.BytesIO()
        img.save(buffered, format)

        cropped_images[i] = base64.b64encode(buffered.getvalue())

    return cropped_images


async def request_inference_from_seed_detector(model: namedtuple, previous_result: str):
    """
    Requests inference from the seed detector model using the previously provided result.

    Args:
        model (namedtuple): The seed detector model.
        previous_result (str): The previous result used for inference.

    Returns:
        dict: A dictionary containing the result JSON and the images generated from the inference.

    Raises:
        ProcessInferenceResultsError: If an error occurs while processing the request.
    """
    try:

        headers = {
            "Content-Type": model.content_type,
            "Authorization": ("Bearer " + model.api_key),
            model.deployment_platform: model.name
        }

        data = {
            "input_data": {
                "columns": ["image"],
                "index": [0],
                "data": [previous_result],
            }
        }

        body = str.encode(json.dumps(data))
        req = Request(model.endpoint, body, headers, method="POST")
        # req = Request("http://192.168.x.x:12380/score", body, headers, method="POST")
        response = urlopen(req)

        result = response.read()
        result_object = [json.loads(result.decode("utf8"))]  
        print(json.dumps(result_object[0].get("boxes"), indent=4)) #TODO Transform into logging

        return {
            "result_json": result_object,
            "images": process_image_slicing(previous_result, result_object)
        }
    except (KeyError, TypeError, IndexError, ValueError, URLError, json.JSONDecodeError)  as error:
        print(error)
        raise SeedDetectorModelAPIError(f"Error while processing inference results :\n {str(error)}") from error
