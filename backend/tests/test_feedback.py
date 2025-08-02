import pytest
import pytest_asyncio
import os
import base64

from app import app, json
from unittest.mock import MagicMock, Mock, patch
import storage.datastore_storage_api as datastore


@pytest_asyncio.fixture
async def positive_feedback_setup():
    test_client = app.test_client()
    test_email = "test.user@inspection.gc.ca"
    
    # Create test user in database
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    try:
        user = await datastore.create_user(test_email, connection_string)
        userId = user.id
    except Exception:
        # User might already exist, get the existing user ID
        userId = datastore.get_user_id(test_email)
    
    # Use existing pipeline from database instead of calling /test endpoint
    pipeline = {"pipeline_name": "swin-27-spp"}
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
    Create a test inference record in the database using real test data
    """
    # Load the test inference data
    import json
    with open('../datastore/tests/nachet/inference_result.json', 'r') as f:
        inference_data = json.load(f)
    
    # Mock Azure storage functions to avoid blob storage dependencies
    with patch('datastore.blob.azure_storage_api.get_blob') as mock_get_blob, \
         patch('datastore.blob.azure_storage_api.get_image_count') as mock_get_image_count:
        
        # Set up mocks
        mock_get_blob.return_value = '{"folder_name": "General"}'
        mock_get_image_count.return_value = 0
        
        # Create a picture first (needed for inference)
        connection = datastore.get_connection()
        cursor = datastore.get_cursor(connection)
        
        try:
            # Create test image data
            import base64
            image_bytes = base64.b64decode(setup["image_src"])
            
            # Mock container client with proper blob list behavior
            from unittest.mock import Mock, MagicMock
            container_client = MagicMock()
            
            # Create a mock blob that represents the General folder
            mock_blob = MagicMock()
            mock_blob.name = "General/General.json"
            mock_blob.download_blob.return_value.readall.return_value = b'{"folder_name": "General"}'
            
            # Mock blob client returned by upload_blob
            mock_blob_client = MagicMock()
            mock_blob_client.set_blob_tags = MagicMock()
            
            # Mock container methods
            container_client.list_blobs.return_value = [mock_blob]
            container_client.get_blob_client.return_value = mock_blob
            container_client.upload_blob.return_value = mock_blob_client
            
            # Create picture record
            picture_id = await datastore.get_picture_id(
                cursor, setup["userId"], image_bytes, container_client
            )
            
            # Save inference result to database using the test data
            saved_inference = await datastore.save_inference_result(
                cursor, setup["userId"], inference_data, picture_id, "swin-27-spp", 1
            )
            
            datastore.end_query(connection, cursor)
            setup["inferences_id"].append(saved_inference.get("inference_id"))
            return saved_inference
            
        except Exception as error:
            datastore.end_query(connection, cursor)
            raise error

@pytest.mark.asyncio
async def test_positive_feedback_successful(positive_feedback_setup):
    setup = positive_feedback_setup
    
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
    setup = positive_feedback_setup
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
        

@pytest_asyncio.fixture        
async def negative_feedback_setup():
    test_client = app.test_client()
    test_email = "test.user@inspection.gc.ca"
    
    # Create test user in database
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    try:
        user = await datastore.create_user(test_email, connection_string)
        userId = user.id
    except Exception:
        # User might already exist, get the existing user ID
        userId = datastore.get_user_id(test_email)
    # Use existing pipeline from database instead of calling /test endpoint
    pipeline = {"pipeline_name": "swin-27-spp"}
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
    setup = negative_feedback_setup
    
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
    setup = negative_feedback_setup
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
