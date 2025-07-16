import os
import pytest
from app import app
from unittest.mock import patch, MagicMock, AsyncMock
import storage.datastore_storage_api as datastore

class TestMissingEnvError(Exception):
    pass

NACHET_DB_URL = os.getenv("NACHET_DB_URL")
NACHET_SCHEMA = os.getenv("NACHET_SCHEMA")

if NACHET_DB_URL is None:
    raise TestMissingEnvError("Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING")
if NACHET_SCHEMA is None:
    raise TestMissingEnvError("Missing environment variable: NACHET_AZURE_STORAGE_CONNECTION_STRING")

@pytest.fixture
def connection_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    connection = None
    cursor = None
    
    yield {
        "test_client": test_client,
        "connection": connection,
        "cursor": cursor
    }
    
    # Teardown
    if cursor and not cursor.closed:
        cursor.close()
    if connection and not connection.closed:
        connection.rollback()
        connection.close()

def test_get_connection_successful(connection_setup):
    setup = connection_setup
    try:
        setup["connection"] = datastore.get_connection()
        assert not setup["connection"].closed
    except Exception as e:
        pytest.fail(f"get_connection() raised an exception: {e}")

@patch('storage.datastore_storage_api.NACHET_DB_URL', 'postgresql://invalid_url')
@patch('storage.datastore_storage_api.NACHET_SCHEMA', 'nonexistent_schema')
def test_get_connection_error_invalid_params(connection_setup):
    setup = connection_setup
    with pytest.raises(datastore.DatastoreError):
        setup["connection"] = datastore.get_connection()

def test_get_cursor_successful(connection_setup):
    setup = connection_setup
    try:
        setup["connection"] = datastore.get_connection()
        setup["cursor"] = datastore.get_cursor(setup["connection"])
        assert not setup["cursor"].closed
    except Exception as e:
        pytest.fail(f"get_cursor() raised an exception: {e}")

def test_get_cursor_error_invalid_connection(connection_setup):
    mock_connection = MagicMock()
    mock_connection.cursor.side_effect = Exception('Connection error')
    with pytest.raises(datastore.DatastoreError):
        datastore.get_cursor(mock_connection)

def test_end_query_successful(connection_setup):
    setup = connection_setup
    try:
        setup["connection"] = datastore.get_connection()
        setup["cursor"] = datastore.get_cursor(setup["connection"])
        with patch.object(setup["connection"], 'commit'):
            datastore.end_query(setup["connection"], setup["cursor"])

        assert setup["connection"].closed
        assert setup["cursor"].closed
    except Exception as e:
        pytest.fail(f"end_query() raised an exception: {e}")

def test_end_query_error_invalid_connection():
    mock_connection = MagicMock()
    mock_connection.close.side_effect = Exception('Error')
    mock_cursor = MagicMock()
    mock_cursor.close.side_effect = Exception('Error')
    with pytest.raises(datastore.DatastoreError):
            datastore.end_query(mock_connection, mock_cursor)


@pytest.fixture
def seeds_getters_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    seeds = [{"seed_id": "test_seed_id", "seed_name": "test_seed_name"}]
    seeds_name = ["test_seed_name"]
    
    return {
        "test_client": test_client,
        "seeds": seeds,
        "seeds_name": seeds_name
    }

@pytest.mark.asyncio
async def test_get_all_seeds_successful(seeds_getters_setup):
    setup = seeds_getters_setup
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
            patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
        mock_get_seed_info = AsyncMock(return_value={'seeds': setup["seeds"]})
        
        with patch('storage.datastore_storage_api.nachet_datastore.get_seed_info', new=mock_get_seed_info):
            seeds = await datastore.get_all_seeds()
            
            assert seeds == {'seeds': setup["seeds"]}
            mock_get_seed_info.assert_awaited_with(mock_cursor)

@pytest.mark.asyncio
async def test_get_all_seeds_error():
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
            patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
        mock_get_seed_info = AsyncMock(side_effect=Exception('Seed not found'))
        
        with patch('storage.datastore_storage_api.nachet_datastore.get_seed_info', new=mock_get_seed_info):
            
            with pytest.raises(datastore.SeedNotFoundError):
                await datastore.get_all_seeds()

def test_get_all_seeds_names_successful(seeds_getters_setup):
    setup = seeds_getters_setup
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
            patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
        mock_get_all_seeds_names = MagicMock(return_value=setup["seeds_name"])
        
        with patch('storage.datastore_storage_api.seed_queries.get_all_seeds_names', new=mock_get_all_seeds_names):
            seeds_name = datastore.get_all_seeds_names()
            
            assert seeds_name == setup["seeds_name"]
            mock_get_all_seeds_names.assert_called_once_with(mock_cursor)

