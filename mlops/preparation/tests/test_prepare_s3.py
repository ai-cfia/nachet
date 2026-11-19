import asyncio
import hashlib
import json
import logging
import sqlite3
import tomllib
from itertools import count
from pathlib import Path
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
from semver import Version

import prepare_s3 as module
import progress_logging
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


def test_warn_mode_matches_local_and_uploads_each_png_once(
    conflicting_collection, tmp_path, s3_provider, caplog
):
    root, relatives, first_split = conflicting_collection
    expected = prepare_images(
        root,
        tmp_path / "local",
        code_revision="test",
        raw_prefix="raw/collection",
        allow_conflicting_duplicates=True,
    )
    originals = {
        ("datasets", "raw/collection/" + relative): (root / relative).read_bytes()
        for relative in relatives
    }
    s3_provider.objects.update(originals)
    caplog.clear()
    caplog.set_level(logging.DEBUG, logger="prepare_s3")
    actual = asyncio.run(
        module.prepare_s3(
            s3_provider.storage,
            "datasets",
            "raw/collection",
            code_revision="test",
            allow_conflicting_duplicates=True,
        )
    )
    assert actual == expected
    assert actual["images"][0]["split"] == first_split
    assert all(s3_provider.objects[key] == data for key, data in originals.items())
    s3_provider.client.put_object.assert_called_once()
    assert [
        call.kwargs["Key"] for call in s3_provider.client.get_object.call_args_list
    ] == ["raw/collection/" + relative for relative in relatives]
    assert any(
        record.levelno == logging.WARNING
        and "Bypassing duplicate conflict" in record.message
        and all(relative in record.message for relative in relatives)
        for record in caplog.records
    )
    for number, relative in enumerate(relatives, 1):
        assert any(
            record.levelno == logging.DEBUG
            and f"Processing image {number}/2" in record.message
            and relative in record.message
            for record in caplog.records
        )
    assert any(
        record.levelno == logging.DEBUG and "Uploaded PNG" in record.message
        for record in caplog.records
    )
    assert any(
        "sources=2 unique_pngs=1 duplicate_sources=1" in message
        for message in caplog.messages
    )


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


@pytest.mark.parametrize("filename", ["seed.tiff", "seed; (1), #50%+&résumé%2F.tiff"])
def test_reads_original_key_without_custom_hash_metadata(
    s3_provider, tmp_path, filename
):
    root = tmp_path / "source"
    path = root / "Amaranthus albus" / filename
    path.parent.mkdir(parents=True)
    Image.new("RGB", (3, 2), "red").save(path)
    raw_key = "raw/collection/Amaranthus albus/" + filename
    original_bytes = path.read_bytes()
    s3_provider.objects["datasets", raw_key] = original_bytes
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
    assert image["sources"][0]["raw_key"] == raw_key
    assert image["sources"][0]["original_path"] == "Amaranthus albus/" + filename
    assert s3_provider.objects["datasets", raw_key] == original_bytes
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


def test_s3_skip_logs_truncated_source_but_not_storage_errors(intake, caplog):
    storage = collection_storage(intake[0])
    key = "raw/collection/Avena fatua/other/c.png"
    storage.objects[key] = storage.objects[key][:41]
    caplog.set_level(logging.INFO)
    result = asyncio.run(
        module.prepare_s3(
            storage,
            "datasets",
            "raw/collection",
            code_revision="test",
            skip_invalid_images=True,
        )
    )
    assert len(result["images"]) == 3
    assert storage.upload_png.call_count == 3
    skipped = result["info"]["preparation"]["skipped_images"]
    assert skipped[0]["raw_key"] == key
    assert "image file is truncated" in skipped[0]["error"]
    assert any(
        key in message and "Skipping invalid image" in message
        for message in caplog.messages
    )
    storage.read_image.side_effect = BlobNotFoundError("datasets", key)
    with pytest.raises(BlobNotFoundError):
        asyncio.run(
            module.prepare_s3(
                storage,
                "datasets",
                "raw/collection",
                code_revision="test",
                skip_invalid_images=True,
            )
        )


