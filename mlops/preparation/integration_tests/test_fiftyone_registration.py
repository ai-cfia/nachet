"""SDK checks against an explicitly selected disposable MongoDB instance."""

import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from prelabel import prelabel
from prepare_images import main as convert_images
from prepare_images import save_coco
from register_fiftyone import register_fiftyone


def test_registration_keeps_fields_and_refuses_to_replace_review_work(
    tmp_path, fiftyone, review_name, draft_coco
):
    # The worker imports JSON without access to the server's image mount.
    server_root = tmp_path / "server-only-mount"
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, draft_coco)
    command = [
        sys.executable,
        str(Path(__file__).parents[1] / "register_fiftyone.py"),
        review_name,
        str(labels),
        "--server-media-root",
        str(server_root),
    ]
    initial = subprocess.run(command, check=False, capture_output=True, text=True)
    assert initial.returncode == 0, initial.stderr
    dataset = fiftyone.load_dataset(review_name)
    assert dataset.persistent
    assert len(dataset) == 3
    assert isinstance(dataset.get_field("image_sha256"), fiftyone.StringField)
    samples = {sample.coco_id: sample for sample in dataset}
    for record in draft_coco["images"]:
        sample = samples[record["id"]]
        assert sample.filepath == str(server_root / record["file_name"])
        assert not Path(sample.filepath).exists()
        assert (sample.metadata.width, sample.metadata.height) == (100, 80)
        assert sample["sources"] == record["sources"]
        assert sample["source_species"] == record["sources"][0]["species"]
        assert sample["split"] == record["split"]
        assert sample["object_key"] == record["file_name"]
        assert sample["image_sha256"] == record["image_sha256"]
        assert sample["prelabel_prompt"] == record["prelabel_prompt"]
        assert sample["prelabel_status"] == record["prelabel_status"]
        assert sample["prelabel_reason"] == record["prelabel_reason"]
    first = samples[11]
    detection = first.draft_boxes.detections[0]
    assert detection.label == "Avena fatua"
    assert detection.bounding_box == pytest.approx([0.1025, 0.25625, 0.4075, 0.378125])
    assert not samples[25].draft_boxes or not samples[25].draft_boxes.detections

    detection.label = "Zea mays"
    detection.bounding_box = [0.1, 0.2, 0.3, 0.4]
    first.save()
    retry = subprocess.run(command, check=False, capture_output=True, text=True)
    assert retry.returncode != 0
    assert "already exists" in retry.stderr
    reviewed = fiftyone.load_dataset(review_name)[first.id]
    assert reviewed.draft_boxes.detections[0].label == "Zea mays"
    assert reviewed.draft_boxes.detections[0].bounding_box == [0.1, 0.2, 0.3, 0.4]
    assert reviewed["source_species"] == "Avena fatua"
    assert reviewed["image_sha256"] == first["image_sha256"]
    assert dataset.info["preparation"] == draft_coco["info"]["preparation"]
    assert dataset.info["prelabel"] == draft_coco["info"]["prelabel"]


@pytest.mark.parametrize("sources", [[], [{"path": "raw/a.tiff"}]])
def test_first_sample_without_split_or_prelabels_keeps_nullable_fields(
    tmp_path, fiftyone, review_name, draft_coco, sources
):
    record = draft_coco["images"][0]
    record["split"] = None
    record["sources"] = sources
    draft_coco["annotations"] = []
    for image in draft_coco["images"]:
        for field in ["prelabel_status", "prelabel_reason", "prelabel_prompt"]:
            image.pop(field)
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, draft_coco)
    register_fiftyone(review_name, labels, str(tmp_path))
    dataset = fiftyone.load_dataset(review_name)
    sample = dataset.match({"coco_id": record["id"]}).first()
    assert sample["split"] is None
    assert sample["source_species"] is None
    assert sample["prelabel_status"] == "unannotated"
    assert sample["prelabel_reason"] is None
    assert sample["prelabel_prompt"] is None
    assert dataset.match({"coco_id": 18}).first()["source_species"] == "Zea mays"


def test_caught_import_failure_deletes_the_temporary_dataset(
    tmp_path, fiftyone, review_name, draft_coco, monkeypatch
):
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, draft_coco)
    original_import = fiftyone.Dataset.add_dir
    existing_names = set(fiftyone.list_datasets())

    def interrupted_import(dataset, *args, **kwargs):
        original_import(dataset, *args, **kwargs)
        raise RuntimeError("synthetic failure after sample insertion")

    with monkeypatch.context() as scoped:
        scoped.setattr(fiftyone.Dataset, "add_dir", interrupted_import)
        with pytest.raises(RuntimeError, match="after sample insertion"):
            register_fiftyone(review_name, labels, str(tmp_path))
    assert set(fiftyone.list_datasets()) == existing_names
    register_fiftyone(review_name, labels, str(tmp_path))
    assert len(fiftyone.load_dataset(review_name)) == 3


