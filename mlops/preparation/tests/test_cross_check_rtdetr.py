import json

import pytest

import cross_check_rtdetr as module
from cross_check_rtdetr import cross_check, has_one_way_disagreement
from prelabel import Prediction, prelabel
from prepare_images import save_coco


@pytest.fixture
def prelabeled(prepare, intake):
    coco = prepare()
    coco["images"] = [
        image
        for image in coco["images"]
        if not image["sources"][0]["original_path"].endswith("d.tiff")
    ]
    return prelabel(
        coco,
        intake[1],
        lambda image: Prediction(
            [[10, 10, 30, 30]],
            prompt="foreground object",
            scores=[0.95],
            has_overlapping_masks=False,
        ),
        padding=0,
    )


def test_one_way_disagreement_logic():
    # Exact match -> False
    assert not has_one_way_disagreement(
        [{"bbox": [10, 10, 20, 20], "score": 0.95}],
        [[10, 10, 30, 30]],
    )
    # RT-DETR finds an extra missed seed -> True
    assert has_one_way_disagreement(
        [{"bbox": [10, 10, 20, 20], "score": 0.95}],
        [[10, 10, 30, 30], [50, 50, 70, 70]],
    )
    # RT-DETR misses a high-confidence SAM3 seed (>= 0.90) -> False
    assert not has_one_way_disagreement(
        [{"bbox": [10, 10, 20, 20], "score": 0.92}],
        [],
    )
    # RT-DETR misses a lower-confidence SAM3 box (< 0.90) -> True
    assert has_one_way_disagreement(
        [{"bbox": [10, 10, 20, 20], "score": 0.85}],
        [],
    )


def test_cross_check_flags_missed_seed_and_preserves_annotations(prelabeled, intake):
    before_annotations = list(prelabeled["annotations"])
    result = cross_check(
        prelabeled,
        intake[1],
        lambda image: [[10, 10, 30, 30], [50, 40, 70, 60]],
    )
    assert all(image["prelabel_status"] == "needs_review" for image in result["images"])
    assert all(
        image["prelabel_reason"] == "detector_disagreement"
        for image in result["images"]
    )
    assert result["annotations"] == before_annotations


def test_cross_check_skips_already_flagged_images(prelabeled, intake):
    prelabeled["images"][0].update(
        prelabel_status="needs_review",
        prelabel_reason="overlapping_masks",
    )
    calls = []

    def predict(image):
        calls.append(image.size)
        return [[10, 10, 30, 30]]

    result = cross_check(prelabeled, intake[1], predict)
    assert len(calls) == len(prelabeled["images"]) - 1
    assert result["images"][0]["prelabel_status"] == "needs_review"
    assert result["images"][0]["prelabel_reason"] == "overlapping_masks"
    assert all(image["prelabel_status"] is None for image in result["images"][1:])


def test_cross_check_cli_writes_output_and_metadata(
    prelabeled, intake, tmp_path, monkeypatch
):
    source = tmp_path / "draft.json"
    output = tmp_path / "checked.json"
    save_coco(source, prelabeled)

    class _StubPredictor:
        def __init__(self, model_path, device):
            self.model_path = model_path
            self.device = device

        def __call__(self, image):
            return [[10, 10, 30, 30], [55, 45, 75, 65]]

    monkeypatch.setattr(module, "RtDetrPredictor", _StubPredictor)
    module.main(
        [
            str(source),
            str(intake[1]),
            str(output),
            "--model-path",
            str(tmp_path / "rtdetr"),
            "--device",
            "cpu",
        ]
    )
    saved = json.loads(output.read_text())
    assert saved["info"]["cross_check"]["device"] == "cpu"
    assert all(
        image["prelabel_reason"] == "detector_disagreement" for image in saved["images"]
    )
