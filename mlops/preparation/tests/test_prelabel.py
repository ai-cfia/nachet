import copy
import json
import tomllib
from pathlib import Path

import cv2
import numpy as np
import pytest
from semver import Version

import prelabel as module
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
    coco["images"][0]["prelabel_project_version"] = "old version"
    coco["images"][0]["prelabel_code_revision"] = "old revision"
    result = prelabel(coco, intake[1], predict)
    assert all(image["prelabel_status"] is None for image in result["images"])
    assert all(image["prelabel_reason"] is None for image in result["images"])
    assert all(image["prelabel_prompt"] is None for image in result["images"])
    assert all("prelabel_project_version" not in image for image in result["images"])
    assert all("prelabel_code_revision" not in image for image in result["images"])
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
        assert "score" not in annotation
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
        return Prediction([[10, 10, 20, 20]] * count, prompt, [0.8] * count)

    # Stub inference without loading weights; exercise SAM3's real prompt loop.
    predictor = Sam3Predictor.__new__(Sam3Predictor)
    monkeypatch.setattr(predictor, "_predict_prompt", predict)
    result = prelabel(coco, intake[1], predictor)
    assert calls == ["foreground object", "thick long seed", "insect"] * 3
    assert len(result["annotations"]) == 3 * count
    assert all(annotation["score"] == 0.8 for annotation in result["annotations"])
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
        if prompt == prompts[accepted]:
            boxes = [[x, 1, x + 2, 3] for x in range(1, 12 * count, 12)]
            return Prediction(boxes, prompt, [0.8] * count)
        return Prediction([], prompt, [])

    predictor = Sam3Predictor.__new__(Sam3Predictor)
    monkeypatch.setattr(predictor, "_predict_prompt", predict)
    result = prelabel(coco, intake[1], predictor)
    assert calls == list(prompts[: accepted + 1]) * len(coco["images"])
    assert all(image["prelabel_status"] is None for image in result["images"])
    assert all(
        image["prelabel_prompt"] == prompts[accepted] for image in result["images"]
    )


def test_prelabel_cannot_replace_existing_labels(prepare, intake):
    coco = prepare()
    coco["annotations"] = [{"id": 10}]
    with pytest.raises(ValueError, match="refusing to replace labels"):
        prelabel(coco, intake[1], lambda image: Prediction([]))


def test_prelabel_resumes_completed_images(coco, intake, tmp_path, monkeypatch):
    checkpoint_dir = tmp_path / "prelabel-checkpoints"
    snapshot_path = tmp_path / "unannotated.coco.json"
    calls = []

    def interrupted_predict(image):
        snapshot = json.loads(snapshot_path.read_text())
        assert snapshot["annotations"] == []
        assert {record["prelabel_status"] for record in snapshot["images"]} == {
            "unannotated"
        }
        calls.append(image.size)
        if len(calls) == 2:
            raise RuntimeError("interrupted inference")
        return Prediction([[1, 1, 3, 3]])

    with pytest.raises(RuntimeError, match="interrupted inference"):
        prelabel(
            coco,
            intake[1],
            interrupted_predict,
            checkpoint_dir=checkpoint_dir,
            predictor_identity="synthetic",
            code_revision="test-revision",
            initial_index_path=snapshot_path,
        )
    assert len(list(checkpoint_dir.rglob("*.json"))) == 1

    def unexpected_snapshot(*args):
        pytest.fail("resuming must skip the unannotated snapshot")

    monkeypatch.setattr(module, "save_coco", unexpected_snapshot)
    resumed_calls = []
    resumed = prelabel(
        coco,
        intake[1],
        lambda image: resumed_calls.append(image.size) or Prediction([[1, 1, 3, 3]]),
        checkpoint_dir=checkpoint_dir,
        predictor_identity="synthetic",
        code_revision="test-revision",
        initial_index_path=snapshot_path,
    )
    expected = prelabel(coco, intake[1], lambda image: Prediction([[1, 1, 3, 3]]))
    for image in expected["images"]:
        image["prelabel_project_version"] = str(module.project_version())
        image["prelabel_code_revision"] = "test-revision"
    assert len(resumed_calls) == 2
    assert resumed == expected


