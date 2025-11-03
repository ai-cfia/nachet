"""
Tests for InferenceRequest Pydantic field validators.

Tests cover:
- imageName field validation (alphanumeric + hyphens only, max 100)
- imageDescription field validation (alphanumeric + periods + spaces only, max 500)
- trayCode enum validation (A, B, C, D, E only)
- Field validator error messages
"""

import pytest
from pydantic import ValidationError
from uuid import uuid4
from app.model.inference import InferenceRequest, TrayCode


class TestInferenceRequestValidation:
    """Test Pydantic validators for InferenceRequest fields."""

    def _get_valid_payload(self, **overrides):
        """Helper to create a valid InferenceRequest payload with optional overrides."""
        payload = {
            "pipelineId": str(uuid4()),
            "folderName": "test-folder",
            "folderId": str(uuid4()),
            "imageDims": [1920, 1080],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "imageName": "Test-Image-001",
            "imageDescription": "Test description",
            "deviceModelId": str(uuid4()),
            "deviceLensId": str(uuid4()),
            "trayCode": "A",
            "magnification": 10.0,
        }
        payload.update(overrides)
        return payload

    # ==================== imageName Tests ====================

    def test_valid_image_name(self):
        """Valid image names should pass validation."""
        valid_names = [
            "Image-123",
            "Test-Image",
            "ABC-DEF-789",
            "sample001",
            "TEST",
            "a",
            "123",
            "Image-123-Test-456",
        ]

        for name in valid_names:
            payload = self._get_valid_payload(imageName=name)
            request = InferenceRequest(**payload)
            assert request.image_name == name

    def test_invalid_image_name_special_chars(self):
        """Image names with special chars should fail."""
        invalid_names = [
            "Image@123",
            "Test#Image",
            "Sample_Image",  # Underscores not allowed
            "Image.png",  # Periods not allowed
            "Test Image",  # Spaces not allowed
            "Image!",
            "Image$123",
            "Test%Name",
            "Image^123",
            "Test&Name",
            "Image*123",
            "Test(Name)",
            "Image+123",
            "Test=Name",
            "Image[123]",
            "Test{Name}",
        ]

        for name in invalid_names:
            payload = self._get_valid_payload(imageName=name)
            with pytest.raises(
                ValidationError, match="can only contain letters, numbers, and hyphens"
            ):
                InferenceRequest(**payload)

    def test_invalid_image_name_empty(self):
        """Empty image names should fail."""
        invalid_names = ["", "   ", "\t", "\n"]

        for name in invalid_names:
            payload = self._get_valid_payload(imageName=name)
            with pytest.raises(ValidationError, match="cannot be empty"):
                InferenceRequest(**payload)

    def test_invalid_image_name_max_length(self):
        """Image names exceeding 100 chars should fail."""
        long_name = "a" * 101
        payload = self._get_valid_payload(imageName=long_name)

        with pytest.raises(ValidationError, match="100 characters"):
            InferenceRequest(**payload)

    def test_image_name_at_max_length(self):
        """Image names at exactly 100 chars should pass."""
        name_100 = "a" * 100
        payload = self._get_valid_payload(imageName=name_100)

        request = InferenceRequest(**payload)
        assert len(request.image_name) == 100

    # ==================== imageDescription Tests ====================

    def test_valid_image_description(self):
        """Valid image descriptions should pass validation."""
        valid_descriptions = [
            "Simple description",
            "Description with periods.",
            "Multiple. Sentences. Here.",
            "Numbers 123 456 789",
            "UPPERCASE lowercase MiXeD",
            "",  # Empty description is allowed
            "   ",  # Whitespace-only should be allowed initially (can be trimmed)
            "a",
            ".",
            "Description with multiple spaces   between words",
        ]

        for desc in valid_descriptions:
            payload = self._get_valid_payload(imageDescription=desc)
            request = InferenceRequest(**payload)
            assert request.image_description == desc

    def test_invalid_description_special_chars(self):
        """Descriptions with disallowed special chars should fail."""
        invalid_descriptions = [
            "Description with @ symbol",
            "Description with # hashtag",
            "Description with $ dollar",
            "Description with % percent",
            "Description with ^ caret",
            "Description with & ampersand",
            "Description with * asterisk",
            "Description with (parentheses)",
            "Description with [brackets]",
            "Description with {braces}",
            "Description with | pipe",
            "Description with \\ backslash",
            "Description with / slash",
            "Description with - hyphen",
            "Description with _ underscore",
            "Description with = equals",
            "Description with + plus",
            "Description with ! exclamation",
            "Description with ? question",
            "Description with : colon",
            "Description with ; semicolon",
            'Description with " quote',
            "Description with ' apostrophe",
            "Description with < less",
            "Description with > greater",
        ]

        for desc in invalid_descriptions:
            payload = self._get_valid_payload(imageDescription=desc)
            with pytest.raises(
                ValidationError,
                match="can only contain letters, numbers, periods, and spaces",
            ):
                InferenceRequest(**payload)

    def test_invalid_description_unicode(self):
        """Descriptions with Unicode chars should fail."""
        invalid_descriptions = [
            "Description with Café",
            "Description with français",
            "Description with 日本語",
            "Description with emoji 😀",
            "Description with é accents",
        ]

        for desc in invalid_descriptions:
            payload = self._get_valid_payload(imageDescription=desc)
            with pytest.raises(
                ValidationError,
                match="can only contain letters, numbers, periods, and spaces",
            ):
                InferenceRequest(**payload)

    def test_invalid_description_max_length(self):
        """Descriptions exceeding 500 chars should fail."""
        long_desc = "a" * 501
        payload = self._get_valid_payload(imageDescription=long_desc)

        with pytest.raises(ValidationError, match="500 characters"):
            InferenceRequest(**payload)

    def test_description_at_max_length(self):
        """Descriptions at exactly 500 chars should pass."""
        desc_500 = "a" * 500
        payload = self._get_valid_payload(imageDescription=desc_500)

        request = InferenceRequest(**payload)
        assert len(request.image_description) == 500

    # ==================== trayCode Tests ====================

    def test_valid_tray_codes(self):
        """Valid tray codes A-E should pass."""
        valid_codes = ["A", "B", "C", "D", "E"]

        for code in valid_codes:
            payload = self._get_valid_payload(trayCode=code)
            request = InferenceRequest(**payload)
            assert request.tray_code == TrayCode(code)
            assert request.tray_code.value == code

    def test_invalid_tray_code_wrong_letter(self):
        """Invalid tray codes (F-Z, etc.) should fail."""
        invalid_codes = ["F", "G", "Z", "X"]

        for code in invalid_codes:
            payload = self._get_valid_payload(trayCode=code)
            with pytest.raises(ValidationError):
                InferenceRequest(**payload)

    def test_invalid_tray_code_lowercase(self):
        """Lowercase tray codes should fail."""
        invalid_codes = ["a", "b", "c", "d", "e"]

        for code in invalid_codes:
            payload = self._get_valid_payload(trayCode=code)
            with pytest.raises(ValidationError):
                InferenceRequest(**payload)

    def test_invalid_tray_code_number(self):
        """Numeric tray codes should fail."""
        invalid_codes = ["1", "2", "3", "4", "5"]

        for code in invalid_codes:
            payload = self._get_valid_payload(trayCode=code)
            with pytest.raises(ValidationError):
                InferenceRequest(**payload)

    def test_invalid_tray_code_empty(self):
        """Empty tray code should fail."""
        payload = self._get_valid_payload(trayCode="")

        with pytest.raises(ValidationError):
            InferenceRequest(**payload)

    def test_invalid_tray_code_multiple_chars(self):
        """Multi-character tray codes should fail."""
        invalid_codes = ["AA", "AB", "ABC", "A1", "1A"]

        for code in invalid_codes:
            payload = self._get_valid_payload(trayCode=code)
            with pytest.raises(ValidationError):
                InferenceRequest(**payload)

    # ==================== Combined Field Tests ====================

    def test_all_valid_fields(self):
        """Request with all valid fields should pass."""
        payload = self._get_valid_payload(
            imageName="Valid-Image-123",
            imageDescription="This is a valid description with periods.",
            trayCode="C",
        )

        request = InferenceRequest(**payload)
        assert request.image_name == "Valid-Image-123"
        assert request.image_description == "This is a valid description with periods."
        assert request.tray_code == TrayCode.C

    def test_multiple_invalid_fields(self):
        """Request with multiple invalid fields should fail."""
        payload = self._get_valid_payload(
            imageName="Invalid_Name!",  # Invalid
            imageDescription="Invalid @ description",  # Invalid
            trayCode="Z",  # Invalid
        )

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**payload)

        # Should have multiple validation errors
        errors = exc_info.value.errors()
        assert len(errors) >= 2  # At least 2 fields invalid

    def test_field_alias_mapping(self):
        """Should correctly map camelCase aliases to snake_case fields."""
        payload = self._get_valid_payload()

        request = InferenceRequest(**payload)

        # Check alias mapping works
        assert hasattr(request, "image_name")
        assert hasattr(request, "image_description")
        assert hasattr(request, "tray_code")