def test_get_all_seeds_names_error():
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
            patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
        mock_get_all_seeds_names = MagicMock(side_effect=Exception('Seed not found'))
        
        with patch('storage.datastore_storage_api.seed_queries.get_all_seeds_names', new=mock_get_all_seeds_names):
            
            with pytest.raises(datastore.SeedNotFoundError):
                datastore.get_all_seeds_names()

@pytest.fixture
def user_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    email = "example@gmail.com"
    user_id = "a427278e-28df-428f-8937-ddeeef44e72f"
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    
    return {
        "test_client": test_client,
        "email": email,
        "user_id": user_id,
        "connection_string": connection_string
    }

def test_get_user_id_successful(user_setup):
    setup = user_setup
    mock_is_user_registered = MagicMock(return_value=True)
    mock_get_user_id = MagicMock(return_value=setup["user_id"])

    with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
         patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
         patch('storage.datastore_storage_api.user_datastore.is_user_registered', new=mock_is_user_registered), \
         patch('storage.datastore_storage_api.user_datastore.get_user_id', new=mock_get_user_id), \
         patch('storage.datastore_storage_api.end_query') as mock_end_query :
         
        mock_connection = mock_get_connection.return_value
        mock_cursor = mock_get_cursor.return_value

        assert str(datastore.get_user_id(setup["email"])) == setup["user_id"]

        mock_get_connection.assert_called_once()
        mock_get_cursor.assert_called_once_with(mock_connection)
        mock_end_query.assert_called_once_with(mock_connection, mock_cursor)
        
        mock_is_user_registered.assert_called_once_with(mock_cursor, setup["email"])
        mock_get_user_id.assert_called_once_with(mock_cursor, setup["email"])

def test_get_user_id_error_user_not_found():
    email = "not-existing-user-email"
    mock_is_user_registered = MagicMock(return_value=False)
    
    with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
         patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
         patch('storage.datastore_storage_api.user_datastore.is_user_registered', new=mock_is_user_registered), \
         patch('storage.datastore_storage_api.end_query') as mock_end_query :
        
        mock_connection = mock_get_connection.return_value
        mock_cursor = mock_get_cursor.return_value

        with pytest.raises(datastore.DatastoreError):
            datastore.get_user_id(email)
        
        mock_get_connection.assert_called_once()
        mock_get_cursor.assert_called_once_with(mock_connection)
        mock_end_query.assert_called_once_with(mock_connection, mock_cursor)
        
        mock_is_user_registered.assert_called_once_with(mock_cursor, email)

@pytest.mark.asyncio
async def test_create_user_successful(user_setup):
    setup = user_setup
    mock_new_user = AsyncMock(return_value=datastore.datastore.User(setup["email"], setup["user_id"]))

    with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
         patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
         patch('storage.datastore_storage_api.datastore.new_user', new=mock_new_user), \
         patch('storage.datastore_storage_api.end_query') as mock_end_query:

        mock_connection = mock_get_connection.return_value
        mock_cursor = mock_get_cursor.return_value

        await datastore.create_user(setup["email"], setup["connection_string"])
        
        mock_get_connection.assert_called_once()
        mock_get_cursor.assert_called_once_with(mock_connection)
        mock_end_query.assert_called_once_with(mock_connection, mock_cursor)

        mock_new_user.assert_awaited_once_with(mock_cursor, setup["email"], setup["connection_string"])

@pytest.mark.asyncio
async def test_create_user_error(user_setup):
    setup = user_setup
    mock_new_user = AsyncMock(side_effect=Exception('User creation error'))

    with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
         patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
         patch('storage.datastore_storage_api.datastore.new_user', new=mock_new_user) :

        mock_connection = mock_get_connection.return_value
        with pytest.raises(datastore.DatastoreError):
            await datastore.create_user(setup["email"], setup["connection_string"])
        
        mock_get_connection.assert_called_once()
        mock_get_cursor.assert_called_once_with(mock_connection)

