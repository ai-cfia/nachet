"""
Comprehensive tests for folder.py module to achieve 100% test coverage.
"""

import asyncio
import json
import os
import unittest
import uuid
from unittest.mock import Mock, patch

# from PIL import Image
from azure.storage.blob import ContainerClient

from datastore.blob.azure_storage_api.folder import (
    upload_image,
    is_a_folder,
    create_folder,
    create_dev_container_folder,
    upload_inference_result,
    get_folder_uuid,
    get_image_count,
    get_directories,
    delete_folder,
)
from datastore.blob.azure_storage_api.exceptions import (
    CreateDirectoryError,
    FolderListError,
    GetFolderUUIDError,
    UploadInferenceResultError,
)


BLOB_CONNECTION_STRING = os.environ.get("NACHET_STORAGE_URL", "")
if BLOB_CONNECTION_STRING == "":
    raise ValueError("NACHET_STORAGE_URL is not set")


class TestUploadImage(unittest.TestCase):
    """Test upload_image function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        self.image_uuid = str(uuid.uuid4())
        self.image_data = b"fake image data"

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    def test_upload_image_success(self, mock_build_blob_name, mock_is_a_folder):
        """Test successful image upload."""
        mock_is_a_folder.return_value = True
        mock_build_blob_name.return_value = "test_folder/image_uuid"
        mock_blob_client = Mock()
        self.mock_container_client.upload_blob.return_value = mock_blob_client

        result = asyncio.run(
            upload_image(
                self.mock_container_client,
                self.folder_name,
                self.folder_uuid,
                self.image_data,
                self.image_uuid,
            )
        )

        self.assertEqual(result, "test_folder/image_uuid")
        mock_blob_client.set_blob_tags.assert_called_once()

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_upload_image_folder_not_exists(self, mock_is_a_folder):
        """Test upload_image raises CreateDirectoryError when folder doesn't exist."""
        mock_is_a_folder.return_value = False

        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                upload_image(
                    self.mock_container_client,
                    self.folder_name,
                    self.folder_uuid,
                    self.image_data,
                    self.image_uuid,
                )
            )

        self.assertIn("does not exist", str(context.exception))

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    def test_upload_image_upload_error(self, mock_build_blob_name, mock_is_a_folder):
        """Test upload_image handles upload exceptions."""
        mock_is_a_folder.return_value = True
        mock_build_blob_name.return_value = "test_folder/image_uuid"
        self.mock_container_client.upload_blob.side_effect = Exception("Upload failed")

        with self.assertRaises(Exception) as context:
            asyncio.run(
                upload_image(
                    self.mock_container_client,
                    self.folder_name,
                    self.folder_uuid,
                    self.image_data,
                    self.image_uuid,
                )
            )

        self.assertEqual(
            str(context.exception), "Datastore.blob.azure_storage unHandled Error"
        )


class TestIsAFolder(unittest.TestCase):
    """Test is_a_folder function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"

    @patch("datastore.blob.azure_storage_api.folder.get_directories")
    def test_is_a_folder_exists(self, mock_get_directories):
        """Test is_a_folder returns True when folder exists."""
        mock_get_directories.return_value = {"test_folder": 5, "other_folder": 3}

        result = asyncio.run(is_a_folder(self.mock_container_client, self.folder_name))

        self.assertTrue(result)

    @patch("datastore.blob.azure_storage_api.folder.get_directories")
    def test_is_a_folder_not_exists(self, mock_get_directories):
        """Test is_a_folder returns False when folder doesn't exist."""
        mock_get_directories.return_value = {"other_folder": 3}

        result = asyncio.run(is_a_folder(self.mock_container_client, self.folder_name))

        self.assertFalse(result)

    @patch("datastore.blob.azure_storage_api.folder.get_directories")
    def test_is_a_folder_list_error(self, mock_get_directories):
        """Test is_a_folder handles FolderListError."""
        mock_get_directories.side_effect = FolderListError("List failed")

        with self.assertRaises(FolderListError) as context:
            asyncio.run(is_a_folder(self.mock_container_client, self.folder_name))

        self.assertIn("could not check if its a folder", str(context.exception))

    @patch("datastore.blob.azure_storage_api.folder.get_directories")
    def test_is_a_folder_unexpected_error(self, mock_get_directories):
        """Test is_a_folder handles unexpected exceptions."""
        mock_get_directories.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception) as context:
            asyncio.run(is_a_folder(self.mock_container_client, self.folder_name))

        self.assertEqual(
            str(context.exception), "Datastore.blob.azure_storage : Unhandled Error"
        )


