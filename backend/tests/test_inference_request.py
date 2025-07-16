import pytest
import json
import os
import base64
import asyncio
import warnings

from app import app, ImageWarning
from unittest.mock import patch, MagicMock, Mock

@pytest.fixture
def inference_request_setup():
    """
    Set up the test environment before running each test case.
    """
    # Start the test pipeline
    test = app.test_client()
    response = asyncio.run(
        test.get("/test")
    )
    pipeline = json.loads(asyncio.run(response.get_data()))[0]
    current_dir = os.path.dirname(__file__)
    image_path = os.path.join(current_dir, 'img/1310_1.png')
    endpoints = "/model-endpoints-metadata"
    inference = "/inf"
    container_name = "a427278e-28df-428f-8937-ddeeef44e72f"
    folder_name = "test1"
    image_header = "data:image/PNG;base64,"
    with open(image_path, 'rb') as image_file:
        image_src = base64.b64encode(image_file.read()).decode('utf-8')

    return {
        "test": test,
        "pipeline": pipeline,
        "endpoints": endpoints,
        "inference": inference,
        "container_name": container_name,
        "folder_name": folder_name,
        "image_header": image_header,
        "image_src": image_src
    }

@patch("patch.bin_azure_storage_api.mount_container") # TODO : change to patch the mount_container function of the datastore repo
def test_inference_request_successful(mock_container, inference_request_setup):
    setup = inference_request_setup
    # Mock azure client services
    mock_blob = Mock()
    mock_blob.readall.return_value = bytes(setup["image_src"], encoding="utf-8")

    mock_blob_client = Mock()
    mock_blob_client.configure_mock(name="test_blob.json")
    mock_blob_client.download_blob.return_value = mock_blob

    mock_container_client = MagicMock()
    mock_container_client.list_blobs.return_value = [mock_blob_client]
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_container_client.exists.return_value = True

    mock_container.return_value = mock_container_client
    # Build expected response keys
    responses = set()
    expected_keys = {
        "filename",
        "boxes",
        "labelOccurrence",
        "totalBoxes",
        "box",
        "label",
        "color",
        "score",
        "topN",
        "overlapping",
        "overlappingIndices",
        "models",
        "box_id",
        "inference_id",
        "object_type_id",
        "top_id",
        "models",
        "pipeline_id"
    }

    # Test the answers from inference_request
    response = asyncio.run(
        setup["test"].post(
            '/inf',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "image": setup["image_header"] + setup["image_src"],
                "imageDims": [720,540],
                "folder_name": setup["folder_name"],
                "container_name": setup["container_name"],
                "model_name": setup["pipeline"].get("pipeline_name")
            })
    )

    result_json = json.loads(asyncio.run(response.get_data()))
    keys = set(result_json.keys())
    keys.update(result_json["boxes"][0].keys())
    responses.update(keys)

    assert responses == expected_keys

@patch("patch.bin_azure_storage_api.mount_container") # TODO : change to patch the mount_container function of the datastore repo
def test_inference_request_unsuccessful(mock_container, inference_request_setup):
    setup = inference_request_setup
    # Mock azure client services
    mock_blob = Mock()
    mock_blob.readall.return_value = b""

    mock_blob_client = Mock()
    mock_blob_client.configure_mock(name="test_blob.json")
    mock_blob_client.download_blob.return_value = mock_blob

    mock_container_client = MagicMock()
    mock_container_client.list_blobs.return_value = [mock_blob_client]
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_container_client.exists.return_value = True

    mock_container.return_value = mock_container_client

    # Build expected response
    expected = ("API Error during classification : An error occurred while processing the requests :\n The result send to the inference function is empty")

    # Test the answers from inference_request
    response = asyncio.run(
        setup["test"].post(
            '/inf',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "image": setup["image_header"],
                "imageDims": [720,540],
                "folder_name": setup["folder_name"],
                "container_name": setup["container_name"],
                "model_name":  setup["pipeline"].get("pipeline_name")
            })
    )

    result_json = json.loads(asyncio.run(response.get_data()))
    assert result_json[0] == expected
    assert response.status_code == 400

def test_inference_request_missing_argument(inference_request_setup):
    setup = inference_request_setup
    # Build expected response
    responses = []
    expected = ("API Error during classification : missing request arguments: either folder_name, container_name, imageDims or image is missing")

    data = {
        "image": setup["image_header"],
        "imageDims": [720,540],
        "folder_name": setup["folder_name"],
        "container_name": setup["container_name"],
        "model_name": setup["pipeline"].get("pipeline_name")
    }

    # Test the answers from inference_request

    for k, v in data.items():
        if k != "model_name":
            data[k] = ""
            response = asyncio.run(
                setup["test"].post(
                    '/inf',
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    json=data
                )
            )
            result_json = json.loads(asyncio.run(response.get_data()))
            if len(responses) == 0:
                responses.append(result_json[0])
            if responses[0] != result_json[0]:
                responses.append(result_json[0])
            data[k] = v

    if len(responses) > 1:
        raise ValueError(f"Different errors messages were given; expected only 'missing request arguments', {responses}")
    assert result_json[0] == expected
    assert response.status_code == 400

def test_inference_request_wrong_pipeline_name(inference_request_setup):
    setup = inference_request_setup
    # Build expected response
    expected = ("API Error during classification : model wrong_pipeline_name not found")

    # Test the answers from inference_request
    response = asyncio.run(
        setup["test"].post(
            '/inf',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "image": setup["image_src"],
                "imageDims": [720,540],
                "folder_name": setup["folder_name"],
                "container_name": setup["container_name"],
                "model_name": "wrong_pipeline_name"
            }
        )
    )
    result_json = json.loads(asyncio.run(response.get_data()))

    assert result_json[0] == expected
    assert response.status_code == 400

# TODO test validation error when frontend return validators
def test_inference_request_validation_warning(inference_request_setup):
    setup = inference_request_setup
    # Build expected response
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        asyncio.run(
            setup["test"].post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": "data:python," + setup["image_src"],
                    "imageDims": [720,540],
                    "folder_name": setup["folder_name"],
                    "container_name": setup["container_name"],
                    "model_name": setup["pipeline"].get("pipeline_name")
                }
            )
        )

    assert issubclass(w[-1].category, ImageWarning)
    assert "this picture was not validate" in str(w[-1].message)