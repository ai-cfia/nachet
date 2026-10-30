"""Release publication, recovery, integrity and real detector-loader contracts."""

import asyncio
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, date, datetime
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from mlops_blob import create_blob_storage_client
from mlops_blob.exceptions import BlobAlreadyExistsError, BlobNotFoundError
from PIL import Image
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dataset_release import cli
from dataset_release.contract import (
    DatasetDescription,
    ReleaseMetadata,
    ReleaseSpec,
    canonical_json,
    sha256,
)
from dataset_release.reader import ReleasedDataset
from dataset_release.registry import DatasetRelease
from dataset_release.release import DatasetController, ReleaseConflict, ReleaseNotReady
from dataset_release.settings import Settings
from dataset_release.storage import BlobStorageAdapter


def s3_storage(client):
    """Use the copied factory and provider, replacing only its SDK transport."""
    with patch("mlops_blob.s3.storage.create_s3_client", return_value=client):
        return BlobStorageAdapter(create_blob_storage_client("s3", {}))


class MemoryStorage:
    """Atomic in-memory object-store boundary, including fault injection."""

    def __init__(self):
        self.objects = {}
        self.fail_on = None
        self.reads = []

    async def upload_blob(self, container, name, data, **kwargs):
        if self.fail_on and name.endswith(self.fail_on):
            raise OSError("Simulated interrupted upload")
        if (container, name) in self.objects and not kwargs.get("overwrite", True):
            raise BlobAlreadyExistsError(container, name)
        self.objects[container, name] = data
        return {}

    async def download_blob(self, container, name, **kwargs):
        self.reads.append(name)
        try:
            return self.objects[container, name]
        except KeyError as error:
            raise BlobNotFoundError(container, name) from error


def png_bytes(color):
    output = BytesIO()
    Image.new("RGB", (12, 10), color).save(output, format="PNG")
    return output.getvalue()


def specification(storage, version="v1", crops=True):
    images = []
    annotations = []
    for index, (color, split) in enumerate(
        (("red", "train"), ("green", "validation"), ("blue", "test")), 1
    ):
        data = png_bytes(color)
        key = f"png/detection/{sha256(data)}.png"
        storage.objects["datasets", key] = data
        images.append(
            {
                "id": index,
                "file_name": key,
                "width": 12,
                "height": 10,
                "split": split,
                "sources": [
                    {
                        "original_path": f"share/batch{index}/tray{index}/seed.tiff",
                        "species": "Avena",
                        "batch": str(index),
                        "tray": str(index),
                        "specimen_group": f"specimen-{index}",
                    }
                ],
            }
        )
        annotations.append(
            {
                "id": index + 10,
                "image_id": index,
                "category_id": 7,
                "bbox": [1.25, 2.5, 4.5, 3.0],
                "iscrowd": 0,
            }
        )
    return ReleaseSpec.model_validate(
        {
            "name": "reviewed-seeds",
            "version": version,
            "author": "reviewer",
            "conversion": {
                "code_revision": "png-converter-abc123",
                "settings": {"mode": "RGB"},
            },
            "generate_crops": crops,
            "coco": {
                "images": images,
                "annotations": annotations,
                "categories": [{"id": 7, "name": "Avena"}],
                "info": {"description": "Reviewed in FiftyOne"},
            },
        }
    )


