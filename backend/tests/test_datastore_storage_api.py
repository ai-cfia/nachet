import os
import unittest
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

class TestConnection(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.connection = None
        self.cursor = None
    
    def tearDown(self) -> None:
        self.test_client = None
        if self.cursor and not self.cursor.closed:
            self.cursor.close()
        if self.connection and not self.connection.closed:
            self.connection.rollback()
            self.connection.close()

    def test_get_connection_successful(self):
        try :
            self.connection = datastore.get_connection()
            self.assertFalse(self.connection.closed)
        except Exception as e:
            self.fail(f"get_connection() raised an exception: {e}")

    @patch('storage.datastore_storage_api.NACHET_DB_URL', 'postgresql://invalid_url')
    @patch('storage.datastore_storage_api.NACHET_SCHEMA', 'nonexistent_schema')
    def test_get_connection_error_invalid_params(self):
        with self.assertRaises(datastore.DatastoreError):
            self.connection = datastore.get_connection()

    def test_get_cursor_successful(self):
        try :
            self.connection = datastore.get_connection()
            self.cursor = datastore.get_cursor(self.connection)
            self.assertFalse(self.cursor.closed)
        except Exception as e:
            self.fail(f"get_cursor() raised an exception: {e}")

    def test_get_cursor_error_invalid_connection(self):
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = Exception('Connection error')
        with self.assertRaises(datastore.DatastoreError):
            self.cursor = datastore.get_cursor(mock_connection)

    def test_end_query_successful(self):
        try :
            self.connection = datastore.get_connection()
            self.cursor = datastore.get_cursor(self.connection)
            with patch.object(self.connection, 'commit') :
                datastore.end_query(self.connection, self.cursor)

            self.assertTrue(self.connection.closed)
            self.assertTrue(self.cursor.closed)
        except Exception as e:
            self.fail(f"end_query() raised an exception: {e}")

    def test_end_query_error_invalid_connection(self):
        mock_connection = MagicMock()
        mock_connection.close.side_effect = Exception('Error')
        mock_cursor = MagicMock()
        mock_cursor.close.side_effect = Exception('Error')
        with self.assertRaises(datastore.DatastoreError):
                datastore.end_query(mock_connection, mock_cursor)


class TestSeedsGetters(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.seeds = [{"seed_id": "test_seed_id", "seed_name": "test_seed_name"}]
        self.seeds_name = ["test_seed_name"]
    
    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_all_seeds_successful(self):
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
                patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
            mock_get_seed_info = AsyncMock(return_value={'seeds': self.seeds})
            
            with patch('storage.datastore_storage_api.nachet_datastore.get_seed_info', new=mock_get_seed_info):
                seeds = await datastore.get_all_seeds()
                
                self.assertEqual(seeds, {'seeds': self.seeds})
                mock_get_seed_info.assert_awaited_with(mock_cursor)

    async def test_get_all_seeds_error(self):
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
                patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
            mock_get_seed_info = AsyncMock(side_effect=Exception('Seed not found'))
            
            with patch('storage.datastore_storage_api.nachet_datastore.get_seed_info', new=mock_get_seed_info):
                
                with self.assertRaises(datastore.SeedNotFoundError):
                    await datastore.get_all_seeds()

    def test_get_all_seeds_names_successful(self):
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
                patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
            mock_get_all_seeds_names = MagicMock(return_value=self.seeds_name)
            
            with patch('storage.datastore_storage_api.seed_queries.get_all_seeds_names', new=mock_get_all_seeds_names):
                seeds_name = datastore.get_all_seeds_names()
                
                self.assertEqual(seeds_name, self.seeds_name)
                mock_get_all_seeds_names.assert_called_once_with(mock_cursor)

    def test_get_all_seeds_names_error(self):
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        with patch('storage.datastore_storage_api.get_connection', return_value=mock_connection), \
                patch('storage.datastore_storage_api.get_cursor', return_value=mock_cursor):
            mock_get_all_seeds_names = MagicMock(side_effect=Exception('Seed not found'))
            
            with patch('storage.datastore_storage_api.seed_queries.get_all_seeds_names', new=mock_get_all_seeds_names):
                
                with self.assertRaises(datastore.SeedNotFoundError):
                    datastore.get_all_seeds_names()

class TestUser(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.email = "example@gmail.com"
        self.user_id = "a427278e-28df-428f-8937-ddeeef44e72f"
        self.connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")
    
    def tearDown(self) -> None:
        self.test_client = None
    
    def test_get_user_id_successful(self):
        mock_is_user_registered = MagicMock(return_value=True)
        mock_get_user_id = MagicMock(return_value=self.user_id)

        with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
             patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
             patch('storage.datastore_storage_api.user_datastore.is_user_registered', new=mock_is_user_registered), \
             patch('storage.datastore_storage_api.user_datastore.get_user_id', new=mock_get_user_id), \
             patch('storage.datastore_storage_api.end_query') as mock_end_query :
             
            mock_connection = mock_get_connection.return_value
            mock_cursor = mock_get_cursor.return_value

            self.assertEqual(str(datastore.get_user_id(self.email)), self.user_id)

            mock_get_connection.assert_called_once()
            mock_get_cursor.assert_called_once_with(mock_connection)
            mock_end_query.assert_called_once_with(mock_connection, mock_cursor)
            
            mock_is_user_registered.assert_called_once_with(mock_cursor, self.email)
            mock_get_user_id.assert_called_once_with(mock_cursor, self.email)

    def test_get_user_id_error_user_not_found(self):
        email = "not-existing-user-email"
        mock_is_user_registered = MagicMock(return_value=False)
        
        with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
             patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
             patch('storage.datastore_storage_api.user_datastore.is_user_registered', new=mock_is_user_registered), \
             patch('storage.datastore_storage_api.end_query') as mock_end_query :
            
            mock_connection = mock_get_connection.return_value
            mock_cursor = mock_get_cursor.return_value

            with self.assertRaises(datastore.DatastoreError):
                datastore.get_user_id(email)
            
            mock_get_connection.assert_called_once()
            mock_get_cursor.assert_called_once_with(mock_connection)
            mock_end_query.assert_called_once_with(mock_connection, mock_cursor)
            
            mock_is_user_registered.assert_called_once_with(mock_cursor, email)

    async def test_create_user_successful(self):
        mock_new_user = AsyncMock(return_value=datastore.datastore.User(self.email, self.user_id))

        with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
             patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
             patch('storage.datastore_storage_api.datastore.new_user', new=mock_new_user), \
             patch('storage.datastore_storage_api.end_query') as mock_end_query:

            mock_connection = mock_get_connection.return_value
            mock_cursor = mock_get_cursor.return_value

            await datastore.create_user(self.email, self.connection_string)
            
            mock_get_connection.assert_called_once()
            mock_get_cursor.assert_called_once_with(mock_connection)
            mock_end_query.assert_called_once_with(mock_connection, mock_cursor)

            mock_new_user.assert_awaited_once_with(mock_cursor, self.email, self.connection_string)

    async def test_create_user_error(self):
        mock_new_user = AsyncMock(side_effect=Exception('User creation error'))

        with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
             patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
             patch('storage.datastore_storage_api.datastore.new_user', new=mock_new_user) :

            mock_connection = mock_get_connection.return_value
            with self.assertRaises(datastore.DatastoreError):
                await datastore.create_user(self.email, self.connection_string)
            
            mock_get_connection.assert_called_once()
            mock_get_cursor.assert_called_once_with(mock_connection)

class TestPicture(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.mock_cursor = MagicMock()
        self.user_id = "test_user_id"
        self.mock_image = MagicMock()
        self.mock_container_client = MagicMock()
        self.picture_id = "test_picture_id"
        self.picture_set_id = "test_picture_set_id"
        self.seed_name = "test_seed_name"
        self.seed_id = "test_seed_name"
        self.folder_name = "test_folder_name"

    
    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_picture_id_successful(self):
        mock_upload_picture_unknown = AsyncMock(return_value=self.picture_id)
        with patch('storage.datastore_storage_api.nachet_datastore.upload_picture_unknown', new=mock_upload_picture_unknown) :
            self.assertEqual(str(await datastore.get_picture_id(self.mock_cursor, self.user_id, self.mock_image, self.mock_container_client)), self.picture_id)
            mock_upload_picture_unknown.assert_awaited_once_with(self.mock_cursor, self.user_id, self.mock_image, self.mock_container_client)

    async def test_get_picture_id_error(self):
        mock_upload_picture_unknown = AsyncMock(side_effect=Exception('User not found error'))
        with patch('storage.datastore_storage_api.nachet_datastore.upload_picture_unknown', new=mock_upload_picture_unknown) :
            with self.assertRaises(datastore.DatastoreError) :
                await datastore.get_picture_id(self.mock_cursor, self.user_id, self.mock_image, self.mock_container_client)
                mock_upload_picture_unknown.assert_awaited_once_with(self.mock_cursor, self.user_id, self.mock_image, self.mock_container_client)

    async def test_upload_pictures_successful(self):
        mock_upload_pictures = AsyncMock(return_value=[self.picture_id])
        with patch('storage.datastore_storage_api.nachet_datastore.upload_pictures', new=mock_upload_pictures) :
            self.assertEqual(await datastore.upload_pictures(self.mock_cursor, self.user_id, self.picture_set_id, self.mock_container_client, [self.mock_image], self.seed_name, self.seed_id), [self.picture_id])
            mock_upload_pictures.assert_awaited_once_with(self.mock_cursor, self.user_id, self.picture_set_id, self.mock_container_client, [self.mock_image], self.seed_name, self.seed_id, None, None)
    
    async def test_upload_pictures_error(self):
        mock_upload_pictures = AsyncMock(side_effect=Exception('User not found error'))
        with patch('storage.datastore_storage_api.nachet_datastore.upload_pictures', new=mock_upload_pictures) :
            with self.assertRaises(datastore.DatastoreError) :
                await datastore.upload_pictures(self.mock_cursor, self.user_id, self.picture_set_id, self.mock_container_client, [self.mock_image], self.seed_name, self.seed_id)
                mock_upload_pictures.assert_awaited_once_with(self.mock_cursor, self.user_id, self.picture_set_id, self.mock_container_client, [self.mock_image], self.seed_name, self.seed_id, None, None)

    async def test_create_picture_set_successful(self):
        mock_create_picture_set = AsyncMock(return_value=self.picture_set_id)
        with patch('storage.datastore_storage_api.datastore.create_picture_set', new=mock_create_picture_set) :
            self.assertEqual(await datastore.create_picture_set(self.mock_cursor, self.mock_container_client, self.user_id, len([self.mock_image]), self.folder_name), self.picture_set_id)
            mock_create_picture_set.assert_awaited_once_with(self.mock_cursor, self.mock_container_client, len([self.mock_image]), self.user_id, self.folder_name)
    
    async def test_create_picture_set_error(self):
        mock_create_picture_set = AsyncMock(side_effect=Exception('User not found error'))
        with patch('storage.datastore_storage_api.datastore.create_picture_set', new=mock_create_picture_set) :
            with self.assertRaises(datastore.DatastoreError) :
                await datastore.create_picture_set(self.mock_cursor, self.mock_container_client, self.user_id, len([self.mock_image]), self.folder_name)
                mock_create_picture_set.assert_awaited_once_with(self.mock_cursor, self.mock_container_client, len([self.mock_image]), self.user_id, self.folder_name)

class TestPipelines(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.test_pipeline_id = "test_pipeline_id"
        self.connection_string = os.getenv("NACHET_AZURE_STORAGE_CONNECTION_STRING")

    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_pipelines_successful(self):
        mock_get_ml_structure = AsyncMock(return_value=[{'pipeline_id': self.test_pipeline_id}])
        with patch('storage.datastore_storage_api.get_connection') as mock_get_connection, \
             patch('storage.datastore_storage_api.get_cursor') as mock_get_cursor, \
             patch('storage.datastore_storage_api.nachet_datastore.get_ml_structure', new=mock_get_ml_structure):
            
            mock_connection = mock_get_connection.return_value
            mock_cursor = mock_get_cursor.return_value

            pipelines = await datastore.get_pipelines()

            self.assertEqual(pipelines, [{'pipeline_id': self.test_pipeline_id}])
            mock_get_ml_structure.assert_awaited_once_with(mock_cursor)
            mock_get_cursor.assert_called_once_with(mock_connection)
            mock_get_connection.assert_called_once()

    async def test_get_pipelines_error(self):
        mock_get_ml_structure = AsyncMock(side_effect=Exception('Pipeline retrieval failed'))
        with patch('storage.datastore_storage_api.get_connection'), \
             patch('storage.datastore_storage_api.get_cursor'), \
             patch('storage.datastore_storage_api.nachet_datastore.get_ml_structure', new=mock_get_ml_structure):

            with self.assertRaises(datastore.GetPipelinesError):
                await datastore.get_pipelines()

class TestSaveInferenceResult(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = MagicMock()
        self.test_user_id = "test_user_id"
        self.test_inference_dict = {'boxes': []}
        self.test_picture_id = "test_picture_id"
        self.test_pipeline_id = "test_pipeline_id"
        self.test_type = 1

    async def test_save_inference_result_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.register_inference_result', new_callable=AsyncMock) as mock_register_inference_result:
            mock_register_inference_result.return_value = self.test_inference_dict
            result = await datastore.save_inference_result(
                self.mock_cursor, self.test_user_id, 
                self.test_inference_dict, self.test_picture_id, 
                self.test_pipeline_id, self.test_type
            )
            mock_register_inference_result.assert_awaited_once_with(
                self.mock_cursor, self.test_user_id, 
                self.test_inference_dict, self.test_picture_id, 
                self.test_pipeline_id, self.test_type
            )
            self.assertEqual(result, self.test_inference_dict)

    async def test_save_inference_result_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.register_inference_result', new_callable=AsyncMock) as mock_register_inference_result:
            mock_register_inference_result.side_effect = Exception('Save inference failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.save_inference_result(
                    self.mock_cursor, self.test_user_id, 
                    self.test_inference_dict, self.test_picture_id, 
                    self.test_pipeline_id, self.test_type
                )

class TestSaveFeedback(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = AsyncMock()
        self.test_user_id = "test_user_id"
        self.test_inference_id = "test_inference_id"
        self.test_feedback_dict = {'boxes': []}
        self.test_boxes_id = ["box1", "box2"]

    def tearDown(self) -> None:
        self.test_client = None

    async def test_save_perfect_feedback_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.new_perfect_inference_feeback', new_callable=AsyncMock) as mock_new_perfect_feedback:
            await datastore.save_perfect_feedback(
                self.mock_cursor, self.test_inference_id, 
                self.test_user_id, self.test_boxes_id
            )
            mock_new_perfect_feedback.assert_awaited_once_with(
                self.mock_cursor, self.test_inference_id, 
                self.test_user_id, self.test_boxes_id
            )

    async def test_save_perfect_feedback_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.new_perfect_inference_feeback', new_callable=AsyncMock) as mock_new_perfect_feedback:
            mock_new_perfect_feedback.side_effect = Exception('Save perfect feedback failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.save_perfect_feedback(
                    self.mock_cursor, self.test_inference_id, 
                    self.test_user_id, self.test_boxes_id
                )

    async def test_save_annoted_feedback_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.new_correction_inference_feedback', new_callable=AsyncMock) as mock_new_correction_feedback:
            await datastore.save_annoted_feedback(
                self.mock_cursor, self.test_feedback_dict
            )
            mock_new_correction_feedback.assert_awaited_once_with(
                self.mock_cursor, self.test_feedback_dict
            )

    async def test_save_annoted_feedback_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.new_correction_inference_feedback', new_callable=AsyncMock) as mock_new_correction_feedback:
            mock_new_correction_feedback.side_effect = Exception('Save annoted feedback failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.save_annoted_feedback(
                    self.mock_cursor, self.test_feedback_dict
                )

class TestDeleteDirectories(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = AsyncMock()
        self.test_user_id = "test_user_id"
        self.test_picture_set_id = "test_picture_set_id"
        self.test_validated_pictures = ['picture1', 'picture2']
        self.mock_container_client = MagicMock()

    def tearDown(self) -> None:
        self.test_client = None

    async def test_delete_directory_request_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.find_validated_pictures', new_callable=AsyncMock) as mock_find_validated_pictures:
            mock_find_validated_pictures.return_value = self.test_validated_pictures
            self.assertTrue(await datastore.delete_directory_request(self.mock_cursor, self.test_user_id, self.test_picture_set_id))
            mock_find_validated_pictures.assert_awaited_once_with(
                self.mock_cursor, self.test_user_id,
                self.test_picture_set_id
            )

    async def test_delete_directory_request_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.find_validated_pictures', new_callable=AsyncMock) as mock_find_validated_pictures:
            mock_find_validated_pictures.side_effect = Exception('Search for validated pictures failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.delete_directory_request(self.mock_cursor, self.test_user_id, self.test_picture_set_id)

    async def test_delete_directory_permanently_successful(self):
        with patch('storage.datastore_storage_api.datastore.delete_picture_set_permanently', new_callable=AsyncMock) as mock_delete_permanently:
            mock_delete_permanently.return_value = True
            self.assertTrue(await datastore.delete_directory_permanently(self.mock_cursor, self.test_user_id, self.test_picture_set_id, self.mock_container_client))
            mock_delete_permanently.assert_awaited_once_with(
                self.mock_cursor, self.test_user_id,
                self.test_picture_set_id, self.mock_container_client
            )

    async def test_delete_directory_permanently_error(self):
        with patch('storage.datastore_storage_api.datastore.delete_picture_set_permanently', new_callable=AsyncMock) as mock_delete_permanently:
            mock_delete_permanently.side_effect = Exception('Search for validated pictures failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.delete_directory_permanently(self.mock_cursor, self.test_user_id, self.test_picture_set_id, self.mock_container_client)

    async def test_delete_directory_with_archive_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.delete_picture_set_with_archive', new_callable=AsyncMock) as mock_delete_with_archive:
            mock_delete_with_archive.return_value = True
            self.assertTrue(await datastore.delete_directory_with_archive(self.mock_cursor, self.test_user_id, self.test_picture_set_id, self.mock_container_client))
            mock_delete_with_archive.assert_awaited_once_with(
                self.mock_cursor, self.test_user_id,
                self.test_picture_set_id, self.mock_container_client
                )

    async def test_delete_directory_with_archive_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.delete_picture_set_with_archive', new_callable=AsyncMock) as mock_delete_with_archive:
            mock_delete_with_archive.side_effect = Exception('Search for validated pictures failed')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.delete_directory_with_archive(self.mock_cursor, self.test_user_id, self.test_picture_set_id, self.mock_container_client)

class TestGetDirectories(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = AsyncMock()
        self.test_user_id = "test_user_id"
        self.test_picture_set_id = "test_picture_set_id"
        self.folder_name = "test_folder_name"
        self.test_picture_sets = [{'picture_set_id': self.test_picture_set_id, 'folder_name': self.folder_name}]

    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_directories_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_sets_info', new_callable=AsyncMock) as mock_get_picture_sets_info:
            mock_get_picture_sets_info.return_value = self.test_picture_sets
            directories_info = await datastore.get_directories(self.mock_cursor, self.test_user_id)
            self.assertEqual(directories_info, self.test_picture_sets)

    async def test_get_directories_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_sets_info', new_callable=AsyncMock) as mock_get_picture_sets_info:
            mock_get_picture_sets_info.side_effect = Exception('Failed to retrieve directories information')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.get_directories(self.mock_cursor, self.test_user_id)

class TestGetInference(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = AsyncMock()
        self.test_user_id = "test_user_id"
        self.test_picture_id = "test_picture_id"
        self.test_inference_id = "test_inference_id"
        self.test_inference_dict = {'boxes': []}

    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_inference_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_inference', new_callable=AsyncMock) as mock_get_inference:
            mock_get_inference.return_value = self.test_inference_dict
            
            result = await datastore.get_inference(self.mock_cursor, self.test_user_id, self.test_picture_id)
            self.assertEqual(result, self.test_inference_dict)
            mock_get_inference.assert_awaited_once_with(self.mock_cursor, self.test_user_id, self.test_picture_id, None)

            result = await datastore.get_inference(self.mock_cursor, self.test_user_id, inference_id=self.test_inference_id)
            self.assertEqual(result, self.test_inference_dict)
            mock_get_inference.assert_awaited_with(self.mock_cursor, self.test_user_id, None, self.test_inference_id)

    async def test_get_inference_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_inference', new_callable=AsyncMock) as mock_get_inference:
            mock_get_inference.side_effect = Exception('Failed to retrieve inference information')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.get_inference(self.mock_cursor, self.test_user_id, self.test_picture_id)

class TestGetPictureBlob(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_cursor = AsyncMock()
        self.test_user_id = "test_user_id"
        self.test_picture_id = "test_picture_id"
        self.mock_container_client = MagicMock()
        self.mock_blob = MagicMock()

    def tearDown(self) -> None:
        self.test_client = None

    async def test_get_picture_blob_successful(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_blob', new_callable=AsyncMock) as mock_get_picture_blob:
            mock_get_picture_blob.return_value = self.mock_blob
            result = await datastore.get_picture_blob(self.mock_cursor, self.test_user_id, self.mock_container_client, self.test_picture_id)
            self.assertEqual(result, self.mock_blob)

    async def test_get_picture_blob_error(self):
        with patch('storage.datastore_storage_api.nachet_datastore.get_picture_blob', new_callable=AsyncMock) as mock_get_picture_blob:
            mock_get_picture_blob.side_effect = Exception('Failed to retrieve directories information')
            with self.assertRaises(datastore.DatastoreError):
                await datastore.get_picture_blob(self.mock_cursor, self.test_user_id, self.mock_container_client, self.test_picture_id)
