import copy
import hashlib
import json
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
from mlops_blob.exceptions import BlobNotFoundError

import prelabel as module
from prepare_images import save_coco


@pytest.fixture
def s3_media(prepare, intake, s3_provider):
    coco = prepare()
    for record in coco["images"]:
        s3_provider.objects["datasets", record["file_name"]] = (
            intake[1] / record["file_name"]
        ).read_bytes()
    return coco, intake[1], s3_provider


def test_s3_and_local_inputs_keep_pixels_annotations_and_metadata(s3_media):
    coco, local, provider = s3_media
    before = copy.deepcopy(coco)
    pixels = []

    def predict(image):
        pixels.append((image.size, image.mode, image.tobytes()))
        return module.Prediction([[10.5, 20.25, 30.75, 40.5]])

    expected = module.prelabel(coco, local, predict)
    local_pixels = pixels[:]
    pixels.clear()
    actual = module.prelabel_s3(coco, provider.storage, "datasets", predict)
    assert actual == expected
    assert pixels == local_pixels
    assert coco == before
    assert provider.client.get_object.call_count == len(coco["images"])
    provider.client.put_object.assert_not_called()
    assert any(
        record["prelabel_reason"] == "high_bit_depth" for record in actual["images"]
    )


def test_s3_rgb16_png_is_flagged_without_lossy_inference(s3_media):
    coco, _, provider = s3_media
    pixels = np.full((5, 7, 3), 40000, dtype=np.uint16)
    ok, encoded = cv2.imencode(".png", pixels)
    assert ok
    data = encoded.tobytes()
    digest = hashlib.sha256(data).hexdigest()
    record = coco["images"][0]
    record.update(
        file_name=f"png/detection/{digest}.png", image_sha256=digest, width=7, height=5
    )
    coco["images"] = [record]
    provider.objects["datasets", record["file_name"]] = data
    predictor = Mock()
    result = module.prelabel_s3(coco, provider.storage, "datasets", predictor)
    assert result["images"][0]["prelabel_reason"] == "high_bit_depth"
    assert result["annotations"] == []
    predictor.assert_not_called()


@pytest.mark.parametrize("problem", ["key", "bytes", "missing", "dimensions"])
def test_bad_s3_input_fails_before_inference(s3_media, problem):
    coco, _, provider = s3_media
    record = coco["images"][0]
    if problem == "key":
        record["file_name"] = "png/detection/other.png"
        error, message = ValueError, "PNG key does not match"
    elif problem == "bytes":
        provider.objects["datasets", record["file_name"]] = b"changed"
        error, message = ValueError, "PNG does not match"
    elif problem == "missing":
        provider.client.get_object.side_effect = BlobNotFoundError(
            "datasets", record["file_name"]
        )
        error, message = BlobNotFoundError, "not found"
    else:
        record["width"] += 1
        error, message = ValueError, "COCO dimensions do not match"
    predictor = Mock()
    with pytest.raises(error, match=message):
        module.prelabel_s3(coco, provider.storage, "datasets", predictor)
    predictor.assert_not_called()
    provider.client.put_object.assert_not_called()


@pytest.mark.parametrize("failure", [None, "hash", "model"])
def test_s3_cli_closes_client_and_saves_only_a_completed_draft(
    s3_media, tmp_path, monkeypatch, failure
):
    import s3_storage

    coco, _, provider = s3_media
    index, output = tmp_path / "index.json", tmp_path / "draft.json"
    save_coco(index, coco)
    factory = Mock(return_value=lambda image: module.Prediction([[1, 1, 3, 3]]))
    if failure == "model":
        factory.side_effect = RuntimeError("test model failure")
    elif failure == "hash":
        provider.objects["datasets", coco["images"][0]["file_name"]] = b"changed"
    monkeypatch.setattr(module, "Sam3Predictor", factory)
    monkeypatch.setattr(s3_storage, "create_storage", lambda *a, **kw: provider.storage)
    args = [
        str(index),
        "s3://datasets",
        str(output),
        "--model-path",
        str(tmp_path),
        "--model-revision",
        "test-weights",
        "--device",
        "cpu",
        "--endpoint-url",
        "https://storage.example.test",
        "--region",
        "garage",
    ]
    if failure:
        with pytest.raises((RuntimeError, ValueError)):
            module.main(args)
        assert not output.exists()
    else:
        module.main(args)
        result = json.loads(output.read_text())
        assert len(result["images"]) == len(coco["images"])
        assert result["info"]["prelabel"]["model_revision"] == "test-weights"
        assert len(result["annotations"]) == 3
    provider.client.close.assert_called_once()


@pytest.mark.parametrize(
    "media,options",
    [
        ("s3://datasets", []),
        ("s3://datasets/png", ["--endpoint-url", "https://s3.test", "--region", "x"]),
        ("s3://", []),
        ("/local", ["--region", "x"]),
    ],
)
def test_invalid_s3_configuration_fails_before_loading_the_model(
    tmp_path, monkeypatch, media, options
):
    model = Mock()
    monkeypatch.setattr(module, "Sam3Predictor", model)
    with pytest.raises(SystemExit) as error:
        module.main(
            [
                str(tmp_path / "index"),
                media,
                str(tmp_path / "out"),
                "--model-path",
                str(tmp_path),
                "--model-revision",
                "test",
                "--device",
                "cpu",
                *options,
            ]
        )
    assert error.value.code == 2
    model.assert_not_called()