@pytest_asyncio.fixture
async def release_env(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'releases.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: DatasetRelease.__table__.create(sync))
    sessions = async_sessionmaker(engine)
    storage = MemoryStorage()
    controller = DatasetController(storage, sessions, "datasets")
    try:
        yield controller, storage, sessions
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_release_uses_copied_blob_provider_for_publication_and_reads(
    release_env, blob_provider
):
    _, original_storage, sessions = release_env
    spec = specification(original_storage)
    blob_provider.objects.update(original_storage.objects)
    controller = DatasetController(blob_provider.storage, sessions, "datasets")
    # Interrupt after writing the manifest but before marking the row ready.
    # The retry must reuse existing crops/COCO/manifest via the common conflicts.
    with patch.object(controller, "_validate", side_effect=OSError("Interrupted")):
        with pytest.raises(OSError, match="Interrupted"):
            await controller.publish(spec)
    assert (await controller.registration(spec.name, spec.version)).status == "staging"
    interrupted_objects = dict(blob_provider.objects)
    first = await controller.publish(spec)
    assert first.status == "ready"
    assert blob_provider.objects == interrupted_objects
    saved_objects = dict(blob_provider.objects)
    assert await controller.publish(spec) == first
    assert blob_provider.objects == saved_objects

    reader = await ReleasedDataset.open(
        controller, spec.name, spec.version, first.manifest_sha256
    )
    assert len(reader.manifest.crops) == 3
    records = [record async for record in reader.detector_records("train")]
    crops = [record async for record in reader.classifier_records("train")]
    assert records[0]["image_id"] == crops[0]["image_id"] == 1
    assert (
        records[0]["image"]["bytes"]
        == saved_objects["datasets", spec.coco.images[0].file_name]
    )
    changed = specification(original_storage).model_copy(
        update={"author": "another reviewer"}
    )
    with pytest.raises(ReleaseConflict):
        await controller.publish(changed)
    assert blob_provider.objects == saved_objects


@pytest.mark.asyncio
async def test_publish_retry_corrected_version_and_s3_readers(release_env):
    controller, storage, sessions = release_env
    spec = specification(storage)
    first = await controller.publish(spec)
    saved_objects = dict(storage.objects)
    again = await controller.publish(spec)
    assert again == first
    assert storage.objects == saved_objects
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(DatasetRelease)) == 1
        )

    reader = await ReleasedDataset.open(
        controller, spec.name, spec.version, first.manifest_sha256
    )
    assert reader.coco.model_dump(mode="json") == spec.coco.model_dump(mode="json")
    assert len(reader.manifest.crops) == 3
    detector = [item async for item in reader.detector_records("validation")]
    classifier = [item async for item in reader.classifier_records("validation")]
    assert len(detector) == len(classifier) == 1
    assert detector[0]["objects"]["bbox"] == [[1.25, 2.5, 4.5, 3.0]]
    assert detector[0]["objects"]["category"] == [0]
    assert classifier[0]["image_id"] == detector[0]["image_id"] == 2
    assert classifier[0]["annotation_id"] == 12
    with Image.open(BytesIO(classifier[0]["image"]["bytes"])) as crop:
        assert crop.size == (5, 4)
    reference = reader.training_reference({"max_train_samples": 32})
    assert reference["model_dataset"] == f"{first.id}@sha256:{first.manifest_sha256}"
    assert json.loads(reference["dataset_run_settings"]) == {"max_train_samples": 32}

    corrected = spec.model_dump(mode="json")
    corrected["coco"]["annotations"][0]["bbox"] = [0.5, 1.5, 6.0, 5.0]
    with pytest.raises(ReleaseConflict):
        await controller.publish(ReleaseSpec.model_validate(corrected))
    corrected["version"] = "v2"
    second = await controller.publish(ReleaseSpec.model_validate(corrected))
    assert second.id != first.id
    assert all(storage.objects[key] == value for key, value in saved_objects.items())
    old = await ReleasedDataset.open(controller, spec.name, "v1", first.manifest_sha256)
    assert old.coco.annotations[0].bbox == [1.25, 2.5, 4.5, 3.0]
    with pytest.raises(ReleaseConflict, match="Pinned"):
        await controller.resolve(spec.name, "v2", first.manifest_sha256)