class TestCreateFolder(unittest.TestCase):
    """Test create_folder function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())

    def test_create_folder_no_params_error(self):
        """Test create_folder raises error when no parameters provided."""
        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(create_folder(self.mock_container_client))

        self.assertEqual(str(context.exception), "Folder name and uuid not provided")

    def test_create_folder_no_uuid_error(self):
        """Test create_folder raises error when no uuid provided."""
        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(create_folder(self.mock_container_client, folder_name="test"))

        self.assertEqual(str(context.exception), "Folder uuid not provided")

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    @patch("datetime.datetime")
    def test_create_folder_success_with_name(
        self, mock_datetime, mock_build_blob_name, mock_is_a_folder
    ):
        """Test successful folder creation with both uuid and name."""
        mock_is_a_folder.return_value = False
        mock_build_blob_name.return_value = "test_folder/test_folder.json"
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        mock_blob_client = Mock()
        self.mock_container_client.upload_blob.return_value = mock_blob_client

        result = asyncio.run(
            create_folder(
                self.mock_container_client,
                folder_uuid=self.folder_uuid,
                folder_name=self.folder_name,
            )
        )

        self.assertTrue(result)
        mock_blob_client.set_blob_tags.assert_called_once()

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    @patch("datetime.datetime")
    def test_create_folder_success_uuid_only(
        self, mock_datetime, mock_build_blob_name, mock_is_a_folder
    ):
        """Test successful folder creation with only uuid (name defaults to uuid)."""
        mock_is_a_folder.return_value = False
        mock_build_blob_name.return_value = (
            f"{self.folder_uuid}/{self.folder_uuid}.json"
        )
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        mock_blob_client = Mock()
        self.mock_container_client.upload_blob.return_value = mock_blob_client

        result = asyncio.run(
            create_folder(self.mock_container_client, folder_uuid=self.folder_uuid)
        )

        self.assertTrue(result)

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_folder_already_exists(self, mock_is_a_folder):
        """Test create_folder raises error when folder already exists."""
        mock_is_a_folder.return_value = True

        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                )
            )

        self.assertEqual(str(context.exception), "Folder already exists")

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_folder_list_error(self, mock_is_a_folder):
        """Test create_folder handles FolderListError."""
        mock_is_a_folder.side_effect = FolderListError("List failed")

        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                )
            )

        self.assertIn("Error getting folder list", str(context.exception))

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_folder_unexpected_error(self, mock_is_a_folder):
        """Test create_folder handles unexpected exceptions."""
        mock_is_a_folder.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception) as context:
            asyncio.run(
                create_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                )
            )

        self.assertEqual(str(context.exception), "Datastore unHandled Error")


class TestCreateDevContainerFolder(unittest.TestCase):
    """Test create_dev_container_folder function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"
        self.folder_uuid = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def test_create_dev_folder_no_params_error(self):
        """Test create_dev_container_folder raises error when no parameters provided."""
        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(create_dev_container_folder(self.mock_container_client))

        self.assertEqual(str(context.exception), "Folder name and uuid not provided")

    def test_create_dev_folder_no_uuid_error(self):
        """Test create_dev_container_folder raises error when no uuid provided."""
        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_dev_container_folder(
                    self.mock_container_client, folder_name="test", user_id=self.user_id
                )
            )

        self.assertEqual(str(context.exception), "Folder uuid not provided")

    def test_create_dev_folder_no_user_id_error(self):
        """Test create_dev_container_folder raises error when no user_id provided."""
        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_dev_container_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                )
            )

        self.assertEqual(str(context.exception), "User id not provided")

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    @patch("datetime.datetime")
    def test_create_dev_folder_success(
        self, mock_datetime, mock_build_blob_name, mock_is_a_folder
    ):
        """Test successful dev folder creation."""
        mock_is_a_folder.return_value = False
        mock_build_blob_name.return_value = (
            f"{self.user_id}/{self.folder_name}/{self.folder_name}.json"
        )
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        mock_blob_client = Mock()
        self.mock_container_client.upload_blob.return_value = mock_blob_client

        result = asyncio.run(
            create_dev_container_folder(
                self.mock_container_client,
                folder_uuid=self.folder_uuid,
                folder_name=self.folder_name,
                user_id=self.user_id,
            )
        )

        self.assertTrue(result)
        mock_blob_client.set_blob_tags.assert_called_once()

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    @patch("datetime.datetime")
    def test_create_dev_folder_uuid_only(
        self, mock_datetime, mock_build_blob_name, mock_is_a_folder
    ):
        """Test dev folder creation with only uuid (name defaults to uuid)."""
        mock_is_a_folder.return_value = False
        mock_build_blob_name.return_value = (
            f"{self.user_id}/{self.folder_uuid}/{self.folder_uuid}.json"
        )
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"
        mock_blob_client = Mock()
        self.mock_container_client.upload_blob.return_value = mock_blob_client

        result = asyncio.run(
            create_dev_container_folder(
                self.mock_container_client,
                folder_uuid=self.folder_uuid,
                user_id=self.user_id,
            )
        )

        self.assertTrue(result)

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_dev_folder_already_exists(self, mock_is_a_folder):
        """Test create_dev_container_folder raises error when folder already exists."""
        mock_is_a_folder.return_value = True

        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_dev_container_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                    user_id=self.user_id,
                )
            )

        self.assertEqual(str(context.exception), "Folder already exists")

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_dev_folder_list_error(self, mock_is_a_folder):
        """Test create_dev_container_folder handles FolderListError."""
        mock_is_a_folder.side_effect = FolderListError("List failed")

        with self.assertRaises(CreateDirectoryError) as context:
            asyncio.run(
                create_dev_container_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                    user_id=self.user_id,
                )
            )

        self.assertIn("Error getting folder list", str(context.exception))

    @patch("datastore.blob.azure_storage_api.folder.is_a_folder")
    def test_create_dev_folder_unexpected_error(self, mock_is_a_folder):
        """Test create_dev_container_folder handles unexpected exceptions."""
        mock_is_a_folder.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception) as context:
            asyncio.run(
                create_dev_container_folder(
                    self.mock_container_client,
                    folder_uuid=self.folder_uuid,
                    folder_name=self.folder_name,
                    user_id=self.user_id,
                )
            )

        self.assertEqual(str(context.exception), "Datastore unHandled Error")


