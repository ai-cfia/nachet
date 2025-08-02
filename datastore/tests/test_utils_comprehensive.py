"""
Comprehensive tests for utils.py module to achieve 100% test coverage.
"""

import asyncio
import unittest
from unittest.mock import patch
import hashlib

from datastore.blob.azure_storage_api.utils import (
    generate_hash,
    build_container_name,
    build_blob_name,
)
from datastore.blob.azure_storage_api.exceptions import GenerateHashError


class TestGenerateHash(unittest.TestCase):
    """Test generate_hash function with all edge cases."""

    def test_generate_hash_valid_bytes(self):
        """Test hash generation with valid bytes."""
        test_data = b"test image data"
        result = asyncio.run(generate_hash(test_data))

        # Verify it's a valid SHA256 hash (64 hex characters)
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

        # Verify it matches expected hash
        expected = hashlib.sha256(test_data).hexdigest()
        self.assertEqual(result, expected)

    def test_generate_hash_empty_bytes(self):
        """Test hash generation with empty bytes."""
        test_data = b""
        result = asyncio.run(generate_hash(test_data))
        expected = hashlib.sha256(test_data).hexdigest()
        self.assertEqual(result, expected)

    def test_generate_hash_large_data(self):
        """Test hash generation with large data."""
        test_data = b"x" * 10000  # Large byte array
        result = asyncio.run(generate_hash(test_data))
        expected = hashlib.sha256(test_data).hexdigest()
        self.assertEqual(result, expected)

    def test_generate_hash_type_error(self):
        """Test generate_hash raises GenerateHashError on TypeError."""
        with self.assertRaises(GenerateHashError) as context:
            asyncio.run(generate_hash("not bytes string"))

        self.assertEqual(
            str(context.exception), "The image is not in the correct format"
        )

    def test_generate_hash_type_error_with_int(self):
        """Test generate_hash raises GenerateHashError with integer input."""
        with self.assertRaises(GenerateHashError) as context:
            asyncio.run(generate_hash(12345))

        self.assertEqual(
            str(context.exception), "The image is not in the correct format"
        )

    def test_generate_hash_type_error_with_none(self):
        """Test generate_hash raises GenerateHashError with None input."""
        with self.assertRaises(GenerateHashError) as context:
            asyncio.run(generate_hash(None))

        self.assertEqual(
            str(context.exception), "The image is not in the correct format"
        )

    @patch("datastore.blob.azure_storage_api.utils.hashlib.sha256")
    def test_generate_hash_unexpected_exception(self, mock_sha256):
        """Test generate_hash handles unexpected exceptions."""
        # Mock sha256 to raise an unexpected exception
        mock_sha256.side_effect = RuntimeError("Unexpected error")

        with self.assertRaises(Exception) as context:
            asyncio.run(generate_hash(b"test data"))

        self.assertEqual(
            str(context.exception), "Unhandeled Datastore.blob.azure_storage Error"
        )


class TestBuildContainerName(unittest.TestCase):
    """Test build_container_name function with all edge cases."""

    def test_build_container_name_default_tier(self):
        """Test building container name with default tier."""
        result = build_container_name("test-uuid-123")
        self.assertEqual(result, "user-test-uuid-123")

    def test_build_container_name_custom_tier(self):
        """Test building container name with custom tier."""
        result = build_container_name("test-uuid-123", "dev")
        self.assertEqual(result, "dev-test-uuid-123")

    def test_build_container_name_special_characters(self):
        """Test building container name with special characters."""
        result = build_container_name("uuid-with-dashes", "test-tier")
        self.assertEqual(result, "test-tier-uuid-with-dashes")

    def test_build_container_name_empty_name_error(self):
        """Test build_container_name raises ValueError for empty name."""
        with self.assertRaises(ValueError) as context:
            build_container_name("")

        self.assertEqual(str(context.exception), "Name is required")

    def test_build_container_name_none_name_error(self):
        """Test build_container_name raises ValueError for None name."""
        with self.assertRaises(ValueError) as context:
            build_container_name(None)

        self.assertEqual(str(context.exception), "Name is required")

    def test_build_container_name_whitespace_only_error(self):
        """Test build_container_name raises ValueError for whitespace-only name."""
        with self.assertRaises(ValueError) as context:
            build_container_name("   \t\n   ")

        self.assertEqual(str(context.exception), "Name is required")

    def test_build_container_name_empty_tier(self):
        """Test building container name with empty tier."""
        result = build_container_name("test-uuid", "")
        self.assertEqual(result, "-test-uuid")


