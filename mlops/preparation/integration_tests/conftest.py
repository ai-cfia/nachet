import os
from uuid import uuid4

import pytest


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


@pytest.fixture
def review_name(fiftyone):
    name = "preparation-test-" + uuid4().hex
    yield name
    if fiftyone.dataset_exists(name):
        fiftyone.delete_dataset(name)


@pytest.fixture
def draft_coco():
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
    return {
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