def test_compatible_upgrade_resumes_across_interruption_and_tracks_provenance(
    coco, intake, tmp_path, monkeypatch
):
    checkpoint_dir = tmp_path / "checkpoints"
    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.0"))
    calls = []

    def interrupt_after_one(image):
        calls.append(image.size)
        if len(calls) == 2:
            raise RuntimeError("interrupted inference")
        return Prediction([[1, 1, 3, 3]], "synthetic", [0.8])

    options = {
        "checkpoint_dir": checkpoint_dir,
        "predictor_identity": "model-a",
        "code_revision": "revision-a",
        "initial_index_path": tmp_path / "first.unannotated.json",
    }
    with pytest.raises(RuntimeError, match="interrupted inference"):
        prelabel(coco, intake[1], interrupt_after_one, **options)

    old_checkpoint = next(checkpoint_dir.rglob("*.json"))
    old_content = old_checkpoint.read_bytes()

    updated = copy.deepcopy(coco)
    updated["info"]["preparation"]["code_revision"] = "revision-b"
    for image in updated["images"]:
        for source in image["sources"]:
            source["preparation"] = {
                "project_version": "0.2.1",
                "code_revision": "revision-b",
            }
    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.1"))
    options["code_revision"] = "revision-b"
    options["initial_index_path"] = tmp_path / "second.unannotated.json"
    calls.clear()
    with pytest.raises(RuntimeError, match="interrupted inference"):
        prelabel(updated, intake[1], interrupt_after_one, **options)

    calls.clear()
    result = prelabel(
        updated,
        intake[1],
        lambda image: (
            calls.append(image.size) or Prediction([[1, 1, 3, 3]], "synthetic", [0.8])
        ),
        **options,
    )
    assert len(calls) == 1
    assert [
        (image["prelabel_project_version"], image["prelabel_code_revision"])
        for image in result["images"]
    ] == [("0.2.0", "revision-a"), ("0.2.1", "revision-b"), ("0.2.1", "revision-b")]
    assert result["images"][0]["prelabel_prompt"] == "synthetic"
    assert all(image["prelabel_status"] is None for image in result["images"])
    assert [annotation["id"] for annotation in result["annotations"]] == [0, 1, 2]
    assert {annotation["score"] for annotation in result["annotations"]} == {0.8}
    assert old_checkpoint.read_bytes() == old_content
    assert not options["initial_index_path"].exists()
    versions = {path.parent.name for path in checkpoint_dir.rglob("*.json")}
    assert versions == {"0.2.0", "0.2.1"}


@pytest.mark.parametrize("next_version", ["0.2.0", "0.3.0"])
def test_prelabel_incompatible_or_newer_checkpoint_starts_fresh(
    coco, intake, tmp_path, monkeypatch, next_version
):
    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.1"))
    options = {
        "checkpoint_dir": tmp_path / "checkpoints",
        "predictor_identity": "model-a",
        "code_revision": "test",
    }
    prelabel(coco, intake[1], lambda image: Prediction([]), **options)
    old_files = {
        path: path.read_bytes() for path in options["checkpoint_dir"].rglob("*.json")
    }
    monkeypatch.setattr(module, "project_version", lambda: Version.parse(next_version))
    calls = []
    result = prelabel(
        coco,
        intake[1],
        lambda image: calls.append(image.size) or Prediction([]),
        **options,
    )
    assert len(calls) == len(coco["images"])
    assert all(
        image["prelabel_project_version"] == next_version for image in result["images"]
    )
    assert all(path.read_bytes() == data for path, data in old_files.items())


