"""
This file contains the function that requests the inference and processes the data from
the swin model.
"""

import json
from collections import namedtuple
from urllib.error import URLError
from urllib.request import Request, urlopen
from model.model_exceptions import ModelAPIError


class SwinModelAPIError(ModelAPIError):
    pass


def process_swin_result(img_box: dict, results: dict) -> list:
    """
    Args:
        img_box (dict): The image box containing the bounding boxes and labels.
        results (dict): The results from the model containing the detected seeds.

    Returns:
        list: The updated image box with modified labels and scores.
    """
    for i, result in enumerate(results):
        img_box[0]["boxes"][i]["label"] = result[0].get("label")
        img_box[0]["boxes"][i]["score"] = result[0].get("score")
        img_box[0]["boxes"][i]["topN"] = [d for d in result]

    # Adding the "filename" field (mandatory)
    img_box[0]["filename"] = "default_filename"

    return img_box


async def request_inference_from_torch_swin(model: namedtuple, previous_result: "dict"):
    """
    Perform inference using the SWIN model on a list of images.

    Args:
        model (namedtuple): The SWIN model to use for inference.
        previous_result (dict): The previous result containing the images to perform inference on.

    Returns:
        The result of the inference.

    Raises:
        ProcessInferenceResultsError: If an error occurs while processing the request.
    """
    try:
        results = []
        for img in previous_result.get("images"):
            headers = {
                "Content-Type": model.content_type,
                "Authorization": ("Bearer " + model.api_key),
                model.deployment_platform: model.name,
            }
            body = img
            req = Request(model.endpoint, body, headers, method="POST")
            response = urlopen(req)
            result = response.read()
            result_json = json.loads(result.decode("utf8"))
            results.append(result_json)

        print(json.dumps(results, indent=4))  # TODO Transform into logging

        return process_swin_result(previous_result.get("result_json"), results)
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
