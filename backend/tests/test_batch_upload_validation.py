"""
Tests for batch upload Pydantic field validators.

Tests cover:
- sample_id field validation (alphanumeric + hyphens only, no trailing dash)
- image_description field validation (alphanumeric + periods + spaces, max 500)
- Field validator error messages
"""

import pytest
from pydantic import ValidationError
from uuid import uuid4
from app.model.batch_upload import BatchUploadImageRequest


class TestBatchUploadValidation:
    """Test Pydantic validators for BatchUploadImageRequest fields."""

    def _get_valid_payload(self, **overrides):
        """Helper to create valid batch upload payload."""
        payload = {
            "sessionId": str(uuid4()),
            "seedId": str(uuid4()),
            "trayCode": "A",
            "sampleId": "Sample-001",
            "imageDescription": "Test description",  # Required field
            "deviceBrandId": str(uuid4()),
            "deviceModelId": str(uuid4()),
            "deviceLensId": str(uuid4()),
            "magnification": 40.0,
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        }
        payload.update(overrides)
        return payload

    # ==================== sample_id Tests ====================

    def test_valid_sample_id(self):
        """Valid sample IDs should pass."""
        valid_ids = ["Sample-001", "Test-Image", "ABC-123", "sample", "123", "A-B-C"]

        for sample_id in valid_ids:
            payload = self._get_valid_payload(sampleId=sample_id)
            request = BatchUploadImageRequest(**payload)
            assert request.sample_id == sample_id

    def test_invalid_sample_id_underscore(self):
        """Sample IDs with underscores should fail."""
        payload = self._get_valid_payload(sampleId="Sample_001")
        with pytest.raises(
            ValidationError, match="can only contain letters, numbers, and hyphens"
        ):
            BatchUploadImageRequest(**payload)

    def test_invalid_sample_id_spaces(self):
        """Sample IDs with spaces should fail."""
        payload = self._get_valid_payload(sampleId="Sample 001")
        with pytest.raises(
            ValidationError, match="can only contain letters, numbers, and hyphens"
        ):
            BatchUploadImageRequest(**payload)

    def test_invalid_sample_id_special_chars(self):
        """Sample IDs with special chars should fail."""
        invalid_ids = ["Sample@001", "Test#Image", "Sample.png", "Image!", "Test$123"]

        for sample_id in invalid_ids:
            payload = self._get_valid_payload(sampleId=sample_id)
            with pytest.raises(
                ValidationError, match="can only contain letters, numbers, and hyphens"
            ):
                BatchUploadImageRequest(**payload)

    def test_invalid_sample_id_trailing_dash(self):
        """Sample IDs ending with dash should fail."""
        payload = self._get_valid_payload(sampleId="Sample-")
        with pytest.raises(ValidationError, match="cannot end with a hyphen"):
            BatchUploadImageRequest(**payload)

    def test_invalid_sample_id_empty(self):
        """Empty sample IDs should fail."""
        # Empty string caught by min_length constraint
        payload = self._get_valid_payload(sampleId="")
        with pytest.raises(ValidationError):
            BatchUploadImageRequest(**payload)

        # Whitespace-only caught by our validator
        payload = self._get_valid_payload(sampleId="   ")
        with pytest.raises(ValidationError, match="cannot be empty"):
            BatchUploadImageRequest(**payload)

    def test_sample_id_max_length(self):
        """Sample IDs at exactly 100 chars should pass."""
        sample_id = "a" * 100
        payload = self._get_valid_payload(sampleId=sample_id)
        request = BatchUploadImageRequest(**payload)
        assert len(request.sample_id) == 100

    def test_sample_id_exceeds_max_length(self):
        """Sample IDs exceeding 100 chars should fail."""
        sample_id = "a" * 101
        payload = self._get_valid_payload(sampleId=sample_id)
        with pytest.raises(ValidationError):
            BatchUploadImageRequest(**payload)

    # ==================== image_description Tests ====================

    def test_valid_description(self):
        """Valid descriptions should pass."""
        valid_descriptions = [
            "Test description",
            "Description with periods.",
            "Multiple. Sentences. Here.",
            "Numbers 123 456",
            "UPPERCASE lowercase MiXeD",
        ]

        for desc in valid_descriptions:
            payload = self._get_valid_payload(imageDescription=desc)
            request = BatchUploadImageRequest(**payload)
            assert request.image_description == desc

    def test_description_required(self):
        """Description should be required (missing field should fail)."""
        payload = self._get_valid_payload()
        # Remove imageDescription - should fail
        del payload["imageDescription"]
        with pytest.raises(ValidationError):
            BatchUploadImageRequest(**payload)

    def test_description_empty_string(self):
        """Empty description string should be allowed."""
        payload = self._get_valid_payload(imageDescription="")
        request = BatchUploadImageRequest(**payload)
        assert request.image_description == ""

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
            payload = self._get_valid_payload(imageDescription=desc)
            with pytest.raises(
                ValidationError,
                match="can only contain letters, numbers, periods, and spaces",
            ):
                BatchUploadImageRequest(**payload)

    def test_invalid_description_newlines(self):
        """Descriptions with newlines should fail."""
        payload = self._get_valid_payload(imageDescription="Line 1\nLine 2")
        with pytest.raises(
            ValidationError,
            match="can only contain letters, numbers, periods, and spaces",
        ):
            BatchUploadImageRequest(**payload)

    def test_description_max_length(self):
        """Descriptions at exactly 500 chars should pass."""
        desc = "a" * 500
        payload = self._get_valid_payload(imageDescription=desc)
        request = BatchUploadImageRequest(**payload)
        assert len(request.image_description) == 500

    def test_description_exceeds_max_length(self):
        """Descriptions exceeding 500 chars should fail."""
        desc = "a" * 501
        payload = self._get_valid_payload(imageDescription=desc)
        with pytest.raises(ValidationError, match="500 characters"):
            BatchUploadImageRequest(**payload)

    # ==================== tray_code Tests ====================

    def test_valid_tray_codes(self):
        """Valid tray codes A-E should pass."""
        for code in ["A", "B", "C", "D", "E"]:
            payload = self._get_valid_payload(trayCode=code)
            request = BatchUploadImageRequest(**payload)
            assert request.tray_code == code

    def test_invalid_tray_code(self):
        """Invalid tray codes should fail."""
        invalid_codes = ["F", "Z", "1", "a", "AA", ""]

        for code in invalid_codes:
            payload = self._get_valid_payload(trayCode=code)
            with pytest.raises(ValidationError):
                BatchUploadImageRequest(**payload)
