import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import cv2
import numpy as np
import pytest
from blob.exceptions import (
    BlobNotFoundError,
    BlobStorageError,
)
from botocore.exceptions import ClientError
from PIL import Image

import prepare_s3 as module
from prepare_images import prepare_images


def cli_args(output, prefix="raw/collection"):
    return [
        str(output),
        "--bucket",
        "datasets",
        "--endpoint-url",
        "https://storage.example.test",
        "--region",
        "garage",
        "--raw-prefix",
        prefix,
        "--code-revision",
        "test",
    ]


def collection_storage(root, prefix="raw/collection/"):
    objects = {
        prefix + path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    # S3 only represents an empty directory when an explicit marker exists.
    keys = list(objects) + [
        prefix + path.relative_to(root).as_posix() + "/"
        for path in root.rglob("*")
        if path.is_dir() and not any(path.iterdir())
    ]
    return SimpleNamespace(
        list_collection_keys=AsyncMock(return_value=keys),
        read_image=AsyncMock(side_effect=lambda bucket, key: objects[key]),
        upload_png=AsyncMock(
            side_effect=lambda bucket, key, data, **kwargs: objects.__setitem__(
                key, data
            )
        ),
        objects=objects,
        close=Mock(),
    )


@pytest.mark.parametrize(
    "layout", ["unsplit", "mixed", "aliases", "duplicate", "hidden", "rgb16"]
)
def test_s3_and_local_conversion_produce_identical_outputs(
    intake, automatic_collection, tmp_path, layout
):
    root = automatic_collection[0] if layout in {"mixed", "aliases"} else intake[0]
    if layout == "aliases":
        (root / "Training").rename(root / "Train")
        (root / "Validation").rename(root / "vAL")
        test = root / "Testing/A/seed.png"
        test.parent.mkdir(parents=True)
        Image.new("RGB", (8, 6), "blue").save(test)
    elif layout == "duplicate":
        source = root / "Avena fatua/other/c.png"
        source.with_name("copy.png").write_bytes(source.read_bytes())
    elif layout == "hidden":
        for relative in ["Avena fatua/.ignored.png", "Hidden only/.seed.png"]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (3, 2), "blue").save(path)
        (root / "Empty species").mkdir()
    elif layout == "rgb16":
        pixels = np.array([[[1000, 20000, 65535], [4000, 5000, 6000]]], dtype=np.uint16)
        ok, encoded = cv2.imencode(".tiff", pixels)
        assert ok
        (root / "Avena fatua/color16.tiff").write_bytes(encoded.tobytes())
    local = tmp_path / "local"
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    expected = prepare_images(
        root, local, code_revision="test", raw_prefix="raw/collection"
    )
    storage = collection_storage(root)
    actual = asyncio.run(
        module.prepare_s3(storage, "datasets", "raw/collection", code_revision="test")
    )
    assert actual == expected
    assert len(storage.upload_png.call_args_list) == len(actual["images"])
    for image in actual["images"]:
        assert (
            storage.objects[image["file_name"]]
            == (local / image["file_name"]).read_bytes()
        )
    assert all(path.read_bytes() == data for path, data in before.items())
    downloaded = {call.args[1] for call in storage.read_image.call_args_list}
    assert downloaded == {
        "raw/collection/" + source["original_path"]
        for image in actual["images"]
        for source in image["sources"]
    }


def test_explicit_split_matches_local_input(intake, tmp_path):
    root, _ = intake
    expected = prepare_images(
        root,
        tmp_path / "local",
        code_revision="test",
        split="train",
        raw_prefix="raw/collection",
    )
    actual = asyncio.run(
        module.prepare_s3(
            collection_storage(root),
            "datasets",
            "raw/collection",
            code_revision="test",
            split="train",
        )
    )
    assert actual == expected


def test_explicit_split_cannot_override_s3_split_folders(automatic_collection):
    storage = collection_storage(automatic_collection[0])
    with pytest.raises(ValueError, match="Cannot set a split"):
        asyncio.run(
            module.prepare_s3(
                storage,
                "datasets",
                "raw/collection",
                code_revision="test",
                split="train",
            )
        )
    storage.read_image.assert_not_called()


def test_collection_without_images_is_reported():
    storage = SimpleNamespace(
        list_collection_keys=AsyncMock(return_value=["raw/collection/A/notes.txt"]),
        read_image=AsyncMock(),
    )
    with pytest.raises(
        ValueError, match="No images found.*s3://datasets/raw/collection"
    ):
        asyncio.run(
            module.prepare_s3(
                storage, "datasets", "raw/collection", code_revision="test"
            )
        )
    storage.read_image.assert_not_called()


