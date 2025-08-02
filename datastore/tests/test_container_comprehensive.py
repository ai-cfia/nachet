"""
Comprehensive tests for container.py module to achieve 100% test coverage.
"""

import asyncio
import os
import unittest
import uuid
from unittest.mock import Mock, patch, mock_open

from azure.storage.blob import ContainerClient

from datastore.blob.azure_storage_api.container import (
    mount_container,
    download_container,
)
from datastore.blob.azure_storage_api.exceptions import (
    MountContainerError,
    ConnectionStringError,
)


BLOB_CONNECTION_STRING = os.environ.get("NACHET_STORAGE_URL", "")
if BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL is not set")


class TestMountContainer(unittest.TestCase):
    """Test mount_container function with all edge cases."""

    def setUp(self):
        self.connection_string = (
            "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test=="
        )
        self.container_uuid = str(uuid.uuid4())
        self.tier = "test"
        self.credentials = ""

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    def test_mount_container_exists_success(
        self, mock_build_container_name, mock_blob_service_client
    ):
        """Test successful mounting of existing container."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.return_value = True

        result = asyncio.run(
            mount_container(
                self.connection_string,
                self.container_uuid,
                create_container=True,
                tier=self.tier,
                credentials=self.credentials,
            )
        )

        # Verify result
        self.assertEqual(result, mock_container_client)
        mock_blob_service_client.from_connection_string.assert_called_once_with(
            conn_str=self.connection_string, credential=self.credentials
        )

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    @patch("datastore.blob.azure_storage_api.container.create_folder")
    def test_mount_container_create_new_success(
        self, mock_create_folder, mock_build_container_name, mock_blob_service_client
    ):
        """Test successful creation of new container."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.return_value = False
        mock_service_client.create_container.return_value = mock_container_client
        mock_create_folder.return_value = True

        result = asyncio.run(
            mount_container(
                self.connection_string,
                self.container_uuid,
                create_container=True,
                tier=self.tier,
                credentials=self.credentials,
            )
        )

        # Verify result
        self.assertEqual(result, mock_container_client)
        mock_service_client.create_container.assert_called_once_with(
            "test-container-name"
        )
        mock_create_folder.assert_called_once_with(mock_container_client, "General")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    @patch("datastore.blob.azure_storage_api.container.create_folder")
    def test_mount_container_create_folder_fails(
        self, mock_create_folder, mock_build_container_name, mock_blob_service_client
    ):
        """Test container creation fails when create_folder fails."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.return_value = False
        mock_service_client.create_container.return_value = mock_container_client
        mock_create_folder.return_value = False  # Folder creation fails

        with self.assertRaises(MountContainerError) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    create_container=True,
                    tier=self.tier,
                    credentials=self.credentials,
                )
            )

        self.assertEqual(str(context.exception), "Error creating general directory")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    def test_mount_container_no_create_not_exists(
        self, mock_build_container_name, mock_blob_service_client
    ):
        """Test mount fails when container doesn't exist and create_container=False."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.return_value = False

        with self.assertRaises(MountContainerError) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    create_container=False,  # Don't create
                    tier=self.tier,
                    credentials=self.credentials,
                )
            )

        self.assertEqual(str(context.exception), "Container does not exist")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    def test_mount_container_invalid_service_client(self, mock_blob_service_client):
        """Test mount fails when BlobServiceClient returns None/falsy."""
        mock_blob_service_client.from_connection_string.return_value = None

        with self.assertRaises(ConnectionStringError) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    credentials=self.credentials,
                )
            )

        self.assertEqual(str(context.exception), "Invalid connection string")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    def test_mount_container_value_error(self, mock_blob_service_client):
        """Test mount handles ValueError from connection string."""
        mock_blob_service_client.from_connection_string.side_effect = ValueError(
            "Invalid connection string format"
        )

        with self.assertRaises(ConnectionStringError) as context:
            asyncio.run(
                mount_container(
                    "invalid-connection-string",
                    self.container_uuid,
                    credentials=self.credentials,
                )
            )

        self.assertIn("The given connection string is invalid", str(context.exception))
        self.assertIn("Invalid connection string format", str(context.exception))

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    def test_mount_container_mount_error_passthrough(
        self, mock_build_container_name, mock_blob_service_client
    ):
        """Test mount passes through MountContainerError."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.side_effect = MountContainerError(
            "Custom mount error"
        )

        with self.assertRaises(MountContainerError) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    credentials=self.credentials,
                )
            )

        self.assertEqual(str(context.exception), "Custom mount error")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    def test_mount_container_connection_error_passthrough(
        self, mock_build_container_name, mock_blob_service_client
    ):
        """Test mount passes through ConnectionStringError."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.side_effect = ConnectionStringError(
            "Custom connection error"
        )

        with self.assertRaises(ConnectionStringError) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    credentials=self.credentials,
                )
            )

        self.assertEqual(str(context.exception), "Custom connection error")

    @patch("datastore.blob.azure_storage_api.container.BlobServiceClient")
    @patch("datastore.blob.azure_storage_api.container.build_container_name")
    def test_mount_container_unexpected_error(
        self, mock_build_container_name, mock_blob_service_client
    ):
        """Test mount handles unexpected exceptions."""
        # Setup mocks
        mock_build_container_name.return_value = "test-container-name"
        mock_service_client = Mock()
        mock_blob_service_client.from_connection_string.return_value = (
            mock_service_client
        )
        mock_container_client = Mock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.exists.side_effect = RuntimeError("Unexpected error")

        with self.assertRaises(Exception) as context:
            asyncio.run(
                mount_container(
                    self.connection_string,
                    self.container_uuid,
                    credentials=self.credentials,
                )
            )

        self.assertIn("Unhandeled error:", str(context.exception))
        self.assertIn("Unexpected error", str(context.exception))


