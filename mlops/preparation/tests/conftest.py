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


@pytest.fixture(
    params=[
        pytest.param(
            (
                [
                    "Amaranthus albus/Tray_A/ColorChecker - Jan. 09, 2026.tiff",
                    "Amaranthus palmeri/AmPa-01; Date_ 20260617/Tray_A/ColorChecker - Jan. 09, 2026.tiff",
                ],
                None,
            ),
            id="species",
        ),
        pytest.param(
            (
                [
                    "Training/Amaranthus palmeri/ColorChecker.tiff",
                    "Validation/Amaranthus palmeri/ColorChecker.tiff",
                ],
                "train",
            ),
            id="split",
        ),
        pytest.param(
            (
                [
                    "Abutilon theophrasti/ColorChecker.tiff",
                    "Training/Zea mays/ColorChecker.tiff",
                ],
                None,
            ),
            id="mixed",
        ),
    ]
)
def conflicting_collection(request, tmp_path):
    relatives, first_split = request.param
    root = tmp_path / "conflicting"
    first = root / relatives[0]
    first.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), "gray").save(first)
    for relative in relatives[1:]:
        path = root / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(first.read_bytes())
    return root, relatives, first_split
