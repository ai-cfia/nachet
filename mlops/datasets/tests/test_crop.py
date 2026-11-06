from io import BytesIO

import pytest
from PIL import Image

from utility.crop import crop_image, crop_recipe, decode_png, pixel_box


def test_render_crop_returns_rgb_png_with_outward_rounded_box():
    source = Image.new("RGB", (12, 10), (12, 34, 56))
    encoded_source = BytesIO()
    source.save(encoded_source, format="PNG")

    box = pixel_box([1.25, 2.5, 4.5, 3.0])
    decoded = decode_png(encoded_source.getvalue(), (12, 10))
    actual_box, crop_bytes = crop_image(decoded, [1.25, 2.5, 4.5, 3.0])
    assert actual_box == box

    with Image.open(BytesIO(crop_bytes)) as crop:
        assert crop.mode == "RGB"
        assert crop.size == (5, 4)
        assert crop.getpixel((0, 0)) == (12, 34, 56)


@pytest.mark.parametrize(
    ("data", "expected_size"),
    [(b"not a PNG", (12, 10)), (b"\x89PNG\r\n\x1a\n", (12, 10))],
)
def test_decode_png_rejects_invalid_data(data, expected_size):
    with pytest.raises(ValueError):
        decode_png(data, expected_size)


def test_crop_recipe_records_opencv_algorithm_version():
    recipe = crop_recipe()

    assert recipe["code_revision"] == "nachet-coco-crop-v2"
    assert recipe["opencv_version"]
    assert recipe["coordinates"] == "floor-left-top-ceil-right-bottom"