@pytest.mark.parametrize(
    ("keys", "message"),
    [
        (["raw/other/A/seed.tiff"], "outside the collection"),
        (["raw/collection/A/../seed.tiff"], "invalid collection path"),
        (["raw/collection/A//seed.tiff"], "invalid collection path"),
        (["raw/collection/seed.tiff"], "inside a species folder"),
        (
            ["raw/collection/A/Training/B/seed.tiff"],
            "collection folder, not its parent",
        ),
        (
            [
                "raw/collection/Training/A/seed.tiff",
                "raw/collection/Validation/a/seed.tiff",
            ],
            "differ only in case",
        ),
    ],
)
def test_invalid_layout_fails_before_reading_images(keys, message):
    storage = SimpleNamespace(
        list_collection_keys=AsyncMock(return_value=keys),
        read_image=AsyncMock(),
    )
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            module.prepare_s3(
                storage,
                "datasets",
                "raw/collection",
                code_revision="test",
            )
        )
    storage.read_image.assert_not_called()


def test_duplicate_png_in_different_splits_is_rejected(automatic_collection):
    root, _ = automatic_collection
    (root / "Validation/C/seed.tiff").write_bytes(
        (root / "Training/C/seed.tiff").read_bytes()
    )
    with pytest.raises(ValueError, match="conflicting species or splits"):
        asyncio.run(
            module.prepare_s3(
                collection_storage(root),
                "datasets",
                "raw/collection",
                code_revision="test",
            )
        )


def test_reads_spaced_original_without_custom_hash_metadata(s3_provider, tmp_path):
    root = tmp_path / "source"
    path = root / "Amaranthus albus/seed.tiff"
    path.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), "red").save(path)
    s3_provider.objects["datasets", "raw/collection/Amaranthus albus/seed.tiff"] = (
        path.read_bytes()
    )
    actual = asyncio.run(
        module.prepare_s3(
            s3_provider.storage,
            "datasets",
            "raw/collection",
            code_revision="test",
        )
    )
    expected = prepare_images(
        root, tmp_path / "local", code_revision="test", raw_prefix="raw/collection"
    )
    assert actual == expected
    image = actual["images"][0]
    assert (
        s3_provider.objects["datasets", image["file_name"]]
        == (tmp_path / "local" / image["file_name"]).read_bytes()
    )
    assert s3_provider.client.put_object.call_args.kwargs["IfNoneMatch"] == "*"


def test_missing_object_is_not_silently_omitted(intake):
    storage = collection_storage(intake[0])
    storage.read_image.side_effect = BlobNotFoundError("datasets", "missing.tiff")
    with pytest.raises(BlobNotFoundError, match="missing.tiff"):
        asyncio.run(
            module.prepare_s3(
                storage,
                "datasets",
                "raw/collection",
                code_revision="test",
            )
        )


@pytest.mark.parametrize("corrupt", [False, True])
def test_cli_writes_index_and_closes_client(intake, tmp_path, monkeypatch, corrupt):
    storage = collection_storage(intake[0])
    if corrupt:
        storage.read_image.side_effect = lambda bucket, key: b"invalid image"
    monkeypatch.setattr(module, "create_storage", Mock(return_value=storage))
    output = tmp_path / "remote"
    args = cli_args(output)
    if corrupt:
        with pytest.raises(OSError, match="Avena fatua/.*a.tiff"):
            module.main(args)
        assert not (output / "index.coco.json").exists()
    else:
        module.main(args)
        result = json.loads((output / "index.coco.json").read_text())
        assert len(result["images"]) == 4
        assert list(output.iterdir()) == [output / "index.coco.json"]
    storage.close.assert_called_once()


