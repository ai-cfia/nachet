import json
import unittest
import asyncio
from unittest.mock import patch, Mock, MagicMock
from bin.bin_azure_storage_api import (
    mount_container,
    get_blob,
    get_pipeline_info,
    get_blob_client,
    GetBlobError,
    PipelineNotFoundError,
    ConnectionStringError
)
from azure.core.exceptions import ResourceNotFoundError


class TestGetBlobServiceClient(unittest.TestCase):
    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_get_blob_service_successful(self, MockFromConnectionString):
        mock_blob_service_client = MockFromConnectionString.return_value

        result = asyncio.run(
            get_blob_client("connection_string")
        )

        print(result == mock_blob_service_client)

        self.assertEqual(result, mock_blob_service_client)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_get_blob_service_unsuccessful(self, MockFromConnectionString):
        MockFromConnectionString.return_value = None

        with self.assertRaises(ConnectionStringError) as context:
            asyncio.run(get_blob_client("invalid_connection_string"))

        print(context.exception == "the given connection string is invalid: invalid_connection_string")

class TestMountContainerFunction(unittest.TestCase):
    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_mount_existing_container(self, MockFromConnectionString):
        # mock the client container
        mock_container_client = Mock()
        mock_container_client.exists.return_value = True
        # mock the blob service client
        mock_blob_service_client = MockFromConnectionString.return_value
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )
        container_name = "testcontainer"

        result = asyncio.run(
            mount_container(mock_blob_service_client, container_name)
        )

        print(result == mock_container_client)

        self.assertEqual(result, mock_container_client)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_mount_nonexisting_container_create(self, MockFromConnectionString):
        """
        tests when a container does not exists and create_container flag is set to True,
        should create a new container and return the container client
        """
        # mock the client container and blob service client
        mock_container_client = MagicMock()
        mock_container_client.exists.return_value = False

        mock_blob_service_client = MockFromConnectionString.return_value
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )

        # Simulate that a new container is created
        mock_new_container_client = MagicMock()
        mock_blob_service_client.create_container.return_value = (
            mock_new_container_client
        )

        container_name = "testcontainer"
        expected_container_name = "user-{}".format(container_name)

        result = asyncio.run(
            mount_container(mock_blob_service_client, container_name, create_container=True)
        )

        mock_blob_service_client.create_container.assert_called_once_with(
            expected_container_name
        )
        print(result == mock_new_container_client)
        self.assertEqual(result, mock_new_container_client)

    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_mount_nonexisting_container_no_create(self, MockFromConnectionString):
        mock_container_client = Mock()
        mock_container_client.exists.return_value = False

        mock_blob_service_client = MockFromConnectionString.return_value
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )

        container_name = "testcontainer"

        result = asyncio.run(
            mount_container(mock_blob_service_client, container_name, create_container=False)
        )

        mock_blob_service_client.create_container.assert_not_called()
        print(result is None)
        self.assertEqual(result, None)


class TestGetBlob(unittest.TestCase):
    def test_get_blob_successful(self):
        mock_blob_name = "test_blob"
        mock_blob_content = b"blob content"

        mock_blob = Mock()
        mock_blob.readall.return_value = mock_blob_content

        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = mock_blob

        mock_container_client = Mock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        result = asyncio.run(
            get_blob(mock_container_client, mock_blob_name)
        )

        print(result == mock_blob_content)

        self.assertEqual(result, mock_blob_content)

    def test_get_blob_unsuccessful(self):
        blob = "nonexisting_blob"

        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Resource not found")

        mock_container_client = Mock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        with self.assertRaises(GetBlobError) as context:
            asyncio.run(get_blob(mock_container_client, blob))
        print(str(context.exception) == f"the specified blob: {blob} cannot be found")


class testGetPipeline(unittest.TestCase):
    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_get_pipeline_info_successful(self, MockFromConnectionString,):

        mock_blob_content = b'''{
            "name": "test_blob.json",
            "version": "v1"
        }'''

        mock_blob = Mock()
        mock_blob.readall.return_value = mock_blob_content

        mock_blob_client = Mock()
        mock_blob_client.configure_mock(name="test_blob.json")
        mock_blob_client.download_blob.return_value = mock_blob

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob_client]
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_blob_service_client = MockFromConnectionString.return_value
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )

        result = asyncio.run(get_pipeline_info(mock_blob_service_client, "test_blob", "v1"))

        print(result == json.loads(mock_blob_content))

        self.assertEqual(result, json.loads(mock_blob_content))


    @patch("azure.storage.blob.BlobServiceClient.from_connection_string")
    def test_get_pipeline_info_unsuccessful(self, MockFromConnectionString):
        pipeline_version = "v1"

        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Resource not found")

        mock_container_client = Mock()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_blob_service_client = MockFromConnectionString.return_value
        mock_blob_service_client.get_container_client.return_value = (
            mock_container_client
        )

        with self.assertRaises(PipelineNotFoundError) as context:
            asyncio.run(get_pipeline_info(mock_blob_service_client, "test_blob", pipeline_version))

        print(str(context.exception) == f"This version {pipeline_version} was not found")


if __name__ == "__main__":
    unittest.main()
