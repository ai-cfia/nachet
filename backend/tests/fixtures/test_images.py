"""Test image fixtures for generating test images."""

from PIL import Image
import io


def get_test_image_bytes(
    filename: str = "test.png", width: int = 100, height: int = 100, color: str = "red"
) -> bytes:
    """
    Generate a test image as bytes.

    Args:
        filename: Filename to use (determines format from extension)
        width: Width of the image in pixels
        height: Height of the image in pixels
        color: Color name or RGB tuple for the image

    Returns:
        bytes: PNG image data as bytes
    """
    # Create a simple test image
    img = Image.new("RGB", (width, height), color=color)

    # Determine format from filename extension
    ext = filename.split(".")[-1].upper()
    if ext == "JPG":
        ext = "JPEG"

    # Save to bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format=ext if ext in ["PNG", "JPEG"] else "PNG")

    return buffer.getvalue()


def get_test_seed_image() -> bytes:
    """Generate a test seed image (100x100 red square)."""
    return get_test_image_bytes("test_seed.png", width=100, height=100, color="red")


def get_malware_test_image() -> bytes:
    """Generate a test image that simulates malware detection (100x100 black square)."""
    return get_test_image_bytes("malware.png", width=100, height=100, color="black")


def get_large_test_image() -> bytes:
    """Generate a larger test image (500x500 blue square) for testing larger files."""
    return get_test_image_bytes("large_test.png", width=500, height=500, color="blue")