@pytest.mark.parametrize("changed", ["predictor", "padding", "index"])
def test_prelabel_checkpoint_rejects_changed_inference_inputs(
    coco, intake, tmp_path, changed
):
    options = {
        "checkpoint_dir": tmp_path / "checkpoints",
        "predictor_identity": "model-a",
        "code_revision": "test",
    }
    prelabel(coco, intake[1], lambda image: Prediction([]), **options)
    updated = copy.deepcopy(coco)
    if changed == "predictor":
        options["predictor_identity"] = "model-b"
    elif changed == "padding":
        options["padding"] = 4
    else:
        updated["images"][0]["split"] = "validation"
    calls = []
    prelabel(
        updated,
        intake[1],
        lambda image: calls.append(image.size) or Prediction([]),
        **options,
    )
    assert len(calls) == len(coco["images"])


def test_legacy_prelabel_checkpoint_is_not_reused_or_removed(
    coco, intake, tmp_path, caplog
):
    checkpoint_dir = tmp_path / "checkpoints"
    legacy = checkpoint_dir / ("a" * 64) / "00000000.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"version": 1}')
    calls = []
    prelabel(
        coco,
        intake[1],
        lambda image: calls.append(image.size) or Prediction([]),
        checkpoint_dir=checkpoint_dir,
        predictor_identity="model-a",
        code_revision="test",
    )
    assert len(calls) == len(coco["images"])
    assert legacy.read_text() == '{"version": 1}'
    assert "Ignoring legacy integer-version pre-label checkpoints" in caplog.text


@pytest.mark.parametrize("problem", ["version", "box", "legacy_draft"])
def test_corrupt_prelabel_checkpoint_fails_before_inference(
    coco, intake, tmp_path, problem
):
    options = {
        "checkpoint_dir": tmp_path / "checkpoints",
        "predictor_identity": "model-a",
        "code_revision": "test",
    }
    prelabel(coco, intake[1], lambda image: Prediction([[1, 1, 3, 3]]), **options)
    path = next(options["checkpoint_dir"].rglob("00000000.json"))
    checkpoint = json.loads(path.read_text())
    message = None
    if problem == "version":
        checkpoint["version"] = 1
        error = TypeError
    elif problem == "legacy_draft":
        checkpoint["prelabel_status"] = "draft"
        error = ValueError
        message = "Restart with a fresh checkpoint directory"
    else:
        checkpoint["annotations"][0]["bbox"] = [1]
        error = ValueError
    path.write_text(json.dumps(checkpoint))
    with pytest.raises(error, match=message):
        prelabel(
            coco,
            intake[1],
            lambda image: pytest.fail("invalid checkpoint must stop inference"),
            **options,
        )


def test_checkpointed_predictor_requires_explicit_identity(coco, intake, tmp_path):
    with pytest.raises(ValueError, match="identities"):
        prelabel(coco, intake[1], lambda image: Prediction([]), checkpoint_dir=tmp_path)


@pytest.mark.parametrize("location", ["root", "releases", "version"])
def test_prelabel_rejects_symlinked_checkpoint_directories(
    coco, intake, tmp_path, location
):
    root = tmp_path / "checkpoints"
    actual = tmp_path / "elsewhere"
    actual.mkdir()
    options = {
        "checkpoint_dir": root,
        "predictor_identity": "model-a",
        "code_revision": "test",
    }
    if location == "root":
        root.symlink_to(actual, target_is_directory=True)
    elif location == "releases":
        root.mkdir()
        (root / "releases").symlink_to(actual, target_is_directory=True)
    else:
        prelabel(coco, intake[1], lambda image: Prediction([]), **options)
        version_dir = next(root.rglob(str(module.project_version())))
        version_dir.rename(actual / version_dir.name)
        version_dir.symlink_to(actual / version_dir.name, target_is_directory=True)
    with pytest.raises(
        ValueError, match="symlink|Invalid checkpoint version directory"
    ):
        prelabel(
            coco,
            intake[1],
            lambda image: pytest.fail("unsafe checkpoint path was accepted"),
            **options,
        )


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
        assert record["prelabel_status"] is None
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
        coco,
        intake[1],
        lambda image: Prediction(
            [[10, 10, 30, 30], box, [50, 50, 60, 60]],
            scores=[0.8, 0.95, 0.7],
        ),
    )
    assert [
        (annotation["bbox"], annotation["score"])
        for annotation in result["annotations"]
    ] == [([7, 7, 29, 29], 0.8), ([47, 47, 19, 19], 0.7)] * len(coco["images"])
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


