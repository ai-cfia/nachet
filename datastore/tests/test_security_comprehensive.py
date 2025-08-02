"""
Comprehensive test suite for datastore.db.queries.user.security module.
This test suite verifies SQL injection protection and input validation.
"""

import unittest
import uuid

from datastore.db.queries.user.security import (
    SecurityValidationError,
    validate_email,
    validate_user_id,
    validate_container_url,
    sanitize_query_log,
)


class TestEmailValidation(unittest.TestCase):
    """Test class for email validation security functions."""

    def test_validate_email_valid(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "firstname+lastname@company.ca",
            "user123@test-domain.co.uk",
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                result = validate_email(email)
                self.assertEqual(result, email.lower())

    def test_validate_email_invalid_type(self):
        """Test rejection of non-string email inputs."""
        invalid_inputs = [
            123,
            None,
            [],
            {},
            True,
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_email(invalid_input)
                self.assertIn("must be a string", str(context.exception))

    def test_validate_email_too_long(self):
        """Test rejection of overly long email addresses."""
        long_email = "a" * 250 + "@example.com"  # 265 characters
        
        with self.assertRaises(SecurityValidationError) as context:
            validate_email(long_email)
        self.assertIn("too long", str(context.exception))

    def test_validate_email_too_short(self):
        """Test rejection of overly short email addresses."""
        short_emails = ["a", "ab", "@."]
        
        for email in short_emails:
            with self.subTest(email=email):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_email(email)
                self.assertIn("too short", str(context.exception))

    def test_validate_email_invalid_format(self):
        """Test rejection of invalid email formats."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",
            "user.example.com",
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_email(email)
                self.assertIn("Invalid email format", str(context.exception))

    def test_validate_email_sql_injection_attempts(self):
        """Test rejection of SQL injection attempts in email."""
        malicious_emails = [
            "test'; DROP TABLE users; --@example.com",
            'test"; DELETE FROM users; --@example.com',
            "test@example.com'; UNION SELECT * FROM passwords; --",
            "test@example.com/*comment*/",
            "test\\@example.com",
            "test\x00@example.com",
        ]
        
        for email in malicious_emails:
            with self.subTest(email=email):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_email(email)
                self.assertTrue(
                    "suspicious character" in str(context.exception) or
                    "Invalid email format" in str(context.exception)
                )

    def test_validate_email_sql_keywords(self):
        """Test rejection of SQL keywords in email."""
        malicious_emails = [
            "selecttest@example.com",
            "test-union@example.com",
            "drop-table@example.com",
            "INSERT-INTO@example.com",
        ]
        
        for email in malicious_emails:
            with self.subTest(email=email):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_email(email)
                self.assertIn("SQL keyword", str(context.exception))


class TestUserIdValidation(unittest.TestCase):
    """Test class for user ID validation security functions."""

    def test_validate_user_id_valid_string(self):
        """Test validation of valid UUID strings."""
        valid_uuid = str(uuid.uuid4())
        result = validate_user_id(valid_uuid)
        self.assertEqual(result, valid_uuid)

    def test_validate_user_id_valid_uuid_object(self):
        """Test validation of valid UUID objects."""
        valid_uuid = uuid.uuid4()
        result = validate_user_id(valid_uuid)
        self.assertEqual(result, str(valid_uuid))

    def test_validate_user_id_invalid_type(self):
        """Test rejection of non-string/UUID inputs."""
        invalid_inputs = [
            123,
            None,
            [],
            {},
            True,
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_user_id(invalid_input)
                self.assertIn("must be a string or UUID", str(context.exception))

    def test_validate_user_id_invalid_length(self):
        """Test rejection of invalid UUID lengths."""
        invalid_lengths = [
            "too-short",
            "this-is-way-too-long-to-be-a-valid-uuid-string",
        ]
        
        for invalid_uuid in invalid_lengths:
            with self.subTest(uuid=invalid_uuid):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_user_id(invalid_uuid)
                self.assertTrue(
                    "too short" in str(context.exception) or
                    "too long" in str(context.exception)
                )

    def test_validate_user_id_invalid_format(self):
        """Test rejection of invalid UUID formats."""
        # Test UUIDs with correct length but invalid format
        invalid_uuids = [
            "12345678-1234-1234-1234-12345678901z",  # invalid character
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # invalid format
        ]
        
        for invalid_uuid in invalid_uuids:
            with self.subTest(uuid=invalid_uuid):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_user_id(invalid_uuid)
                self.assertIn("Invalid UUID format", str(context.exception))
                
        # Test UUIDs with wrong length (these should fail length check first)
        wrong_length_uuids = [
            "not-a-valid-uuid-format-at-all-here",  # too short
            "12345678-1234-1234-1234-1234567890123",  # too long
        ]
        
        for invalid_uuid in wrong_length_uuids:
            with self.subTest(uuid=invalid_uuid):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_user_id(invalid_uuid)
                self.assertTrue(
                    "too short" in str(context.exception) or
                    "too long" in str(context.exception)
                )

    def test_validate_user_id_sql_injection_attempts(self):
        """Test rejection of SQL injection attempts in user ID."""
        malicious_uuids = [
            "12345678-1234-1234-1234-123456789012'; DROP TABLE users; --",
            '12345678-1234-1234-1234-123456789012"; DELETE FROM users; --',
            "12345678-1234-1234-1234-123456789012/*comment*/",
            "12345678-1234-1234-1234-123456789012\\",
            "12345678-1234-1234-1234-123456789012\x00",
        ]
        
        for malicious_uuid in malicious_uuids:
            with self.subTest(uuid=malicious_uuid):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_user_id(malicious_uuid)
                self.assertTrue(
                    "suspicious character" in str(context.exception) or
                    "Invalid UUID format" in str(context.exception) or
                    "too long" in str(context.exception)
                )


class TestContainerUrlValidation(unittest.TestCase):
    """Test class for container URL validation security functions."""

    def test_validate_container_url_valid(self):
        """Test validation of valid container URLs."""
        valid_urls = [
            "https://example.blob.core.windows.net/container",
            "https://storage.googleapis.com/bucket/path",
            "http://localhost:8080/container",
            "https://myaccount.blob.core.windows.net/container/folder/file.txt",
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                result = validate_container_url(url)
                self.assertEqual(result, url)

    def test_validate_container_url_invalid_type(self):
        """Test rejection of non-string URL inputs."""
        invalid_inputs = [
            123,
            None,
            [],
            {},
            True,
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(invalid_input)
                self.assertIn("must be a string", str(context.exception))

    def test_validate_container_url_invalid_length(self):
        """Test rejection of overly long or short URLs."""
        # Too long
        long_url = "https://example.com/" + "a" * 2050
        with self.assertRaises(SecurityValidationError) as context:
            validate_container_url(long_url)
        self.assertIn("too long", str(context.exception))
        
        # Too short (some fail length check, some fail format check)
        short_urls = [
            ("http://", "too short"),  # 7 chars - fails length check
            ("https://", "Invalid URL format"),  # 8 chars - passes length but fails format
        ]
        for url, expected_error in short_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertIn(expected_error, str(context.exception))
                
        # URLs that are short but fail format validation first
        format_first_urls = ["a.com"]  # too short AND invalid format
        for url in format_first_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertTrue(
                    "too short" in str(context.exception) or 
                    "Invalid URL format" in str(context.exception)
                )
                
        # Invalid format (not length issues)
        format_invalid_urls = ["ftp://example.com"]  # wrong protocol
        for url in format_invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertIn("Invalid URL format", str(context.exception))

    def test_validate_container_url_invalid_format(self):
        """Test rejection of invalid URL formats."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Not http/https
            "javascript:alert('xss')",
            "file:///etc/passwd",
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertIn("Invalid URL format", str(context.exception))

    def test_validate_container_url_sql_injection_attempts(self):
        """Test rejection of SQL injection attempts in URLs."""
        # URLs that fail format validation first 
        format_fail_urls = [
            "https://example.com'; DROP TABLE users; --",
            'https://example.com"; DELETE FROM users; --',
            "https://example.com\\malicious",
        ]
        
        for url in format_fail_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertTrue(
                    "Invalid URL format" in str(context.exception) or
                    "suspicious character" in str(context.exception)
                )
                
        # URLs that should fail due to null byte (may be caught by format or suspicious char check)
        suspicious_char_urls = [
            "https://example.com\x00",  # null byte
        ]
        
        for url in suspicious_char_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                # Either format validation or suspicious character check should catch this
                self.assertTrue(
                    "suspicious character" in str(context.exception) or
                    "Invalid URL format" in str(context.exception)
                )

    def test_validate_container_url_sql_keywords(self):
        """Test rejection of SQL keywords in URLs."""
        malicious_urls = [
            "https://DROP-TABLE.example.com/container",
            "https://example.com/SELECT-ALL",
            "https://UNION-SELECT.blob.core.windows.net/container",
        ]
        
        for url in malicious_urls:
            with self.subTest(url=url):
                with self.assertRaises(SecurityValidationError) as context:
                    validate_container_url(url)
                self.assertIn("SQL keyword", str(context.exception))


class TestQueryLogging(unittest.TestCase):
    """Test class for secure query logging functions."""

    def test_sanitize_query_log_email(self):
        """Test sanitization of query logs containing emails."""
        query = "SELECT id FROM users WHERE email = %s"
        params = ("user@example.com",)
        
        result = sanitize_query_log(query, params)
        
        self.assertIn("Query:", result)
        self.assertIn("Params:", result)
        self.assertIn("***@***.***", result)
        self.assertNotIn("user@example.com", result)

    def test_sanitize_query_log_uuid(self):
        """Test sanitization of query logs containing UUIDs."""
        query = "UPDATE users SET name = %s WHERE id = %s"
        test_uuid = str(uuid.uuid4())
        params = ("John Doe", test_uuid)
        
        result = sanitize_query_log(query, params)
        
        self.assertIn("***", result)
        self.assertIn("********-****-****-****-************", result)
        self.assertNotIn(test_uuid, result)
        self.assertNotIn("John Doe", result)

    def test_sanitize_query_log_mixed_params(self):
        """Test sanitization of query logs with mixed parameter types."""
        query = "INSERT INTO users (email, id, active) VALUES (%s, %s, %s)"
        test_uuid = str(uuid.uuid4())
        params = ("user@example.com", test_uuid, True)
        
        result = sanitize_query_log(query, params)
        
        # Check that all sensitive data is masked
        self.assertNotIn("user@example.com", result)
        self.assertNotIn(test_uuid, result)
        self.assertIn("***@***.***", result)
        self.assertIn("********-****-****-****-************", result)
        self.assertIn("***", result)  # For the boolean value


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security functions."""

    def test_security_validation_error_inheritance(self):
        """Test that SecurityValidationError is properly defined."""
        error = SecurityValidationError("test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "test error")

    def test_validation_functions_raise_correct_exceptions(self):
        """Test that validation functions raise SecurityValidationError."""
        with self.assertRaises(SecurityValidationError):
            validate_email("invalid')email")
        
        with self.assertRaises(SecurityValidationError):
            validate_user_id("invalid')uuid")
        
        with self.assertRaises(SecurityValidationError):
            validate_container_url("invalid')url")


if __name__ == "__main__":
    unittest.main()