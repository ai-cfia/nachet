"""
This module contains functions for performing inference using different models.

Functions:
    request_inference_from_swin: Perform inference using the SWIN model on a list of images.
    request_inference_from_seed_detector: Requests inference from the seed detector model using the provided previous result.
    request_inference_from_nachet_six_seed: Requests inference from the Nachet Six Seed model.
"""
from collections import namedtuple
from model.model_exceptions import ModelAPIError

class TestModelAPIError(ModelAPIError) :
    pass

async def request_inference_from_test(model: namedtuple, previous_result: str):
    """
    Requests a test case inference.

    Args:
        model (namedtuple): The model to use for the test inference.
        previous_result (str): The previous result to pass to the model.

    Returns:
        dict: The result of the inference as a JSON object.

    Raises:
        ProcessInferenceResultsError: If an error occurs while processing the request.
    """
    try:
        if previous_result == '':
           raise ValueError("The result send to the inference function is empty")
        print(f"processing test request for {model.name} with {type(previous_result)} arguments")
        return [
            {
                "filename": "test_image.jpg",
                "boxes": [
                    {
                        "box": {
                            "topX": 0.078,
                            "topY": 0.068,
                            "bottomX": 0.86,
                            "bottomY": 0.56
                        },
                        "label": "Ambrosia artemisiifolia",
                        "score": 1.0,
                        "topN": [
                            {
                                "label": "Ambrosia artemisiifolia",
                                "score": 1.0,
                            },
                        ],
                    }
                ],
                "models" : 
                    [
                        {
                            "name" : model.name,
                            "version" : 1
                        }
                    ]
            }
        ]

    except ValueError as error:
        print(error)
        raise TestModelAPIError(f"An error occurred while processing the requests :\n {str(error)}") from error
