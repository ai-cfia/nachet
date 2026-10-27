import hashlib
import io
import json

import pytest
from PIL import Image

from prelabel import coco_box, prelabel
from prepare_images import main, prepare_images, save_coco


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


def prepare(intake):
    return prepare_images(
        *intake,
        code_revision="test-revision",
        split="train",
        raw_prefix="raw/intake-01/Training",
    )


def test_conversion_preserves_raw_pixels_lineage_and_split(intake):
    source, output = intake
    before = {
        p.relative_to(source).as_posix(): p.read_bytes()
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
        assert "original_path" not in original
        assert original["raw_key"] == f"raw/intake-01/Training/{original['path']}"
        assert original["species"] == original["path"].split("/")[0]
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
        assert image["split"] == "train"
    assert before == {
        p.relative_to(source).as_posix(): p.read_bytes()
        for p in source.rglob("*")
        if p.is_file()
    }
    assert prepare(intake) == coco


def test_identical_pngs_share_bytes_but_keep_both_source_paths(intake):
    source, _ = intake
    copy = source / "Avena fatua/batch-02/tray-c/copy.png"
    copy.parent.mkdir(parents=True)
    copy.write_bytes((source / "Avena fatua/other/c.png").read_bytes())
    result = prepare(intake)
    assert len(result["images"]) == 4
    duplicates = [image for image in result["images"] if len(image["sources"]) == 2]
    assert len(duplicates) == 1
    assert {s["path"] for s in duplicates[0]["sources"]} == {
        "Avena fatua/other/c.png",
        "Avena fatua/batch-02/tray-c/copy.png",
    }


def test_duplicate_png_cannot_have_different_species(intake):
    source, _ = intake
    (source / "Zea mays/copy.png").write_bytes(
        (source / "Avena fatua/other/c.png").read_bytes()
    )
    with pytest.raises(ValueError, match="conflicting species or splits"):
        prepare(intake)


def test_unknown_split_stays_unset_and_s3_is_optional(intake):
    result = prepare_images(*intake, code_revision="test")
    assert all(image["split"] is None for image in result["images"])
    assert all(
        "raw_key" not in source
        for image in result["images"]
        for source in image["sources"]
    )


def test_cli_reads_species_folders_without_an_intake_file(intake, capsys):
    source, output = intake
    main(
        [
            str(source),
            str(output),
            "--code-revision",
            "test-cli",
            "--split",
            "validation",
            "--raw-prefix",
            "raw/intake-01/Validation",
        ]
    )
    result = json.loads((output / "index.coco.json").read_text())
    assert result["info"]["preparation"]["code_revision"] == "test-cli"
    assert all(image["split"] == "validation" for image in result["images"])
    assert all(
        source["raw_key"] == f"raw/intake-01/Validation/{source['path']}"
        for image in result["images"]
        for source in image["sources"]
    )
    assert "Prepared 4 images from 4 sources" in capsys.readouterr().out


def test_hidden_files_are_skipped_and_empty_species_are_retained(intake):
    source, _ = intake
    (source / "Empty species").mkdir()
    for name in [
        ".hidden-root/hidden.png",
        "Avena fatua/.hidden.png",
        "Avena fatua/.hidden/tray.png",
    ]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (2, 2), "blue").save(path)
    (source / "Avena fatua/notes.txt").write_text("metadata, not an image")
    result = prepare(intake)
    assert len(result["images"]) == 4
    assert [category["name"] for category in result["categories"]] == [
        "Avena fatua",
        "Empty species",
        "Zea mays",
    ]


def test_source_root_images_require_a_species_folder(intake):
    source, output = intake
    Image.new("RGB", (2, 2)).save(source / "unlabelled.png")
    with pytest.raises(ValueError, match="species subfolder: .*unlabelled.png"):
        prepare(intake)
    assert not output.exists()


def test_output_cannot_be_inside_the_input_tree(intake):
    source, _ = intake
    with pytest.raises(ValueError, match="outside the source root"):
        prepare_images(source, source / "generated", code_revision="test")
    assert not (source / "generated").exists()


def test_empty_species_tree_is_reported(tmp_path):
    source = tmp_path / "source"
    (source / "Avena fatua").mkdir(parents=True)
    with pytest.raises(ValueError, match="No images found in species subfolders"):
        prepare_images(source, tmp_path / "out", code_revision="test")