@pytest.mark.asyncio
async def test_metadata_survives_publication_registry_reader_and_inspect(
    release_env, monkeypatch
):
    controller, storage, sessions = release_env
    payload = specification(storage, crops=False).model_dump(mode="json")
    payload.update(
        description="Reviewed seeds from the autumn collection.\nIncludes negatives.",
        dataset_cutoff_date="2026-10-22",
        previous_version="releases/reviewed-seeds/v0/release.json",
    )
    # One image with two objects, one with one object, and one negative image.
    payload["coco"]["annotations"][1]["image_id"] = 1
    payload["coco"]["categories"].append({"id": 8, "name": "Unused category"})
    spec = ReleaseSpec.model_validate(payload)
    registration = await controller.publish(spec)
    expected = {
        "description": payload["description"],
        "dataset_cutoff_date": "2026-10-22",
        "previous_version": payload["previous_version"],
        "has_bounding_boxes": True,
        "has_classes": True,
        "num_classes": 2,
        "num_multi_object_images": 1,
        "num_single_object_images": 1,
    }
    assert registration.metadata().model_dump(mode="json") == expected
    assert registration.dataset_cutoff_date == date(2026, 10, 22)
    async with sessions() as session:
        row = await session.get(DatasetRelease, registration.id)
        assert (
            ReleaseMetadata.model_validate(row, from_attributes=True).model_dump(
                mode="json"
            )
            == expected
        )
    reader = await ReleasedDataset.open(controller, spec.name, spec.version)
    for field, value in expected.items():
        assert reader.manifest.model_dump(mode="json")[field] == value
    assert await controller.publish(spec) == registration

    monkeypatch.setenv("DATASET_DATABASE_URL", str(sessions.kw["bind"].url))
    monkeypatch.setattr(BlobStorageAdapter, "from_environment", lambda: storage)
    storage.close = Mock()
    result = await cli.execute(
        cli.parse_args(["--container", "datasets", "inspect", spec.name, spec.version])
    )
    assert {field: result[field] for field in expected} == expected
    storage.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", "Changed dataset purpose"),
        ("dataset_cutoff_date", "2026-10-23"),
        ("previous_version", "https://example.org/datasets/v0"),
    ],
)
async def test_metadata_changes_require_a_new_version(release_env, field, value):
    controller, storage, _ = release_env
    spec = specification(storage)
    await controller.publish(spec)
    changed = spec.model_dump(mode="json")
    changed[field] = value
    with pytest.raises(ReleaseConflict, match="different inputs"):
        await controller.publish(ReleaseSpec.model_validate(changed))


@pytest.mark.asyncio
async def test_recorded_statistics_must_match_coco(release_env):
    controller, storage, _ = release_env
    spec = specification(storage)
    await controller.publish(spec)
    _, manifest, coco = await controller.resolve(spec.name, spec.version)
    for field, value in ReleaseMetadata.statistics(coco).items():
        incorrect = int(value) + 1
        if isinstance(value, bool):
            incorrect = not value
        with pytest.raises(ValueError, match=f"Manifest {field} differs"):
            await controller._validate(
                manifest.model_copy(update={field: incorrect}), coco
            )


