import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
    source = {
        "species": "A",
        "preparation": {"project_version": "0.2.0", "code_revision": "old"},
    }
    labels = tmp_path / "draft.json"
    labels.write_text(
        json.dumps(
            {
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
                ]
            }
        )
    )
    register_fiftyone("review", labels, "/server/media")
    assert dataset.add_dir.call_args.kwargs["tags"] == ["not-verified"]
    assert sample["sources"] == [source]
    assert sample["prelabel_status"] == expected_status
    dataset.add_sample_field.assert_any_call("prelabel_status", fo.StringField)
    assert sample["prelabel_project_version"] == "0.2.1"
    assert sample["prelabel_code_revision"] == "new"
    assert dataset.persistent is True
    assert dataset.name == "review"
