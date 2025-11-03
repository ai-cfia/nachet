"""
Tests for InferenceRequest metadata field validation.

Tests cover:
- Required metadata fields validation
- Pydantic alias handling (camelCase from frontend)
- UUID validation for device fields
- Type validation for all metadata fields
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.model.inference import InferenceRequest


class TestInferenceRequestMetadata:
    """Test suite for InferenceRequest metadata validation."""

    @pytest.fixture
    def valid_request_data(self):
        """Valid inference request payload with all required fields."""
        return {
            "pipeline_id": str(uuid4()),
            "folder_name": "test_folder",
            "folder_id": str(uuid4()),
            "imageDims": [1920, 1080],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            # Metadata fields (camelCase from frontend)
            "imageName": "Test-Image",  # Alphanumeric + hyphens only
            "imageDescription": "Test description",
            "deviceModelId": str(uuid4()),
            "deviceLensId": str(uuid4()),
            "trayCode": "A",  # Must be A, B, C, D, or E
            "magnification": 40.0,
        }

    def test_valid_request_with_all_metadata(self, valid_request_data):
        """Should accept valid request with all metadata fields."""
        request = InferenceRequest(**valid_request_data)

        assert request.image_name == "Test-Image"
        assert request.image_description == "Test description"
        assert request.tray_code.value == "A"  # tray_code is now an enum
        assert request.magnification == 40.0
        assert isinstance(request.device_model_id, type(uuid4()))
        assert isinstance(request.device_lens_id, type(uuid4()))

    def test_missing_image_name_raises_error(self, valid_request_data):
        """Should raise ValidationError if imageName is missing."""
        del valid_request_data["imageName"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        # Pydantic shows the alias name (imageName) in error messages
        assert (
            "imagename" in str(exc_info.value).lower()
            or "required" in str(exc_info.value).lower()
        )

    def test_missing_image_description_raises_error(self, valid_request_data):
        """Should raise ValidationError if imageDescription is missing."""
        del valid_request_data["imageDescription"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert (
            "imagedescription" in str(exc_info.value).lower()
            or "required" in str(exc_info.value).lower()
        )

    def test_missing_device_model_id_raises_error(self, valid_request_data):
        """Should raise ValidationError if deviceModelId is missing."""
        del valid_request_data["deviceModelId"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert (
            "devicemodelid" in str(exc_info.value).lower()
            or "required" in str(exc_info.value).lower()
        )

    def test_missing_device_lens_id_raises_error(self, valid_request_data):
        """Should raise ValidationError if deviceLensId is missing."""
        del valid_request_data["deviceLensId"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert (
            "devicelensid" in str(exc_info.value).lower()
            or "required" in str(exc_info.value).lower()
        )

    def test_missing_tray_code_raises_error(self, valid_request_data):
        """Should raise ValidationError if trayCode is missing."""
        del valid_request_data["trayCode"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert (
            "traycode" in str(exc_info.value).lower()
            or "required" in str(exc_info.value).lower()
        )

    def test_missing_magnification_raises_error(self, valid_request_data):
        """Should raise ValidationError if magnification is missing."""
        del valid_request_data["magnification"]

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert "magnification" in str(exc_info.value).lower()

    def test_invalid_device_model_id_uuid(self, valid_request_data):
        """Should raise ValidationError if deviceModelId is not a valid UUID."""
        valid_request_data["deviceModelId"] = "not-a-uuid"

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        error_str = str(exc_info.value).lower()
        assert "uuid" in error_str or "device_model_id" in error_str

    def test_invalid_device_lens_id_uuid(self, valid_request_data):
        """Should raise ValidationError if deviceLensId is not a valid UUID."""
        valid_request_data["deviceLensId"] = "not-a-uuid"

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        error_str = str(exc_info.value).lower()
        assert "uuid" in error_str or "device_lens_id" in error_str

    def test_invalid_magnification_type(self, valid_request_data):
        """Should raise ValidationError if magnification is not a number."""
        valid_request_data["magnification"] = "not-a-number"

        with pytest.raises(ValidationError) as exc_info:
            InferenceRequest(**valid_request_data)

        assert "magnification" in str(exc_info.value).lower()

    def test_pydantic_alias_camelcase_to_snakecase(self, valid_request_data):
        """Should correctly map camelCase aliases to snake_case field names."""
        request = InferenceRequest(**valid_request_data)

        # Verify internal field names are snake_case
        assert hasattr(request, "image_name")
        assert hasattr(request, "image_description")
        assert hasattr(request, "device_model_id")
        assert hasattr(request, "device_lens_id")
        assert hasattr(request, "tray_code")

        # Verify values are correctly assigned
        assert request.image_name == valid_request_data["imageName"]
        assert request.image_description == valid_request_data["imageDescription"]
        assert str(request.device_model_id) == valid_request_data["deviceModelId"]
        assert str(request.device_lens_id) == valid_request_data["deviceLensId"]
        assert request.tray_code == valid_request_data["trayCode"]

    def test_empty_string_metadata_fields(self, valid_request_data):
        """Should reject empty imageName and invalid trayCode (validation at Pydantic level)."""
        # Empty imageName should be rejected
        valid_request_data["imageName"] = ""
        with pytest.raises(ValidationError, match="Image name cannot be empty"):
            InferenceRequest(**valid_request_data)

        # Reset imageName, test invalid trayCode
        valid_request_data["imageName"] = "Valid-Name"
        valid_request_data["trayCode"] = ""
        with pytest.raises(ValidationError):
            InferenceRequest(**valid_request_data)

        # Empty imageDescription is allowed
        valid_request_data["trayCode"] = "C"
        valid_request_data["imageDescription"] = ""
        request = InferenceRequest(**valid_request_data)
        assert request.image_description == ""

    def test_zero_magnification(self, valid_request_data):
        """Should accept zero magnification."""
        valid_request_data["magnification"] = 0.0
        request = InferenceRequest(**valid_request_data)
        assert request.magnification == 0.0

    def test_negative_magnification(self, valid_request_data):
        """Should accept negative magnification (validation in service layer)."""
        valid_request_data["magnification"] = -10.0
        request = InferenceRequest(**valid_request_data)
        assert request.magnification == -10.0

    def test_integer_magnification_converted_to_float(self, valid_request_data):
        """Should convert integer magnification to float."""
        valid_request_data["magnification"] = 40  # Integer
        request = InferenceRequest(**valid_request_data)
        assert isinstance(request.magnification, float)
        assert request.magnification == 40.0

    def test_long_text_metadata_fields(self, valid_request_data):
        """Should reject text exceeding max lengths (validation at Pydantic level)."""
        # imageName max 100 chars
        valid_request_data["imageName"] = "A" * 101
        with pytest.raises(ValidationError, match="100 characters"):
            InferenceRequest(**valid_request_data)

        # imageDescription max 500 chars
        valid_request_data["imageName"] = "Valid-Name"
        valid_request_data["imageDescription"] = "B" * 501
        with pytest.raises(ValidationError, match="500 characters"):
            InferenceRequest(**valid_request_data)

        # At max length should work
        valid_request_data["imageName"] = "A" * 100
        valid_request_data["imageDescription"] = "B" * 500
        request = InferenceRequest(**valid_request_data)
        assert len(request.image_name) == 100
        assert len(request.image_description) == 500

    def test_special_characters_in_metadata(self, valid_request_data):
        """Should reject special characters in metadata fields (validation at Pydantic level)."""
        # imageName rejects special characters
        valid_request_data["imageName"] = "Image @#$%^&*() 123"
        with pytest.raises(
            ValidationError, match="can only contain letters, numbers, and hyphens"
        ):
            InferenceRequest(**valid_request_data)

        # imageDescription rejects special characters (except periods and spaces)
        valid_request_data["imageName"] = "Valid-Name"
        valid_request_data["imageDescription"] = "Description with\nnewlines and\ttabs"
        with pytest.raises(
            ValidationError,
            match="can only contain letters, numbers, periods, and spaces",
        ):
            InferenceRequest(**valid_request_data)

        # trayCode must be enum
        valid_request_data["imageDescription"] = "Valid description"
        valid_request_data["trayCode"] = "TRAY-001"
        with pytest.raises(ValidationError):
            InferenceRequest(**valid_request_data)