@pytest.mark.parametrize(
    "raw_prefix", ["/raw/collection", "raw/../other", "s3://bucket/raw"]
)
def test_raw_prefix_is_an_object_key_under_raw(intake, raw_prefix):
    with pytest.raises(ValueError, match="raw_prefix must start with raw/"):
        prepare_images(*intake, code_revision="test", raw_prefix=raw_prefix)


def test_invalid_split_is_not_recorded(intake):
    with pytest.raises(ValueError, match="Invalid split"):
        prepare_images(*intake, code_revision="test", split="unknown")


def test_corrupt_input_is_named_and_cannot_replace_working_coco(intake):
    source, output = intake
    (source / "Avena fatua/batch-01/tray-a/a.tiff").write_bytes(b"broken TIFF")
    with pytest.raises(OSError, match="Avena fatua/batch-01/tray-a/a.tiff"):
        prepare(intake)
    save_coco(output / "index.json", {"annotations": ["human correction"]})
    with pytest.raises(ValueError, match="Refusing to replace"):
        save_coco(output / "index.json", {"annotations": []})


@pytest.mark.parametrize("mode", ["YCbCr", "LAB"])
def test_png_encoding_error_names_the_source_file(tmp_path, mode):
    source = tmp_path / "source"
    species = source / "Avena fatua"
    species.mkdir(parents=True)
    filename = f"unsupported-{mode}.tiff"
    Image.new(mode, (8, 6)).save(species / filename, format="TIFF")
    with pytest.raises(
        OSError,
        match=rf"Avena fatua/unsupported-{mode}\.tiff: cannot write mode {mode}",
    ):
        prepare_images(source, tmp_path / "prepared", code_revision="test")


@pytest.mark.parametrize("kind", ["file", "species_folder"])
def test_source_symlinks_cannot_escape_the_input_tree(intake, tmp_path, kind):
    source, output = intake
    outside = tmp_path / "outside"
    outside.mkdir()
    Image.new("RGB", (4, 3), "blue").save(outside / "outside.png")
    if kind == "file":
        (source / "Avena fatua/escape.png").symlink_to(outside / "outside.png")
    else:
        (source / "Outside species").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        prepare(intake)
    assert not (output / "index.coco.json").exists()


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
    path = source / "Avena fatua/rgb16.tiff"
    path.parent.mkdir(parents=True)
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
    with pytest.raises(ValueError, match="rgb16.tiff.*lossless conversion policy"):
        prepare_images(source, tmp_path / "prepared", code_revision="test")
    assert not list((tmp_path / "prepared").glob("**/*.png"))
    assert path.read_bytes().endswith(pixels)


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


def test_automatic_layout_shares_categories_and_preserves_mixed_splits(
    automatic_collection,
):
    result = prepare_images(
        *automatic_collection, code_revision="test", raw_prefix="raw/collection"
    )
    assert [c["name"] for c in result["categories"]] == ["A", "B", "C", "D"]
    assert len(result["images"]) == 6
    assert result["annotations"] == []
    for image in result["images"]:
        source = image["sources"][0]
        parent = source["path"].split("/")[0]
        assert (
            image["split"]
            == {"Training": "train", "Validation": "validation", "D": None}[parent]
        )
        assert source["species"] == (
            "D" if parent == "D" else source["path"].split("/")[1]
        )
        assert source["raw_key"] == "raw/collection/" + source["path"]
        assert "original_path" not in source


@pytest.mark.parametrize("layout", ["split", "unsplit", "mixed"])
def test_collection_cli_needs_no_split_mapping(automatic_collection, layout):
    import shutil

    root, output = automatic_collection
    if layout == "split":
        shutil.rmtree(root / "D")
    elif layout == "unsplit":
        shutil.rmtree(root / "Training")
        shutil.rmtree(root / "Validation")
    main(
        [
            str(root),
            str(output),
            "--code-revision",
            "test-cli",
            "--raw-prefix",
            "raw/collection",
        ]
    )
    result = json.loads((output / "index.coco.json").read_text())
    expected = {
        "split": {"train", "validation"},
        "unsplit": {None},
        "mixed": {"train", "validation", None},
    }[layout]
    assert {i["split"] for i in result["images"]} == expected
    assert all(
        c["name"] not in {"Training", "Validation"} for c in result["categories"]
    )