@pytest.mark.parametrize("value", ["2026-02-30", "not-a-date", "2026-10-22T12:30:00"])
def test_invalid_dataset_cutoff_date_is_rejected(value):
    payload = specification(MemoryStorage()).model_dump(mode="json")
    payload["dataset_cutoff_date"] = value
    with pytest.raises(ValueError):
        ReleaseSpec.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("num_classes", -1),
        ("num_classes", True),
        ("num_multi_object_images", -1),
        ("num_single_object_images", 1.5),
        ("has_classes", "true"),
        ("has_bounding_boxes", 1),
    ],
)
def test_invalid_metadata_types_and_counts_are_rejected(field, value):
    with pytest.raises(ValueError):
        ReleaseMetadata.model_validate({field: value})


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["ready", "staging"])
async def test_legacy_releases_keep_hashes_and_remain_retryable(release_env, status):
    controller, storage, sessions = release_env
    spec = specification(storage)
    registration = await controller.publish(spec)
    key = ("datasets", registration.manifest_key)
    # Recreate a manifest and registration from before metadata was introduced.
    legacy_manifest = json.loads(storage.objects[key])
    for field in ReleaseMetadata.model_fields:
        legacy_manifest.pop(field, None)
    legacy_bytes = canonical_json(legacy_manifest)
    storage.objects[key] = legacy_bytes
    legacy_spec = spec.model_dump(
        mode="json", exclude=set(DatasetDescription.model_fields)
    )
    assert registration.request_sha256 == sha256(
        canonical_json(
            {"spec": legacy_spec, "crop_recipe": legacy_manifest["crop_recipe"]}
        )
    )
    async with sessions.begin() as session:
        row = await session.get(DatasetRelease, registration.id)
        for field in ReleaseMetadata.model_fields:
            setattr(row, field, None)
        row.status = status
        row.manifest_sha256 = sha256(legacy_bytes) if status == "ready" else None
    saved_objects = dict(storage.objects)
    result = await controller.publish(spec)
    assert result.status == "ready"
    assert result.manifest_sha256 == sha256(legacy_bytes)
    assert storage.objects == saved_objects
    _, manifest, _ = await controller.resolve(spec.name, spec.version)
    assert all(
        getattr(manifest, field) is None for field in ReleaseMetadata.model_fields
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["coco.json", "release.json"])
async def test_interrupted_publication_is_unselectable_and_retryable(
    release_env, failure
):
    controller, storage, sessions = release_env
    spec = specification(storage)
    storage.fail_on = failure
    with pytest.raises(OSError):
        await controller.publish(spec)
    with pytest.raises(ReleaseNotReady):
        await controller.resolve(spec.name, spec.version)
    storage.fail_on = None
    ready = await controller.publish(spec)
    assert ready.status == "ready"
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(DatasetRelease)) == 1
        )


@pytest.mark.asyncio
async def test_concurrent_identical_publishers_share_one_registration(release_env):
    controller, storage, sessions = release_env
    spec = specification(storage)
    results = await asyncio.gather(controller.publish(spec), controller.publish(spec))
    assert results[0] == results[1]
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(DatasetRelease)) == 1
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["parent", "crop", "coco", "manifest"])
async def test_corruption_and_missing_referenced_files_fail(release_env, target):
    controller, storage, _ = release_env
    spec = specification(storage)
    registration = await controller.publish(spec)
    _, manifest, _ = await controller.resolve(spec.name, spec.version)
    key = {
        "parent": spec.coco.images[0].file_name,
        "crop": manifest.crops[0].file.key,
        "coco": manifest.coco.key,
        "manifest": registration.manifest_key,
    }[target]
    original = storage.objects["datasets", key]
    storage.objects["datasets", key] = b"corrupted"
    with pytest.raises(ReleaseConflict):
        await controller.resolve(spec.name, spec.version)
    storage.objects["datasets", key] = original
    del storage.objects["datasets", key]
    with pytest.raises(BlobNotFoundError):
        await controller.resolve(spec.name, spec.version)


@pytest.mark.asyncio
async def test_missing_parent_and_existing_conflicting_object_fail(release_env):
    controller, storage, _ = release_env
    spec = specification(storage)
    parent = storage.objects.pop(("datasets", spec.coco.images[0].file_name))
    with pytest.raises(BlobNotFoundError):
        await controller.publish(spec)
    storage.objects["datasets", spec.coco.images[0].file_name] = parent
    storage.objects["datasets", f"releases/{spec.name}/{spec.version}/coco.json"] = (
        b"other"
    )
    with pytest.raises(ReleaseConflict):
        await controller.publish(spec)
    with pytest.raises(ReleaseNotReady):
        await controller.resolve(spec.name, spec.version)