@pytest.mark.parametrize("corruption", ["truncated", "unidentified"])
def test_resume_relogs_skips_and_never_treats_them_as_completed(
    intake, tmp_path, monkeypatch, caplog, corruption
):
    root, _ = intake
    storage = collection_storage(root)
    key = "raw/collection/Avena fatua/other/c.png"
    storage.objects[key] = (
        storage.objects[key][:41] if corruption == "truncated" else b"not an image"
    )
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    output = tmp_path / "skips"
    args = cli_args(output) + ["--resume", "--invalid-images", "skip"]
    module.main(args)
    first = (output / "index.coco.json").read_bytes()
    skipped = json.loads(first)["info"]["preparation"]["skipped_images"]
    assert "0x" not in skipped[0]["error"]
    storage.read_image.reset_mock()
    storage.upload_png.reset_mock()
    caplog.clear()
    caplog.set_level(logging.INFO, logger=module.__name__)
    monkeypatch.setattr(progress_logging, "monotonic", count(step=300).__next__)
    module.main(args)
    storage.read_image.assert_awaited_once_with("datasets", key)
    storage.upload_png.assert_not_called()
    assert (output / "index.coco.json").read_bytes() == first
    assert any(
        "Skipping invalid image" in message and key in message
        for message in caplog.messages
    )
    assert [
        message
        for message in caplog.messages
        if message.startswith("S3 conversion progress")
    ] == [
        "S3 conversion progress: 1/4",
        "S3 conversion progress: 2/4",
        "S3 conversion progress: 3/4",
    ]
    with pytest.raises(OSError, match="c.png"):
        module.main(cli_args(tmp_path / "strict") + ["--checkpoint-dir", str(output)])
    assert not (tmp_path / "strict/index.coco.json").exists()


def test_resume_replays_conflicting_duplicates_with_the_same_policy(
    conflicting_collection, tmp_path, monkeypatch, caplog
):
    root, _, first_split = conflicting_collection
    storage = collection_storage(root)
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    output = tmp_path / "conflicts"
    args = cli_args(output) + ["--resume", "--duplicate-conflicts", "warn"]
    module.main(args)
    expected = (output / "index.coco.json").read_bytes()
    storage.read_image.reset_mock()
    storage.upload_png.reset_mock()
    caplog.clear()
    module.main(args)
    assert (output / "index.coco.json").read_bytes() == expected
    storage.read_image.assert_not_called()
    storage.upload_png.assert_not_called()
    warnings = [
        message
        for message in caplog.messages
        if "Bypassing duplicate conflict" in message
    ]
    assert len(warnings) == 1
    if first_split == "train":
        assert "incoming_split='validation'" in warnings[0]