def test_automatic_layout_rejects_an_image_in_training_and_validation(
    automatic_collection,
):
    root, output = automatic_collection
    (root / "Validation/C/seed.tiff").write_bytes(
        (root / "Training/C/seed.tiff").read_bytes()
    )
    with pytest.raises(
        ValueError, match="conflicting species or splits: Validation/C/seed.tiff"
    ):
        main([str(root), str(output), "--code-revision", "test"])
    assert not (output / "index.coco.json").exists()


def test_global_split_cannot_override_discovered_split_folders(automatic_collection):
    with pytest.raises(ValueError, match="--split cannot override"):
        prepare_images(*automatic_collection, code_revision="test", split="train")


def test_automatic_split_folder_names_are_case_insensitive(automatic_collection):
    root, _ = automatic_collection
    (root / "Training").rename(root / "training")
    (root / "Validation").rename(root / "VALIDATION")
    result = prepare_images(*automatic_collection, code_revision="test")
    assert {i["split"] for i in result["images"]} == {"train", "validation", None}
    assert {c["name"] for c in result["categories"]} == {"A", "B", "C", "D"}


def test_automatic_split_folder_cannot_be_an_escaping_symlink(
    automatic_collection, tmp_path
):
    root, _ = automatic_collection
    outside = tmp_path / "outside"
    (root / "Training").rename(outside)
    (root / "Training").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="Split folder escapes"):
        prepare_images(*automatic_collection, code_revision="test")


@pytest.mark.parametrize(
    "names", [("Train", "val", "Test"), ("TRAINING", "vAlIdAtIoN", "TeStInG")]
)
def test_split_folder_aliases_are_recognized(automatic_collection, names):
    root, _ = automatic_collection
    (root / "Training").rename(root / names[0])
    (root / "Validation").rename(root / names[1])
    path = root / names[2] / "A/held-out.tiff"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(path)
    result = prepare_images(*automatic_collection, code_revision="test")
    assert {i["split"] for i in result["images"]} == {
        "train",
        "validation",
        "test",
        None,
    }
    assert [c["name"] for c in result["categories"]] == ["A", "B", "C", "D"]


def test_split_folders_below_a_species_folder_are_rejected(tmp_path):
    root = tmp_path / "parent"
    path = root / "collection/Validation/Avena fatua/seed.tiff"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (8, 6), "red").save(path)
    with pytest.raises(ValueError, match="collection folder, not its parent"):
        prepare_images(root, tmp_path / "prepared", code_revision="test")


def test_species_folders_that_differ_only_in_case_are_rejected(
    automatic_collection,
):
    root, _ = automatic_collection
    (root / "Validation/C").rename(root / "Validation/c")
    with pytest.raises(ValueError, match="differ only in case: 'C', 'c'"):
        prepare_images(*automatic_collection, code_revision="test")


def draft_index(intake):
    coco = prepare(intake)
    coco["images"] = [
        image
        for image in coco["images"]
        if not image["sources"][0]["path"].endswith("d.tiff")
    ]
    return coco


def test_prelabel_first_image_unique_ids_boxes_and_metadata(intake):
    coco = draft_index(intake)
    calls = []

    def predict(image, prompt):
        calls.append((image.size, prompt))
        return [[10.5, 20.25, 30.75, 40.5], [0, 0, 2, 3]]

    coco["images"][0]["prelabel_reason"] = "old warning"
    result = prelabel(coco, intake[1], predict)
    assert all(image["prelabel_reason"] is None for image in result["images"])
    assert len(calls) == 3
    assert [annotation["id"] for annotation in result["annotations"]] == list(range(6))
    assert {annotation["image_id"] for annotation in result["annotations"]} == {
        image["id"] for image in coco["images"]
    }
    assert result["annotations"][0]["bbox"] == [7.5, 17.25, 29.25, 29.25]
    assert result["annotations"][1]["bbox"] == [0, 0, 8, 9]
    by_id = {image["id"]: image for image in result["images"]}
    names = {category["id"]: category["name"] for category in result["categories"]}
    for annotation in result["annotations"]:
        assert (
            names[annotation["category_id"]]
            == by_id[annotation["image_id"]]["sources"][0]["species"]
        )
    for before, after in zip(coco["images"], result["images"]):
        assert before["sources"] == after["sources"]
        assert before["split"] == after["split"]
    assert coco["annotations"] == []


def test_prompt_fallback_and_empty_image_are_retained(intake):
    coco = draft_index(intake)
    calls = []

    def predict(image, prompt):
        calls.append(prompt)
        return []

    result = prelabel(coco, intake[1], predict)
    assert len(calls) == 9
    assert result["annotations"] == []
    assert len(result["images"]) == 3
    assert all(image["prelabel_status"] == "needs_review" for image in result["images"])


