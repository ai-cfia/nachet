import json

import cv2
import numpy as np
import pytest

from prelabel import Prediction, Sam3Predictor, coco_box, prelabel
from prepare_images import prepare_images, save_coco


@pytest.fixture
def coco(prepare):
    """The prepared index without its 16-bit image, so every image is inferred."""
    coco = prepare()
    coco["images"] = [
        image
        for image in coco["images"]
        if not image["sources"][0]["original_path"].endswith("d.tiff")
    ]
    return coco


def test_image_only_predictor_builds_coco_without_prompts(coco, intake):
    calls = []

    def predict(image):
        calls.append(image.size)
        return Prediction([[10.5, 20.25, 30.75, 40.5], [0, 0, 2, 3]])

    coco["images"][0]["prelabel_reason"] = "old warning"
    coco["images"][0]["prelabel_prompt"] = "old prompt"
    result = prelabel(coco, intake[1], predict)
    assert all(image["prelabel_reason"] is None for image in result["images"])
    assert all(image["prelabel_prompt"] is None for image in result["images"])
    assert calls == [(100, 80)] * 3
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
        assert before["image_sha256"] == after["image_sha256"]
        assert before["sources"] == after["sources"]
        assert before["split"] == after["split"]
    assert coco["annotations"] == []


@pytest.mark.parametrize(
    "count, reason", [(0, "no_detections"), (10, "too_many_detections")]
)
def test_sam3_fallback_keeps_the_last_prompt_result(
    coco, intake, monkeypatch, count, reason
):
    calls = []

    def predict(image, prompt):
        calls.append(prompt)
        return [[10, 10, 20, 20]] * count

    # Stub inference without loading weights; exercise SAM3's real prompt loop.
    predictor = Sam3Predictor.__new__(Sam3Predictor)
    monkeypatch.setattr(predictor, "_predict_prompt", predict)
    result = prelabel(coco, intake[1], predictor)
    assert calls == ["foreground object", "thick long seed", "insect"] * 3
    assert len(result["annotations"]) == 3 * count
    assert len(result["images"]) == 3
    assert all(image["prelabel_status"] == "needs_review" for image in result["images"])
    assert all(image["prelabel_reason"] == reason for image in result["images"])
    assert all(image["prelabel_prompt"] == "insect" for image in result["images"])


@pytest.mark.parametrize("accepted, count", [(0, 1), (0, 9), (1, 1), (2, 1)])
def test_sam3_stops_after_the_first_accepted_prompt(
    coco, intake, monkeypatch, accepted, count
):
    prompts = ("foreground object", "thick long seed", "insect")
    calls = []

    def predict(image, prompt):
        calls.append(prompt)
        return [[1, 1, 3, 3]] * count if prompt == prompts[accepted] else []

    predictor = Sam3Predictor.__new__(Sam3Predictor)
    monkeypatch.setattr(predictor, "_predict_prompt", predict)
    result = prelabel(coco, intake[1], predictor)
    assert calls == list(prompts[: accepted + 1]) * len(coco["images"])
    assert all(image["prelabel_status"] == "draft" for image in result["images"])
    assert all(
        image["prelabel_prompt"] == prompts[accepted] for image in result["images"]
    )


def test_prelabel_cannot_replace_existing_labels(prepare, intake):
    coco = prepare()
    coco["annotations"] = [{"id": 10}]
    with pytest.raises(ValueError, match="refusing to replace labels"):
        prelabel(coco, intake[1], lambda image: Prediction([]))


def test_high_bit_depth_images_remain_for_review_without_stopping_the_batch(
    prepare, intake
):
    calls = []
    index = prepare()
    result = prelabel(
        index, intake[1], lambda image: calls.append(1) or Prediction([[1, 1, 3, 3]])
    )
    high_bit = next(
        i
        for i in result["images"]
        if i["sources"][0]["original_path"].endswith("d.tiff")
    )
    assert high_bit["prelabel_status"] == "needs_review"
    assert high_bit["prelabel_reason"] == "high_bit_depth"
    assert high_bit["prelabel_prompt"] is None
    assert high_bit["image_sha256"] == next(
        i["image_sha256"] for i in index["images"] if i["id"] == high_bit["id"]
    )
    assert len(calls) == 3
    assert high_bit["id"] not in {a["image_id"] for a in result["annotations"]}


