"""Actual SDK checks against an explicitly selected disposable MongoDB instance."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from prepare_images import save_coco


@pytest.fixture
def fiftyone(monkeypatch):
    uri = os.environ.get("PREPARATION_TEST_MONGO_URI")
    if not uri:
        pytest.skip("PREPARATION_TEST_MONGO_URI is required for the isolated SDK check")
    monkeypatch.setenv("FIFTYONE_DATABASE_URI", uri)
    monkeypatch.setenv("FIFTYONE_DATABASE_NAME", "fiftyone_preparation_test")
    monkeypatch.setenv("FIFTYONE_DO_NOT_TRACK", "true")
    fo = pytest.importorskip("fiftyone")
    assert fo.__version__ == "1.22.1"
    return fo


def test_registration_survives_process_exit_and_preserves_the_review_handoff(
    tmp_path, fiftyone
):
    fo = fiftyone
    name = "preparation-test-" + uuid4().hex
    # The import worker cannot access this server-side mount.
    server_root = tmp_path / "server-only-mount"
    records = []
    for index in range(3):
        records.append(
            {
                "id": 11 + index * 7,
                "file_name": "png/detection/" + str(index) * 64 + ".png",
                "width": 100,
                "height": 80,
                "split": ["train", "validation", None][index],
                "sources": [
                    {
                        "path": f"collection/batch/tray/{index}.tiff",
                        "species": ["Avena fatua", "Zea mays", "Avena fatua"][index],
                        "batch": "batch",
                        "specimen_group": f"seed-{index}",
                    }
                ],
                "prelabel_status": "needs_review" if index == 2 else "draft",
                "prelabel_prompt": "thick long seed",
                "prelabel_reason": "no_detections" if index == 2 else None,
            }
        )
    coco = {
        "info": {
            "preparation": {"code_revision": "integration-test"},
            "prelabel": {
                "model_path": "/models/sam3",
                "model_revision": "local-weights",
                "padding": 3,
                "device": "cuda",
                "precision": "bf16",
            },
        },
        "images": records,
        "categories": [
            {"id": 17, "name": "Avena fatua"},
            {"id": 93, "name": "Zea mays"},
        ],
        "annotations": [
            {
                "id": 31,
                "image_id": 11,
                "category_id": 17,
                "bbox": [10.25, 20.5, 40.75, 30.25],
                "iscrowd": 0,
            },
            {
                "id": 43,
                "image_id": 18,
                "category_id": 93,
                "bbox": [3, 4, 5, 6],
                "iscrowd": 0,
            },
        ],
    }
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, coco)
    command = [
        sys.executable,
        str(Path(__file__).parents[1] / "register_fiftyone.py"),
        name,
        str(labels),
        "--server-media-root",
        str(server_root),
    ]
    try:
        initial = subprocess.run(command, check=False, capture_output=True, text=True)
        assert initial.returncode == 0, initial.stderr
        dataset = fo.load_dataset(name)
        assert dataset.persistent
        assert len(dataset) == 3
        samples = {sample.coco_id: sample for sample in dataset}
        for record in records:
            sample = samples[record["id"]]
            assert sample.filepath == str(server_root / record["file_name"])
            assert not Path(sample.filepath).exists()
            assert (sample.metadata.width, sample.metadata.height) == (100, 80)
            assert sample["sources"] == record["sources"]
            assert sample["split"] == record["split"]
            assert sample["prelabel_prompt"] == record["prelabel_prompt"]
            assert sample["prelabel_status"] == record["prelabel_status"]
            assert sample["prelabel_reason"] == record["prelabel_reason"]
        first = samples[11]
        detection = first.draft_boxes.detections[0]
        assert detection.label == "Avena fatua"
        assert detection.bounding_box == pytest.approx(
            [0.1025, 0.25625, 0.4075, 0.378125]
        )
        assert not samples[25].draft_boxes or not samples[25].draft_boxes.detections

        # Human correction is authoritative; subsequent registration must refuse it.
        detection.label = "Zea mays"
        detection.bounding_box = [0.1, 0.2, 0.3, 0.4]
        first.save()
        retry = subprocess.run(command, check=False, capture_output=True, text=True)
        assert retry.returncode != 0
        assert "already exists" in retry.stderr
        assert (
            fo.load_dataset(name)[first.id].draft_boxes.detections[0].label
            == "Zea mays"
        )

        assert dataset.info["preparation"] == coco["info"]["preparation"]
        assert dataset.info["prelabel"] == coco["info"]["prelabel"]
    finally:
        if fo.dataset_exists(name):
            fo.delete_dataset(name)


@pytest.mark.parametrize("failure", ["exception", "kill"])
def test_unassigned_first_sample_and_failed_import_recovery(
    tmp_path, fiftyone, monkeypatch, failure
):
    from register_fiftyone import register_fiftyone

    fo = fiftyone
    name = "preparation-test-" + uuid4().hex
    key = "png/detection/" + "a" * 64 + ".png"
    labels = tmp_path / "draft.coco.json"
    save_coco(
        labels,
        {
            "images": [
                {
                    "id": 1,
                    "file_name": key,
                    "width": 12,
                    "height": 10,
                    "split": None,
                    "sources": [{"path": "raw/a.tiff"}],
                    "prelabel_status": "needs_review",
                    "prelabel_reason": "no_detections",
                }
            ],
            "categories": [{"id": 1, "name": "Avena fatua"}],
            "annotations": [],
        },
    )
    original_import = fo.Dataset.add_dir

    def interrupted_import(dataset, *args, **kwargs):
        original_import(dataset, *args, **kwargs)
        raise RuntimeError("synthetic failure after sample insertion")

    staging_name = None
    if failure == "exception":
        with monkeypatch.context() as scoped:
            scoped.setattr(fo.Dataset, "add_dir", interrupted_import)
            with pytest.raises(RuntimeError, match="after sample insertion"):
                register_fiftyone(name, labels, str(tmp_path))
    else:
        marker = tmp_path / "staging-name.txt"
        script = tmp_path / "kill_import.py"
        script.write_text(
            "import os, signal, sys\n"
            "from pathlib import Path\n"
            "import fiftyone as fo\n"
            "from register_fiftyone import register_fiftyone\n"
            "original = fo.Dataset.add_dir\n"
            "def interrupted(dataset, *args, **kwargs):\n"
            "    original(dataset, *args, **kwargs)\n"
            "    Path(sys.argv[4]).write_text(dataset.name)\n"
            "    os.kill(os.getpid(), signal.SIGKILL)\n"
            "fo.Dataset.add_dir = interrupted\n"
            "register_fiftyone(sys.argv[1], Path(sys.argv[2]), sys.argv[3])\n"
        )
        killed = subprocess.run(
            [
                sys.executable,
                str(script),
                name,
                str(labels),
                str(tmp_path),
                str(marker),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1])},
        )
        assert killed.returncode < 0, killed.stderr
        staging_name = marker.read_text()
        assert fo.dataset_exists(staging_name)
    assert not fo.dataset_exists(name)
    try:
        register_fiftyone(name, labels, str(tmp_path))
        sample = fo.load_dataset(name).first()
        assert sample["split"] is None
        assert sample["prelabel_reason"] == "no_detections"
    finally:
        if fo.dataset_exists(name):
            fo.delete_dataset(name)
        if staging_name and fo.dataset_exists(staging_name):
            fo.delete_dataset(staging_name)