def test_prelabel_cannot_replace_existing_labels(intake):
    coco = prepare(intake)
    coco["annotations"] = [{"id": 10}]
    with pytest.raises(ValueError, match="refusing to replace labels"):
        prelabel(coco, intake[1], lambda *args: [])


def test_high_bit_depth_images_remain_for_review_without_stopping_the_batch(intake):
    calls = []
    result = prelabel(
        prepare(intake), intake[1], lambda *args: calls.append(1) or [[1, 1, 3, 3]]
    )
    high_bit = next(
        i for i in result["images"] if i["sources"][0]["path"].endswith("d.tiff")
    )
    assert high_bit["prelabel_status"] == "needs_review"
    assert high_bit["prelabel_reason"] == "high_bit_depth"
    assert high_bit["prelabel_prompt"] is None
    assert len(calls) == 3
    assert high_bit["id"] not in {a["image_id"] for a in result["annotations"]}


@pytest.mark.parametrize(
    "box", [[110, 10, 120, 20], [1, 1, 1, 2], [0, 0, float("nan"), 20]]
)
def test_invalid_boxes_keep_valid_detections_and_mark_the_image_for_review(intake, box):
    coco = draft_index(intake)
    result = prelabel(coco, intake[1], lambda *args: [[10, 10, 30, 30], box])
    assert len(result["annotations"]) == len(coco["images"])
    assert all(i["prelabel_status"] == "needs_review" for i in result["images"])
    assert all(i["prelabel_reason"] == "invalid_boxes" for i in result["images"])


@pytest.mark.parametrize(
    "box, expected",
    [
        ([-0.4, 10, 50, 60], [0, 7, 56, 59]),
        ([10, 10, 100.3, 60], [7, 7, 93, 59]),
        ([0, 0, 101, 80], [0, 0, 100, 80]),
    ],
)
def test_edge_predictions_are_clipped(box, expected):
    assert coco_box(box, 100, 80, 3) == expected


def test_nested_drafts_retain_the_notebook_warning(intake):
    coco = draft_index(intake)
    result = prelabel(
        coco, intake[1], lambda image, prompt: [[0, 0, 50, 60], [10, 10, 30, 30]]
    )
    assert all(image["prelabel_status"] == "draft" for image in result["images"])
    assert all(image["prelabel_reason"] == "nested_boxes" for image in result["images"])
    assert len(result["annotations"]) == 6


def test_prelabel_cli_records_run_options_once(intake, tmp_path, monkeypatch):
    import json

    import prelabel as command

    source = tmp_path / "index.json"
    save_coco(source, draft_index(intake))
    output = tmp_path / "draft.json"
    monkeypatch.setattr(
        command, "Sam3Predictor", lambda *args: lambda image, prompt: []
    )
    command.main(
        [
            str(source),
            str(intake[1]),
            str(output),
            "--model-path",
            "/models/sam3",
            "--model-revision",
            "test-weights",
            "--device",
            "cpu",
            "--padding",
            "4",
        ]
    )
    result = json.loads(output.read_text())
    assert result["info"]["prelabel"] == {
        "model_path": "/models/sam3",
        "model_revision": "test-weights",
        "padding": 4,
        "device": "cpu",
        "precision": "fp32",
    }
    assert len(result["images"]) == 3


def test_automatic_collection_keeps_labels_and_splits_through_prelabel(
    automatic_collection,
):
    root, output = automatic_collection
    index = prepare_images(
        root, output, code_revision="test", raw_prefix="raw/collection"
    )
    draft = prelabel(index, output, lambda *args: [[1, 1, 3, 3]])
    images = {i["id"]: i for i in draft["images"]}
    classes = {c["id"]: c["name"] for c in draft["categories"]}
    c_splits = set()
    for box in draft["annotations"]:
        image = images[box["image_id"]]
        source = image["sources"][0]
        assert classes[box["category_id"]] == source["species"]
        assert source["raw_key"] == "raw/collection/" + source["path"]
        if source["species"] == "C":
            assert box["category_id"] == 3
            c_splits.add(image["split"])
    assert c_splits == {"train", "validation"}
    assert len(draft["annotations"]) == 6
    assert any(i["split"] is None for i in draft["images"])
