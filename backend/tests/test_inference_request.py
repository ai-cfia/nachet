import unittest
import json
import os
import base64
import asyncio
import warnings

from app import app, ImageWarning
from unittest.mock import patch, MagicMock, Mock

class TestInferenceRequest(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the test environment before running each test case.
        """
        # Start the test pipeline
        self.test = app.test_client()
        response = asyncio.run(
            self.test.get("/test")
        )
        self.pipeline = json.loads(asyncio.run(response.get_data()))[0]
        current_dir = os.path.dirname(__file__)
        image_path = os.path.join(current_dir, 'img/1310_1.png')
        self.endpoints = "/model-endpoints-metadata"
        self.inference = "/inf"
        self.container_name = "a427278e-28df-428f-8937-ddeeef44e72f"
        self.folder_name = "test1"
        self.image_header = "data:image/PNG;base64,"
        with open(image_path, 'rb') as image_file:
            self.image_src = base64.b64encode(image_file.read()).decode('utf-8')

    def tearDown(self) -> None:
        """
        Tear down the test environment at the end of each test case.
        """
        self.image_src = None
        self.test = None

    @patch("patch.bin_azure_storage_api.mount_container") # TODO : change to patch the mount_container function of the datastore repo
    def test_inference_request_successful(self, mock_container):
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
            self.test.post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": self.image_header + self.image_src,
                    "imageDims": [720,540],
                    "folder_name": self.folder_name,
                    "container_name": self.container_name,
                    "model_name": self.pipeline.get("pipeline_name")
                })
        )

        result_json = json.loads(asyncio.run(response.get_data()))
        keys = set(result_json.keys())
        keys.update(result_json["boxes"][0].keys())
        responses.update(keys)

        print(expected_keys == responses)
        self.assertEqual(responses, expected_keys)

    @patch("patch.bin_azure_storage_api.mount_container") # TODO : change to patch the mount_container function of the datastore repo
    def test_inference_request_unsuccessful(self, mock_container):
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
            self.test.post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": self.image_header,
                    "imageDims": [720,540],
                    "folder_name": self.folder_name,
                    "container_name": self.container_name,
                    "model_name":  self.pipeline.get("pipeline_name")
                })
        )

        result_json = json.loads(asyncio.run(response.get_data()))
        print(expected == result_json[0])
        print(response.status_code == 400)
        self.assertEqual(result_json[0], expected)
        self.assertEqual(response.status_code, 400)

    def test_inference_request_missing_argument(self):
        # Build expected response
        responses = []
        expected = ("API Error during classification : missing request arguments: either folder_name, container_name, imageDims or image is missing")

        data = {
            "image": self.image_header,
            "imageDims": [720,540],
            "folder_name": self.folder_name,
            "container_name": self.container_name,
            "model_name": self.pipeline.get("pipeline_name")
        }

        # Test the answers from inference_request

        for k, v in data.items():
            if k != "model_name":
                data[k] = ""
                response = asyncio.run(
                    self.test.post(
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
        print(expected == result_json[0])
        print(response.status_code == 400)
        self.assertEqual(result_json[0], expected)
        self.assertEqual(response.status_code, 400)

    def test_inference_request_wrong_pipeline_name(self):
        # Build expected response
        expected = ("API Error during classification : model wrong_pipeline_name not found")

        # Test the answers from inference_request
        response = asyncio.run(
            self.test.post(
                '/inf',
                headers={
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                json={
                    "image": self.image_src,
                    "imageDims": [720,540],
                    "folder_name": self.folder_name,
                    "container_name": self.container_name,
                    "model_name": "wrong_pipeline_name"
                }
            )
        )
        result_json = json.loads(asyncio.run(response.get_data()))

        print(expected == result_json[0])
        print(response.status_code == 400)

        self.assertEqual(result_json[0], expected)
        self.assertEqual(response.status_code, 400)

    # TODO test validation error when frontend return validators
    def test_inference_request_validation_warning(self):
        # Build expected response
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            asyncio.run(
                self.test.post(
                    '/inf',
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    json={
                        "image": "data:python," + self.image_src,
                        "imageDims": [720,540],
                        "folder_name": self.folder_name,
                        "container_name": self.container_name,
                        "model_name": self.pipeline.get("pipeline_name")
                    }
                )
            )

        self.assertTrue(issubclass(w[-1].category, ImageWarning))
        self.assertTrue("this picture was not validate" in str(w[-1].message))

if __name__ == '__main__':
    unittest.main()
