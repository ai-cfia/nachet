import os
import pytest
# import asyncio
import json
import base64
from unittest.mock import patch, MagicMock
from app import app
from storage.datastore_storage_api import DatastoreError

class TestMissingEnvError(Exception):
    pass

CONNECTION_STRING = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_SCHEMA = os.getenv("NACHET_SCHEMA")

if CONNECTION_STRING is None:
    raise TestMissingEnvError("Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING")
if NACHET_DB_URL is None:
    raise TestMissingEnvError("Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING")
if NACHET_SCHEMA is None:
    raise TestMissingEnvError("Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING")

@pytest.fixture
def create_folder_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    container_name = "test_container_name"
    folder_name = "test_folder_name"
    picture_set_id = "picture_set_id"
    
    # Mock the azure_storage and database variables
    mock_cur = MagicMock()     
    mock_connection = MagicMock()
    mock_container_client = MagicMock()
    
    # Patch the azure_storage and datastore functions
    patch_connect_db = patch('app.datastore.db.connect_db', return_value=mock_connection)
    patch_cursor = patch('app.datastore.db.cursor', return_value=mock_cur)
    patch_mount_container = patch('app.azure_storage.mount_container', return_value=mock_container_client)
    patch_create_picture_set = patch('app.datastore.create_picture_set', return_value = picture_set_id)
    patch_end_query = patch('app.datastore.end_query')
    
    mock_connect_db = patch_connect_db.start()
    mock_cursor = patch_cursor.start()
    mock_mount_container = patch_mount_container.start()
    mock_create_picture_set = patch_create_picture_set.start()
    mock_end_query = patch_end_query.start()
    
    yield {
        "test_client": test_client,
        "container_name": container_name,
        "folder_name": folder_name,
        "picture_set_id": picture_set_id,
        "mock_cur": mock_cur,
        "mock_connection": mock_connection,
        "mock_container_client": mock_container_client,
        "mock_connect_db": mock_connect_db,
        "mock_cursor": mock_cursor,
        "mock_mount_container": mock_mount_container,
        "mock_create_picture_set": mock_create_picture_set,
        "mock_end_query": mock_end_query
    }
    
    # Teardown
    patch_connect_db.stop()
    patch_cursor.stop()
    patch_mount_container.stop()
    patch_create_picture_set.stop()
    patch_end_query.stop()


@pytest.mark.asyncio
async def test_create_directory_successful(create_folder_setup):
    """
    Test the directory creation route with successful conditions.
    """
    setup = create_folder_setup
    response = await setup["test_client"].post(
        '/create-dir',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": setup["folder_name"]
        })
    
    assert response.status_code == 200
    assert json.loads(await response.get_data()) == [setup["picture_set_id"]]
    setup["mock_mount_container"].assert_called_once_with(CONNECTION_STRING, setup["container_name"], create_container=True)
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_create_picture_set"].assert_called_once_with(setup["mock_cur"], setup["mock_container_client"], setup["container_name"], 0, setup["folder_name"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])
 