class TestUploadInferenceResult(unittest.TestCase):
    """Test upload_inference_result function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"
        self.result = '{"inference": "data"}'
        self.hash_value = "abcd1234"

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    @patch("datastore.blob.azure_storage_api.folder.build_blob_name")
    def test_upload_inference_result_success(
        self, mock_build_blob_name, mock_get_folder_uuid
    ):
        """Test successful inference result upload."""
        mock_get_folder_uuid.return_value = str(uuid.uuid4())
        mock_build_blob_name.return_value = "test_folder/abcd1234.json"

        result = asyncio.run(
            upload_inference_result(
                self.mock_container_client,
                self.folder_name,
                self.result,
                self.hash_value,
            )
        )

        self.assertTrue(result)
        self.mock_container_client.upload_blob.assert_called_once()

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    def test_upload_inference_result_no_folder_uuid(self, mock_get_folder_uuid):
        """Test upload_inference_result when folder UUID not found."""
        mock_get_folder_uuid.return_value = None

        result = asyncio.run(
            upload_inference_result(
                self.mock_container_client,
                self.folder_name,
                self.result,
                self.hash_value,
            )
        )

        self.assertIsNone(result)

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    def test_upload_inference_result_error(self, mock_get_folder_uuid):
        """Test upload_inference_result handles UploadInferenceResultError."""
        mock_get_folder_uuid.side_effect = UploadInferenceResultError("Upload failed")

        result = asyncio.run(
            upload_inference_result(
                self.mock_container_client,
                self.folder_name,
                self.result,
                self.hash_value,
            )
        )

        self.assertFalse(result)


class TestGetFolderUuid(unittest.TestCase):
    """Test get_folder_uuid function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"

    @patch("datastore.blob.azure_storage_api.folder.get_blob")
    def test_get_folder_uuid_success(self, mock_get_blob):
        """Test successful folder UUID retrieval."""
        folder_uuid = str(uuid.uuid4())
        mock_blob = Mock()
        mock_blob.name = "test_folder/test_folder.json"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        folder_json = {
            "folder_name": "test_folder",
            "folder_uuid": folder_uuid,
            "date_created": "2024-01-01 12:00:00",
        }
        mock_get_blob.return_value = json.dumps(folder_json).encode()

        result = asyncio.run(
            get_folder_uuid(self.mock_container_client, self.folder_name)
        )

        self.assertEqual(result, folder_uuid)

    @patch("datastore.blob.azure_storage_api.folder.get_blob")
    def test_get_folder_uuid_missing_uuid_field(self, mock_get_blob):
        """Test get_folder_uuid raises error when UUID field missing."""
        mock_blob = Mock()
        mock_blob.name = "test_folder/test_folder.json"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        folder_json = {
            "folder_name": "test_folder",
            "date_created": "2024-01-01 12:00:00",
            # Missing folder_uuid field
        }
        mock_get_blob.return_value = json.dumps(folder_json).encode()

        with self.assertRaises(GetFolderUUIDError) as context:
            asyncio.run(get_folder_uuid(self.mock_container_client, self.folder_name))

        self.assertIn("Folder UUID not found", str(context.exception))

    def test_get_folder_uuid_not_found(self):
        """Test get_folder_uuid raises error when folder not found."""
        self.mock_container_client.list_blobs.return_value = []

        with self.assertRaises(GetFolderUUIDError) as context:
            asyncio.run(get_folder_uuid(self.mock_container_client, self.folder_name))

        self.assertIn("not found", str(context.exception))

    def test_get_folder_uuid_unexpected_error(self):
        """Test get_folder_uuid handles unexpected exceptions."""
        self.mock_container_client.list_blobs.side_effect = Exception(
            "Unexpected error"
        )

        with self.assertRaises(Exception) as context:
            asyncio.run(get_folder_uuid(self.mock_container_client, self.folder_name))

        self.assertEqual(
            str(context.exception), "Datastore.blob.azure_storage unHandled Error"
        )


