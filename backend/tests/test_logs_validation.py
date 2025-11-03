"""
Tests for frontend log request Pydantic field validators.

Tests cover:
- FrontendLogRequest field validation
- Level enum restriction
- Max length enforcement
- Control character sanitization
"""

import pytest
from typing import Any, Literal
from pydantic import ValidationError
from app.model.logs import FrontendLogRequest


class TestFrontendLogRequestValidation:
    """Test Pydantic validators for FrontendLogRequest."""

    def _create_request(self, **kwargs: Any) -> FrontendLogRequest:
        """
        Helper to create FrontendLogRequest with defaults.

        Uses Any for kwargs to allow test flexibility while maintaining
        type safety for the return value.
        """
        defaults: dict[str, Any] = {
            "level": "ERROR",
            "message": "Test error message",
        }
        defaults.update(kwargs)
        return FrontendLogRequest(**defaults)

    # ==================== level Tests ====================

    def test_valid_levels(self):
        """Valid log levels should pass."""
        levels: tuple[Literal["ERROR", "WARNING", "INFO"], ...] = (
            "ERROR",
            "WARNING",
            "INFO",
        )
        for level in levels:
            request = self._create_request(level=level)
            assert request.level == level

    def test_level_defaults_to_error(self):
        """Level should default to ERROR if not provided."""
        payload = {"message": "Test message"}
        request = FrontendLogRequest(**payload)  # type: ignore[arg-type]
        assert request.level == "ERROR"

    def test_invalid_level(self):
        """Invalid log levels should fail."""
        invalid_levels = ["DEBUG", "TRACE", "CRITICAL", "FATAL", "error", "warning"]

        for level in invalid_levels:
            with pytest.raises(ValidationError):
                self._create_request(level=level)

    # ==================== message Tests ====================

    def test_valid_messages(self):
        """Valid messages should pass."""
        valid_messages = [
            "Simple error message",
            "Error with numbers 123",
            "Error with special chars: @#$%",
            "Multi-word error message with spaces",
            "a" * 1000,  # Max length
        ]

        for message in valid_messages:
            request = self._create_request(message=message)
            assert request.message == message

    def test_message_required(self):
        """Message field should be required."""
        with pytest.raises(ValidationError):
            FrontendLogRequest(level="ERROR")  # type: ignore[call-arg]

    def test_message_max_length(self):
        """Messages at exactly 1000 chars should pass."""
        message = "a" * 1000
        request = self._create_request(message=message)
        assert len(request.message) == 1000

    def test_message_exceeds_max_length(self):
        """Messages exceeding 1000 chars should fail."""
        message = "a" * 1001
        with pytest.raises(ValidationError):
            self._create_request(message=message)

    def test_message_sanitizes_control_characters(self):
        """Messages with control characters should be sanitized."""
        # Test null byte removal
        message_with_null = "Error\x00message"
        request = self._create_request(message=message_with_null)
        assert "\x00" not in request.message
        assert request.message == "Errormessage"

        # Test other control character removal (except newlines and tabs)
        message_with_controls = "Error\x01\x02\x03message"
        request = self._create_request(message=message_with_controls)
        assert request.message == "Errormessage"

    def test_message_preserves_newlines_and_tabs(self):
        """Messages should preserve newlines and tabs."""
        message_with_whitespace = "Error\nmessage\twith\ttabs"
        request = self._create_request(message=message_with_whitespace)
        assert "\n" in request.message
        assert "\t" in request.message
        assert request.message == "Error\nmessage\twith\ttabs"

    # ==================== error_type Tests ====================

    def test_valid_error_types(self):
        """Valid error types should pass."""
        valid_error_types = [
            None,  # Optional
            "TypeError",
            "NetworkError",
            "ValidationError",
            "CustomError123",
            "a" * 200,  # Max length
        ]

        for error_type in valid_error_types:
            request = self._create_request(error_type=error_type)
            assert request.error_type == error_type

    def test_error_type_optional(self):
        """Error type should be optional."""
        request = self._create_request()
        assert request.error_type is None

    def test_error_type_max_length(self):
        """Error types at exactly 200 chars should pass."""
        error_type = "a" * 200
        request = self._create_request(error_type=error_type)
        assert request.error_type is not None
        assert len(request.error_type) == 200

    def test_error_type_exceeds_max_length(self):
        """Error types exceeding 200 chars should fail."""
        error_type = "a" * 201
        with pytest.raises(ValidationError):
            self._create_request(error_type=error_type)

    def test_error_type_sanitizes_control_characters(self):
        """Error types with control characters should be sanitized."""
        error_type_with_null = "TypeError\x00Extra"
        request = self._create_request(error_type=error_type_with_null)
        assert request.error_type is not None
        assert "\x00" not in request.error_type
        assert request.error_type == "TypeErrorExtra"

    # ==================== stack_trace Tests ====================

    def test_valid_stack_traces(self):
        """Valid stack traces should pass."""
        valid_stack_traces = [
            None,  # Optional
            "at function (file.js:10:5)",
            "Error: Test\n    at function1 (file1.js:10:5)\n    at function2 (file2.js:20:10)",
            "a" * 5000,  # Max length
        ]

        for stack_trace in valid_stack_traces:
            request = self._create_request(stack_trace=stack_trace)
            assert request.stack_trace == stack_trace

    def test_stack_trace_optional(self):
        """Stack trace should be optional."""
        request = self._create_request()
        assert request.stack_trace is None

    def test_stack_trace_max_length(self):
        """Stack traces at exactly 5000 chars should pass."""
        stack_trace = "a" * 5000
        request = self._create_request(stack_trace=stack_trace)
        assert request.stack_trace is not None
        assert len(request.stack_trace) == 5000

    def test_stack_trace_exceeds_max_length(self):
        """Stack traces exceeding 5000 chars should fail."""
        stack_trace = "a" * 5001
        with pytest.raises(ValidationError):
            self._create_request(stack_trace=stack_trace)

    def test_stack_trace_preserves_newlines(self):
        """Stack traces should preserve newlines for formatting."""
        stack_trace = "Error: Test\n    at function1 (file.js:10:5)\n    at function2 (file.js:20:10)"
        request = self._create_request(stack_trace=stack_trace)
        assert request.stack_trace is not None
        assert stack_trace.count("\n") == request.stack_trace.count("\n")
        assert request.stack_trace == stack_trace

    # ==================== url Tests ====================

    def test_valid_urls(self):
        """Valid URLs should pass."""
        valid_urls = [
            None,  # Optional
            "https://example.com",
            "https://example.com/path/to/page",
            "https://example.com/path?query=value&other=123",
            "http://localhost:3000/page",
            "a" * 500,  # Max length
        ]

        for url in valid_urls:
            request = self._create_request(url=url)
            assert request.url == url

    def test_url_optional(self):
        """URL should be optional."""
        request = self._create_request()
        assert request.url is None

    def test_url_max_length(self):
        """URLs at exactly 500 chars should pass."""
        url = "a" * 500
        request = self._create_request(url=url)
        assert request.url is not None
        assert len(request.url) == 500

    def test_url_exceeds_max_length(self):
        """URLs exceeding 500 chars should fail."""
        url = "a" * 501
        with pytest.raises(ValidationError):
            self._create_request(url=url)

    def test_url_sanitizes_control_characters(self):
        """URLs with control characters should be sanitized."""
        url_with_null = "https://example.com/path\x00extra"
        request = self._create_request(url=url_with_null)
        assert request.url is not None
        assert "\x00" not in request.url
        assert request.url == "https://example.com/pathextra"

    # ==================== correlation_id Tests ====================

    def test_valid_correlation_ids(self):
        """Valid correlation IDs should pass."""
        valid_ids = [
            None,  # Optional
            "abc-123-def-456",
            "01933e4f-8b2a-7890-abcd-ef1234567890",
            "correlation_12345",
            "a" * 100,  # Max length
        ]

        for correlation_id in valid_ids:
            request = self._create_request(correlation_id=correlation_id)
            assert request.correlation_id == correlation_id

    def test_correlation_id_optional(self):
        """Correlation ID should be optional."""
        request = self._create_request()
        assert request.correlation_id is None

    def test_correlation_id_max_length(self):
        """Correlation IDs exceeding 100 chars should fail."""
        correlation_id = "a" * 101
        with pytest.raises(ValidationError):
            self._create_request(correlation_id=correlation_id)

    # ==================== session_id Tests ====================

    def test_valid_session_ids(self):
        """Valid session IDs should pass."""
        valid_ids = [
            None,  # Optional
            "session-123",
            "01933e4f-8b2a-7890-abcd-ef1234567890",
            "a" * 100,  # Max length
        ]

        for session_id in valid_ids:
            request = self._create_request(session_id=session_id)
            assert request.session_id == session_id

    def test_session_id_optional(self):
        """Session ID should be optional."""
        request = self._create_request()
        assert request.session_id is None

    def test_session_id_max_length(self):
        """Session IDs exceeding 100 chars should fail."""
        session_id = "a" * 101
        with pytest.raises(ValidationError):
            self._create_request(session_id=session_id)

    # ==================== Complete Request Tests ====================

    def test_complete_log_request(self):
        """Should accept complete log request with all fields."""
        request = FrontendLogRequest(
            level="ERROR",
            message="Test error occurred",
            error_type="NetworkError",
            stack_trace="at function (file.js:10:5)",
            url="https://example.com/page",
            correlation_id="abc-123",
            session_id="session-456",
        )
        assert request.message == "Test error occurred"
        assert request.error_type == "NetworkError"
        assert request.stack_trace == "at function (file.js:10:5)"
        assert request.url == "https://example.com/page"
        assert request.correlation_id == "abc-123"
        assert request.session_id == "session-456"

    def test_minimal_log_request(self):
        """Should accept minimal log request with only required fields."""
        request = FrontendLogRequest(message="Minimal error")  # type: ignore[call-arg]
        assert request.level == "ERROR"  # Default
        assert request.message == "Minimal error"
        assert request.error_type is None
        assert request.stack_trace is None
        assert request.url is None
        assert request.correlation_id is None
        assert request.session_id is None