@pytest.mark.asyncio
async def test_create_directory_missing_argument_error(create_folder_setup):
    """
    Test the directory creation route with unsuccessful conditions : missing argument.
    """
    setup = create_folder_setup
    expected = ("API Error creating directory : missing container or directory name")
    
    response = await setup["test_client"].post(
        '/create-dir',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": ""
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected
        
@pytest.mark.asyncio
async def test_create_directory_datastore_error(create_folder_setup):
    """
    Test the directory creation route with unsuccessful conditions : an error from datastore is raised.
    """
    setup = create_folder_setup
    expected = ("Datastore Error creating directory : An error occured during the upload of the picture set")
    setup["mock_create_picture_set"].side_effect = DatastoreError("An error occured during the upload of the picture set")
    
    response = await setup["test_client"].post(
        '/create-dir',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": setup["folder_name"]
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected

@pytest.fixture
def get_folders_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    container_name = "test_container_name"
    folders_data = [
        {
            "folder_name": "General",
            "nb_pictures": 1,
            "picture_set_id": "picture_set_id",
            "pictures": [{
                "inference_exist": True,
                "is_validated": False,
                "picture_id": "picture_id"
            }]
        }
    ]

    # Mock the azure_storage and database variables
    mock_cur = MagicMock()     
    mock_connection = MagicMock()
    
    # Patch the azure_storage and datastore functions
    patch_connect_db = patch('app.datastore.db.connect_db', return_value=mock_connection)
    patch_cursor = patch('app.datastore.db.cursor', return_value=mock_cur)
    patch_get_directories = patch('app.datastore.get_directories', return_value = folders_data)
    patch_end_query = patch('app.datastore.end_query')
    
    mock_connect_db = patch_connect_db.start()
    mock_cursor = patch_cursor.start()
    mock_get_directories = patch_get_directories.start()
    mock_end_query = patch_end_query.start()

    yield {
        "test_client": test_client,
        "container_name": container_name,
        "folders_data": folders_data,
        "mock_cur": mock_cur,
        "mock_connection": mock_connection,
        "mock_connect_db": mock_connect_db,
        "mock_cursor": mock_cursor,
        "mock_get_directories": mock_get_directories,
        "mock_end_query": mock_end_query
    }
    
    # Teardown
    patch_connect_db.stop()
    patch_cursor.stop()
    patch_get_directories.stop()
    patch_end_query.stop()

@pytest.mark.asyncio
async def test_get_directories_successful(get_folders_setup):
    """
    Test the get directories route with successful conditions.
    """
    setup = get_folders_setup
    response = await setup["test_client"].post(
        '/get-directories',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"]
        })
    
    assert response.status_code == 200
    assert json.loads(await response.get_data()) == {"folders" : setup["folders_data"]}
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_get_directories"].assert_called_once_with(setup["mock_cur"], setup["container_name"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])

@pytest.mark.asyncio
async def test_get_directories_missing_argument_error(get_folders_setup):
    """
    Test the get directories route with unsuccessful conditions : missing argument.
    """
    setup = get_folders_setup
    expected = ("API Error retrieving user directories : Missing container name")
    
    response = await setup["test_client"].post(
        '/get-directories',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": ""
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected

@pytest.mark.asyncio
async def test_get_directories_datastore_error(get_folders_setup):
    """
    Test the get directories route with unsuccessful conditions : an error from datastore is raised.
    """
    setup = get_folders_setup
    expected = ("Datastore Error retrieving user directories : An error occured while retrieving the picture sets")
    setup["mock_get_directories"].side_effect = DatastoreError("An error occured while retrieving the picture sets")
    
    response = await setup["test_client"].post(
        '/get-directories',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"]
        })
    
    assert response.status_code == 400
    result_json = json.loads(await response.get_data())
    assert result_json[0] == expected        


@pytest.fixture
def get_picture_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    container_name = "test_container_name"
    picture_id = "test_picture_id"
    inference = {
        "boxes": [
            {
                "box_id": "test_box_id",
                "label": "test_label",
                "score": 1,
                "top_id": "test_top_id"
            }
        ],
        "inference_id": "test_inference_id",
        "models": [
            {
                "name": "test_model_name",
                "version": "1"
            },
        ],
        "pipeline_id": "test_pipeline_id",
    }
    picture_blob = b"blob"
    image_base64 = base64.b64encode(picture_blob)
    image = "data:image/tiff;base64," + image_base64.decode("utf-8")
    
    # Mock the azure_storage and database variables
    mock_cur = MagicMock()     
    mock_connection = MagicMock()
    mock_container_client = MagicMock()
    
    # Patch the azure_storage and datastore functions
    patch_connect_db = patch('app.datastore.db.connect_db', return_value=mock_connection)
    patch_cursor = patch('app.datastore.db.cursor', return_value=mock_cur)
    patch_mount_container = patch('app.azure_storage.mount_container', return_value=mock_container_client)
    patch_get_inference = patch('app.datastore.get_inference', return_value = inference)
    patch_get_picture_blob = patch('app.datastore.get_picture_blob', return_value = picture_blob)
    patch_end_query = patch('app.datastore.end_query')
    
    mock_connect_db = patch_connect_db.start()
    mock_cursor = patch_cursor.start()
    mock_mount_container = patch_mount_container.start()
    mock_get_inference = patch_get_inference.start()
    mock_get_picture_blob = patch_get_picture_blob.start()
    mock_end_query = patch_end_query.start()

    yield {
        "test_client": test_client,
        "container_name": container_name,
        "picture_id": picture_id,
        "inference": inference,
        "picture_blob": picture_blob,
        "image": image,
        "mock_cur": mock_cur,
        "mock_connection": mock_connection,
        "mock_container_client": mock_container_client,
        "mock_connect_db": mock_connect_db,
        "mock_cursor": mock_cursor,
        "mock_mount_container": mock_mount_container,
        "mock_get_inference": mock_get_inference,
        "mock_get_picture_blob": mock_get_picture_blob,
        "mock_end_query": mock_end_query
    }
    
    # Teardown
    patch_connect_db.stop()
    patch_cursor.stop()
    patch_mount_container.stop()
    patch_get_inference.stop()
    patch_get_picture_blob.stop()
    patch_end_query.stop()

@pytest.mark.asyncio
async def test_get_picture_successful(get_picture_setup):
    """
    Test the get picture route with successful conditions.
    """
    setup = get_picture_setup
    response = await setup["test_client"].post(
        '/get-picture',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "picture_id": setup["picture_id"]
        })
    
    assert response.status_code == 200
    expected_response = {"inference": setup["inference"], "image": setup["image"], "picture_id": setup["picture_id"]}
    assert json.loads(await response.get_data()) == expected_response
    setup["mock_mount_container"].assert_called_once_with(CONNECTION_STRING, setup["container_name"], create_container=True)
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_get_inference"].assert_called_once_with(setup["mock_cur"], setup["container_name"], setup["picture_id"])
    setup["mock_get_picture_blob"].assert_called_once_with(setup["mock_cur"], setup["container_name"], setup["mock_container_client"], setup["picture_id"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])
        