class TestBuildBlobName(unittest.TestCase):
    """Test build_blob_name function with all edge cases."""

    def test_build_blob_name_with_file_type(self):
        """Test building blob name with file type."""
        result = build_blob_name("folder/path", "image-uuid", "jpg")
        self.assertEqual(result, "folder/path/image-uuid.jpg")

    def test_build_blob_name_without_file_type(self):
        """Test building blob name without file type."""
        result = build_blob_name("folder/path", "image-uuid")
        self.assertEqual(result, "folder/path/image-uuid")

    def test_build_blob_name_with_none_file_type(self):
        """Test building blob name with None file type."""
        result = build_blob_name("folder/path", "image-uuid", None)
        self.assertEqual(result, "folder/path/image-uuid")

    def test_build_blob_name_with_empty_file_type(self):
        """Test building blob name with empty file type."""
        result = build_blob_name("folder/path", "image-uuid", "")
        self.assertEqual(result, "folder/path/image-uuid")

    def test_build_blob_name_with_whitespace_file_type(self):
        """Test building blob name with whitespace-only file type."""
        result = build_blob_name("folder/path", "image-uuid", "   ")
        self.assertEqual(result, "folder/path/image-uuid")

    def test_build_blob_name_complex_paths(self):
        """Test building blob name with complex folder paths."""
        result = build_blob_name("deep/folder/structure", "complex-uuid-123", "png")
        self.assertEqual(result, "deep/folder/structure/complex-uuid-123.png")

    def test_build_blob_name_empty_folder_path_error(self):
        """Test build_blob_name raises ValueError for empty folder path."""
        with self.assertRaises(ValueError) as context:
            build_blob_name("", "image-uuid", "jpg")

        self.assertEqual(str(context.exception), "Folder name is required")

    def test_build_blob_name_none_folder_path_error(self):
        """Test build_blob_name raises ValueError for None folder path."""
        with self.assertRaises(ValueError) as context:
            build_blob_name(None, "image-uuid", "jpg")

        self.assertEqual(str(context.exception), "Folder name is required")

    def test_build_blob_name_whitespace_folder_path_error(self):
        """Test build_blob_name raises ValueError for whitespace-only folder path."""
        with self.assertRaises(ValueError) as context:
            build_blob_name("   \t\n   ", "image-uuid", "jpg")

        self.assertEqual(str(context.exception), "Folder name is required")

    def test_build_blob_name_empty_blob_name_error(self):
        """Test build_blob_name raises ValueError for empty blob name."""
        with self.assertRaises(ValueError) as context:
            build_blob_name("folder", "", "jpg")

        self.assertEqual(
            str(context.exception), "Image uuid is required (parameter: blob_name)"
        )

    def test_build_blob_name_none_blob_name_error(self):
        """Test build_blob_name raises ValueError for None blob name."""
        with self.assertRaises(ValueError) as context:
            build_blob_name("folder", None, "jpg")

        self.assertEqual(
            str(context.exception), "Image uuid is required (parameter: blob_name)"
        )

    def test_build_blob_name_whitespace_blob_name_error(self):
        """Test build_blob_name raises ValueError for whitespace-only blob name."""
        with self.assertRaises(ValueError) as context:
            build_blob_name("folder", "   \t\n   ", "jpg")

        self.assertEqual(
            str(context.exception), "Image uuid is required (parameter: blob_name)"
        )

    def test_build_blob_name_multiple_dots_in_file_type(self):
        """Test building blob name with file type containing dots."""
        result = build_blob_name("folder", "image-uuid", "tar.gz")
        self.assertEqual(result, "folder/image-uuid.tar.gz")


if __name__ == "__main__":
    unittest.main(verbosity=2)