@pytest.mark.asyncio
async def test_detection_only_release_and_negative_images_are_preserved(release_env):
    controller, storage, _ = release_env
    spec = specification(storage, crops=False).model_dump(mode="json")
    spec["coco"]["annotations"] = []
    spec = ReleaseSpec.model_validate(spec)
    await controller.publish(spec)
    reader = await ReleasedDataset.open(controller, spec.name, spec.version)
    samples = [sample async for sample in reader.detector_records("train")]
    assert len(samples) == 1
    assert samples[0]["objects"]["bbox"] == []
    assert reader.manifest.has_bounding_boxes is False
    assert reader.manifest.has_classes is True
    assert reader.manifest.num_classes == 1
    assert reader.manifest.num_single_object_images == 0
    assert reader.manifest.num_multi_object_images == 0
    with pytest.raises(ReleaseNotReady, match="classifier-ready"):
        _ = [sample async for sample in reader.classifier_records("train")]


@pytest.mark.asyncio
async def test_duplicate_bytes_keep_separate_provenance(release_env):
    controller, storage, _ = release_env
    spec = specification(storage).model_dump(mode="json")
    image = deepcopy(spec["coco"]["images"][0])
    image["id"] = 4
    image["sources"][0]["original_path"] = "other-share/same-image.tiff"
    spec["coco"]["images"].append(image)
    spec = ReleaseSpec.model_validate(spec)
    await controller.publish(spec)
    _, manifest, coco = await controller.resolve(spec.name, spec.version)
    assert len(manifest.images) == 3
    assert len(coco.images) == 4
    assert manifest.num_single_object_images == 3
    assert manifest.num_multi_object_images == 0
    assert coco.images[-1].sources[0].original_path == "other-share/same-image.tiff"


@pytest.mark.parametrize(
    "change",
    [
        "unsafe_path",
        "duplicate_id",
        "unknown_image",
        "unknown_category",
        "outside_box",
        "negative_box",
        "nan_box",
        "duplicate_split",
        "specimen_split",
        "unknown_field",
        "boolean_box",
        "invalid_area",
    ],
)
def test_invalid_specs_fail_before_publication(change):
    spec = specification(MemoryStorage()).model_dump(mode="json")
    image = spec["coco"]["images"][0]
    annotation = spec["coco"]["annotations"][0]
    if change == "unsafe_path":
        image["file_name"] = "../credentials.png"
    elif change == "duplicate_id":
        spec["coco"]["images"][1]["id"] = image["id"]
    elif change == "unknown_image":
        annotation["image_id"] = 400
    elif change == "unknown_category":
        annotation["category_id"] = 400
    elif change == "outside_box":
        annotation["bbox"] = [1, 1, 400, 400]
    elif change == "negative_box":
        annotation["bbox"] = [-1, 1, 3, 3]
    elif change == "nan_box":
        annotation["bbox"][0] = float("nan")
    elif change == "duplicate_split":
        spec["coco"]["images"][1]["file_name"] = image["file_name"]
    elif change == "specimen_split":
        spec["coco"]["images"][1]["sources"] = image["sources"]
    elif change == "unknown_field":
        spec["unrecognized_setting"] = True
    elif change == "boolean_box":
        annotation["bbox"][0] = True
    elif change == "invalid_area":
        annotation["area"] = float("inf")
    with pytest.raises(ValueError):
        ReleaseSpec.model_validate(spec)