class TestDownloadContainer(unittest.TestCase):
    """Test download_container function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.container_name = "test-container"
        self.local_dir = "/tmp/test_download"

    @patch("datastore.blob.azure_storage_api.container.os.makedirs")
    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_container_success(
        self, mock_file_open, mock_build_blob_name, mock_makedirs
    ):
        """Test successful container download."""
        # Setup mock blobs
        mock_blob1 = Mock()
        mock_blob1.name = "folder1/file1.txt"
        mock_blob2 = Mock()
        mock_blob2.name = "folder2/file2.jpg"
        self.mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]

        # Setup mock blob clients
        mock_blob_client1 = Mock()
        mock_blob_client2 = Mock()
        self.mock_container_client.get_blob_client.side_effect = [
            mock_blob_client1,
            mock_blob_client2,
        ]

        # Setup mock blob data
        mock_blob_data1 = Mock()
        mock_blob_data2 = Mock()
        mock_blob_client1.download_blob.return_value = mock_blob_data1
        mock_blob_client2.download_blob.return_value = mock_blob_data2

        # Setup build_blob_name returns
        mock_build_blob_name.side_effect = [
            "/tmp/test_download/folder1/file1.txt",
            "/tmp/test_download/folder2/file2.jpg",
        ]

        # Run the function
        asyncio.run(
            download_container(
                self.mock_container_client, self.container_name, self.local_dir
            )
        )

        # Verify calls
        self.mock_container_client.list_blobs.assert_called_once()
        self.assertEqual(self.mock_container_client.get_blob_client.call_count, 2)

        # Verify get_blob_client calls
        expected_calls = [
            unittest.mock.call(container=self.container_name, blob=mock_blob1),
            unittest.mock.call(container=self.container_name, blob=mock_blob2),
        ]
        self.mock_container_client.get_blob_client.assert_has_calls(expected_calls)

        # Verify file operations
        self.assertEqual(mock_file_open.call_count, 2)
        mock_blob_data1.readinto.assert_called_once()
        mock_blob_data2.readinto.assert_called_once()

        # Verify directory creation
        self.assertEqual(mock_makedirs.call_count, 2)

    @patch("datastore.blob.azure_storage_api.container.os.makedirs")
    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_container_single_blob(
        self, mock_file_open, mock_build_blob_name, mock_makedirs
    ):
        """Test download with single blob."""
        # Setup mock blob
        mock_blob = Mock()
        mock_blob.name = "single_file.txt"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        # Setup mock blob client
        mock_blob_client = Mock()
        self.mock_container_client.get_blob_client.return_value = mock_blob_client

        # Setup mock blob data
        mock_blob_data = Mock()
        mock_blob_client.download_blob.return_value = mock_blob_data

        # Setup build_blob_name return
        mock_build_blob_name.return_value = "/tmp/test_download/single_file.txt"

        # Run the function
        asyncio.run(
            download_container(
                self.mock_container_client, self.container_name, self.local_dir
            )
        )

        # Verify single blob processed
        self.mock_container_client.get_blob_client.assert_called_once_with(
            container=self.container_name, blob=mock_blob
        )
        mock_blob_data.readinto.assert_called_once()

    def test_download_container_empty_container(self):
        """Test download with empty container."""
        # Setup empty blob list
        self.mock_container_client.list_blobs.return_value = []

        # Run the function - should complete without error
        asyncio.run(
            download_container(
                self.mock_container_client, self.container_name, self.local_dir
            )
        )

        # Verify no blob clients created
        self.mock_container_client.get_blob_client.assert_not_called()

    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    def test_download_container_list_blobs_error(self, mock_build_blob_name):
        """Test download handles list_blobs exception."""
        self.mock_container_client.list_blobs.side_effect = Exception(
            "List blobs failed"
        )

        with self.assertRaises(Exception) as context:
            asyncio.run(
                download_container(
                    self.mock_container_client, self.container_name, self.local_dir
                )
            )

        self.assertEqual(str(context.exception), "Error downloading container")

    @patch("datastore.blob.azure_storage_api.container.os.makedirs")
    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    def test_download_container_get_blob_client_error(
        self, mock_build_blob_name, mock_makedirs
    ):
        """Test download handles get_blob_client exception."""
        # Setup mock blob
        mock_blob = Mock()
        mock_blob.name = "test_file.txt"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        # Mock get_blob_client to raise exception
        self.mock_container_client.get_blob_client.side_effect = Exception(
            "Blob client failed"
        )

        # Setup build_blob_name return
        mock_build_blob_name.return_value = "/tmp/test_download/test_file.txt"

        with self.assertRaises(Exception) as context:
            asyncio.run(
                download_container(
                    self.mock_container_client, self.container_name, self.local_dir
                )
            )

        self.assertEqual(str(context.exception), "Error downloading container")

    @patch("datastore.blob.azure_storage_api.container.os.makedirs")
    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_container_file_write_error(
        self, mock_file_open, mock_build_blob_name, mock_makedirs
    ):
        """Test download handles file write exception."""
        # Setup mock blob
        mock_blob = Mock()
        mock_blob.name = "test_file.txt"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        # Setup mock blob client
        mock_blob_client = Mock()
        self.mock_container_client.get_blob_client.return_value = mock_blob_client

        # Setup mock blob data that fails on readinto
        mock_blob_data = Mock()
        mock_blob_data.readinto.side_effect = Exception("File write failed")
        mock_blob_client.download_blob.return_value = mock_blob_data

        # Setup build_blob_name return
        mock_build_blob_name.return_value = "/tmp/test_download/test_file.txt"

        with self.assertRaises(Exception) as context:
            asyncio.run(
                download_container(
                    self.mock_container_client, self.container_name, self.local_dir
                )
            )

        self.assertEqual(str(context.exception), "Error downloading container")

    @patch("datastore.blob.azure_storage_api.container.os.makedirs")
    @patch("datastore.blob.azure_storage_api.container.build_blob_name")
    def test_download_container_makedirs_error(
        self, mock_build_blob_name, mock_makedirs
    ):
        """Test download handles os.makedirs exception."""
        # Setup mock blob
        mock_blob = Mock()
        mock_blob.name = "test_file.txt"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        # Setup mock blob client
        mock_blob_client = Mock()
        self.mock_container_client.get_blob_client.return_value = mock_blob_client

        # Setup build_blob_name return
        mock_build_blob_name.return_value = "/tmp/test_download/test_file.txt"

        # Mock makedirs to raise exception
        mock_makedirs.side_effect = Exception("Directory creation failed")

        with self.assertRaises(Exception) as context:
            asyncio.run(
                download_container(
                    self.mock_container_client, self.container_name, self.local_dir
                )
            )

        self.assertEqual(str(context.exception), "Error downloading container")


if __name__ == "__main__":
    unittest.main(verbosity=2)
