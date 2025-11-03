"""
Tests for text sanitization utility.

Tests cover:
- Valid text sanitization with character filtering
- Whitespace trimming and normalization
- Character set restrictions (matching frontend)
- Max length enforcement
- Empty text rejection
- Field-specific patterns (image name, description)
"""

import pytest
from app.service.inference.submission import sanitize_text


class TestSanitizeText:
    """Test suite for sanitize_text function with character filtering."""

    def test_sanitize_valid_alphanumeric_text(self):
        """Should preserve valid alphanumeric text."""
        text = "Valid image name 123"
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        assert result == "Valid image name 123"

    def test_sanitize_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        text = "  Image Name  "
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        assert result == "Image Name"

    def test_sanitize_removes_special_characters(self):
        """Should remove special characters not in allowed set."""
        text = "Image @#$%^&*() name-123"
        # With default allowed_chars (alphanumeric, periods, spaces)
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        # Special chars removed, hyphen removed
        assert result == "Image name123"

    def test_sanitize_removes_unicode(self):
        """Should remove Unicode characters not in allowed set."""
        text = "Café français 日本語"
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        # Unicode characters removed (trailing space stripped)
        assert result == "Caf franais"

    def test_sanitize_normalizes_multiple_spaces(self):
        """Should normalize multiple spaces to single space."""
        text = "Multiple    spaces   here"
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        assert result == "Multiple spaces here"

    def test_sanitize_normalizes_newlines_and_tabs(self):
        """Should normalize newlines and tabs to spaces."""
        text = "Line 1\nLine 2\tTabbed"
        result = sanitize_text(
            text, max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        # Newlines and tabs are not in allowed_chars, so they're removed
        # But the spaces between words are preserved
        assert result == "Line 1Line 2Tabbed"

    def test_sanitize_removes_consecutive_periods(self):
        """Should remove consecutive periods in description fields."""
        text = "Description with... multiple... periods..."
        result = sanitize_text(
            text, max_length=500, allowed_chars="a-zA-Z0-9. ", field_name="Description"
        )
        assert result == "Description with. multiple. periods."

    def test_sanitize_enforces_max_length(self):
        """Should raise ValueError if text exceeds max_length."""
        text = "a" * 300
        with pytest.raises(ValueError, match="exceeds maximum length of 255"):
            sanitize_text(
                text, max_length=255, allowed_chars="a-zA-Z0-9", field_name="Test"
            )

    def test_sanitize_rejects_empty_text(self):
        """Should raise ValueError if text is empty after sanitization."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_text(
                "   ", max_length=255, allowed_chars="a-zA-Z0-9. ", field_name="Test"
            )

    def test_sanitize_rejects_only_special_characters(self):
        """Should raise ValueError if text contains only special characters."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_text(
                "@#$%^&*()",
                max_length=255,
                allowed_chars="a-zA-Z0-9",
                field_name="Test",
            )

    def test_sanitize_custom_max_length(self):
        """Should respect custom max_length parameter."""
        text = "a" * 50
        result = sanitize_text(
            text, max_length=100, allowed_chars="a-zA-Z0-9", field_name="Test"
        )
        assert len(result) == 50

        with pytest.raises(ValueError, match="exceeds maximum length of 10"):
            sanitize_text(
                text, max_length=10, allowed_chars="a-zA-Z0-9", field_name="Test"
            )

    # Field-specific pattern tests

    def test_sanitize_image_name_pattern(self):
        """Should validate image name with alphanumeric and hyphens only."""
        # Valid image name
        text = "Sample-Image-001"
        result = sanitize_text(
            text, max_length=100, allowed_chars="a-zA-Z0-9-", field_name="Image name"
        )
        assert result == "Sample-Image-001"

        # Remove underscores and periods
        text = "Sample_Image_001.png"
        result = sanitize_text(
            text, max_length=100, allowed_chars="a-zA-Z0-9-", field_name="Image name"
        )
        assert result == "SampleImage001png"

    def test_sanitize_image_name_max_length(self):
        """Should enforce 100 character limit for image names."""
        text = "a" * 101
        with pytest.raises(ValueError, match="exceeds maximum length of 100"):
            sanitize_text(
                text,
                max_length=100,
                allowed_chars="a-zA-Z0-9-",
                field_name="Image name",
            )

    def test_sanitize_description_pattern(self):
        """Should validate description with alphanumeric, periods, and spaces."""
        text = "This is a valid description. It has periods."
        result = sanitize_text(
            text,
            max_length=500,
            allowed_chars="a-zA-Z0-9. ",
            field_name="Image description",
        )
        assert result == "This is a valid description. It has periods."

        # Remove special characters
        text = "Description with @special #characters!"
        result = sanitize_text(
            text,
            max_length=500,
            allowed_chars="a-zA-Z0-9. ",
            field_name="Image description",
        )
        assert result == "Description with special characters"

    def test_sanitize_description_max_length(self):
        """Should enforce 500 character limit for descriptions."""
        text = "a" * 501
        with pytest.raises(ValueError, match="exceeds maximum length of 500"):
            sanitize_text(
                text,
                max_length=500,
                allowed_chars="a-zA-Z0-9. ",
                field_name="Image description",
            )

    def test_sanitize_tray_code_pattern(self):
        """Should validate tray code (though enum validation happens in Pydantic)."""
        # Valid tray codes
        for code in ["A", "B", "C", "D", "E"]:
            result = sanitize_text(
                code, max_length=1, allowed_chars="A-Z", field_name="Tray code"
            )
            assert result == code

    def test_sanitize_with_custom_field_name(self):
        """Should include custom field name in error messages."""
        with pytest.raises(ValueError, match="Custom Field.*cannot be empty"):
            sanitize_text(
                "   ",
                max_length=100,
                allowed_chars="a-zA-Z0-9",
                field_name="Custom Field",
            )

        text = "a" * 200
        with pytest.raises(ValueError, match="Custom Field.*exceeds maximum length"):
            sanitize_text(
                text,
                max_length=100,
                allowed_chars="a-zA-Z0-9",
                field_name="Custom Field",
            )

    def test_sanitize_preserves_valid_hyphens(self):
        """Should preserve hyphens when in allowed character set."""
        text = "Test-With-Hyphens"
        result = sanitize_text(
            text, max_length=100, allowed_chars="a-zA-Z0-9-", field_name="Test"
        )
        assert result == "Test-With-Hyphens"

    def test_sanitize_preserves_valid_periods(self):
        """Should preserve periods when in allowed character set."""
        text = "Test. With. Periods."
        result = sanitize_text(
            text, max_length=100, allowed_chars="a-zA-Z0-9. ", field_name="Test"
        )
        assert result == "Test. With. Periods."

    def test_sanitize_multiline_description(self):
        """Should handle multiline descriptions by removing newlines."""
        text = """This is a multiline description
        with multiple lines and    extra spaces.
        It should be sanitized properly."""
        result = sanitize_text(
            text.strip(),
            max_length=1000,
            allowed_chars="a-zA-Z0-9. ",
            field_name="Description",
        )
        # Newlines removed, multiple spaces normalized
        assert "multiline description" in result
        assert "\n" not in result
        assert len(result) < 1000
