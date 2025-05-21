import unittest
import asyncio
import os
import base64

from app import app, json


class TestNewBatchImport(unittest.TestCase):
    def setUp(self):
        self.test_client = app.test_client()
        self.container_name = "a427278e-28df-428f-8937-ddeeef44e72f"
        self.nb_pictures = 1
        self.folder_name = "test_batch_import"
        self.session_id = None
    def tearDown(self):
        if(self.session_id is not None):
            response = asyncio.run(
                self.test_client.post(
                    '/delete-permanently',
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    json={
                        "container_name": self.container_name,
                        "folder_uuid": self.session_id
                    })
            )
            if(response.status_code == 200):
                self.session_id = None
        self.test_client = None

    def test_new_batch_import_successful(self):

        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": self.folder_name,
                    "nb_pictures": self.nb_pictures
                })
        )
        
        self.assertEqual(response.status_code, 200)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertTrue(result_json.get("session_id") is not None)
        
        self.session_id = result_json.get("session_id")

    def test_new_batch_import_missing_arguments_error(self):
        """
        Test if a request with missing arguments return an error
        """
        expected = ("API Error initiating batch upload : missing request arguments: either container_name or nb_pictures is missing")

        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "folder_name": self.folder_name,
                    "nb_pictures": self.nb_pictures
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)
        
    def test_new_batch_import_wrong_nb_pictures(self):
        """
        Test if a request with a wrong argument return an error
        """
        expected = ("API Error initiating batch upload : wrong request arguments: either container_name or nb_pictures is wrong")

        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": "",
                    "folder_name": self.folder_name,
                    "nb_pictures": self.nb_pictures
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)

        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": self.folder_name,
                    "nb_pictures": "1"
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)
        
        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": "test_batch_import",
                    "nb_pictures": 0
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)
        
class TestUploadBatchImport(unittest.TestCase):
    def setUp(self):
        self.test_client = app.test_client()
        self.container_name = "a427278e-28df-428f-8937-ddeeef44e72f"
        self.nb_pictures = 1
        self.folder_name = "test_batch_import"
        self.session_id = None
        response = asyncio.run(
            self.test_client.post(
                '/new-batch-import',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "folder_name": self.folder_name,
                    "nb_pictures": self.nb_pictures
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        if response.status_code == 200:
            print("Setup : folder successfully created")
        else :
            print(result_json)
        self.session_id = result_json.get("session_id")
        
        self.seed_name = "Ambrosia artemisiifolia"
        self.seed_id = "14e96554-aadf-42e4-8665-d141354800d1"
        self.zoom_level = None
        self.nb_seeds = None
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, 'img/1310_1.png')
        self.image_header = "data:image/PNG;base64,"
        with open(image_path, 'rb') as image_file:
            self.image_src = base64.b64encode(image_file.read()).decode('utf-8')
        self.image = self.image_header + self.image_src
        
    def tearDown(self):
        if(self.session_id is not None):
            response = asyncio.run(
                self.test_client.post(
                    '/delete-permanently',
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    json={
                        "container_name": self.container_name,
                        "folder_uuid": self.session_id
                    })
            )
            if(response.status_code == 200):
                print("Teardown : folder successfully deleted")
                self.session_id = None
        self.test_client = None
        
    def test_upload_picture_successful(self):
        response = asyncio.run(
            self.test_client.post(
                '/upload-picture',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    "session_id": self.session_id,
                    "seed_name": self.seed_name,
                    "seed_id" : self.seed_id,
                    "zoom_level": self.zoom_level,
                    "nb_seeds": self.nb_seeds,
                    "image": self.image
                })
        )
        self.assertEqual(response.status_code, 200)
        result_json = json.loads(asyncio.run(response.get_data()))[0]
        print(result_json)
        
    def test_upload_picture_missing_arguments_error(self):
        """
        Test if a request with missing arguments return an error
        """
        expected = ("API Error uploading picture : missing request arguments: either seed_name, session_id, container_name or image is missing")

        response = asyncio.run(
            self.test_client.post(
                '/upload-picture',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": self.container_name,
                    # missing session_id
                    "seed_name": self.seed_name,
                    "seed_id" : self.seed_id,
                    "zoom_level": self.zoom_level,
                    "nb_seeds": self.nb_seeds,
                    "image": self.image 
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)

    def test_upload_picture_wrong_arguments_error(self):
        """
        Test if a request with wrong arguments return an error
        """
        expected = ("API Error uploading picture : missing request arguments: either seed_name, session_id, container_name or image is missing")

        response = asyncio.run(
            self.test_client.post(
                '/upload-picture',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "container_name": "", # wrong container_name
                    "session_id": self.session_id,
                    "seed_name": self.seed_name,
                    "seed_id" : self.seed_id,
                    "zoom_level": self.zoom_level,
                    "nb_seeds": self.nb_seeds,
                    "image": self.image 
                })
        )
        result_json = json.loads(asyncio.run(response.get_data()))
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(result_json[0], expected)
