import pytest
import pytest_asyncio
import os
import base64

from app import app, json


@pytest_asyncio.fixture
async def new_batch_import_setup():
    test_client = app.test_client()
    test_email = "test.user@inspection.gc.ca"
    
    # Create test user in database
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    try:
        import storage.datastore_storage_api as datastore
        user = await datastore.create_user(test_email, connection_string)
        container_name = user.id
    except Exception:
        # User might already exist, get the existing user ID
        import storage.datastore_storage_api as datastore
        container_name = datastore.get_user_id(test_email)
    
    nb_pictures = 1
    folder_name = "test_batch_import"
    session_id = None
    
    return {
        "test_client": test_client,
        "container_name": container_name,
        "nb_pictures": nb_pictures,
        "folder_name": folder_name,
        "session_id": session_id
    }

@pytest.mark.asyncio 
async def test_new_batch_import_successful(new_batch_import_setup):
    setup = new_batch_import_setup
    
    response = await setup["test_client"].post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": setup["folder_name"],
            "nb_pictures": setup["nb_pictures"]
        })
    
    result_json = json.loads(await response.get_data())
    if response.status_code != 200:
        print(f"Unexpected error response: {result_json}")
    assert response.status_code == 200
    assert result_json.get("session_id") is not None
    
    setup["session_id"] = result_json.get("session_id")
    
    # Cleanup
    if setup["session_id"] is not None:
        response = await setup["test_client"].post(
            '/delete-permanently',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "container_name": setup["container_name"],
                "folder_uuid": setup["session_id"]
            })

@pytest.mark.asyncio
async def test_new_batch_import_missing_arguments_error(new_batch_import_setup):
    """
    Test if a request with missing arguments return an error
    """
    setup = new_batch_import_setup
    expected = ("API Error initiating batch upload : missing request arguments: either container_name or nb_pictures is missing")

    response = await setup["test_client"].post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "folder_name": setup["folder_name"],
            "nb_pictures": setup["nb_pictures"]
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected
        
@pytest.mark.asyncio
async def test_new_batch_import_wrong_nb_pictures(new_batch_import_setup):
    """
    Test if a request with a wrong argument return an error
    """
    setup = new_batch_import_setup
    expected = ("API Error initiating batch upload : wrong request arguments: either container_name or nb_pictures is wrong")

    response = await setup["test_client"].post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": "",
            "folder_name": setup["folder_name"],
            "nb_pictures": setup["nb_pictures"]
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected

    response = await setup["test_client"].post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": setup["folder_name"],
            "nb_pictures": "1"
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected
    
    response = await setup["test_client"].post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "folder_name": "test_batch_import",
            "nb_pictures": 0
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected
        

@pytest_asyncio.fixture
async def upload_batch_import_setup():
    test_client = app.test_client()
    test_email = "test.user@inspection.gc.ca"
    
    # Create test user in database
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    try:
        import storage.datastore_storage_api as datastore
        user = await datastore.create_user(test_email, connection_string)
        container_name = user.id
    except Exception:
        # User might already exist, get the existing user ID
        import storage.datastore_storage_api as datastore
        container_name = datastore.get_user_id(test_email)
    nb_pictures = 1
    folder_name = "test_batch_import"
    session_id = None
    
    response = await test_client.post(
        '/new-batch-import',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": container_name,
            "folder_name": folder_name,
            "nb_pictures": nb_pictures
        })
    result_json = json.loads(await response.get_data())
    if response.status_code == 200:
        print("Setup : folder successfully created")
    else :
        print(result_json)
    session_id = result_json.get("session_id")
    
    seed_name = "Ambrosia artemisiifolia"
    seed_id = "14e96554-aadf-42e4-8665-d141354800d1"
    zoom_level = None
    nb_seeds = None
    current_dir = os.path.dirname(__file__)
    image_path = os.path.join(current_dir, 'img/1310_1.png')
    image_header = "data:image/PNG;base64,"
    with open(image_path, 'rb') as image_file:
        image_src = base64.b64encode(image_file.read()).decode('utf-8')
    image = image_header + image_src
    
    yield {
        "test_client": test_client,
        "container_name": container_name,
        "nb_pictures": nb_pictures,
        "folder_name": folder_name,
        "session_id": session_id,
        "seed_name": seed_name,
        "seed_id": seed_id,
        "zoom_level": zoom_level,
        "nb_seeds": nb_seeds,
        "image": image
    }
    
    # Teardown
    if session_id is not None:
        response = await test_client.post(
            '/delete-permanently',
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            json={
                "container_name": container_name,
                "folder_uuid": session_id
            })
        if response.status_code == 200:
            print("Teardown : folder successfully deleted")
        
@pytest.mark.asyncio
async def test_upload_picture_successful(upload_batch_import_setup):
    setup = upload_batch_import_setup
    response = await setup["test_client"].post(
        '/upload-picture',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            "session_id": setup["session_id"],
            "seed_name": setup["seed_name"],
            "seed_id" : setup["seed_id"],
            "zoom_level": setup["zoom_level"],
            "nb_seeds": setup["nb_seeds"],
            "image": setup["image"]
        })
    assert response.status_code == 200
    result_json = json.loads(await response.get_data())
    print(result_json)
        
@pytest.mark.asyncio
async def test_upload_picture_missing_arguments_error(upload_batch_import_setup):
    """
    Test if a request with missing arguments return an error
    """
    setup = upload_batch_import_setup
    expected = ("API Error uploading picture : missing request arguments: either seed_name, session_id, container_name or image is missing")

    response = await setup["test_client"].post(
        '/upload-picture',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": setup["container_name"],
            # missing session_id
            "seed_name": setup["seed_name"],
            "seed_id" : setup["seed_id"],
            "zoom_level": setup["zoom_level"],
            "nb_seeds": setup["nb_seeds"],
            "image": setup["image"] 
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected

@pytest.mark.asyncio
async def test_upload_picture_wrong_arguments_error(upload_batch_import_setup):
    """
    Test if a request with wrong arguments return an error
    """
    setup = upload_batch_import_setup
    expected = ("API Error uploading picture : missing request arguments: either seed_name, session_id, container_name or image is missing")

    response = await setup["test_client"].post(
        '/upload-picture',
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        json={
            "container_name": "", # wrong container_name
            "session_id": setup["session_id"],
            "seed_name": setup["seed_name"],
            "seed_id" : setup["seed_id"],
            "zoom_level": setup["zoom_level"],
            "nb_seeds": setup["nb_seeds"],
            "image": setup["image"] 
        })
    result_json = json.loads(await response.get_data())
    
    assert response.status_code == 400
    assert result_json[0] == expected
