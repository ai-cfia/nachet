import json
import sys
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

import register_fiftyone as registration
from register_fiftyone import register_fiftyone


@pytest.mark.parametrize(
    "status_field, expected_status",
    [
        ({}, "unannotated"),
        ({"prelabel_status": None}, None),
        ({"prelabel_status": "needs_review"}, "needs_review"),
    ],
)
def test_registration_carries_per_source_and_prelabel_provenance(
    tmp_path, monkeypatch, status_field, expected_status
):
    class Sample(dict):
        def __init__(self, coco_id):
            super().__init__()
            self.coco_id = coco_id

    sample = Sample(4)
    dataset = MagicMock()
    dataset.__len__.return_value = 1
    dataset.iter_samples.return_value = [sample]
    dataset.info = {}
    fo = SimpleNamespace(
        dataset_exists=lambda name: False,
        Dataset=lambda **kwargs: dataset,
        StringField=object(),
        types=SimpleNamespace(COCODetectionDataset=object()),
    )
    monkeypatch.setitem(sys.modules, "fiftyone", fo)
    fixed_date = datetime(2026, 11, 20, tzinfo=UTC)
    monkeypatch.setattr(
        registration, "datetime", SimpleNamespace(now=fixed_date.astimezone)
    )
    source = {
        "species": "A",
        "preparation": {"project_version": "0.2.0", "code_revision": "old"},
    }
    labels = tmp_path / "draft.json"
    labels.write_text(
        json.dumps(
            {
                "info": {
                    "prelabel": {
                        "model_path": "/tmp/staged-model",
                        "model_source": "s3://models/snapshots/sam3_hf_transformers/",
                        "model_revision": "test-weights",
                    }
                },
                "images": [
                    {
                        "id": 4,
                        "file_name": "png/detection/test.png",
                        "image_sha256": "test",
                        "split": None,
                        "sources": [source],
                        **status_field,
                        "prelabel_project_version": "0.2.1",
                        "prelabel_code_revision": "new",
                    }
                ],
                "annotations": [{"id": 0, "image_id": 4, "bbox": [1, 1, 4, 4]}],
            }
        )
    )
    register_fiftyone("review", labels, "/server/media")
    assert dataset.add_dir.call_args.kwargs["tags"] == ["not-verified"]
    assert dataset.add_dir.call_args.kwargs["label_field"] == {
        "detections": "boxes_20261120",
        "coco_id": "coco_id",
    }
    assert dataset.tag_labels.call_args_list == [
        call("not-verified"),
        call("sam3_hf_transformers-test-weights", label_fields="boxes_20261120"),
    ]
    assert sample["sources"] == [source]
    assert sample["prelabel_status"] == expected_status
    dataset.add_sample_field.assert_any_call("prelabel_status", fo.StringField)
    assert sample["prelabel_project_version"] == "0.2.1"
    assert sample["prelabel_code_revision"] == "new"
    assert dataset.persistent is True
    assert dataset.name == "review"