@pytest.mark.parametrize(
    "second_box, reason",
    [
        pytest.param([15, 15, 20, 20], "nested_boxes", id="contained"),
        pytest.param([25, 20, 45, 40], "overlapping_boxes", id="partial-overlap"),
        pytest.param([35, 10, 55, 30], "overlapping_boxes", id="overlap-after-padding"),
        pytest.param([39, 10, 59, 30], None, id="touching-edges"),
        pytest.param([44, 10, 64, 30], None, id="separate"),
    ],
)
def test_overlapping_boxes_keep_detections_and_flag_review(
    coco, intake, second_box, reason
):
    result = prelabel(
        coco,
        intake[1],
        lambda image: Prediction([[10, 10, 30, 30], second_box]),
    )
    status = "needs_review" if reason else None
    assert all(image["prelabel_status"] == status for image in result["images"])
    assert all(image["prelabel_reason"] == reason for image in result["images"])
    assert len(result["annotations"]) == 6


@pytest.mark.parametrize(
    "second_box, has_overlapping_masks, reason",
    [
        pytest.param([25, 20, 45, 40], True, "overlapping_masks", id="nearly-nested-masks"),
        pytest.param([25, 20, 45, 40], False, None, id="overlapping-boxes-disjoint-masks"),
        pytest.param([15, 15, 20, 20], False, "nested_boxes", id="strict-nested-still-flags"),
    ],
)
def test_mask_overlap_overrides_box_overlap_and_keeps_detections(
    coco, intake, second_box, has_overlapping_masks, reason
):
    result = prelabel(
        coco,
        intake[1],
        lambda image: Prediction(
            [[10, 10, 30, 30], second_box],
            has_overlapping_masks=has_overlapping_masks,
        ),
    )
    status = "needs_review" if reason else None
    assert all(image["prelabel_status"] == status for image in result["images"])
    assert all(image["prelabel_reason"] == reason for image in result["images"])
    assert len(result["annotations"]) == 6


def test_has_overlapping_masks_matrix_logic():
    class _FakeTensor:
        def __init__(self, arr):
            self.arr = np.asarray(arr)

        def __len__(self):
            return len(self.arr)

        def flatten(self, start_dim=0):
            return _FakeTensor(self.arr.reshape(self.arr.shape[0], -1))

        def float(self):
            return _FakeTensor(self.arr.astype(np.float32))

        def sum(self, dim=None):
            return _FakeTensor(self.arr.sum(axis=dim))

        def unsqueeze(self, dim):
            return _FakeTensor(np.expand_dims(self.arr, axis=dim))

        def minimum(self, other):
            return _FakeTensor(np.minimum(self.arr, other.arr))

        @property
        def T(self):
            return _FakeTensor(self.arr.T)

        def __matmul__(self, other):
            return _FakeTensor(self.arr @ other.arr)

        def fill_diagonal_(self, val):
            np.fill_diagonal(self.arr, val)

        def __rmul__(self, scalar):
            return _FakeTensor(scalar * self.arr)

        def __ge__(self, other):
            return _FakeTensor(self.arr >= other.arr)

        def __gt__(self, scalar):
            return _FakeTensor(self.arr > scalar)

        def __and__(self, other):
            return _FakeTensor(self.arr & other.arr)

        def any(self):
            return _FakeTensor(np.array(self.arr.any()))

        def item(self):
            return self.arr.item()

    # Single mask or empty -> False
    assert not module._has_overlapping_masks(_FakeTensor(np.ones((1, 4, 4), dtype=bool)))
    assert not module._has_overlapping_masks(_FakeTensor(np.zeros((0, 4, 4), dtype=bool)))

    # Two disjoint masks -> False
    disjoint = np.zeros((2, 4, 4), dtype=bool)
    disjoint[0, :2, :2] = True
    disjoint[1, 2:, 2:] = True
    assert not module._has_overlapping_masks(_FakeTensor(disjoint))

    # Partial overlap < 50% of smaller mask (1 of 4 pixels = 25%) -> False
    slight = np.zeros((2, 4, 4), dtype=bool)
    slight[0, :2, :2] = True
    slight[1, 1:3, 1:3] = True
    assert not module._has_overlapping_masks(_FakeTensor(slight))

    # Nearly nested: smaller mask (4 px) shares 3 px (75% >= 50%) with larger mask -> True
    nested = np.zeros((2, 4, 4), dtype=bool)
    nested[0, :3, :3] = True
    nested[1, 1:3, 2:4] = True  # 2x2=4 px, 2 px inside [0:3, 0:3] => 50%
    assert module._has_overlapping_masks(_FakeTensor(nested))


