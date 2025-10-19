"""
Unified validation module for blob storage operations.

This module provides validation functions that are compatible with both
Azure Blob Storage and AWS S3 (including S3-compatible systems like Apache Ozone).

The validation rules follow the most conservative approach - where Azure and S3
differ, we use the stricter rule to ensure compatibility across both platforms.
"""

from .exceptions import BlobStorageError, ValidationError


# Reserved S3 prefixes that cannot be used
RESERVED_PREFIXES = ["xn--", "sthree-", "amzn-s3-demo-"]

# Reserved S3 suffixes that cannot be used
RESERVED_SUFFIXES = ["-s3alias", "--ol-s3", ".mrap", "--x-s3", "--table-s3"]

# Control characters that are not allowed (0x00-0x1F, 0x7F)
CONTROL_CHARS = set(chr(i) for i in range(0x00, 0x20)) | {chr(0x7F)}

# Characters to avoid in blob names (per S3 recommendations)
AVOID_CHARS = set('\\{}^%`]"<>~#|')


def validate_container_name(name: str) -> str:
    """
    Validate container/bucket name according to combined Azure and S3 rules.

    This function enforces the most conservative rules from both platforms:

    Combined Rules:
    - Length: 3-63 characters
    - Characters: Only lowercase letters (a-z), numbers (0-9), and hyphens (-)
    - Must start and end with a letter or number
    - No consecutive hyphens
    - Cannot be formatted as an IP address (e.g., 192.168.5.4)
    - Cannot use reserved S3 prefixes: xn--, sthree-, amzn-s3-demo-
    - Cannot use reserved S3 suffixes: -s3alias, --ol-s3, .mrap, --x-s3, --table-s3
    - No periods (excluded for compatibility - Azure allows, S3 allows but not recommended)

    Args:
        name: Container/bucket name to validate

    Returns:
        Validated container name (converted to lowercase)

    Raises:
        BlobStorageError: If the name violates any validation rule
    """
    if not name or not name.strip():
        raise BlobStorageError("Container name cannot be empty")

    # Convert to lowercase and strip whitespace
    name = name.strip().lower()

    # Check length (3-63 characters)
    if len(name) < 3:
        raise BlobStorageError(
            f"Container name must be at least 3 characters long (got {len(name)})"
        )

    if len(name) > 63:
        raise BlobStorageError(
            f"Container name must be at most 63 characters long (got {len(name)})"
        )

    # Check start and end characters (must be letter or number)
    if not (name[0].isalpha() or name[0].isdigit()):
        raise BlobStorageError(
            f"Container name must start with a letter or number (starts with '{name[0]}')"
        )

    if not (name[-1].isalpha() or name[-1].isdigit()):
        raise BlobStorageError(
            f"Container name must end with a letter or number (ends with '{name[-1]}')"
        )

    # Check for valid characters (only lowercase letters, numbers, and hyphens after converting to lowercase)
    # Note: name is already lowercase at this point
    if not all(c.islower() or c.isdigit() or c == '-' for c in name):
        invalid_chars = set(c for c in name if not (c.islower() or c.isdigit() or c == '-'))
        raise BlobStorageError(
            f"Container name can only contain lowercase letters, numbers, and hyphens. "
            f"Invalid characters: {', '.join(repr(c) for c in sorted(invalid_chars))}"
        )

    # Check for consecutive hyphens (must happen after character validation)
    if '--' in name:
        raise BlobStorageError(
            "Container name cannot contain consecutive hyphens (--)"
        )

    # Check if formatted as IP address (must happen after converting to lowercase)
    if _is_ip_address_format(name):
        raise BlobStorageError(
            f"Container name cannot be formatted as an IP address (got '{name}')"
        )

    # Check for reserved prefixes (must happen after converting to lowercase)
    for prefix in RESERVED_PREFIXES:
        if name.startswith(prefix):
            raise BlobStorageError(
                f"Container name cannot start with reserved prefix '{prefix}'"
            )

    # Check for reserved suffixes (must happen after converting to lowercase)
    for suffix in RESERVED_SUFFIXES:
        if name.endswith(suffix):
            raise BlobStorageError(
                f"Container name cannot end with reserved suffix '{suffix}'"
            )

    return name


