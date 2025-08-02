import pytest
import asyncio
import os
import base64

from app import app, json
from unittest.mock import MagicMock, Mock, patch


@pytest.fixture
async def positive_feedback_setup():
    test_client = app.test_client()
    userId = "a427278e-28df-428f-8937-ddeeef44e72f"
    response = await test_client.get("/test")
    pipeline = json.loads(await response.get_data())[0]
    current_dir = os.path.dirname(__file__)
    image_path = os.path.join(current_dir, 'img/16.tiff')
    folder_name = "test1"
    image_header = "data:image/PNG;base64,"
    with open(image_path, 'rb') as image_file:
        image_src = base64.b64encode(image_file.read()).decode('utf-8')
    inferences_id = []

    return {
        "test_client": test_client,
        "userId": userId,
        "pipeline": pipeline,
        "folder_name": folder_name,
        "image_header": image_header,
        "image_src": image_src,
        "inferences_id": inferences_id
    }

async def create_test_inference(setup):
    """
    Create a test inference to be used in the test
    """
    with patch("patch.bin_azure_storage_api.mount_container") as mock_container:
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

        # Test the answers from inference_request
        response = await setup["test_client"].post(
            '/inf',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "image": setup["image_header"] + setup["image_src"],
                "imageDims": [720,540],
                "folder_name": setup["folder_name"],
                "container_name": setup["userId"],
                "model_name": setup["pipeline"].get("pipeline_name")
            })
        
        inference = json.loads(await response.get_data())
        
        # Check if response is an error (list) or success (dict)
        if isinstance(inference, list):
            raise RuntimeError(f"Failed to create test inference: {inference}")
        
        setup["inferences_id"].append(inference.get("inference_id"))
        
        return inference

@pytest.mark.asyncio
async def test_positive_feedback_successful(positive_feedback_setup):
    setup = await positive_feedback_setup
    
    inference = await create_test_inference(setup)
    inferenceId = inference.get("inference_id")
    boxes = []
    for box in inference.get("boxes"):
        boxes.append({"boxId" : box.get("box_id")})
    
    response = await setup["test_client"].post(
        '/feedback-positive',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "userId": setup["userId"],
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    assert response.status_code == 200
    result_json = json.loads(await response.get_data())
    assert isinstance(result_json, dict)
        
@pytest.mark.asyncio
async def test_positive_feedback_missing_arguments_error(positive_feedback_setup):
    """
    Test if a request with missing arguments return an error
    """
    setup = await positive_feedback_setup
    expected = ("API Error giving a positive feedback : missing request arguments: either userId, inferenceId or boxes is missing")
    
    inference = await create_test_inference(setup)
    inferenceId = inference.get("inference_id")
    boxes = []
    for box in inference.get("boxes"):
        boxes.append({"boxId" : box.get("box_id")})
        
    response = await setup["test_client"].post(
        '/feedback-positive',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected
    
    expected = ("API Error giving a positive feedback : missing request arguments: boxId is missing in boxes")
    
    boxes.append({}) # add a box with a missing argument 
    
    response = await setup["test_client"].post(
        '/feedback-positive',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "userId": setup["userId"],
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected
        

@pytest.fixture        
async def negative_feedback_setup():
    test_client = app.test_client()
    userId = "a427278e-28df-428f-8937-ddeeef44e72f"
    response = await test_client.get("/test")
    pipeline = json.loads(await response.get_data())[0]
    current_dir = os.path.dirname(__file__)
    image_path = os.path.join(current_dir, 'img/16.tiff')
    folder_name = "test1"
    image_header = "data:image/PNG;base64,"
    with open(image_path, 'rb') as image_file:
        image_src = base64.b64encode(image_file.read()).decode('utf-8')
    inferences_id = []

    return {
        "test_client": test_client,
        "userId": userId,
        "pipeline": pipeline,
        "folder_name": folder_name,
        "image_header": image_header,
        "image_src": image_src,
        "inferences_id": inferences_id
    }

@pytest.mark.asyncio
async def test_negative_feedback_successful(negative_feedback_setup):
    setup = await negative_feedback_setup
    
    inference = await create_test_inference(setup)
    inferenceId = inference.get("inference_id")
    boxes = []
    for box in inference.get("boxes"):
        boxes.append(
                {
                    "boxId" : box.get("box_id"),
                    "label": "Solanum carolinense", #instead of "Ambrosia artemisiifolia"
                    "classId": "05d77efa-1e48-4b71-a101-9b59d28318b5",
                    "box": box.get("box"),
                    "color": box.get("color"), 
                    "overlapping": box.get("overlapping"), 
                    "overlappingIndices": box.get("overlappingIndices")
                }
            )
    """
    Test that the negative feedback endpoint correctly returns a 200 status code if the seed is corrected to another seed
    As all the case are already tested by the datastore unit tests we use a simple test here just to be sure the endpoint is working 
    """
    response = await setup["test_client"].post(
        '/feedback-negative',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "userId": setup["userId"],
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    assert response.status_code == 200
    result_json = json.loads(await response.get_data())
    assert isinstance(result_json, dict)

@pytest.mark.asyncio
async def test_negative_feedback_missing_arguments_error(negative_feedback_setup):
    """
    Test if a request with missing arguments return an error
    """
    setup = await negative_feedback_setup
    expected = ("API Error giving a negative feedback : missing request arguments: either userId, inferenceId or boxes is missing")
    
    inference = await create_test_inference(setup)
    inferenceId = inference.get("inference_id")
    boxes = []
    for box in inference.get("boxes"):
        boxes.append(
                {
                    "boxId" : box.get("box_id"),
                    "label": "Solanum carolinense", #instead of "Ambrosia artemisiifolia"
                    "classId": "05d77efa-1e48-4b71-a101-9b59d28318b5",
                    "box": box.get("box"),
                    "color": box.get("color"), 
                    "overlapping": box.get("overlapping"), 
                    "overlappingIndices": box.get("overlappingIndices")
                }
            )
    
    response = await setup["test_client"].post(
        '/feedback-negative',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected
    
    expected = ("API Error giving a negative feedback : missing request arguments: either boxId, label, box or classId is missing in boxes")
    
    boxes.append({                
            "label": "Solanum carolinense",
            "boxId": "2f7137ee-0517-46f9-a80d-a109d41c3f73",
            "box": {
                "topX": 56, 
                "topY": 36, 
                "bottomX": 619, 
                "bottomY": 302
            },
            "color": "#ED1C24", 
            "overlapping": False, 
            "overlappingIndices": []
            }) # add a box with a missing argument (classId)
    
    response = await setup["test_client"].post(
        '/feedback-negative',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "userId": setup["userId"],
            "inferenceId": inferenceId,
            "boxes": boxes
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected
