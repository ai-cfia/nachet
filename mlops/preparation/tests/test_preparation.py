import csv
import hashlib
import io

import pytest
from PIL import Image

from prepare_images import prepare_images, save_coco


@pytest.fixture
def intake(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    rows = []
    for index, (name, mode, color, species, split) in enumerate(
        [
            ("batch/tray/a.tiff", "RGB", "red", "Avena fatua", "train"),
            ("batch/tray/b.jpg", "RGB", "green", "Zea mays", "validation"),
            ("other/c.png", "L", 127, "Avena fatua", "train"),
            ("other/d.tiff", "I;16", 1000, "Avena fatua", "train"),
        ]
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new(mode, (100, 80), color).save(path)
        rows.append(
            {
                "path": name,
                "species": species,
                "split": split,
                "batch": "batch",
                "tray": "tray",
                "specimen_group": f"seed-{index}",
            }
        )
    manifest = tmp_path / "intake.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return source, manifest, tmp_path / "prepared"


def prepare(intake):
    return prepare_images(*intake, code_revision="test-revision")


def test_conversion_preserves_raw_pixels_lineage_and_split(intake):
    source, _, output = intake
    before = {
        str(p.relative_to(source)): p.read_bytes()
        for p in source.rglob("*")
        if p.is_file()
    }
    coco = prepare(intake)
    assert len(coco["images"]) == 4
    assert coco["annotations"] == []
    assert [item["name"] for item in coco["categories"]] == ["Avena fatua", "Zea mays"]
    for image in coco["images"]:
        data = (output / image["file_name"]).read_bytes()
        assert (
            image["file_name"]
            == f"png/detection/{hashlib.sha256(data).hexdigest()}.png"
        )
        original = image["sources"][0]
        assert original["batch"] == "batch"
        assert (
            original["raw_sha256"]
            == hashlib.sha256(before[original["path"]]).hexdigest()
        )
        assert (
            original["legacy_md5"]
            == hashlib.md5(before[original["path"]], usedforsecurity=False).hexdigest()
        )
        with (
            Image.open(io.BytesIO(data)) as png,
            Image.open(source / original["path"]) as raw,
        ):
            assert png.size == raw.size == (100, 80)
            assert list(png.get_flattened_data()) == list(raw.get_flattened_data())
        if original["path"].endswith("c.png"):
            assert data == before[original["path"]]
        assert image["split"] == (
            "validation" if original["species"] == "Zea mays" else "train"
        )
    assert before == {
        str(p.relative_to(source)): p.read_bytes()
        for p in source.rglob("*")
        if p.is_file()
    }
    assert prepare(intake) == coco


def test_identical_pngs_share_bytes_but_keep_both_sources(intake):
    source, manifest, _ = intake
    (source / "other/copy.png").write_bytes((source / "other/c.png").read_bytes())
    with manifest.open("a") as stream:
        stream.write("other/copy.png,Avena fatua,train,batch,second-tray,seed-copy\n")
    result = prepare(intake)
    assert len(result["images"]) == 4
    duplicates = [image for image in result["images"] if len(image["sources"]) == 2]
    assert len(duplicates) == 1
    assert {s["tray"] for s in duplicates[0]["sources"]} == {"tray", "second-tray"}


@pytest.mark.parametrize(
    "species,split", [("Zea mays", "train"), ("Avena fatua", "test")]
)
def test_duplicate_png_cannot_leak_across_species_or_splits(intake, species, split):
    source, manifest, _ = intake
    (source / "copy.png").write_bytes((source / "other/c.png").read_bytes())
    with manifest.open("a") as stream:
        stream.write(f"copy.png,{species},{split},batch,tray,seed-copy\n")
    with pytest.raises(ValueError, match="conflicting species or splits"):
        prepare(intake)


def test_corrupt_input_is_named_and_cannot_replace_working_coco(intake):
    source, _, output = intake
    (source / "batch/tray/a.tiff").write_bytes(b"broken TIFF")
    with pytest.raises(OSError, match="batch/tray/a.tiff"):
        prepare(intake)
    save_coco(output / "index.json", {"annotations": ["human correction"]})
    with pytest.raises(ValueError, match="Refusing to replace"):
        save_coco(output / "index.json", {"annotations": []})


def test_known_specimen_group_cannot_cross_splits(intake):
    _, manifest, _ = intake
    manifest.write_text(manifest.read_text().replace("seed-1", "seed-0"))
    with pytest.raises(ValueError, match="Specimen group"):
        prepare(intake)


@pytest.mark.parametrize("absolute", [False, True])
def test_source_paths_cannot_escape_the_intake_root(intake, tmp_path, absolute):
    source, manifest, _ = intake
    outside = tmp_path / "outside.tiff"
    outside.write_bytes((source / "batch/tray/a.tiff").read_bytes())
    bad_path = str(outside) if absolute else "../outside.tiff"
    manifest.write_text(manifest.read_text().replace("batch/tray/a.tiff", bad_path))
    with pytest.raises(ValueError, match="escapes"):
        prepare(intake)


def test_interrupted_output_publication_can_be_retried(tmp_path, monkeypatch):
    import prepare_images as module

    output = tmp_path / "index.json"

    def fail_link(*args):
        raise OSError("synthetic interrupted publication")

    with monkeypatch.context() as patch:
        patch.setattr(module.os, "link", fail_link)
        with pytest.raises(OSError, match="interrupted"):
            save_coco(output, {"images": []})
    assert not output.exists()
    save_coco(output, {"images": []})
    assert output.read_text().strip() == '{\n  "images": []\n}'


def test_high_bit_colour_tiff_is_rejected_before_writing_png(tmp_path):
    import struct

    source = tmp_path / "source"
    source.mkdir()
    path = source / "rgb16.tiff"
    pixels = struct.pack("<HHH", 40000, 1000, 65535) * 4
    entries = [
        (256, 3, 1, 2),
        (257, 3, 1, 2),
        (258, 3, 3, 122),
        (259, 3, 1, 1),
        (262, 3, 1, 2),
        (273, 4, 1, 128),
        (277, 3, 1, 3),
        (278, 3, 1, 2),
        (279, 4, 1, len(pixels)),
    ]
    data = bytearray(b"II*\x00" + struct.pack("<IH", 8, len(entries)))
    for tag, kind, count, value in entries:
        data += struct.pack("<HHI", tag, kind, count)
        data += (
            struct.pack("<HH", value, 0)
            if kind == 3 and count == 1
            else struct.pack("<I", value)
        )
    path.write_bytes(data + b"\0\0\0\0" + struct.pack("<HHH", 16, 16, 16) + pixels)
    manifest = tmp_path / "intake.csv"
    manifest.write_text("path,species\nrgb16.tiff,Avena fatua\n")
    with pytest.raises(ValueError, match="rgb16.tiff.*lossless conversion policy"):
        prepare_images(source, manifest, tmp_path / "prepared", code_revision="test")
    assert not list((tmp_path / "prepared").glob("**/*.png"))
    assert path.read_bytes().endswith(pixels)
