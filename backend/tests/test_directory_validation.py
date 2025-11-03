"""
Tests for directory/folder Pydantic field validators.

Tests cover:
- CreateOrGetFolderRequest: normalized_path and description validation
- UpdateFolderRequest: name and description validation
- Character restrictions, max lengths, empty handling
"""

import pytest
from pydantic import ValidationError
from app.model.directory import CreateOrGetFolderRequest, UpdateFolderRequest


class TestCreateOrGetFolderRequestValidation:
    """Test Pydantic validators for CreateOrGetFolderRequest."""

    # ==================== normalized_path Tests ====================

    def test_valid_normalized_paths(self):
        """Valid normalized paths should pass."""
        valid_paths = [
            "avena-fatua",
            "mycology/avena-fatua",
            "org/folder/subfolder",
            "test_folder",
            "folder.name",
            "folder-123",
            "a/b/c/d/e",
        ]

        for path in valid_paths:
            request = CreateOrGetFolderRequest(normalized_path=path)
            assert request.normalized_path == path

    def test_normalized_path_strips_whitespace(self):
        """Normalized path should strip leading/trailing whitespace."""
        request = CreateOrGetFolderRequest(normalized_path="  test/path  ")
        assert request.normalized_path == "test/path"

    def test_invalid_normalized_path_empty(self):
        """Empty normalized paths should fail."""
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            CreateOrGetFolderRequest(normalized_path="")

        with pytest.raises(ValidationError, match="Path cannot be empty"):
            CreateOrGetFolderRequest(normalized_path="   ")

    def test_invalid_normalized_path_special_chars(self):
        """Normalized paths with special characters should fail."""
        invalid_paths = [
            "folder@name",
            "folder#test",
            "folder name",  # Space not allowed
            "folder!test",
            "folder$test",
            "folder%test",
            "folder^test",
            "folder&test",
            "folder*test",
            "folder(test)",
            "folder[test]",
            "folder{test}",
        ]

        for path in invalid_paths:
            with pytest.raises(
                ValidationError,
                match="Path can only contain letters, numbers, slashes, underscores, dashes, and periods",
            ):
                CreateOrGetFolderRequest(normalized_path=path)

    # ==================== description Tests ====================

    def test_valid_descriptions(self):
        """Valid descriptions should pass."""
        valid_descriptions = [
            "",  # Empty allowed
            "Test description",
            "Description with periods.",
            "Multiple. Sentences. Here.",
            "Numbers 123 456",
            "UPPERCASE lowercase MiXeD",
        ]

        for desc in valid_descriptions:
            request = CreateOrGetFolderRequest(
                normalized_path="test/path", description=desc
            )
            assert request.description == desc

    def test_description_default_empty(self):
        """Description should default to empty string if not provided."""
        request = CreateOrGetFolderRequest(normalized_path="test/path")
        assert request.description == ""

    def test_invalid_description_special_chars(self):
        """Descriptions with special chars should fail."""
        invalid_descriptions = [
            "Test @#$ description",
            "Description with - hyphen",
            "Description with _ underscore",
            "Description with ! exclamation",
            "Description with / slash",
        ]

        for desc in invalid_descriptions:
            with pytest.raises(
                ValidationError,
                match="Description can only contain letters, numbers, periods, and spaces",
            ):
                CreateOrGetFolderRequest(normalized_path="test/path", description=desc)

    def test_invalid_description_newlines(self):
        """Descriptions with newlines should fail."""
        with pytest.raises(
            ValidationError,
            match="Description can only contain letters, numbers, periods, and spaces",
        ):
            CreateOrGetFolderRequest(
                normalized_path="test/path", description="Line 1\nLine 2"
            )

    def test_description_max_length(self):
        """Descriptions at exactly 500 chars should pass."""
        desc = "a" * 500
        request = CreateOrGetFolderRequest(
            normalized_path="test/path", description=desc
        )
        assert len(request.description) == 500

    def test_description_exceeds_max_length(self):
        """Descriptions exceeding 500 chars should fail."""
        desc = "a" * 501
        with pytest.raises(ValidationError, match="500 characters"):
            CreateOrGetFolderRequest(normalized_path="test/path", description=desc)