@pytest.fixture
def picture_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    mock_cursor = MagicMock()
    user_id = "test_user_id"
    mock_image = MagicMock()
    mock_container_client = MagicMock()
    picture_id = "test_picture_id"
    picture_set_id = "test_picture_set_id"
    seed_name = "test_seed_name"
    seed_id = "test_seed_name"
    folder_name = "test_folder_name"

    return {
        "test_client": test_client,
        "mock_cursor": mock_cursor,
        "user_id": user_id,
        "mock_image": mock_image,
        "mock_container_client": mock_container_client,
        "picture_id": picture_id,
        "picture_set_id": picture_set_id,
        "seed_name": seed_name,
        "seed_id": seed_id,
        "folder_name": folder_name
    }

@pytest.mark.asyncio
async def test_get_picture_id_successful(picture_setup):
    setup = picture_setup
    mock_upload_picture_unknown = AsyncMock(return_value=setup["picture_id"])
    with patch('storage.datastore_storage_api.nachet_datastore.upload_picture_unknown', new=mock_upload_picture_unknown) :
        assert str(await datastore.get_picture_id(setup["mock_cursor"], setup["user_id"], setup["mock_image"], setup["mock_container_client"])) == setup["picture_id"]
        mock_upload_picture_unknown.assert_awaited_once_with(setup["mock_cursor"], setup["user_id"], setup["mock_image"], setup["mock_container_client"])

@pytest.mark.asyncio
async def test_get_picture_id_error(picture_setup):
    setup = picture_setup
    mock_upload_picture_unknown = AsyncMock(side_effect=Exception('User not found error'))
    with patch('storage.datastore_storage_api.nachet_datastore.upload_picture_unknown', new=mock_upload_picture_unknown) :
        with pytest.raises(datastore.DatastoreError) :
            await datastore.get_picture_id(setup["mock_cursor"], setup["user_id"], setup["mock_image"], setup["mock_container_client"])
            mock_upload_picture_unknown.assert_awaited_once_with(setup["mock_cursor"], setup["user_id"], setup["mock_image"], setup["mock_container_client"])

@pytest.mark.asyncio
async def test_upload_pictures_successful(picture_setup):
    setup = picture_setup
    mock_upload_pictures = AsyncMock(return_value=[setup["picture_id"]])
    with patch('storage.datastore_storage_api.nachet_datastore.upload_pictures', new=mock_upload_pictures) :
        assert await datastore.upload_pictures(setup["mock_cursor"], setup["user_id"], setup["picture_set_id"], setup["mock_container_client"], [setup["mock_image"]], setup["seed_name"], setup["seed_id"]) == [setup["picture_id"]]
        mock_upload_pictures.assert_awaited_once_with(setup["mock_cursor"], setup["user_id"], setup["picture_set_id"], setup["mock_container_client"], [setup["mock_image"]], setup["seed_name"], setup["seed_id"], None, None)

@pytest.mark.asyncio
async def test_upload_pictures_error(picture_setup):
    setup = picture_setup
    mock_upload_pictures = AsyncMock(side_effect=Exception('User not found error'))
    with patch('storage.datastore_storage_api.nachet_datastore.upload_pictures', new=mock_upload_pictures) :
        with pytest.raises(datastore.DatastoreError) :
            await datastore.upload_pictures(setup["mock_cursor"], setup["user_id"], setup["picture_set_id"], setup["mock_container_client"], [setup["mock_image"]], setup["seed_name"], setup["seed_id"])
            mock_upload_pictures.assert_awaited_once_with(setup["mock_cursor"], setup["user_id"], setup["picture_set_id"], setup["mock_container_client"], [setup["mock_image"]], setup["seed_name"], setup["seed_id"], None, None)

@pytest.mark.asyncio
async def test_create_picture_set_successful(picture_setup):
    setup = picture_setup
    mock_create_picture_set = AsyncMock(return_value=setup["picture_set_id"])
    with patch('storage.datastore_storage_api.datastore.create_picture_set', new=mock_create_picture_set) :
        assert await datastore.create_picture_set(setup["mock_cursor"], setup["mock_container_client"], setup["user_id"], len([setup["mock_image"]]), setup["folder_name"]) == setup["picture_set_id"]
        mock_create_picture_set.assert_awaited_once_with(setup["mock_cursor"], setup["mock_container_client"], len([setup["mock_image"]]), setup["user_id"], setup["folder_name"])