@pytest.mark.parametrize("after_write", [False, True])
def test_resume_avoids_completed_downloads_and_preserves_duplicate_sources(
    intake, tmp_path, monkeypatch, caplog, after_write
):
    root, _ = intake
    (root / "Avena fatua/other/copy.png").write_bytes(
        (root / "Avena fatua/other/c.png").read_bytes()
    )
    storage = collection_storage(root)
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    output = tmp_path / "resumable"
    args = cli_args(output) + ["--resume"]
    upload = storage.upload_png.side_effect
    attempts = 0

    def interrupted_upload(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            if after_write:
                upload(*args, **kwargs)
            raise BlobStorageError("interrupted upload")
        return upload(*args, **kwargs)

    storage.upload_png.side_effect = interrupted_upload
    with pytest.raises(BlobStorageError, match="interrupted upload"):
        module.main(args)
    assert not (output / "index.coco.json").exists()
    first_key = storage.read_image.call_args_list[0].args[1]
    storage.read_image.reset_mock()
    storage.upload_png.reset_mock()
    storage.upload_png.side_effect = upload
    caplog.set_level(logging.DEBUG, logger="prepare_s3")
    module.main(args)
    assert first_key not in {call.args[1] for call in storage.read_image.call_args_list}
    assert storage.read_image.call_count == 4
    assert storage.upload_png.call_count == 3
    actual = json.loads((output / "index.coco.json").read_text())
    with Path(module.__file__).with_name("pyproject.toml").open("rb") as stream:
        project_version = tomllib.load(stream)["project"]["version"]
    database_path = (
        output / "preparation-checkpoints" / project_version / "preparation.sqlite3"
    )
    with sqlite3.connect(database_path) as database:
        settings = json.loads(
            database.execute(
                "SELECT value FROM metadata WHERE name='settings'"
            ).fetchone()[0]
        )
    assert settings["version"] == project_version
    expected = prepare_images(
        root, tmp_path / "expected", code_revision="test", raw_prefix="raw/collection"
    )
    for image in expected["images"]:
        for source in image["sources"]:
            source["preparation"] = {
                "project_version": str(module.project_version()),
                "code_revision": "test",
            }
    assert actual == expected
    assert any(
        record.levelno == logging.DEBUG and "Resuming completed image" in record.message
        for record in caplog.records
    )

    # A fresh workflow can read the prior run's checkpoint into its own output.
    storage.read_image.reset_mock()
    storage.upload_png.reset_mock()
    new_output = tmp_path / "new-run"
    module.main(cli_args(new_output) + ["--checkpoint-dir", str(output)])
    assert json.loads((new_output / "index.coco.json").read_text()) == expected
    storage.read_image.assert_not_called()
    storage.upload_png.assert_not_called()

    # Completed work cannot silently be reused for a different source or policy.
    for changed in [
        ["--split", "train"],
        ["--endpoint-url", "https://different.example.test"],
        ["--duplicate-conflicts", "warn"],
    ]:
        with pytest.raises(ValueError, match="Checkpoint settings"):
            module.main(args + changed)
    storage.objects["raw/collection/Avena fatua/new.png"] = b"changed listing"
    storage.list_collection_keys.return_value.append(
        "raw/collection/Avena fatua/new.png"
    )
    with pytest.raises(ValueError, match="Checkpoint settings"):
        module.main(args)
    storage.read_image.assert_not_called()


def test_compatible_upgrade_reuses_progress_and_preserves_source_provenance(
    intake, tmp_path, monkeypatch, caplog
):
    caplog.set_level(logging.INFO, logger=module.__name__)
    storage = collection_storage(intake[0])
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.0"))
    first = tmp_path / "first"
    upload = storage.upload_png.side_effect
    attempts = 0

    def interrupt_second_upload(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise BlobStorageError("interrupted upload")
        return upload(*args, **kwargs)

    storage.upload_png.side_effect = interrupt_second_upload
    with pytest.raises(BlobStorageError, match="interrupted upload"):
        module.main(cli_args(first) + ["--resume", "--code-revision", "revision-a"])
    first_key = storage.read_image.call_args_list[0].args[1]
    original_db = first / "preparation-checkpoints/0.2.0/preparation.sqlite3"
    assert original_db.exists()

    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.1"))
    storage.upload_png.side_effect = upload
    storage.read_image.reset_mock()
    resumed = tmp_path / "resumed"
    module.main(
        cli_args(resumed)
        + ["--checkpoint-dir", str(first), "--code-revision", "revision-b"]
    )
    assert first_key not in {call.args[1] for call in storage.read_image.call_args_list}
    result = json.loads((resumed / "index.coco.json").read_text())
    sources = {
        source["raw_key"]: source
        for image in result["images"]
        for source in image["sources"]
    }
    assert sources[first_key]["preparation"] == {
        "project_version": "0.2.0",
        "code_revision": "revision-a",
    }
    assert all(
        source["preparation"]
        == {"project_version": "0.2.1", "code_revision": "revision-b"}
        for key, source in sources.items()
        if key != first_key
    )
    assert "Resuming with a different code revision" in caplog.text
    newer_db = first / "preparation-checkpoints/0.2.1/preparation.sqlite3"
    with sqlite3.connect(original_db) as database:
        old_settings = json.loads(
            database.execute(
                "SELECT value FROM metadata WHERE name='settings'"
            ).fetchone()[0]
        )
        assert old_settings["version"] == "0.2.0"
        assert database.execute("SELECT COUNT(*) FROM completed").fetchone()[0] == 1
    with sqlite3.connect(newer_db) as database:
        new_settings = json.loads(
            database.execute(
                "SELECT value FROM metadata WHERE name='settings'"
            ).fetchone()[0]
        )
        assert new_settings["version"] == "0.2.1"
        assert new_settings["code_revision"] == "revision-b"


@pytest.mark.parametrize("next_version", ["0.2.0", "0.3.0"])
def test_incompatible_or_newer_preparation_checkpoint_starts_fresh(
    intake, tmp_path, monkeypatch, next_version
):
    storage = collection_storage(intake[0])
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    monkeypatch.setattr(module, "project_version", lambda: Version.parse("0.2.1"))
    first = tmp_path / "first"
    module.main(cli_args(first) + ["--resume"])
    old_db = first / "preparation-checkpoints/0.2.1/preparation.sqlite3"
    old_bytes = old_db.read_bytes()

    monkeypatch.setattr(module, "project_version", lambda: Version.parse(next_version))
    storage.read_image.reset_mock()
    module.main(cli_args(tmp_path / "next") + ["--checkpoint-dir", str(first)])
    assert storage.read_image.call_count == len(storage.objects) - 4
    assert old_db.read_bytes() == old_bytes
    assert (
        first / "preparation-checkpoints" / next_version / "preparation.sqlite3"
    ).exists()


@pytest.mark.parametrize(
    "problem", ["root-link", "version-link", "candidate-directory"]
)
def test_preparation_rejects_unsafe_checkpoint_paths(tmp_path, problem):
    root = tmp_path / module.CHECKPOINT_DIRECTORY
    settings = {"version": "0.3.1"}
    if problem == "root-link":
        actual = tmp_path / "elsewhere"
        target = actual / "0.3.1" / "preparation.sqlite3"
        target.parent.mkdir(parents=True)
        target.write_text("not a database")
        root.symlink_to(actual, target_is_directory=True)
    elif problem == "version-link":
        actual = tmp_path / "elsewhere"
        actual.mkdir()
        (actual / "preparation.sqlite3").write_text("not a database")
        root.mkdir()
        (root / "0.3.1").symlink_to(actual, target_is_directory=True)
    else:
        (root / "0.3.0" / "preparation.sqlite3").mkdir(parents=True)
    with (
        pytest.raises(
            ValueError,
            match="Checkpoint cannot be a symlink|Invalid preparation checkpoint",
        ),
        module.open_checkpoint(tmp_path, settings),
    ):
        pytest.fail("unsafe checkpoint path was accepted")


def test_legacy_preparation_checkpoint_is_not_reused_or_removed(
    intake, tmp_path, monkeypatch, caplog
):
    storage = collection_storage(intake[0])
    monkeypatch.setattr(module, "create_storage", lambda *a, **k: storage)
    output = tmp_path / "legacy"
    output.mkdir()
    legacy = output / "preparation.sqlite3"
    legacy.write_bytes(b"legacy checkpoint")
    module.main(cli_args(output) + ["--resume"])
    assert legacy.read_bytes() == b"legacy checkpoint"
    assert "Ignoring legacy integer-version checkpoint" in caplog.text
    assert storage.read_image.call_count == 4


@pytest.mark.parametrize("corrupt", [False, True])
def test_cli_writes_index_and_closes_client(
    intake, tmp_path, monkeypatch, corrupt, caplog
):
    caplog.set_level(logging.INFO)
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
        assert not any(
            "Image processing complete" in message for message in caplog.messages
        )
    else:
        module.main(args)
        result = json.loads((output / "index.coco.json").read_text())
        assert len(result["images"]) == 4
        assert list(output.iterdir()) == [output / "index.coco.json"]
    storage.close.assert_called_once()


def test_cli_can_enable_duplicate_conflict_bypass(intake, tmp_path, monkeypatch):
    root, _ = intake
    (root / "Zea mays/copy.png").write_bytes(
        (root / "Avena fatua/other/c.png").read_bytes()
    )
    storage = collection_storage(root)
    monkeypatch.setattr(module, "create_storage", lambda *args, **kwargs: storage)
    output = tmp_path / "remote"
    module.main(cli_args(output) + ["--duplicate-conflicts", "warn"])
    result = json.loads((output / "index.coco.json").read_text())
    assert len(result["images"]) == 4
    assert sum(len(image["sources"]) for image in result["images"]) == 5
    assert storage.upload_png.call_count == 4
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
