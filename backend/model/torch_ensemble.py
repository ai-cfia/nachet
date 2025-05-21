"""
This file contains the function that requests the inference and processes the data from
the swin model.
"""

import json
from copy import deepcopy
from collections import namedtuple
from urllib.error import URLError
from urllib.request import Request, urlopen
from model.model_exceptions import ModelAPIError


class SwinModelAPIError(ModelAPIError):
    pass


SPECIES_LIST = [
    "012 Ambrosia artemisiifolia",
    "013 Ambrosia trifida",
    "014 Ambrosia psilostachya",
]


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

    img_box[0]["filename"] = "default_filename"

    return img_box


async def request_inference_ensemble_a(model: namedtuple, previous_result: "dict"):
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
        print(f"Requesting inference from {model.name}")
        print(f"Endpoint: {model.endpoint}")

        inf_results = []
        # img_count = len(previous_result.get("images"))
        for idx, img in enumerate(previous_result.get("images")):
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
            inf_results.append(inf_result_json)

        print(json.dumps(inf_results, indent=4))  # TODO Transform into logging

        return {
            "result_json": process_swin_result(
                previous_result.get("result_json"), inf_results
            ),
            "images": previous_result.get("images"),
        }
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


async def request_inference_ensemble_b(model: namedtuple, previous_result: "dict"):
    """
    Perform inference on images that are in the specified species list.
    """
    try:
        print(f"Requesting inference from {model.name}")
        print(f"Endpoint: {model.endpoint}")
        amended_result = deepcopy(previous_result.get("result_json"))

        for i, result in enumerate(previous_result.get("result_json")[0]["boxes"]):
            if result["label"] in SPECIES_LIST:
                headers = {
                    "Content-Type": model.content_type,
                    "Authorization": ("Bearer " + model.api_key),
                    model.deployment_platform: model.name,
                }
                body = previous_result.get("images")[i]
                req = Request(model.endpoint, body, headers, method="POST")
                response = urlopen(req)
                inf_result = response.read()
                inf_result_json = json.loads(inf_result.decode("utf8"))
                amended_result[0]["boxes"][i]["label"] = inf_result_json[0].get("label")
                amended_result[0]["boxes"][i]["score"] = inf_result_json[0].get("score")
                amended_result[0]["boxes"][i]["topN"] = [d for d in inf_result_json]

        print(json.dumps(amended_result, indent=4))  # TODO Transform into logging
        return amended_result
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