def test_killed_import_leaves_a_temporary_dataset_and_allows_retry(
    tmp_path, fiftyone, review_name, draft_coco
):
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, draft_coco)
    marker = tmp_path / "staging-name.txt"
    staging_name = None
    try:
        killed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("kill_during_import.py")),
                review_name,
                str(labels),
                str(tmp_path),
                str(marker),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
        )
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        staging_name = marker.read_text()
        assert fiftyone.dataset_exists(staging_name)
        assert len(fiftyone.load_dataset(staging_name)) == 3
        assert not fiftyone.dataset_exists(review_name)
        register_fiftyone(review_name, labels, str(tmp_path))
        assert len(fiftyone.load_dataset(review_name)) == 3
    finally:
        if staging_name and fiftyone.dataset_exists(staging_name):
            fiftyone.delete_dataset(staging_name)


def test_preparation_output_registers_with_boxes_sources_and_splits(
    tmp_path, fiftyone, review_name
):
    from fiftyone import ViewField as F

    collection = tmp_path / "Collection"
    prepared = tmp_path / "prepared"
    inputs = [
        ("Training/Avena fatua/batch/tray/seed.tiff", (200, 10, 10)),
        ("Validation/Zea mays/seed.jpg", (10, 200, 10)),
        ("Avena fatua/new.png", (10, 10, 200)),
    ]
    raw_bytes = {}
    for relative, color in inputs:
        path = collection / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (20, 16), color).save(path)
        raw_bytes[relative] = path.read_bytes()
    convert_images(
        [
            str(collection),
            str(prepared),
            "--raw-prefix",
            "raw/Collection",
            "--code-revision",
            "integration-test",
        ]
    )
    index = json.loads((prepared / "index.coco.json").read_text())

    def supplied_predictions(image, prompt):
        red, green, blue = image.getpixel((0, 0))
        return [] if blue > max(red, green) else [[2.25, 3.5, 9.25, 10.5]]

    draft = prelabel(index, prepared, supplied_predictions, padding=0)
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, draft)
    register_fiftyone(review_name, labels, str(prepared))
    dataset = fiftyone.load_dataset(review_name)
    assert dataset.persistent
    assert len(dataset) == 3
    assert isinstance(dataset.get_field("source_species"), fiftyone.StringField)
    samples = {sample.coco_id: sample for sample in dataset}
    expected_assignments = {
        inputs[0][0]: ("Avena fatua", "train"),
        inputs[1][0]: ("Zea mays", "validation"),
        inputs[2][0]: ("Avena fatua", None),
    }
    for record in draft["images"]:
        sample = samples[record["id"]]
        relative = record["sources"][0]["path"]
        assert (sample["source_species"], sample["split"]) == expected_assignments[
            relative
        ]
        assert sample["sources"] == record["sources"]
        assert sample["sources"][0]["raw_key"] == "raw/Collection/" + relative
        assert (
            sample["sources"][0]["raw_sha256"]
            == hashlib.sha256(raw_bytes[relative]).hexdigest()
        )
        assert (collection / relative).read_bytes() == raw_bytes[relative]
        assert sample["object_key"] == record["file_name"]
        assert sample.filepath == str(prepared / record["file_name"])
        assert (
            hashlib.sha256(Path(sample.filepath).read_bytes()).hexdigest()
            == sample["image_sha256"]
            == record["image_sha256"]
            == Path(sample.filepath).stem
        )
        assert sample["prelabel_status"] == record["prelabel_status"]
        assert sample["prelabel_reason"] == record["prelabel_reason"]
        if sample["split"] is None:
            assert sample["prelabel_reason"] == "no_detections"
            assert not sample.draft_boxes or not sample.draft_boxes.detections
        else:
            assert sample["prelabel_status"] == "draft"
            assert len(sample.draft_boxes.detections) == 1
            detection = sample.draft_boxes.detections[0]
            assert detection.label == expected_assignments[relative][0]
            assert detection.bounding_box == pytest.approx(
                [0.1125, 0.21875, 0.35, 0.4375]
            )
    no_boxes = dataset.match(F("source_species") == "Avena fatua").match(
        F("draft_boxes.detections").length() == 0
    )
    assert len(no_boxes) == 1
    assert no_boxes.first()["split"] is None
    assert dataset.info["preparation"] == {"code_revision": "integration-test"}
