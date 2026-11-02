import math
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COMPRESSION_LEVEL = 6


def crop_recipe() -> dict[str, Any]:
    return {
        "code_revision": "nachet-coco-crop-v2",
        "opencv_version": cv2.__version__,  # adjusted from pillow to opencv
        "coordinates": "floor-left-top-ceil-right-bottom",
        "mode": "RGB",
        "format": "PNG",
        "compress_level": PNG_COMPRESSION_LEVEL,
    }


def pixel_box(bbox: list[float]) -> tuple[int, int, int, int]:
    x, y, width, height = bbox
    return math.floor(x), math.floor(y), math.ceil(x + width), math.ceil(y + height)


def crop_image(
    image: NDArray[np.uint8], bbox: list[float]
) -> tuple[tuple[int, int, int, int], bytes]:
    box = pixel_box(bbox)
    return box, render_crop(image, box)


def decode_png(data: bytes, expected_size: tuple[int, int]) -> NDArray[np.uint8]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Image is not a PNG")

    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode PNG image")

    expected_width, expected_height = expected_size
    if image.shape[1::-1] != (expected_width, expected_height):
        raise ValueError("PNG dimensions do not match COCO")
    return image


def render_crop(image: NDArray[np.uint8], box: tuple[int, int, int, int]) -> bytes:
    left, top, right, bottom = box
    cropped = image[top:bottom, left:right]
    if cropped.size == 0:
        raise ValueError("Crop box produces an empty image")
    success, encoded = cv2.imencode(
        ".png",
        cropped,
        [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_LEVEL],
    )
    if not success:
        raise ValueError("OpenCV failed to encode crop as PNG")
    return encoded.tobytes()