def test_resume_checks_saved_boxes_for_overlap(coco, intake, tmp_path):
    checkpoint_dir = tmp_path / "checkpoints"
    options = {
        "checkpoint_dir": checkpoint_dir,
        "predictor_identity": "model-a",
        "code_revision": "test",
    }
    expected = prelabel(
        coco,
        intake[1],
        lambda image: Prediction([[10, 10, 30, 30], [25, 20, 45, 40]]),
        **options,
    )
    path = next(checkpoint_dir.rglob("00000000.json"))
    checkpoint = json.loads(path.read_text())
    checkpoint.update(prelabel_status=None, prelabel_reason=None)
    path.write_text(json.dumps(checkpoint))

    resumed = prelabel(
        coco,
        intake[1],
        lambda image: pytest.fail("saved boxes should not require new inference"),
        **options,
    )
    assert resumed == expected
    assert json.loads(path.read_text()) == checkpoint


def test_prelabel_cli_records_run_options_once(coco, intake, tmp_path, monkeypatch):
    import prelabel as command

    source = tmp_path / "index.json"
    coco["images"][0].update(
        prelabel_status="needs_review",
        prelabel_reason="old warning",
        prelabel_prompt="old prompt",
        prelabel_project_version="old version",
        prelabel_code_revision="old revision",
    )
    coco["info"]["prelabel"] = {"model_revision": "old model"}
    save_coco(source, coco)
    output = tmp_path / "draft.json"
    checkpoint_dir = tmp_path / "checkpoints"
    calls = []
    monkeypatch.setattr(
        command,
        "Sam3Predictor",
        lambda *args: lambda image: calls.append(image.size) or Prediction([]),
    )
    args = [
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
        "--checkpoint-dir",
        str(checkpoint_dir),
        "--code-revision",
        "test-revision",
    ]
    command.main(args)
    result = json.loads(output.read_text())
    snapshot = json.loads((tmp_path / "draft.unannotated.json").read_text())
    assert snapshot["annotations"] == []
    assert snapshot["info"] == {
        key: value for key, value in coco["info"].items() if key != "prelabel"
    }
    assert all(
        {key: value for key, value in image.items() if key.startswith("prelabel_")}
        == {"prelabel_status": "unannotated"}
        for image in snapshot["images"]
    )
    assert json.loads(source.read_text()) == coco
    with Path(command.__file__).with_name("pyproject.toml").open("rb") as stream:
        project_version = tomllib.load(stream)["project"]["version"]
    assert {
        json.loads(path.read_text())["version"]
        for path in checkpoint_dir.rglob("*.json")
    } == {project_version}
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

    calls.clear()
    command.main(args)
    assert calls == []

    args[args.index("test-weights")] = "new-model-revision"
    args[2] = str(tmp_path / "new-draft.json")
    command.main(args)
    assert calls == [(100, 80)] * 3


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