@pytest.fixture
def delete_folder_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    container_name = "test_container_name"
    folder_uuid = "test_folder_uuid"
    validated_pictures_id = ["picture_id_1", "picture_id_3"]

    # Mock the azure_storage and database variables
    mock_cur = MagicMock()     
    mock_connection = MagicMock()
    mock_container_client = MagicMock()

    # Patch the azure_storage and datastore functions
    patch_connect_db = patch('app.datastore.db.connect_db', return_value=mock_connection)
    patch_cursor = patch('app.datastore.db.cursor', return_value=mock_cur)
    patch_mount_container = patch('app.azure_storage.mount_container', return_value=mock_container_client)
    patch_delete_directory_request = patch('app.datastore.delete_directory_request', return_value =  validated_pictures_id)
    patch_delete_directory_permanently = patch('app.datastore.delete_directory_permanently', return_value =  True)
    patch_delete_with_archive = patch('app.datastore.delete_directory_with_archive', return_value = folder_uuid)
    patch_end_query = patch('app.datastore.end_query')

    mock_connect_db = patch_connect_db.start()
    mock_cursor = patch_cursor.start()
    mock_mount_container = patch_mount_container.start()
    mock_delete_directory_request = patch_delete_directory_request.start()
    mock_delete_directory_permanently = patch_delete_directory_permanently.start()
    mock_delete_with_archive = patch_delete_with_archive.start()
    mock_end_query = patch_end_query.start()

    yield {
        "test_client": test_client,
        "container_name": container_name,
        "folder_uuid": folder_uuid,
        "validated_pictures_id": validated_pictures_id,
        "mock_cur": mock_cur,
        "mock_connection": mock_connection,
        "mock_container_client": mock_container_client,
        "mock_connect_db": mock_connect_db,
        "mock_cursor": mock_cursor,
        "mock_mount_container": mock_mount_container,
        "mock_delete_directory_request": mock_delete_directory_request,
        "mock_delete_directory_permanently": mock_delete_directory_permanently,
        "mock_delete_with_archive": mock_delete_with_archive,
        "mock_end_query": mock_end_query
    }
    
    # Teardown
    patch_connect_db.stop()
    patch_cursor.stop()
    patch_mount_container.stop()
    patch_delete_directory_request.stop()
    patch_delete_directory_permanently.stop()
    patch_delete_with_archive.stop()
    patch_end_query.stop()

@pytest.mark.asyncio
async def test_delete_request_successful(delete_folder_setup):
    """
    Test the delete request route with successful conditions.
    """
    setup = delete_folder_setup
    response = await setup["test_client"].post(
        '/delete-request',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_uuid": setup["folder_uuid"]
        })
    assert response.status_code == 200
    assert json.loads(await response.get_data()) == setup["validated_pictures_id"]
    
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_delete_directory_request"].assert_called_once_with(setup["mock_cur"], setup["container_name"], setup["folder_uuid"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])
        
@pytest.mark.asyncio
async def test_delete_permanently_successful(delete_folder_setup):
    """
    Test the delete permanently route with successful conditions.
    """
    setup = delete_folder_setup
    response = await setup["test_client"].post(
        '/delete-permanently',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_uuid": setup["folder_uuid"]
        })
    assert response.status_code == 200
    assert json.loads(await response.get_data()) is True

    setup["mock_mount_container"].assert_called_once_with(CONNECTION_STRING, setup["container_name"], create_container=True)
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_delete_directory_permanently"].assert_called_once_with(setup["mock_cur"], setup["container_name"], setup["folder_uuid"], setup["mock_container_client"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])

@pytest.mark.asyncio
async def test_delete_with_archive_successful(delete_folder_setup):
    """
    Test the delete with archive route with successful conditions.
    """
    setup = delete_folder_setup
    response = await setup["test_client"].post(
        '/delete-with-archive',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_uuid": setup["folder_uuid"]
        })
    assert response.status_code == 200
    assert json.loads(await response.get_data()) is True

    setup["mock_mount_container"].assert_called_once_with(CONNECTION_STRING, setup["container_name"], create_container=True)
    setup["mock_connect_db"].assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
    setup["mock_cursor"].assert_called_once_with(setup["mock_connection"])
    setup["mock_delete_with_archive"].assert_called_once_with(setup["mock_cur"], setup["container_name"], setup["folder_uuid"], setup["mock_container_client"])
    setup["mock_end_query"].assert_called_once_with(setup["mock_connection"], setup["mock_cur"])
