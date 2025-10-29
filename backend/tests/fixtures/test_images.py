"""Test image fixtures for generating test images."""

from PIL import Image
import io
import os


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
    """
    Load real seed image (638x559) from test fixtures.

    Returns actual seed image that meets minimum dimension requirements (384x384).
    Falls back to generated image if file not found.
    """
    try:
        # Try to load real seed image from fixtures
        img_path = os.path.join(os.path.dirname(__file__), "..", "img", "1310_1.png")
        with open(img_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to generated image with valid dimensions
        return get_test_image_bytes("test_seed.png", width=638, height=559, color="red")


def get_malware_test_image() -> bytes:
    """
    Generate a test image that simulates malware detection.

    Returns 400x400 image that meets minimum dimension requirements.
    """
    return get_test_image_bytes("malware.png", width=400, height=400, color="black")


def get_large_test_image() -> bytes:
    """Generate a larger test image (500x500 blue square) for testing larger files."""
    return get_test_image_bytes("large_test.png", width=500, height=500, color="blue")


def get_minimum_size_image() -> bytes:
    """
    Load minimum size seed image (384x384) from test fixtures.

    Returns actual seed image at minimum dimension requirements.
    Falls back to generated image if file not found.
    """
    try:
        # Try to load minimum size seed image from fixtures
        img_path = os.path.join(
            os.path.dirname(__file__), "..", "img", "minimum_384.png"
        )
        with open(img_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to generated image with minimum valid dimensions
        return get_test_image_bytes("minimum.png", width=384, height=384, color="green")