@pytest.mark.asyncio
async def test_create_picture_set_error(picture_setup):
    setup = picture_setup
    mock_create_picture_set = AsyncMock(side_effect=Exception('User not found error'))
    with patch('storage.datastore_storage_api.datastore.create_picture_set', new=mock_create_picture_set) :
        with pytest.raises(datastore.DatastoreError) :
            await datastore.create_picture_set(setup["mock_cursor"], setup["mock_container_client"], setup["user_id"], len([setup["mock_image"]]), setup["folder_name"])
            mock_create_picture_set.assert_awaited_once_with(setup["mock_cursor"], setup["mock_container_client"], len([setup["mock_image"]]), setup["user_id"], setup["folder_name"])

@pytest.fixture
def pipelines_setup():
    """
    Set up the test environment before running each test case.
    """
    test_client = app.test_client()
    test_pipeline_id = "test_pipeline_id"
    connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")

    return {
        "test_client": test_client,
        "test_pipeline_id": test_pipeline_id,
        "connection_string": connection_string
    }

@pytest.mark.asyncio
async def test_get_pipelines_successful(pipelines_setup):
    setup = pipelines_setup
    mock_get_ml_structure = AsyncMock(return_value=[{'pipeline_id': setup["test_pipeline_id"]}])
    with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
         patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
         patch('storage.datastore_storage_api.nachet_datastore.get_ml_structure', new=mock_get_ml_structure):
        
        mock_connection = mock_get_connection.return_value
        mock_cursor = mock_get_cursor.return_value

        pipelines = await datastore.get_pipelines()

        assert pipelines == [{'pipeline_id': setup["test_pipeline_id"]}]
        mock_get_ml_structure.assert_awaited_once_with(mock_cursor)
        mock_get_cursor.assert_called_once_with(mock_connection)
        mock_get_connection.assert_called_once()

@pytest.mark.asyncio
async def test_get_pipelines_error():
    mock_get_ml_structure = AsyncMock(side_effect=Exception('Pipeline retrieval failed'))
    with patch('storage.datastore_storage_api.get_connection'), \
         patch('storage.datastore_storage_api.get_cursor'), \
         patch('storage.datastore_storage_api.nachet_datastore.get_ml_structure', new=mock_get_ml_structure):

        with pytest.raises(datastore.GetPipelinesError):
            await datastore.get_pipelines()

@pytest.fixture
def save_inference_result_setup():
    mock_cursor = MagicMock()
    test_user_id = "test_user_id"
    test_inference_dict = {'boxes': []}
    test_picture_id = "test_picture_id"
    test_pipeline_id = "test_pipeline_id"
    test_type = 1

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_inference_dict": test_inference_dict,
        "test_picture_id": test_picture_id,
        "test_pipeline_id": test_pipeline_id,
        "test_type": test_type
    }

@pytest.mark.asyncio
async def test_save_inference_result_successful(save_inference_result_setup):
    setup = save_inference_result_setup
    with patch('storage.datastore_storage_api.nachet_datastore.register_inference_result', new_callable=AsyncMock) as mock_register_inference_result:
        mock_register_inference_result.return_value = setup["test_inference_dict"]
        result = await datastore.save_inference_result(
            setup["mock_cursor"], setup["test_user_id"], 
            setup["test_inference_dict"], setup["test_picture_id"], 
            setup["test_pipeline_id"], setup["test_type"]
        )
        mock_register_inference_result.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_user_id"], 
            setup["test_inference_dict"], setup["test_picture_id"], 
            setup["test_pipeline_id"], setup["test_type"]
        )
        assert result == setup["test_inference_dict"]

@pytest.mark.asyncio
async def test_save_inference_result_error(save_inference_result_setup):
    setup = save_inference_result_setup
    with patch('storage.datastore_storage_api.nachet_datastore.register_inference_result', new_callable=AsyncMock) as mock_register_inference_result:
        mock_register_inference_result.side_effect = Exception('Save inference failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.save_inference_result(
                setup["mock_cursor"], setup["test_user_id"], 
                setup["test_inference_dict"], setup["test_picture_id"], 
                setup["test_pipeline_id"], setup["test_type"]
            )

@pytest.fixture
def save_feedback_setup():
    mock_cursor = AsyncMock()
    test_user_id = "test_user_id"
    test_inference_id = "test_inference_id"
    test_feedback_dict = {'boxes': []}
    test_boxes_id = ["box1", "box2"]

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_inference_id": test_inference_id,
        "test_feedback_dict": test_feedback_dict,
        "test_boxes_id": test_boxes_id
    }

