"""Release publication, recovery, integrity and real detector-loader contracts."""

import asyncio
import importlib.util
import json
import os
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
import pytest_asyncio
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from PIL import Image
from sqlalchemy import MetaData, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.blob.exceptions import BlobAlreadyExistsError, BlobNotFoundError
from app.blob.interface import BlobStorageInterface
from app.datasets.contract import ReleaseSpec, canonical_json, sha256
from app.datasets.reader import ReleasedDataset
from app.datasets.release import DatasetController, ReleaseConflict, ReleaseNotReady
from app.db.model import DatasetRelease


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


# Only upload/download are exercised by the controller; register this small
# test double with the ABC so the application's runtime type checks still run.
BlobStorageInterface.register(MemoryStorage)


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
    migration = (
        Path(__file__).parents[1]
        / "app/db/alembic/versions/2026_10_22_0000-a895d501ea01_add_dataset_releases.py"
    )
    spec = importlib.util.spec_from_file_location(
        "dataset_release_migration", migration
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'migration.sqlite'}")

    def check(connection):
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.upgrade()
        metadata = MetaData()
        DatasetRelease.__table__.to_metadata(metadata)
        assert compare_metadata(context, metadata) == []
        with Operations.context(context):
            module.downgrade()
        assert compare_metadata(context, MetaData()) == []

    try:
        async with engine.begin() as connection:
            await connection.run_sync(check)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_s3_non_overwriting_upload_uses_atomic_condition(monkeypatch):
    from botocore.exceptions import ClientError

    from app.blob.s3.operations import blob_operations

    monkeypatch.setattr(blob_operations, "_logger", Mock())
    client = Mock()
    client.put_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed"}}, "PutObject"
    )
    operations = blob_operations.BlobOperations(client)
    with pytest.raises(BlobAlreadyExistsError):
        await operations.upload_blob(
            "datasets", "releases/a/v1/coco.json", b"{}", overwrite=False
        )
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    client.head_object.assert_not_called()


@pytest.mark.asyncio
async def test_s3_successful_upload_preserves_overwrite_behavior(monkeypatch):
    from datetime import UTC, datetime

    from app.blob.s3.operations import blob_operations

    monkeypatch.setattr(blob_operations, "_logger", Mock())
    client = Mock()
    client.meta.endpoint_url = "https://s3.example.test"
    client.put_object.return_value = {"ETag": '"etag"'}
    client.head_object.return_value = {
        "LastModified": datetime.now(UTC),
        "ContentLength": 2,
    }
    operations = blob_operations.BlobOperations(client)
    result = await operations.upload_blob(
        "datasets", "file.json", b"{}", overwrite=False
    )
    assert result["size"] == 2
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    await operations.upload_blob("datasets", "file.json", b"{}", overwrite=True)
    assert "IfNoneMatch" not in client.put_object.call_args.kwargs