@pytest.mark.asyncio
async def test_current_detector_loader_matches_released_records(release_env, tmp_path):
    """Use the exact loader imported by the user's unchanged detector script."""
    repo = os.environ.get("NACHET_MODEL_CCDS")
    if not repo:
        pytest.skip(
            "Set NACHET_MODEL_CCDS to run the existing detector-loader contract"
        )
    module_path = Path(repo) / "nachetmodel" / "coco_to_hf_dataset.py"
    module_spec = importlib.util.spec_from_file_location(
        "existing_detector_loader", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    from datasets import Dataset
    from datasets import Image as HFImage

    controller, storage, _ = release_env
    spec = specification(storage)
    await controller.publish(spec)
    reader = await ReleasedDataset.open(controller, spec.name, spec.version)
    # Exercise all saved splits independently; the existing loader is told not
    # to resplit them. These local fixtures are solely compatibility-test inputs.
    for split in ("train", "validation", "test"):
        records = [record async for record in reader.detector_records(split)]
        subset = spec.coco.model_dump(mode="json")
        subset["images"] = [
            image for image in subset["images"] if image["split"] == split
        ]
        image_ids = {image["id"] for image in subset["images"]}
        subset["annotations"] = [
            a for a in subset["annotations"] if a["image_id"] in image_ids
        ]
        for image in subset["images"]:
            path = tmp_path / image["file_name"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(storage.objects["datasets", image["file_name"]])
        coco_path = tmp_path / f"{split}.json"
        coco_path.write_bytes(canonical_json(subset))
        existing, categories = module.load_coco_as_hf_dataset(
            str(tmp_path), str(coco_path), train_val_split=0.0
        )
        released = Dataset.from_list(records).cast_column("image", HFImage())
        assert categories == reader.categories
        assert len(existing["train"]) == len(released)
        assert existing["train"][0]["objects"] == released[0]["objects"]
        assert existing["train"][0]["image"].tobytes() == released[0]["image"].tobytes()


@pytest.mark.asyncio
async def test_migration_matches_orm_and_downgrades(tmp_path):
    migrations = []
    for filename in (
        "a895d501ea01_dataset_releases.py",
        "b72e15c4d901_dataset_metadata.py",
    ):
        migration = Path(__file__).parents[1] / "migrations/versions" / filename
        spec = importlib.util.spec_from_file_location(filename, migration)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migrations.append(module)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'migration.sqlite'}")

    def check(connection):
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migrations[0].upgrade()
            old_table = Table("dataset_release", MetaData(), autoload_with=connection)
            release_id = uuid4()
            connection.execute(
                old_table.insert().values(
                    id=release_id.hex,
                    name="existing",
                    version="v1",
                    author="reviewer",
                    date_created=datetime.now(UTC),
                    container="datasets",
                    request_sha256="a" * 64,
                    manifest_key="releases/existing/v1/release.json",
                    manifest_sha256="b" * 64,
                    status="ready",
                )
            )
            migrations[1].upgrade()
        metadata = MetaData()
        DatasetRelease.__table__.to_metadata(metadata)
        assert compare_metadata(context, metadata) == []
        row = connection.execute(select(DatasetRelease.__table__)).mappings().one()
        assert row["id"] == release_id
        assert row["manifest_sha256"] == "b" * 64
        assert all(row[field] is None for field in ReleaseMetadata.model_fields)
        with Operations.context(context):
            migrations[1].downgrade()
        restored = Table("dataset_release", MetaData(), autoload_with=connection)
        assert connection.execute(select(restored.c.id)).scalar_one() == release_id.hex
        with Operations.context(context):
            migrations[0].downgrade()
        assert compare_metadata(context, MetaData()) == []

    try:
        async with engine.begin() as connection:
            await connection.run_sync(check)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_s3_non_overwriting_upload_uses_atomic_condition():
    from botocore.exceptions import ClientError

    client = Mock()
    client.put_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed"}}, "PutObject"
    )
    operations = s3_storage(client)
    with pytest.raises(BlobAlreadyExistsError):
        await operations.upload_blob(
            "datasets", "releases/a/v1/coco.json", b"{}", overwrite=False
        )
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    client.head_object.assert_not_called()


@pytest.mark.asyncio
async def test_s3_successful_upload_preserves_overwrite_behavior():
    from datetime import UTC, datetime

    client = Mock()
    client.meta.endpoint_url = "https://s3.example.test"
    client.put_object.return_value = {"ETag": '"etag"'}
    client.head_object.return_value = {
        "LastModified": datetime.now(UTC),
        "ContentLength": 2,
    }
    operations = s3_storage(client)
    result = await operations.upload_blob(
        "datasets", "file.json", b"{}", overwrite=False
    )
    assert result["size"] == 2
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    await operations.upload_blob("datasets", "file.json", b"{}", overwrite=True)
    assert "IfNoneMatch" not in client.put_object.call_args.kwargs