@pytest.mark.asyncio
async def test_save_perfect_feedback_successful(save_feedback_setup):
    setup = save_feedback_setup
    with patch('storage.datastore_storage_api.nachet_datastore.new_perfect_inference_feeback', new_callable=AsyncMock) as mock_new_perfect_feedback:
        await datastore.save_perfect_feedback(
            setup["mock_cursor"], setup["test_inference_id"], 
            setup["test_user_id"], setup["test_boxes_id"]
        )
        mock_new_perfect_feedback.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_inference_id"], 
            setup["test_user_id"], setup["test_boxes_id"]
        )

@pytest.mark.asyncio
async def test_save_perfect_feedback_error(save_feedback_setup):
    setup = save_feedback_setup
    with patch('storage.datastore_storage_api.nachet_datastore.new_perfect_inference_feeback', new_callable=AsyncMock) as mock_new_perfect_feedback:
        mock_new_perfect_feedback.side_effect = Exception('Save perfect feedback failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.save_perfect_feedback(
                setup["mock_cursor"], setup["test_inference_id"], 
                setup["test_user_id"], setup["test_boxes_id"]
            )

@pytest.mark.asyncio
async def test_save_annoted_feedback_successful(save_feedback_setup):
    setup = save_feedback_setup
    with patch('storage.datastore_storage_api.nachet_datastore.new_correction_inference_feedback', new_callable=AsyncMock) as mock_new_correction_feedback:
        await datastore.save_annoted_feedback(
            setup["mock_cursor"], setup["test_feedback_dict"]
        )
        mock_new_correction_feedback.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_feedback_dict"]
        )

@pytest.mark.asyncio
async def test_save_annoted_feedback_error(save_feedback_setup):
    setup = save_feedback_setup
    with patch('storage.datastore_storage_api.nachet_datastore.new_correction_inference_feedback', new_callable=AsyncMock) as mock_new_correction_feedback:
        mock_new_correction_feedback.side_effect = Exception('Save annoted feedback failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.save_annoted_feedback(
                setup["mock_cursor"], setup["test_feedback_dict"]
            )

@pytest.fixture
def delete_directories_setup():
    mock_cursor = AsyncMock()
    test_user_id = "test_user_id"
    test_picture_set_id = "test_picture_set_id"
    test_validated_pictures = ['picture1', 'picture2']
    mock_container_client = MagicMock()

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_picture_set_id": test_picture_set_id,
        "test_validated_pictures": test_validated_pictures,
        "mock_container_client": mock_container_client
    }

