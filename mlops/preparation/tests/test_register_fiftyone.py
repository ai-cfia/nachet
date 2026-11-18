import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

from register_fiftyone import register_fiftyone


def test_registration_carries_per_source_and_prelabel_provenance(tmp_path, monkeypatch):
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
                        "prelabel_project_version": "0.2.1",
                        "prelabel_code_revision": "new",
                    }
                ]
            }
        )
    )
    register_fiftyone("review", labels, "/server/media")
    assert sample["sources"] == [source]
    assert sample["prelabel_project_version"] == "0.2.1"
    assert sample["prelabel_code_revision"] == "new"
    assert dataset.persistent is True
    assert dataset.name == "review"