class TestUpdateFolderRequestValidation:
    """Test Pydantic validators for UpdateFolderRequest."""

    # ==================== name Tests ====================

    def test_valid_folder_names(self):
        """Valid folder names should pass."""
        valid_names = [
            "folder",
            "folder-name",
            "folder_name",
            "folder.name",
            "Folder123",
            "test-folder_123.v2",
        ]

        for name in valid_names:
            request = UpdateFolderRequest(name=name)
            assert request.name == name

    def test_folder_name_strips_whitespace(self):
        """Folder name should strip leading/trailing whitespace."""
        request = UpdateFolderRequest(name="  test-folder  ")
        assert request.name == "test-folder"

    def test_folder_name_optional(self):
        """Name field should be optional (None allowed)."""
        request = UpdateFolderRequest(name=None)
        assert request.name is None

        request = UpdateFolderRequest()
        assert request.name is None

    def test_invalid_folder_name_empty(self):
        """Empty folder names should fail."""
        with pytest.raises(ValidationError, match="Name cannot be empty"):
            UpdateFolderRequest(name="")

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            UpdateFolderRequest(name="   ")

    def test_invalid_folder_name_special_chars(self):
        """Folder names with special characters should fail."""
        invalid_names = [
            "folder name",  # Space not allowed
            "folder@test",
            "folder#test",
            "folder!test",
            "folder$test",
            "folder%test",
            "folder^test",
            "folder&test",
            "folder*test",
            "folder(test)",
            "folder[test]",
            "folder{test}",
            "folder/test",  # Slash not allowed in name
        ]

        for name in invalid_names:
            with pytest.raises(
                ValidationError,
                match="Name can only contain letters, numbers, underscores, dashes, and periods",
            ):
                UpdateFolderRequest(name=name)

    def test_invalid_folder_name_must_end_alphanumeric(self):
        """Folder names must end with alphanumeric character."""
        invalid_names = [
            "folder-",
            "folder_",
            "folder.",
            "test-folder-",
        ]

        for name in invalid_names:
            with pytest.raises(
                ValidationError,
                match="Name must end with alphanumeric character",
            ):
                UpdateFolderRequest(name=name)

    # ==================== description Tests ====================

    def test_valid_update_descriptions(self):
        """Valid descriptions should pass."""
        valid_descriptions = [
            None,  # Optional
            "",  # Empty allowed
            "Test description",
            "Description with periods.",
            "Multiple. Sentences. Here.",
            "Numbers 123 456",
            "UPPERCASE lowercase MiXeD",
        ]

        for desc in valid_descriptions:
            request = UpdateFolderRequest(description=desc)
            assert request.description == desc

    def test_description_optional(self):
        """Description field should be optional (None allowed)."""
        request = UpdateFolderRequest(description=None)
        assert request.description is None

        request = UpdateFolderRequest()
        assert request.description is None

    def test_invalid_update_description_special_chars(self):
        """Descriptions with special chars should fail."""
        invalid_descriptions = [
            "Test @#$ description",
            "Description with - hyphen",
            "Description with _ underscore",
            "Description with ! exclamation",
            "Description with / slash",
        ]

        for desc in invalid_descriptions:
            with pytest.raises(
                ValidationError,
                match="Description can only contain letters, numbers, periods, and spaces",
            ):
                UpdateFolderRequest(description=desc)

    def test_invalid_update_description_newlines(self):
        """Descriptions with newlines should fail."""
        with pytest.raises(
            ValidationError,
            match="Description can only contain letters, numbers, periods, and spaces",
        ):
            UpdateFolderRequest(description="Line 1\nLine 2")

    def test_update_description_max_length(self):
        """Descriptions at exactly 500 chars should pass."""
        desc = "a" * 500
        request = UpdateFolderRequest(description=desc)
        assert request.description is not None
        assert len(request.description) == 500

    def test_update_description_exceeds_max_length(self):
        """Descriptions exceeding 500 chars should fail."""
        desc = "a" * 501
        with pytest.raises(ValidationError, match="500 characters"):
            UpdateFolderRequest(description=desc)

    def test_update_both_fields(self):
        """Should allow updating both name and description."""
        request = UpdateFolderRequest(
            name="new-folder-name",
            description="New folder description with periods.",
        )
        assert request.name == "new-folder-name"
        assert request.description == "New folder description with periods."

    def test_update_no_fields(self):
        """Should allow creating request with no fields (both None)."""
        request = UpdateFolderRequest()
        assert request.name is None
        assert request.description is None
