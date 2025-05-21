import os
import unittest
import asyncio
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

class TestCreateFolder(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.container_name = "test_container_name"
        self.folder_name = "test_folder_name"
        self.picture_set_id = "picture_set_id"
        
        # Mock the azure_storage and database variables
        self.mock_cur = MagicMock()     
        self.mock_connection = MagicMock()
        self.mock_container_client = MagicMock()
        
        # Patch the azure_storage and datastore functions
        self.patch_connect_db = patch('app.datastore.db.connect_db', return_value=self.mock_connection)
        self.patch_cursor = patch('app.datastore.db.cursor', return_value=self.mock_cur)
        self.patch_mount_container = patch('app.azure_storage.mount_container', return_value=self.mock_container_client)
        self.patch_create_picture_set = patch('app.datastore.create_picture_set', return_value = self.picture_set_id)
        self.patch_end_query = patch('app.datastore.end_query')
        
        self.mock_connect_db = self.patch_connect_db.start()
        self.mock_cursor = self.patch_cursor.start()
        self.mock_mount_container = self.patch_mount_container.start()
        self.mock_create_picture_set = self.patch_create_picture_set.start()
        self.mock_end_query = self.patch_end_query.start()

    def tearDown(self) -> None:
        """
        Tear down the test environment at the end of each test case.
        """
        self.test_client = None
        self.patch_connect_db.stop()
        self.patch_cursor.stop()
        self.patch_mount_container.stop()
        self.patch_create_picture_set.stop()
        self.patch_end_query.stop()


    def test_create_directory_successful(self):
        """
        Test the directory creation route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/create-dir',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": self.folder_name
                })
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(asyncio.run(response.get_data())), [self.picture_set_id])
        self.mock_mount_container.assert_called_once_with(CONNECTION_STRING, self.container_name, create_container=True)
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_create_picture_set.assert_called_once_with(self.mock_cur, self.mock_container_client, self.container_name, 0, self.folder_name)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)
     
    def test_create_directory_missing_argument_error(self):
        """
        Test the directory creation route with unsuccessful conditions : missing argument.
        """
        expected = ("API Error creating directory : missing container or directory name")
        
        response = asyncio.run(
            self.test_client.post(
                '/create-dir',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": ""
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
        
    def test_create_directory_datastore_error(self):
        """
        Test the directory creation route with unsuccessful conditions : an error from datastore is raised.
        """
        expected = ("Datastore Error creating directory : An error occured during the upload of the picture set")
        self.mock_create_picture_set.side_effect = DatastoreError("An error occured during the upload of the picture set")
        
        response = asyncio.run(
            self.test_client.post(
                '/create-dir',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": self.folder_name
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
    
class TestGetFolders(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.container_name = "test_container_name"
        self.folders_data = [
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
        self.mock_cur = MagicMock()     
        self.mock_connection = MagicMock()
        
        # Patch the azure_storage and datastore functions
        self.patch_connect_db = patch('app.datastore.db.connect_db', return_value=self.mock_connection)
        self.patch_cursor = patch('app.datastore.db.cursor', return_value=self.mock_cur)
        self.patch_get_directories = patch('app.datastore.get_directories', return_value = self.folders_data)
        self.patch_end_query = patch('app.datastore.end_query')
        
        self.mock_connect_db = self.patch_connect_db.start()
        self.mock_cursor = self.patch_cursor.start()
        self.mock_get_directories = self.patch_get_directories.start()
        self.mock_end_query = self.patch_end_query.start()

    def tearDown(self) -> None:
        """
        Tear down the test environment at the end of each test case.
        """
        self.test_client = None
        self.patch_connect_db.stop()
        self.patch_cursor.stop()
        self.patch_get_directories.stop()
        self.patch_end_query.stop()

    def test_get_directories_successful(self):
        """
        Test the get directories route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/get-directories',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name
                })
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(asyncio.run(response.get_data())), {"folders" : self.folders_data})
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_get_directories.assert_called_once_with(self.mock_cur, self.container_name)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)
    
    def test_get_directories_missing_argument_error(self):
        """
        Test the get directories route with unsuccessful conditions : missing argument.
        """
        expected = ("API Error retrieving user directories : Missing container name")
        
        response = asyncio.run(
            self.test_client.post(
                '/get-directories',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": ""
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
    
    def test_get_directories_datastore_error(self):
        """
        Test the get directories route with unsuccessful conditions : an error from datastore is raised.
        """
        expected = ("Datastore Error retrieving user directories : An error occured while retrieving the picture sets")
        self.mock_get_directories.side_effect = DatastoreError("An error occured while retrieving the picture sets")
        
        response = asyncio.run(
            self.test_client.post(
                '/get-directories',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)        


class TestGetPicture(unittest.TestCase):
    
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.container_name = "test_container_name"
        self.picture_id = "test_picture_id"
        self.inference = {
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
        self.picture_blob = b"blob"
        image_base64 = base64.b64encode(self.picture_blob)
        self.image = "data:image/tiff;base64," + image_base64.decode("utf-8")
        
        # Mock the azure_storage and database variables
        self.mock_cur = MagicMock()     
        self.mock_connection = MagicMock()
        self.mock_container_client = MagicMock()
        
        # Patch the azure_storage and datastore functions
        self.patch_connect_db = patch('app.datastore.db.connect_db', return_value=self.mock_connection)
        self.patch_cursor = patch('app.datastore.db.cursor', return_value=self.mock_cur)
        self.patch_mount_container = patch('app.azure_storage.mount_container', return_value=self.mock_container_client)
        self.patch_get_inference = patch('app.datastore.get_inference', return_value = self.inference)
        self.patch_get_picture_blob = patch('app.datastore.get_picture_blob', return_value = self.picture_blob)
        self.patch_end_query = patch('app.datastore.end_query')
        
        self.mock_connect_db = self.patch_connect_db.start()
        self.mock_cursor = self.patch_cursor.start()
        self.mock_mount_container = self.patch_mount_container.start()
        self.mock_get_inference = self.patch_get_inference.start()
        self.mock_get_picture_blob = self.patch_get_picture_blob.start()
        self.mock_end_query = self.patch_end_query.start()

    def tearDown(self) -> None:
        """
        Tear down the test environment at the end of each test case.
        """
        self.test_client = None
        self.patch_connect_db.stop()
        self.patch_cursor.stop()
        self.patch_mount_container.stop()
        self.patch_get_inference.stop()
        self.patch_get_picture_blob.stop()
        self.patch_end_query.stop()
    
    def test_get_picture_successful(self):
        """
        Test the get picture route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/get-picture',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "picture_id": self.picture_id
                })
        )
        
        self.assertEqual(response.status_code, 200)
        self.maxDiff = None
        self.assertDictEqual(json.loads(asyncio.run(response.get_data())), {"inference": self.inference, "image": self.image, "picture_id": self.picture_id})
        self.mock_mount_container.assert_called_once_with(CONNECTION_STRING, self.container_name, create_container=True)
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_get_inference.assert_called_once_with(self.mock_cur, self.container_name, self.picture_id)
        self.mock_get_picture_blob.assert_called_once_with(self.mock_cur, self.container_name, self.mock_container_client, self.picture_id)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)
        

class TestDeleteFolder(unittest.TestCase):
    
    #TODO: implement the tests for the delete folder route
    
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        self.test_client = app.test_client()
        self.container_name = "test_container_name"
        self.folder_uuid = "test_folder_uuid"
        self.validated_pictures_id = ["picture_id_1", "picture_id_3"]

        # Mock the azure_storage and database variables
        self.mock_cur = MagicMock()     
        self.mock_connection = MagicMock()
        self.mock_container_client = MagicMock()

        # Patch the azure_storage and datastore functions
        self.patch_connect_db = patch('app.datastore.db.connect_db', return_value=self.mock_connection)
        self.patch_cursor = patch('app.datastore.db.cursor', return_value=self.mock_cur)
        self.patch_mount_container = patch('app.azure_storage.mount_container', return_value=self.mock_container_client)
        self.patch_delete_directory_request = patch('app.datastore.delete_directory_request', return_value =  self.validated_pictures_id)
        self.patch_delete_directory_permanently = patch('app.datastore.delete_directory_permanently', return_value =  True)
        self.patch_delete_with_archive = patch('app.datastore.delete_directory_with_archive', return_value = self.folder_uuid)
        self.patch_end_query = patch('app.datastore.end_query')

        self.mock_connect_db = self.patch_connect_db.start()
        self.mock_cursor = self.patch_cursor.start()
        self.mock_mount_container = self.patch_mount_container.start()
        self.mock_delete_directory_request = self.patch_delete_directory_request.start()
        self.mock_delete_directory_permanently = self.patch_delete_directory_permanently.start()
        self.mock_delete_with_archive = self.patch_delete_with_archive.start()
        self.mock_end_query = self.patch_end_query.start()

    def tearDown(self) -> None:
        """
        Tear down the test environment at the end of each test case.
        """
        self.test_client = None
        self.patch_connect_db.stop()
        self.patch_cursor.stop()
        self.patch_mount_container.stop()
        self.patch_delete_directory_request.stop()
        self.patch_delete_directory_permanently.stop()
        self.patch_delete_with_archive.stop()
        self.patch_end_query.stop()

    def test_delete_request_successful(self):
        """
        Test the delete request route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/delete-request',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_uuid": self.folder_uuid
                })
        )
        self.assertEqual(response.status_code, 200)
        self.maxDiff = None
        self.assertEqual(json.loads(asyncio.run(response.get_data())), self.validated_pictures_id)
        
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_delete_directory_request.assert_called_once_with(self.mock_cur, self.container_name, self.folder_uuid)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)
        
    def test_delete_permanently_successful(self):
        """
        Test the delete permanently route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/delete-permanently',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_uuid": self.folder_uuid
                })
        )
        self.assertEqual(response.status_code, 200)
        self.maxDiff = None
        self.assertTrue(json.loads(asyncio.run(response.get_data())))

        self.mock_mount_container.assert_called_once_with(CONNECTION_STRING, self.container_name, create_container=True)
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_delete_directory_permanently.assert_called_once_with(self.mock_cur, self.container_name, self.folder_uuid, self.mock_container_client)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)

    def test_delete_with_archive_successful(self):
        """
        Test the delete with archive route with successful conditions.
        """
        response = asyncio.run(
            self.test_client.post(
                '/delete-with-archive',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_uuid": self.folder_uuid
                })
        )
        self.assertEqual(response.status_code, 200)
        self.maxDiff = None
        self.assertTrue(json.loads(asyncio.run(response.get_data())))

        self.mock_mount_container.assert_called_once_with(CONNECTION_STRING, self.container_name, create_container=True)
        self.mock_connect_db.assert_called_once_with(NACHET_DB_URL, NACHET_SCHEMA)
        self.mock_cursor.assert_called_once_with(self.mock_connection)
        self.mock_delete_with_archive.assert_called_once_with(self.mock_cur, self.container_name, self.folder_uuid, self.mock_container_client)
        self.mock_end_query.assert_called_once_with(self.mock_connection, self.mock_cur)


if __name__ == '__main__':
    unittest.main()