@pytest.mark.parametrize("failure", ["before_write", "after_write"])
def test_interrupted_upload_leaves_no_index_and_retry_finishes(
    tmp_path, s3_provider, monkeypatch, failure
):
    root = tmp_path / "source"
    for index, color in enumerate(["red", "green", "blue"]):
        path = root / "A" / f"{index}.tiff"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (3, 2), color).save(path)
        s3_provider.objects["datasets", f"raw/collection/A/{index}.tiff"] = (
            path.read_bytes()
        )
    originals = dict(s3_provider.objects)
    client = s3_provider.client
    put = client.put_object.side_effect
    writes = 0

    def interrupted_put(**kwargs):
        nonlocal writes
        writes += 1
        if failure == "before_write" and writes == 2:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        result = put(**kwargs)
        if failure == "after_write" and writes == 2:
            raise ClientError({"Error": {"Code": "InternalError"}}, "PutObject")
        return result

    client.put_object.side_effect = interrupted_put
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: s3_provider.storage)
    output = tmp_path / "prepared"
    args = cli_args(output)
    with pytest.raises(BlobStorageError):
        module.main(args)
    assert not output.exists()
    partial = {
        key: value
        for key, value in s3_provider.objects.items()
        if key[1].startswith("png/")
    }
    assert len(partial) == (1 if failure == "before_write" else 2)

    client.put_object.side_effect = put
    module.main(args)
    assert list(output.iterdir()) == [output / "index.coco.json"]
    result = json.loads((output / "index.coco.json").read_text())
    assert len(result["images"]) == 3
    assert all(s3_provider.objects[key] == value for key, value in originals.items())
    assert all(s3_provider.objects[key] == value for key, value in partial.items())
    for image in result["images"]:
        data = s3_provider.objects["datasets", image["file_name"]]
        assert hashlib.sha256(data).hexdigest() == image["image_sha256"]
        for source in image["sources"]:
            assert source["raw_key"] == "raw/collection/" + source["original_path"]
            assert (
                hashlib.sha256(originals["datasets", source["raw_key"]]).hexdigest()
                == source["raw_sha256"]
            )


def test_retry_when_store_ignores_create_only_condition(tmp_path, s3_provider):
    raw = tmp_path / "seed.tiff"
    Image.new("RGB", (3, 2), "red").save(raw)
    source_key = ("datasets", "raw/collection/Amaranthus albus/seed.tiff")
    s3_provider.objects[source_key] = raw.read_bytes()
    put = s3_provider.client.put_object.side_effect

    def unconditional_put(**kwargs):
        # Garage 2.3.0 ignored this header in the earlier real-store probe.
        kwargs.pop("IfNoneMatch", None)
        return put(**kwargs)

    s3_provider.client.put_object.side_effect = unconditional_put
    first = asyncio.run(
        module.prepare_s3(
            s3_provider.storage, "datasets", "raw/collection", code_revision="test"
        )
    )
    objects = dict(s3_provider.objects)
    second = asyncio.run(
        module.prepare_s3(
            s3_provider.storage, "datasets", "raw/collection", code_revision="test"
        )
    )
    assert second == first
    assert s3_provider.objects == objects
    assert len(objects) == 2


def test_changed_collection_does_not_replace_an_existing_index(
    intake, tmp_path, monkeypatch
):
    storage = collection_storage(intake[0])
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    output = tmp_path / "prepared"
    args = cli_args(output)
    module.main(args)
    labels = output / "index.coco.json"
    original_index = labels.read_bytes()
    objects = dict(storage.objects)
    key = next(key for key in objects if key.endswith("a.tiff"))
    changed = tmp_path / "changed.tiff"
    Image.new("RGB", (3, 2), "blue").save(changed)
    storage.objects[key] = changed.read_bytes()
    with pytest.raises(ValueError, match="Refusing to replace different content"):
        module.main(args)
    assert labels.read_bytes() == original_index
    assert all(
        storage.objects[key] == data
        for key, data in objects.items()
        if key.startswith("png/")
    )


@pytest.mark.parametrize(
    "prefix", ["raw", "/raw/c", "raw/c/../other", "raw\\c", "other/c"]
)
def test_cli_rejects_invalid_collection_before_creating_client(
    tmp_path, monkeypatch, prefix
):
    factory = Mock()
    monkeypatch.setattr(module, "create_storage", factory)
    with pytest.raises(SystemExit) as error:
        module.main(cli_args(tmp_path / "prepared", prefix))
    assert error.value.code == 2
    factory.assert_not_called()


@pytest.mark.parametrize(
    "code", ["AccessDenied", "NotImplemented", "ConditionalRequestConflict"]
)
def test_upload_errors_do_not_fall_back_to_overwrite(s3_provider, code):
    s3_provider.client.put_object.side_effect = ClientError(
        {"Error": {"Code": code}}, "PutObject"
    )
    with pytest.raises(BlobStorageError):
        asyncio.run(
            s3_provider.storage.upload_png("datasets", "png/detection/a.png", b"a")
        )
    s3_provider.client.put_object.assert_called_once()
    assert s3_provider.client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    s3_provider.client.get_object.assert_not_called()