@pytest.mark.asyncio
async def test_delete_directory_request_successful(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.find_validated_pictures', new_callable=AsyncMock) as mock_find_validated_pictures:
        mock_find_validated_pictures.return_value = setup["test_validated_pictures"]
        assert await datastore.delete_directory_request(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"])
        mock_find_validated_pictures.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_user_id"],
            setup["test_picture_set_id"]
        )

@pytest.mark.asyncio
async def test_delete_directory_request_error(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.find_validated_pictures', new_callable=AsyncMock) as mock_find_validated_pictures:
        mock_find_validated_pictures.side_effect = Exception('Search for validated pictures failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.delete_directory_request(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"])

@pytest.mark.asyncio
async def test_delete_directory_permanently_successful(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.datastore.delete_picture_set_permanently', new_callable=AsyncMock) as mock_delete_permanently:
        mock_delete_permanently.return_value = True
        assert await datastore.delete_directory_permanently(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"], setup["mock_container_client"])
        mock_delete_permanently.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_user_id"],
            setup["test_picture_set_id"], setup["mock_container_client"]
        )

@pytest.mark.asyncio
async def test_delete_directory_permanently_error(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.datastore.delete_picture_set_permanently', new_callable=AsyncMock) as mock_delete_permanently:
        mock_delete_permanently.side_effect = Exception('Search for validated pictures failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.delete_directory_permanently(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"], setup["mock_container_client"])

@pytest.mark.asyncio
async def test_delete_directory_with_archive_successful(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.delete_picture_set_with_archive', new_callable=AsyncMock) as mock_delete_with_archive:
        mock_delete_with_archive.return_value = True
        assert await datastore.delete_directory_with_archive(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"], setup["mock_container_client"])
        mock_delete_with_archive.assert_awaited_once_with(
            setup["mock_cursor"], setup["test_user_id"],
            setup["test_picture_set_id"], setup["mock_container_client"]
            )

@pytest.mark.asyncio
async def test_delete_directory_with_archive_error(delete_directories_setup):
    setup = delete_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.delete_picture_set_with_archive', new_callable=AsyncMock) as mock_delete_with_archive:
        mock_delete_with_archive.side_effect = Exception('Search for validated pictures failed')
        with pytest.raises(datastore.DatastoreError):
            await datastore.delete_directory_with_archive(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_set_id"], setup["mock_container_client"])

@pytest.fixture
def get_directories_setup():
    mock_cursor = AsyncMock()
    test_user_id = "test_user_id"
    test_picture_set_id = "test_picture_set_id"
    folder_name = "test_folder_name"
    test_picture_sets = [{'picture_set_id': test_picture_set_id, 'folder_name': folder_name}]

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_picture_set_id": test_picture_set_id,
        "folder_name": folder_name,
        "test_picture_sets": test_picture_sets
    }

@pytest.mark.asyncio
async def test_get_directories_successful(get_directories_setup):
    setup = get_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_sets_info', new_callable=AsyncMock) as mock_get_picture_sets_info:
        mock_get_picture_sets_info.return_value = setup["test_picture_sets"]
        directories_info = await datastore.get_directories(setup["mock_cursor"], setup["test_user_id"])
        assert directories_info == setup["test_picture_sets"]

@pytest.mark.asyncio
async def test_get_directories_error(get_directories_setup):
    setup = get_directories_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_sets_info', new_callable=AsyncMock) as mock_get_picture_sets_info:
        mock_get_picture_sets_info.side_effect = Exception('Failed to retrieve directories information')
        with pytest.raises(datastore.DatastoreError):
            await datastore.get_directories(setup["mock_cursor"], setup["test_user_id"])

@pytest.fixture
def get_inference_setup():
    mock_cursor = AsyncMock()
    test_user_id = "test_user_id"
    test_picture_id = "test_picture_id"
    test_inference_id = "test_inference_id"
    test_inference_dict = {'boxes': []}

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_picture_id": test_picture_id,
        "test_inference_id": test_inference_id,
        "test_inference_dict": test_inference_dict
    }

@pytest.mark.asyncio
async def test_get_inference_successful(get_inference_setup):
    setup = get_inference_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_inference', new_callable=AsyncMock) as mock_get_inference:
        mock_get_inference.return_value = setup["test_inference_dict"]
        
        result = await datastore.get_inference(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_id"])
        assert result == setup["test_inference_dict"]
        mock_get_inference.assert_awaited_once_with(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_id"], None)

        result = await datastore.get_inference(setup["mock_cursor"], setup["test_user_id"], inference_id=setup["test_inference_id"])
        assert result == setup["test_inference_dict"]
        mock_get_inference.assert_awaited_with(setup["mock_cursor"], setup["test_user_id"], None, setup["test_inference_id"])

@pytest.mark.asyncio
async def test_get_inference_error(get_inference_setup):
    setup = get_inference_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_inference', new_callable=AsyncMock) as mock_get_inference:
        mock_get_inference.side_effect = Exception('Failed to retrieve inference information')
        with pytest.raises(datastore.DatastoreError):
            await datastore.get_inference(setup["mock_cursor"], setup["test_user_id"], setup["test_picture_id"])

@pytest.fixture
def get_picture_blob_setup():
    mock_cursor = AsyncMock()
    test_user_id = "test_user_id"
    test_picture_id = "test_picture_id"
    mock_container_client = MagicMock()
    mock_blob = MagicMock()

    return {
        "mock_cursor": mock_cursor,
        "test_user_id": test_user_id,
        "test_picture_id": test_picture_id,
        "mock_container_client": mock_container_client,
        "mock_blob": mock_blob
    }

@pytest.mark.asyncio
async def test_get_picture_blob_successful(get_picture_blob_setup):
    setup = get_picture_blob_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_blob', new_callable=AsyncMock) as mock_get_picture_blob:
        mock_get_picture_blob.return_value = setup["mock_blob"]
        result = await datastore.get_picture_blob(setup["mock_cursor"], setup["test_user_id"], setup["mock_container_client"], setup["test_picture_id"])
        assert result == setup["mock_blob"]

@pytest.mark.asyncio
async def test_get_picture_blob_error(get_picture_blob_setup):
    setup = get_picture_blob_setup
    with patch('storage.datastore_storage_api.nachet_datastore.get_picture_blob', new_callable=AsyncMock) as mock_get_picture_blob:
        mock_get_picture_blob.side_effect = Exception('Failed to retrieve directories information')
        with pytest.raises(datastore.DatastoreError):
            await datastore.get_picture_blob(setup["mock_cursor"], setup["test_user_id"], setup["mock_container_client"], setup["test_picture_id"])