"""
This file contains the function that requests the inference and processes the data from
the nachet-6seeds model.
"""

import json
from collections import namedtuple
from urllib.error import URLError
from urllib.request import Request, urlopen
from model.model_exceptions import ModelAPIError

class SixSeedModelAPIError(ModelAPIError) :
    pass

async def request_inference_from_nachet_6seeds(model: namedtuple, previous_result: str):
    """
    Requests inference from the Nachet Six Seed model.

    Args:
        model (namedtuple): The model to use for inference.
        previous_result (str): The previous result to pass to the model.

    Returns:
        dict: The result of the inference as a JSON object.

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

        req = Request(model.endpoint, body, headers)
        response = urlopen(req)
        result = response.read()
        result_object = json.loads(result.decode("utf8"))

        print(json.dumps(result_object[0].get("boxes"), indent=4)) #TODO Transform into logging

        return result_object

    except (KeyError, TypeError, IndexError, URLError, json.JSONDecodeError)  as error:
        print(error)
        raise SixSeedModelAPIError(f"Error while processing inference results :\n {str(error)}") from error