@pytest.mark.parametrize("channels", [3, 4], ids=["rgb", "rgba"])
@pytest.mark.parametrize("dtype", [np.uint8, np.uint16], ids=["8bit", "16bit"])
def test_colour_png_depth_is_checked_before_prediction(
    prepare, intake, channels, dtype
):
    source, prepared = intake
    path = source / "Avena fatua/colour.png"
    pixels = np.full((80, 100, channels), 100, dtype=dtype)
    if dtype == np.uint16:
        pixels[:, :, 0] = 40000
    ok, encoded = cv2.imencode(".png", pixels)
    assert ok
    raw = encoded.tobytes()
    path.write_bytes(raw)
    index = prepare()
    before = next(
        image
        for image in index["images"]
        if image["sources"][0]["original_path"].endswith("colour.png")
    )
    calls = []
    result = prelabel(
        index,
        prepared,
        lambda image: calls.append(image.mode) or Prediction([[1, 1, 3, 3]]),
    )
    record = next(image for image in result["images"] if image["id"] == before["id"])
    if dtype == np.uint16:
        assert record["prelabel_status"] == "needs_review"
        assert record["prelabel_reason"] == "high_bit_depth"
        assert len(calls) == 3
        assert record["id"] not in {a["image_id"] for a in result["annotations"]}
    else:
        assert record["prelabel_status"] == "draft"
        assert record["prelabel_reason"] is None
        assert calls == ["RGB"] * 4
    assert record["prelabel_prompt"] is None
    for field in ["image_sha256", "file_name", "sources", "split"]:
        assert record[field] == before[field]
    assert (prepared / record["file_name"]).read_bytes() == raw
    assert path.read_bytes() == raw


@pytest.mark.parametrize(
    "box", [[110, 10, 120, 20], [1, 1, 1, 2], [0, 0, float("nan"), 20]]
)
def test_invalid_boxes_keep_valid_detections_and_mark_the_image_for_review(
    coco, intake, box
):
    result = prelabel(
        coco, intake[1], lambda image: Prediction([[10, 10, 30, 30], box])
    )
    assert len(result["annotations"]) == len(coco["images"])
    assert all(i["prelabel_status"] == "needs_review" for i in result["images"])
    assert all(i["prelabel_reason"] == "invalid_boxes" for i in result["images"])


@pytest.mark.parametrize("count", [10, 11])
def test_too_many_detections_reason_survives_invalid_geometry(coco, intake, count):
    boxes = [[10, 10, 30, 30]] * (count - 1) + [[110, 10, 120, 20]]
    result = prelabel(coco, intake[1], lambda image: Prediction(boxes))
    assert all(i["prelabel_status"] == "needs_review" for i in result["images"])
    assert all(i["prelabel_reason"] == "too_many_detections" for i in result["images"])
    assert len(result["annotations"]) == len(coco["images"]) * (count - 1)


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


def test_nested_drafts_retain_the_notebook_warning(coco, intake):
    result = prelabel(
        coco,
        intake[1],
        lambda image: Prediction([[0, 0, 50, 60], [10, 10, 30, 30]]),
    )
    assert all(image["prelabel_status"] == "draft" for image in result["images"])
    assert all(image["prelabel_reason"] == "nested_boxes" for image in result["images"])
    assert len(result["annotations"]) == 6


def test_prelabel_cli_records_run_options_once(coco, intake, tmp_path, monkeypatch):
    import prelabel as command

    source = tmp_path / "index.json"
    save_coco(source, coco)
    output = tmp_path / "draft.json"
    monkeypatch.setattr(
        command, "Sam3Predictor", lambda *args: lambda image: Prediction([])
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
    assert [image["image_sha256"] for image in result["images"]] == [
        image["image_sha256"] for image in coco["images"]
    ]


def test_automatic_collection_keeps_labels_and_splits_through_prelabel(
    automatic_collection,
):
    root, output = automatic_collection
    index = prepare_images(
        root, output, code_revision="test", raw_prefix="raw/collection"
    )
    draft = prelabel(index, output, lambda image: Prediction([[1, 1, 3, 3]]))
    images = {i["id"]: i for i in draft["images"]}
    classes = {c["id"]: c["name"] for c in draft["categories"]}
    c_splits = set()
    for box in draft["annotations"]:
        image = images[box["image_id"]]
        source = image["sources"][0]
        assert classes[box["category_id"]] == source["species"]
        assert source["raw_key"] == "raw/collection/" + source["original_path"]
        if source["species"] == "C":
            assert box["category_id"] == 3
            c_splits.add(image["split"])
    assert c_splits == {"train", "validation"}
    assert len(draft["annotations"]) == 6
    assert any(i["split"] is None for i in draft["images"])