def validate_blob_name(name: str) -> str:
    """
    Validate blob/object key name according to combined Azure and S3 rules.

    This function enforces conservative rules for compatibility across platforms:

    Combined Rules:
    - Length: 1-1024 characters
    - No control characters (0x00-0x1F, 0x7F)
    - No leading or trailing whitespace
    - Avoid period-only path segments (., ..)
    - No trailing dots, slashes, or backslashes
    - Characters: Alphanumeric, hyphen, underscore, period, forward slash
    - Path segments: Limited to prevent deep nesting issues

    Args:
        name: Blob/object key name to validate

    Returns:
        Validated blob name (trimmed of whitespace)

    Raises:
        BlobStorageError: If the name violates any validation rule
    """
    if not name or not name.strip():
        raise BlobStorageError("Blob name cannot be empty")

    # Trim whitespace
    original_name = name
    name = name.strip()

    if name != original_name:
        raise BlobStorageError(
            "Blob name cannot have leading or trailing whitespace"
        )

    # Check length (1-1024 characters)
    if len(name) > 1024:
        raise BlobStorageError(
            f"Blob name must be at most 1024 characters long (got {len(name)})"
        )

    # Check for control characters (check first as they're most restrictive)
    control_chars_found = set()
    for char in name:
        if char in CONTROL_CHARS:
            control_chars_found.add(char)

    if control_chars_found:
        raise BlobStorageError(
            f"Blob name cannot contain control characters (0x00-0x1F, 0x7F). "
            f"Found: {', '.join(repr(c) for c in sorted(control_chars_found))}"
        )

    # Check for characters to avoid (S3 recommendations + Azure restrictions)
    # This includes backslash which is also in avoid chars
    avoid_chars_found = set()
    for char in name:
        if char in AVOID_CHARS:
            avoid_chars_found.add(char)

    if avoid_chars_found:
        raise BlobStorageError(
            f"Blob name contains characters that should be avoided for compatibility: "
            f"{', '.join(repr(c) for c in sorted(avoid_chars_found))}"
        )

    # Check for allowed characters (conservative approach)
    # Allow: alphanumeric, hyphen, underscore, period, forward slash
    if not all(c.isalnum() or c in '-_/.' for c in name):
        invalid_chars = set(c for c in name if not (c.isalnum() or c in '-_/.'))
        raise BlobStorageError(
            f"Blob name can only contain letters, numbers, hyphens, underscores, "
            f"periods, and forward slashes. "
            f"Invalid characters: {', '.join(repr(c) for c in sorted(invalid_chars))}"
        )

    # Check for trailing dots or slashes (backslash already caught above)
    if name.endswith(('.', '/')):
        raise BlobStorageError(
            f"Blob name cannot end with a dot (.) or forward slash (/). "
            f"Name ends with: '{name[-1]}'"
        )

    # Check for period-only path segments
    if _has_period_only_segments(name):
        raise BlobStorageError(
            "Blob name cannot contain period-only path segments (. or ..)"
        )

    # Check path segment count (Azure flat storage limit: 254 segments)
    segments = name.split('/')
    if len(segments) > 254:
        raise BlobStorageError(
            f"Blob name cannot have more than 254 path segments (got {len(segments)})"
        )

    # Check for double slashes (empty path segments)
    if '//' in name:
        raise BlobStorageError(
            "Blob name cannot contain consecutive forward slashes (//)"
        )

    return name


def _is_ip_address_format(name: str) -> bool:
    """
    Check if a name is formatted as an IP address.

    Args:
        name: Name to check

    Returns:
        True if the name looks like an IP address (e.g., 192.168.5.4)
    """
    parts = name.split('.')

    # Must have exactly 4 parts
    if len(parts) != 4:
        return False

    # Each part must be a number between 0 and 255
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
            # Check for leading zeros (e.g., 192.168.01.1 is not valid)
            if len(part) > 1 and part[0] == '0':
                return False
        return True
    except ValueError:
        return False


def _has_period_only_segments(name: str) -> bool:
    """
    Check if a name contains period-only path segments (. or ..).

    These are problematic because they can be interpreted as relative path
    references by various systems.

    Args:
        name: Blob name to check

    Returns:
        True if the name contains . or .. as standalone path segments
    """
    # Split by forward slash to get path segments
    segments = name.split('/')

    for segment in segments:
        # Check for standalone period segments
        if segment == '.' or segment == '..':
            return True

    return False


def validate_metadata_key(key: str) -> str:
    """
    Validate metadata key name.

    Metadata keys must:
    - Start with a letter or underscore
    - Contain only letters, numbers, or underscores
    - Be valid ASCII

    Args:
        key: Metadata key to validate

    Returns:
        Validated key

    Raises:
        ValidationError: If the key is invalid
    """
    if not key:
        raise ValidationError("metadata_key", key, "Metadata key cannot be empty")

    # Must start with letter or underscore
    if not (key[0].isalpha() or key[0] == '_'):
        raise ValidationError(
            "metadata_key",
            key,
            "Metadata key must start with a letter or underscore"
        )

    # Must contain only letters, numbers, or underscores
    if not all(c.isalnum() or c == '_' for c in key):
        raise ValidationError(
            "metadata_key",
            key,
            "Metadata key can only contain letters, numbers, or underscores"
        )

    # Must be valid ASCII
    try:
        key.encode('ascii')
    except UnicodeEncodeError:
        raise ValidationError(
            "metadata_key",
            key,
            "Metadata key must be valid ASCII"
        )

    return key


def validate_metadata_value(value: str) -> str:
    """
    Validate metadata value.

    Metadata values must be valid ASCII.

    Args:
        value: Metadata value to validate

    Returns:
        Validated value

    Raises:
        ValidationError: If the value is invalid
    """
    if value is None:
        return value

    # Must be valid ASCII
    try:
        value.encode('ascii')
    except UnicodeEncodeError:
        raise ValidationError(
            "metadata_value",
            value,
            "Metadata value must be valid ASCII"
        )

    return value
