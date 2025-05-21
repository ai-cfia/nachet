import unittest
import asyncio
import os
import base64

from app import app, json
from unittest.mock import MagicMock, Mock


class TestPositiveFeedback(unittest.TestCase):
    def setUp(self):
        self.test_client = app.test_client()
        self.userId = "a427278e-28df-428f-8937-ddeeef44e72f"
        response = asyncio.run(
            self.test_client.get("/test")
        )
        self.pipeline = json.loads(asyncio.run(response.get_data()))[0]
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, 'img/16.tiff')
        self.folder_name = "test1"
        self.image_header = "data:image/PNG;base64,"
        with open(image_path, 'rb') as image_file:
            self.image_src = base64.b64encode(image_file.read()).decode('utf-8')
        self.inferences_id = []

    def create_test_inference(self):
        """
        Create a test inference to be used in the test
        """
        # Mock azure client services
        mock_blob = Mock()
        mock_blob.readall.return_value = bytes(self.image_src, encoding="utf-8")

        mock_blob_client = Mock()
        mock_blob_client.configure_mock(name="test_blob.json")
        mock_blob_client.download_blob.return_value = mock_blob

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob_client]
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_container_client.exists.return_value = True

        # Test the answers from inference_request
        response = asyncio.run(
            self.test_client.post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": self.image_header + self.image_src,
                    "imageDims": [720,540],
                    "folder_name": self.folder_name,
                    "container_name": self.userId,
                    "model_name": self.pipeline.get("pipeline_name")
                })
        )
        
        inference = json.loads(asyncio.run(response.get_data()))
        self.inferences_id.append(inference.get("inference_id"))
        
        return inference
    
    def tearDown(self):
        #TODO delete the inference :
        #for inference_id in self.inferences_id :
            #datastore.delete_test_inference(inference_id)
        self.test_client = None
        
    def test_positive_feedback_successful(self):
        
        inference = self.create_test_inference()
        inferenceId = inference.get("inference_id")
        boxes = []
        for box in inference.get("boxes"):
            boxes.append({"boxId" : box.get("box_id")})
        
        response = asyncio.run(
            self.test_client.post(
                '/feedback-positive',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "userId": self.userId,
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        self.assertEqual(response.status_code, 200)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertIsInstance(result_json, dict)
        
    def test_positive_feedback_missing_arguments_error(self):
        """
        Test if a request with missing arguments return an error
        """
        expected = ("API Error giving a positive feedback : missing request arguments: either userId, inferenceId or boxes is missing")
        
        inference = self.create_test_inference()
        inferenceId = inference.get("inference_id")
        boxes = []
        for box in inference.get("boxes"):
            boxes.append({"boxId" : box.get("box_id")})
            
        response = asyncio.run(
            self.test_client.post(
                '/feedback-positive',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
        
        expected = ("API Error giving a positive feedback : missing request arguments: boxId is missing in boxes")
        
        boxes.append({}) # add a box with a missing argument 
        
        response = asyncio.run(
            self.test_client.post(
                '/feedback-positive',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "userId": self.userId,
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
        
        
class TestNegativeFeedback(unittest.TestCase):
    def setUp(self):
        self.test_client = app.test_client()
        self.userId = "a427278e-28df-428f-8937-ddeeef44e72f"
        response = asyncio.run(
            self.test_client.get("/test")
        )
        self.pipeline = json.loads(asyncio.run(response.get_data()))[0]
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, 'img/16.tiff')
        self.folder_name = "test1"
        self.image_header = "data:image/PNG;base64,"
        with open(image_path, 'rb') as image_file:
            self.image_src = base64.b64encode(image_file.read()).decode('utf-8')
        self.inferences_id = []
    
    def create_test_inference(self):
        """
        Create a test inference to be used in the test
        """
        # Mock azure client services
        mock_blob = Mock()
        mock_blob.readall.return_value = bytes(self.image_src, encoding="utf-8")

        mock_blob_client = Mock()
        mock_blob_client.configure_mock(name="test_blob.json")
        mock_blob_client.download_blob.return_value = mock_blob

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob_client]
        mock_container_client.get_blob_client.return_value = mock_blob_client
        mock_container_client.exists.return_value = True

        # Test the answers from inference_request
        response = asyncio.run(
            self.test_client.post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": self.image_header + self.image_src,
                    "imageDims": [720,540],
                    "folder_name": self.folder_name,
                    "container_name": self.userId,
                    "model_name": self.pipeline.get("pipeline_name")
                })
        )

        inference = json.loads(asyncio.run(response.get_data()))
        self.inferences_id.append(inference.get("inference_id"))
        
        return inference
    
    def tearDown(self):
        #TODO delete the inference :
        #for inference_id in self.inferences_id :
            #datastore.delete_test_inference(inference_id)
        self.test_client = None
            
    def test_negative_feedback_successful(self):
        
        inference = self.create_test_inference()
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
        response = asyncio.run(
            self.test_client.post(
                '/feedback-negative',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "userId": self.userId,
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        self.assertEqual(response.status_code, 200)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertIsInstance(result_json, dict)

    def test_positive_feedback_missing_arguments_error(self):
        """
        Test if a request with missing arguments return an error
        """
        expected = ("API Error giving a negative feedback : missing request arguments: either userId, inferenceId or boxes is missing")
        
        inference = self.create_test_inference()
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
        
        response = asyncio.run(
            self.test_client.post(
                '/feedback-negative',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
        
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
        
        response = asyncio.run(
            self.test_client.post(
                '/feedback-negative',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "userId": self.userId,
                    "inferenceId": inferenceId,
                    "boxes": boxes
                })
        )
        
        self.assertEqual(response.status_code, 400)
        result_json = json.loads(asyncio.run(response.get_data()))
        self.assertEqual(result_json[0], expected)
    