@pytest.mark.asyncio
async def test_s3_download_closes_stream_and_translates_missing_object():
    from botocore.exceptions import ClientError

    client = Mock()
    stream = BytesIO(b"image-bytes")
    client.get_object.return_value = {"Body": stream}
    storage = s3_storage(client)
    assert await storage.download_blob("datasets", "image.png") == b"image-bytes"
    assert stream.closed
    client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )
    with pytest.raises(BlobNotFoundError):
        await storage.download_blob("datasets", "missing.png")


def test_standalone_migration_and_imports_do_not_use_backend(tmp_path, monkeypatch):
    project = Path(__file__).parents[1]
    registry_path = tmp_path / "standalone.sqlite"
    monkeypatch.setenv("DATASET_DATABASE_URL", f"sqlite+aiosqlite:///{registry_path}")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    with sqlite3.connect(registry_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            )
        }
        assert tables == {"dataset_release", "dataset_release_version"}
        assert connection.execute(
            "select version_num from dataset_release_version"
        ).fetchone() == ("b72e15c4d901",)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import dataset_release.cli, dataset_release.reader; assert not any(name == 'app' or name.startswith('app.') for name in sys.modules)",
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_postgresql_migration_targets_only_mlops_schema(monkeypatch):
    monkeypatch.setenv(
        "DATASET_DATABASE_URL", "postgresql+psycopg://example@localhost/datasets"
    )
    monkeypatch.delenv("DATASET_REGISTRY_SCHEMA", raising=False)
    output = StringIO()
    config = Config(
        str(Path(__file__).parents[1] / "alembic.ini"), output_buffer=output
    )
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE nachet_datasets.dataset_release (" in sql
    assert "CREATE TABLE nachet_datasets.dataset_release_version (" in sql
    assert (
        "ALTER TABLE nachet_datasets.dataset_release ADD COLUMN description TEXT" in sql
    )
    assert "ADD COLUMN dataset_cutoff_date DATE" in sql
    assert "ADD COLUMN has_bounding_boxes BOOLEAN" in sql
    assert "alembic_version" not in sql


def test_registry_configuration_is_explicit(monkeypatch):
    monkeypatch.delenv("DATASET_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATASET_DATABASE_URL"):
        Settings.from_environment()
    monkeypatch.setenv(
        "DATASET_DATABASE_URL", "postgresql+psycopg://example@localhost/datasets"
    )
    monkeypatch.setenv("DATASET_REGISTRY_SCHEMA", "nachet_datasets")
    assert Settings.from_environment().registry_schema == "nachet_datasets"
    monkeypatch.setenv("DATASET_REGISTRY_SCHEMA", "bad;schema")
    with pytest.raises(ValueError, match="schema name"):
        Settings.from_environment()


def test_s3_configuration_preserves_standard_region_and_credential_chain(monkeypatch):
    from mlops_blob.s3 import client as s3_client

    for name in (
        "S3_REGION_NAME",
        "AWS_REGION",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_ENDPOINT_URL",
        "S3_USE_SSL",
        "S3_VERIFY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "garage")
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "http://object-store:3900")
    client = Mock()
    monkeypatch.setenv("DATASET_BLOB_PROVIDER", "s3")
    monkeypatch.setattr(s3_client.boto3, "client", client)
    storage = BlobStorageAdapter.from_environment()
    assert client.call_args.kwargs["region_name"] == "garage"
    assert client.call_args.kwargs["use_ssl"] is False
    assert "aws_access_key_id" not in client.call_args.kwargs
    client.return_value.list_buckets.assert_not_called()
    storage.close()
    client.return_value.close.assert_called_once()
