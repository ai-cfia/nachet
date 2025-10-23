"""
Comprehensive test suite for unified blob storage validation.

This test suite validates the unified validation module that ensures
compatibility between Azure Blob Storage and AWS S3.

Tests cover:
- Container/bucket name validation (combined Azure + S3 rules)
- Blob/object key name validation (combined Azure + S3 rules)
- Metadata key and value validation
- Edge cases and boundary conditions
"""

import pytest
from app.blob.validation import (
    validate_container_name,
    validate_blob_name,
    validate_metadata_key,
    validate_metadata_value,
)
from app.blob.exceptions import BlobStorageError, ValidationError


class TestContainerNameValidation:
    """Test cases for container/bucket name validation."""

    # Valid container names
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("abc", "abc"),  # Minimum length
            ("test-container", "test-container"),
            ("my-container-123", "my-container-123"),
            ("a" * 63, "a" * 63),  # Maximum length
            ("test123", "test123"),
            ("123test", "123test"),  # Can start with number
            ("a-b-c-d-e", "a-b-c-d-e"),  # Multiple hyphens (non-consecutive)
            ("TEST-CONTAINER", "test-container"),  # Converts to lowercase
            ("  test-container  ", "test-container"),  # Trims whitespace
        ],
    )
    def test_valid_container_names(self, name, expected):
        """Test that valid container names pass validation."""
        result = validate_container_name(name)
        assert result == expected

    # Invalid container names - length
    @pytest.mark.parametrize(
        "name,error_message",
        [
            ("", "cannot be empty"),
            ("   ", "cannot be empty"),
            ("ab", "at least 3 characters"),  # Too short
            ("a" * 64, "at most 63 characters"),  # Too long
        ],
    )
    def test_invalid_container_names_length(self, name, error_message):
        """Test that container names with invalid length fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        assert error_message in str(exc_info.value).lower()

    # Invalid container names - start/end characters
    @pytest.mark.parametrize(
        "name,error_message",
        [
            ("-test", "must start with a letter or number"),
            ("test-", "must end with a letter or number"),
            ("-test-", "must start with a letter or number"),
        ],
    )
    def test_invalid_container_names_start_end(self, name, error_message):
        """Test that container names with invalid start/end fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        assert error_message in str(exc_info.value).lower()

    # Invalid container names - characters
    @pytest.mark.parametrize(
        "name,error_message",
        [
            ("test_container", "can only contain lowercase"),  # Underscore not allowed
            ("test.container", "can only contain lowercase"),  # Period not allowed
            ("test container", "can only contain lowercase"),  # Space not allowed
            ("test/container", "can only contain lowercase"),  # Slash not allowed
            ("test@container", "can only contain lowercase"),  # Special char
        ],
    )
    def test_invalid_container_names_characters(self, name, error_message):
        """Test that container names with invalid characters fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        assert error_message in str(exc_info.value).lower()

    def test_container_name_with_uppercase_converts_to_lowercase(self):
        """Test that container names with uppercase letters are converted to lowercase."""
        # Uppercase letters are converted to lowercase, so this should pass
        assert validate_container_name("testContainer") == "testcontainer"
        assert validate_container_name("TEST") == "test"

    # Invalid container names - consecutive hyphens
    def test_invalid_container_names_consecutive_hyphens(self):
        """Test that container names with consecutive hyphens fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name("test--container")
        assert "consecutive hyphens" in str(exc_info.value).lower()

    # Invalid container names - IP address format
    # Note: These fail because periods are not allowed, not because they're IP addresses
    @pytest.mark.parametrize(
        "name",
        [
            "192.168.1.1",
            "10.0.0.1",
            "255.255.255.255",
            "1.2.3.4",
        ],
    )
    def test_invalid_container_names_ip_format(self, name):
        """Test that container names formatted as IP addresses fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        # These fail because they contain periods, which are not allowed
        assert "can only contain" in str(exc_info.value).lower()

    # Not IP addresses (should pass or fail for other reasons)
    @pytest.mark.parametrize(
        "name",
        [
            "192.168.1",  # Only 3 parts - not an IP, but too short for container name
            "256.0.0.1",  # Invalid IP - should still fail as periods not allowed
            "1.2.3.abc",  # Not all numbers - should fail as periods not allowed
        ],
    )
    def test_not_ip_addresses(self, name):
        """Test that non-IP formats are handled correctly."""
        with pytest.raises(BlobStorageError):
            # These should fail for other reasons (too short, periods not allowed, etc.)
            validate_container_name(name)

    # Invalid container names - reserved prefixes
    @pytest.mark.parametrize(
        "name",
        [
            "xn--test",  # Fails due to consecutive hyphens
            "sthree-test",
            "amzn-s3-demo-test",
        ],
    )
    def test_invalid_container_names_reserved_prefixes(self, name):
        """Test that container names with reserved prefixes fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        # xn--test fails because of consecutive hyphens, others fail due to reserved prefix
        assert (
            "reserved prefix" in str(exc_info.value).lower()
            or "consecutive hyphens" in str(exc_info.value).lower()
        )

    # Invalid container names - reserved suffixes
    @pytest.mark.parametrize(
        "name",
        [
            "test-s3alias",
            "test--ol-s3",  # Has consecutive hyphens
            "test.mrap",  # Has period
            "test--x-s3",  # Has consecutive hyphens
            "test--table-s3",  # Has consecutive hyphens
        ],
    )
    def test_invalid_container_names_reserved_suffixes(self, name):
        """Test that container names with reserved suffixes fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_container_name(name)
        # Some fail due to consecutive hyphens or periods, others due to reserved suffix
        assert (
            "reserved suffix" in str(exc_info.value).lower()
            or "consecutive hyphens" in str(exc_info.value).lower()
            or "can only contain" in str(exc_info.value).lower()
        )


class TestBlobNameValidation:
    """Test cases for blob/object key name validation."""

    # Valid blob names
    @pytest.mark.parametrize(
        "name",
        [
            "a",  # Minimum length
            "test.txt",
            "folder/file.txt",
            "folder/subfolder/file.txt",
            "my-file_name.jpg",
            "test-123_abc.pdf",
            "a" * 1024,  # Maximum length
            "folder1/folder2/folder3/file.txt",
            "2024/01/15/data.csv",  # Date-based paths
            "user_123/photos/IMG-001.jpg",
        ],
    )
    def test_valid_blob_names(self, name):
        """Test that valid blob names pass validation."""
        result = validate_blob_name(name)
        assert result == name

    # Invalid blob names - empty
    @pytest.mark.parametrize(
        "name",
        [
            "",
            "   ",
        ],
    )
    def test_invalid_blob_names_empty(self, name):
        """Test that empty blob names fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "cannot be empty" in str(exc_info.value).lower()

    # Invalid blob names - whitespace
    def test_invalid_blob_names_whitespace(self):
        """Test that blob names with leading/trailing whitespace fail."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name("  test.txt")
        assert "whitespace" in str(exc_info.value).lower()

        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name("test.txt  ")
        assert "whitespace" in str(exc_info.value).lower()

    # Invalid blob names - length
    def test_invalid_blob_names_too_long(self):
        """Test that blob names exceeding 1024 characters fail validation."""
        name = "a" * 1025
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "1024 characters" in str(exc_info.value)

    # Invalid blob names - control characters
    def test_invalid_blob_names_control_characters(self):
        """Test that blob names with control characters fail validation."""
        # Test various control characters
        for i in range(0x00, 0x20):
            name = f"test{chr(i)}file.txt"
            with pytest.raises(BlobStorageError) as exc_info:
                validate_blob_name(name)
            assert "control characters" in str(exc_info.value).lower()

        # Test DEL character (0x7F)
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(f"test{chr(0x7F)}file.txt")
        assert "control characters" in str(exc_info.value).lower()

    # Invalid blob names - characters to avoid
    @pytest.mark.parametrize(
        "char",
        ["\\", "{", "}", "^", "%", "`", "]", '"', "<", ">", "~", "#", "|"],
    )
    def test_invalid_blob_names_avoid_characters(self, char):
        """Test that blob names with characters to avoid fail validation."""
        name = f"test{char}file.txt"
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "should be avoided" in str(exc_info.value).lower()

    # Invalid blob names - invalid characters
    @pytest.mark.parametrize(
        "char",
        ["@", "&", "$", "=", ";", ":", "+", ",", "?", " "],
    )
    def test_invalid_blob_names_invalid_characters(self, char):
        """Test that blob names with invalid characters fail validation."""
        name = f"test{char}file.txt"
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        # Should fail with invalid characters message
        assert (
            "invalid characters" in str(exc_info.value).lower()
            or "can only contain" in str(exc_info.value).lower()
        )

    def test_invalid_blob_names_tab_character(self):
        """Test that blob names with tab character fail (control character)."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name("test\tfile.txt")
        # Tab is a control character, so it's caught by that check
        assert "control characters" in str(exc_info.value).lower()

    # Invalid blob names - trailing dots/slashes
    @pytest.mark.parametrize(
        "name,trailing_char",
        [
            ("test.txt.", "."),
            ("folder/file/", "/"),
        ],
    )
    def test_invalid_blob_names_trailing(self, name, trailing_char):
        """Test that blob names ending with dots/slashes fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "cannot end with" in str(exc_info.value).lower()

    def test_invalid_blob_names_trailing_backslash(self):
        """Test that blob names with backslash fail (avoid character)."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name("test.txt\\")
        # Backslash is in the avoid chars list, so it's caught by that check
        assert "should be avoided" in str(exc_info.value).lower()

    # Invalid blob names - period-only segments
    @pytest.mark.parametrize(
        "name",
        [
            "folder/./file.txt",
            "folder/../file.txt",
            "./file.txt",
            "../file.txt",
            "folder/./subfolder/file.txt",
            "folder/../subfolder/file.txt",
        ],
    )
    def test_invalid_blob_names_period_segments(self, name):
        """Test that blob names with period-only segments fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "period-only path segments" in str(exc_info.value).lower()

    # Valid names with periods (not standalone)
    @pytest.mark.parametrize(
        "name",
        [
            "folder/.hidden/file.txt",
            "folder/..backup/file.txt",
            ".gitignore",
            "..config",
        ],
    )
    def test_valid_blob_names_with_periods(self, name):
        """Test that blob names with periods (not standalone) pass validation."""
        result = validate_blob_name(name)
        assert result == name

    # Invalid blob names - double slashes
    def test_invalid_blob_names_double_slashes(self):
        """Test that blob names with consecutive slashes fail validation."""
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name("folder//file.txt")
        assert "consecutive forward slashes" in str(exc_info.value).lower()

    # Invalid blob names - too many path segments
    def test_invalid_blob_names_too_many_segments(self):
        """Test that blob names with too many segments fail validation."""
        # Create a name with 255 segments (254 is max)
        segments = ["a"] * 255
        name = "/".join(segments)
        with pytest.raises(BlobStorageError) as exc_info:
            validate_blob_name(name)
        assert "254 path segments" in str(exc_info.value)


class TestMetadataValidation:
    """Test cases for metadata key and value validation."""

    # Valid metadata keys
    @pytest.mark.parametrize(
        "key",
        [
            "key",
            "Key",
            "KEY",
            "_key",
            "key_name",
            "key123",
            "Key_Name_123",
            "_private",
        ],
    )
    def test_valid_metadata_keys(self, key):
        """Test that valid metadata keys pass validation."""
        result = validate_metadata_key(key)
        assert result == key

    # Invalid metadata keys - empty
    def test_invalid_metadata_keys_empty(self):
        """Test that empty metadata keys fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metadata_key("")
        assert "cannot be empty" in str(exc_info.value).lower()

    # Invalid metadata keys - start character
    @pytest.mark.parametrize(
        "key",
        [
            "123key",
            "-key",
            " key",
            ".key",
        ],
    )
    def test_invalid_metadata_keys_start(self, key):
        """Test that metadata keys with invalid start character fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metadata_key(key)
        assert "must start with" in str(exc_info.value).lower()

    # Invalid metadata keys - characters
    @pytest.mark.parametrize(
        "key",
        [
            "key-name",
            "key.name",
            "key name",
            "key@name",
            "key#name",
        ],
    )
    def test_invalid_metadata_keys_characters(self, key):
        """Test that metadata keys with invalid characters fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metadata_key(key)
        assert "can only contain" in str(exc_info.value).lower()

    # Invalid metadata keys - non-ASCII
    def test_invalid_metadata_keys_non_ascii(self):
        """Test that metadata keys with non-ASCII characters fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metadata_key("key_ñame")
        assert "valid ascii" in str(exc_info.value).lower()

    # Valid metadata values
    @pytest.mark.parametrize(
        "value",
        [
            "value",
            "Some Value",
            "123",
            "value-with-hyphen",
            "value_with_underscore",
            "value.with.period",
            "",  # Empty string is valid
        ],
    )
    def test_valid_metadata_values(self, value):
        """Test that valid metadata values pass validation."""
        result = validate_metadata_value(value)
        assert result == value

    # Invalid metadata values - non-ASCII
    def test_invalid_metadata_values_non_ascii(self):
        """Test that metadata values with non-ASCII characters fail."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metadata_value("valué")
        assert "valid ascii" in str(exc_info.value).lower()

    # None value should be handled
    def test_metadata_value_none(self):
        """Test that None metadata values are handled."""
        result = validate_metadata_value(None)
        assert result is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_container_name_exactly_3_chars(self):
        """Test container name with exactly 3 characters."""
        assert validate_container_name("abc") == "abc"

    def test_container_name_exactly_63_chars(self):
        """Test container name with exactly 63 characters."""
        name = "a" * 63
        assert validate_container_name(name) == name

    def test_blob_name_exactly_1_char(self):
        """Test blob name with exactly 1 character."""
        assert validate_blob_name("a") == "a"

    def test_blob_name_exactly_1024_chars(self):
        """Test blob name with exactly 1024 characters."""
        name = "a" * 1024
        assert validate_blob_name(name) == name

    def test_blob_name_exactly_254_segments(self):
        """Test blob name with exactly 254 path segments."""
        # Create a name with 254 segments
        segments = ["a"] * 254
        name = "/".join(segments)
        assert validate_blob_name(name) == name

    def test_container_name_case_insensitive(self):
        """Test that container names are converted to lowercase."""
        assert validate_container_name("ABC") == "abc"
        assert validate_container_name("TeSt") == "test"
        assert validate_container_name("TEST-123") == "test-123"

    def test_container_name_whitespace_trimmed(self):
        """Test that container names have whitespace trimmed."""
        assert validate_container_name("  test  ") == "test"
        assert validate_container_name("\ttest\t") == "test"

    def test_almost_ip_addresses(self):
        """Test names that look like IP addresses but aren't."""
        # These should fail because they contain periods (not allowed)
        with pytest.raises(BlobStorageError):
            validate_container_name("192.168.1")  # Only 3 parts

        with pytest.raises(BlobStorageError):
            validate_container_name("256.0.0.1")  # Out of range

        with pytest.raises(BlobStorageError):
            validate_container_name("1.2.3.abc")  # Not all numbers