class TestGetImageCount(unittest.TestCase):
    """Test get_image_count function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.folder_name = "test_folder"

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    def test_get_image_count_success(self, mock_get_folder_uuid):
        """Test successful image count retrieval."""
        mock_get_folder_uuid.return_value = str(uuid.uuid4())

        # Mock blobs: 2 images + 1 json file
        mock_blobs = []
        for i in range(2):
            blob = Mock()
            blob.name = f"test_folder/image_{i}.jpg"
            mock_blobs.append(blob)

        # Add folder json file (should be excluded from count)
        json_blob = Mock()
        json_blob.name = "test_folder/folder.json"
        mock_blobs.append(json_blob)

        self.mock_container_client.list_blobs.return_value = mock_blobs

        result = asyncio.run(
            get_image_count(self.mock_container_client, self.folder_name)
        )

        self.assertEqual(result, 2)

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    def test_get_image_count_no_folder_uuid(self, mock_get_folder_uuid):
        """Test get_image_count when folder UUID not found."""
        mock_get_folder_uuid.return_value = None

        result = asyncio.run(
            get_image_count(self.mock_container_client, self.folder_name)
        )

        self.assertFalse(result)

    @patch("datastore.blob.azure_storage_api.folder.get_folder_uuid")
    def test_get_image_count_error(self, mock_get_folder_uuid):
        """Test get_image_count handles GetFolderUUIDError."""
        mock_get_folder_uuid.side_effect = GetFolderUUIDError("Folder not found")

        result = asyncio.run(
            get_image_count(self.mock_container_client, self.folder_name)
        )

        self.assertFalse(result)


class TestGetDirectories(unittest.TestCase):
    """Test get_directories function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)

    @patch("datastore.blob.azure_storage_api.folder.get_blob")
    @patch("datastore.blob.azure_storage_api.folder.get_image_count")
    def test_get_directories_success(self, mock_get_image_count, mock_get_blob):
        """Test successful directories retrieval."""
        # Mock folder blob
        mock_blob = Mock()
        mock_blob.name = "test_folder/test_folder.json"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        folder_json = {
            "folder_name": "test_folder",
            "folder_uuid": str(uuid.uuid4()),
            "date_created": "2024-01-01 12:00:00",
        }
        mock_get_blob.return_value = json.dumps(folder_json).encode()
        mock_get_image_count.return_value = 5

        result = asyncio.run(get_directories(self.mock_container_client))

        self.assertEqual(result, {"test_folder": 5})

    def test_get_directories_folder_list_error(self):
        """Test get_directories handles FolderListError correctly."""
        # Mock to raise FolderListError somewhere in the process
        mock_blob = Mock()
        mock_blob.name = "test_folder/test_folder.json"
        self.mock_container_client.list_blobs.return_value = [mock_blob]

        with patch("datastore.blob.azure_storage_api.folder.get_blob") as mock_get_blob:
            mock_get_blob.side_effect = FolderListError("Original folder list error")

            with self.assertRaises(FolderListError) as context:
                asyncio.run(get_directories(self.mock_container_client))

            self.assertEqual(str(context.exception), "Original folder list error")

    def test_get_directories_unexpected_error(self):
        """Test get_directories handles unexpected exceptions."""
        self.mock_container_client.list_blobs.side_effect = Exception(
            "Unexpected error"
        )

        with self.assertRaises(FolderListError) as context:
            asyncio.run(get_directories(self.mock_container_client))

        self.assertIn("Error getting directories", str(context.exception))


