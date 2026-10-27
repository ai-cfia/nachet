import pytest
from PIL import Image

from prepare_images import prepare_images


@pytest.fixture
def intake(tmp_path):
    source = tmp_path / "source"
    for name, mode, color in [
        ("Avena fatua/batch-01/tray-a/a.tiff", "RGB", "red"),
        ("Zea mays/batch-01/tray-b/b.jpg", "RGB", "green"),
        ("Avena fatua/other/c.png", "L", 127),
        ("Avena fatua/other/d.tiff", "I;16", 1000),
    ]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new(mode, (100, 80), color).save(path)
    return source, tmp_path / "prepared"


@pytest.fixture
def prepare(intake):
    def run():
        return prepare_images(
            *intake,
            code_revision="test-revision",
            split="train",
            raw_prefix="raw/intake-01/Training",
        )

    return run


@pytest.fixture
def automatic_collection(tmp_path):
    root = tmp_path / "collection"
    for index, relative in enumerate(
        [
            "Training/A/seed.tiff",
            "Training/B/seed.tiff",
            "Training/C/seed.tiff",
            "Validation/A/seed.tiff",
            "Validation/C/seed.tiff",
            "D/tray/seed.tiff",
        ]
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 6), (index * 30, 10, 20)).save(path)
    return root, tmp_path / "prepared"
