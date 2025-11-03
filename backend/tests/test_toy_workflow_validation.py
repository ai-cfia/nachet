"""
Tests for toy workflow request Pydantic field validators.

Tests cover:
- ToyWorkflowRequest name validation
- Empty string rejection
- Max length enforcement
- Whitespace trimming
"""

import pytest
from pydantic import ValidationError
from app.api.test_dbos import ToyWorkflowRequest


class TestToyWorkflowRequestValidation:
    """Test Pydantic validators for ToyWorkflowRequest."""

    # ==================== name Tests ====================

    def test_valid_names(self):
        """Valid names should pass."""
        valid_names = [
            "Alice",
            "Bob",
            "Test User",
            "User123",
            "Test-User-Name",
            "a" * 100,  # Max length
        ]

        for name in valid_names:
            request = ToyWorkflowRequest(name=name)
            assert request.name == name

    def test_name_strips_whitespace(self):
        """Name should strip leading and trailing whitespace."""
        request = ToyWorkflowRequest(name="  Alice  ")
        assert request.name == "Alice"

        request = ToyWorkflowRequest(name="\tBob\t")
        assert request.name == "Bob"

    def test_name_required(self):
        """Name field should be required."""
        with pytest.raises(ValidationError):
            ToyWorkflowRequest()  # type: ignore[call-arg]

    def test_invalid_name_empty(self):
        """Empty names should fail."""
        with pytest.raises(ValidationError, match="Name cannot be empty"):
            ToyWorkflowRequest(name="")

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            ToyWorkflowRequest(name="   ")

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            ToyWorkflowRequest(name="\t\n")

    def test_name_max_length(self):
        """Names at exactly 100 chars should pass."""
        name = "a" * 100
        request = ToyWorkflowRequest(name=name)
        assert len(request.name) == 100

    def test_name_exceeds_max_length(self):
        """Names exceeding 100 chars should fail."""
        name = "a" * 101
        with pytest.raises(ValidationError, match="100 characters"):
            ToyWorkflowRequest(name=name)

    def test_name_with_special_characters(self):
        """Names with special characters should pass (no character restrictions)."""
        # Unlike other validators, ToyWorkflowRequest has no character restrictions
        # (it's just a test endpoint)
        names_with_special_chars = [
            "Test@User",
            "User#123",
            "Name!",
            "Test$Value",
            "User%Name",
        ]

        for name in names_with_special_chars:
            request = ToyWorkflowRequest(name=name)
            assert request.name == name

    def test_name_with_unicode(self):
        """Names with unicode characters should pass."""
        unicode_names = [
            "François",
            "José",
            "日本語",
            "Привет",
            "مرحبا",
        ]

        for name in unicode_names:
            request = ToyWorkflowRequest(name=name)
            assert request.name == name

    def test_name_with_newlines(self):
        """Names with newlines should pass (just testing basic length/empty validation)."""
        # Note: The validator only checks empty and max length, not character content
        name_with_newline = "Line1\nLine2"
        request = ToyWorkflowRequest(name=name_with_newline)
        assert request.name == name_with_newline

    def test_name_preserves_internal_whitespace(self):
        """Internal whitespace should be preserved after stripping edges."""
        request = ToyWorkflowRequest(name="  First  Second  ")
        # Should strip edges but preserve internal spaces
        assert request.name == "First  Second"