class TestDeleteFolder(unittest.TestCase):
    """Test delete_folder function with all edge cases."""

    def setUp(self):
        self.mock_container_client = Mock(spec=ContainerClient)
        self.picture_set_id = str(uuid.uuid4())

    @patch("datastore.blob.azure_storage_api.blob.get_blobs_from_tag")
    def test_delete_folder_success(self, mock_get_blobs_from_tag):
        """Test successful folder deletion."""
        mock_blob1 = Mock()
        mock_blob1.name = "folder/image1.jpg"
        mock_blob2 = Mock()
        mock_blob2.name = "folder/image2.jpg"
        mock_get_blobs_from_tag.return_value = [mock_blob1, mock_blob2]

        result = asyncio.run(
            delete_folder(self.mock_container_client, self.picture_set_id)
        )

        self.assertTrue(result)
        self.assertEqual(self.mock_container_client.delete_blob.call_count, 2)

    @patch("datastore.blob.azure_storage_api.blob.get_blobs_from_tag")
    def test_delete_folder_uuid_error(self, mock_get_blobs_from_tag):
        """Test delete_folder handles GetFolderUUIDError."""
        mock_get_blobs_from_tag.side_effect = GetFolderUUIDError("Folder not found")

        result = asyncio.run(
            delete_folder(self.mock_container_client, self.picture_set_id)
        )

        self.assertFalse(result)

    @patch("datastore.blob.azure_storage_api.blob.get_blobs_from_tag")
    def test_delete_folder_unexpected_error(self, mock_get_blobs_from_tag):
        """Test delete_folder handles unexpected exceptions."""
        mock_get_blobs_from_tag.side_effect = Exception("Unexpected error")

        result = asyncio.run(
            delete_folder(self.mock_container_client, self.picture_set_id)
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
