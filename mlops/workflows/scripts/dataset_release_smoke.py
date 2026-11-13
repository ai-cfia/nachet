"""Small live-service fixtures for the dataset release Argo smoke workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
from copy import deepcopy
from io import BytesIO
from uuid import UUID

from blob.exceptions import BlobNotFoundError
from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from dataset_release.contract import ImageMembership, ReleaseDefinition, sha256
from dataset_release.errors import ReleaseConflict, ReleaseNotReady
from dataset_release.reader import ReleasedDataset
from dataset_release.registry import (
    DatasetCrop,
    DatasetMembership,
    DatasetRelease,
    registry_engine,
)
from dataset_release.release import DatasetController
from dataset_release.settings import Settings
from dataset_release.storage import BlobStorageAdapter
from utility.crop import crop_image, decode_png

VERSION = "v1"
AUTHOR = "nachet-dataset-release-smoke"
BBOX = [1.25, 2.5, 4.5, 3.0]


class SmokeCheckError(RuntimeError):
    """A failed assertion whose message is safe to include in workflow logs."""


def check(condition: bool, message: str) -> None:
    """Fail a smoke assertion even when Python runs with optimization enabled."""
    if not condition:
        raise SmokeCheckError(message)


def validate_target(name: str, container: str) -> None:
    """Limit fixture writes and cleanup to workflow UUIDs and smoke containers."""
    prefix = "dataset-smoke-"
    if (
        not name.startswith(prefix)
        or str(UUID(name[len(prefix) :])) != name[len(prefix) :]
    ):
        raise ValueError("Smoke name must be dataset-smoke-<canonical workflow UUID>")
    if container != "nachet-dataset-smoke" and not container.startswith(
        "nachet-dataset-smoke-"
    ):
        raise ValueError("Use a dedicated nachet-dataset-smoke container or suffix")


def build_fixture(name: str) -> tuple[dict, list[ImageMembership], dict[str, bytes]]:
    """Build unique PNGs, full export paths, reviewed labels, and known splits."""
    from hashlib import shake_256

    images, annotations, members, blobs = [], [], [], {}
    for index, split in enumerate(("train", "validation", "test", "train"), 1):
        # Different pixels per run also make generated crop keys unique per run.
        pixels = shake_256(f"{name}/{index}".encode()).digest(12 * 10 * 3)
        output = BytesIO()
        Image.frombytes("RGB", (12, 10), pixels).save(output, format="PNG")
        data = output.getvalue()
        digest = sha256(data)
        path = f"/review/{name}/{index}/seed.png"  # Deliberately repeated basename.
        members.append(
            ImageMembership(
                file_name=path,
                sha256=digest,
                split=split,
                sources=[
                    {
                        "original_path": f"raw/{name}/{index}.tiff",
                        "specimen_group": f"{name}-{index}",
                    }
                ],
            )
        )
        images.append({"id": index, "file_name": path, "width": 12, "height": 10})
        blobs[f"png/detection/{digest}.png"] = data
        if index != 4:
            annotations.append(
                {
                    "id": index + 10,
                    "image_id": index,
                    "category_id": 42 if index == 2 else 7,
                    "bbox": BBOX,
                    "iscrowd": 0,
                    "reviewed": True,
                }
            )
    return (
        {
            "images": images,
            "annotations": annotations,
            "categories": [{"id": 42, "name": "Beta"}, {"id": 7, "name": "Alpha"}],
        },
        members,
        blobs,
    )


async def delete_blob(storage: BlobStorageAdapter, container: str, key: str) -> None:
    """Run the provider's synchronous SDK work outside the controller event loop."""
    try:
        await asyncio.to_thread(
            lambda: asyncio.run(storage.provider.delete_blob(container, key))
        )
    except BlobNotFoundError:
        pass  # Cleanup can be repeated after partial preparation or cleanup.


async def seed_fixture(controller: DatasetController, name: str) -> dict:
    """Prepare SQL-backed labels and leave a recoverable failed publication."""
    validate_target(name, controller.container)
    coco, members, blobs = build_fixture(name)
    await controller.create_release(
        ReleaseDefinition(
            name=name,
            version=VERSION,
            author=AUTHOR,
            conversion={"code_revision": "argo-smoke-v1", "settings": {"mode": "RGB"}},
            generate_crops=True,
        )
    )
    for member in members:
        await controller.catalog.add_membership(name, VERSION, member)
    for key, data in blobs.items():
        await controller.storage.upload_blob(
            controller.container, key, data, overwrite=False, content_type="image/png"
        )

    invalid = deepcopy(coco)
    invalid["images"][0]["file_name"] = "/unregistered/seed.png"
    try:
        await controller.prepare_coco(name, VERSION, invalid)
    except ValueError as error:
        check("Missing membership" in str(error), "Unexpected preparation failure")
    else:
        raise SmokeCheckError("Unregistered exported path was accepted")
    await controller.prepare_coco(name, VERSION, coco)

    # Fail with a real missing object, rather than patching a controller method.
    missing = next(reversed(blobs))
    await delete_blob(controller.storage, controller.container, missing)
    try:
        try:
            await controller.publish_release(name, VERSION)
        except BlobNotFoundError:
            pass
        else:
            raise SmokeCheckError("Publication succeeded with a missing image")
        registration = await controller.get_release_registration(name, VERSION)
        check(registration.status == "staging", "Failed publication was marked ready")
        try:
            await ReleasedDataset.open(controller, name, VERSION)
        except ReleaseNotReady:
            pass
        else:
            raise SmokeCheckError("Incomplete release was readable")
    finally:
        await controller.storage.upload_blob(
            controller.container, missing, blobs[missing], overwrite=False
        )
    return {"name": name, "version": VERSION, "status": "staging", "images": 4}


async def verify_fixture(
    controller: DatasetController, name: str, expected_hash: str
) -> dict:
    """Read pinned records, retry publication, and reject mutations and bad data."""
    validate_target(name, controller.container)
    coco, members, blobs = build_fixture(name)
    reader = await ReleasedDataset.open(controller, name, VERSION, expected_hash)
    check(reader.categories == {0: "Alpha", 1: "Beta"}, "Category order changed")
    check(len(reader.manifest.crops) == 3, "Expected three classification crops")
    check(
        [image.sources for image in reader.coco.images]
        == [member.sources for member in members],
        "Source provenance changed",
    )
    check(
        [item.model_dump(mode="json") for item in reader.coco.annotations]
        == [dict(item, area=None) for item in coco["annotations"]],
        "Reviewed annotations changed",
    )
    for split, expected_ids in (("train", [1, 4]), ("validation", [2]), ("test", [3])):
        records = [item async for item in reader.detector_records(split)]
        check([item["image_id"] for item in records] == expected_ids, "Split changed")
        for record in records:
            member = members[record["image_id"] - 1]
            expected = blobs[f"png/detection/{member.sha256}.png"]
            check(record["image"]["bytes"] == expected, "Detection PNG bytes changed")
            check((record["width"], record["height"]) == (12, 10), "Dimensions changed")
            expected_boxes = [] if record["image_id"] == 4 else [BBOX]
            check(record["objects"]["bbox"] == expected_boxes, "Reviewed boxes changed")
        crops = [item async for item in reader.classifier_records(split)]
        check(len(crops) == 1, "Classification split changed")
        crop = crops[0]
        image_id = expected_ids[0]
        check(crop["image_id"] == image_id, "Crop parent changed")
        check(crop["label"] == (1 if image_id == 2 else 0), "Crop label changed")
        source = Image.open(
            BytesIO(blobs[f"png/detection/{members[image_id - 1].sha256}.png"])
        )
        decoded = Image.open(BytesIO(crop["image"]["bytes"]))
        check(decoded.size == (5, 4), "Outward-rounded crop dimensions changed")
        check(
            decoded.tobytes() == source.crop((1, 2, 6, 6)).tobytes(),
            "Crop pixels changed",
        )

    first = reader.training_reference()
    retry = await controller.publish_release(name, VERSION)
    check(
        retry.training_reference() == reader.registration.training_reference(),
        "Retry changed identity",
    )
    spec = await controller.catalog.spec(name, VERSION)
    changed = spec.model_copy(update={"author": "changed reviewer"})
    try:
        await controller.publish_release(changed)
    except ReleaseConflict:
        pass
    else:
        raise SmokeCheckError("Changed inputs replaced an immutable release")
    images = list(reader.coco.images)
    images[1] = images[1].model_copy(
        update={
            "sources": [
                images[1]
                .sources[0]
                .model_copy(
                    update={"specimen_group": images[0].sources[0].specimen_group}
                )
            ]
        }
    )
    leaking = spec.model_copy(
        update={"coco": reader.coco.model_copy(update={"images": images})}
    )
    try:
        await controller.publish_release(leaking)
    except ValueError as error:
        check("different splits" in str(error), "Unexpected split validation failure")
    else:
        raise SmokeCheckError("Specimen leakage between splits was accepted")
    wrong_hash = "0" * 64 if expected_hash != "0" * 64 else "1" * 64
    try:
        await ReleasedDataset.open(controller, name, VERSION, wrong_hash)
    except ReleaseConflict:
        pass
    else:
        raise SmokeCheckError("Wrong manifest pin was accepted")

    key, original = next(iter(blobs.items()))
    await controller.storage.upload_blob(
        controller.container, key, b"corrupt", overwrite=True
    )
    try:
        try:
            await ReleasedDataset.open(controller, name, VERSION, expected_hash)
        except ReleaseConflict:
            pass
        else:
            raise SmokeCheckError("Corrupt image was accepted")
    finally:
        await controller.storage.upload_blob(
            controller.container, key, original, overwrite=True
        )
    await ReleasedDataset.open(controller, name, VERSION, expected_hash)
    return {
        **first,
        "checks": "readers,retry,immutability,split-leakage,manifest-pin,corruption",
    }


async def cleanup_fixture(controller: DatasetController, name: str) -> dict:
    """Delete only this UUID's fixture blobs and matching registry entities."""
    validate_target(name, controller.container)
    _, _, blobs = build_fixture(name)
    keys = set(blobs)
    for data in list(blobs.values())[:3]:
        _, crop = crop_image(decode_png(data, (12, 10)), BBOX)
        keys.add(f"png/classification/{sha256(crop)}.png")
    # Retain SQL ownership evidence until all object deletions succeed.
    async with controller.sessions() as session:
        row = await session.scalar(
            select(DatasetRelease).where(
                DatasetRelease.name == name, DatasetRelease.version == VERSION
            )
        )
        if row is not None:
            check(
                row.container == controller.container and row.author == AUTHOR,
                "Refusing to clean a release not owned by this smoke run",
            )
    for key in sorted(keys):
        await delete_blob(controller.storage, controller.container, key)
    async with controller.sessions.begin() as session:
        row = await session.scalar(
            select(DatasetRelease).where(
                DatasetRelease.name == name,
                DatasetRelease.version == VERSION,
                DatasetRelease.container == controller.container,
                DatasetRelease.author == AUTHOR,
            )
        )
        if row is not None:
            for model in (DatasetCrop, DatasetMembership):
                await session.execute(delete(model).where(model.release_id == row.id))
            await session.delete(row)
    return {"name": name, "cleaned": True}


async def run_command(args: argparse.Namespace) -> dict:
    """Use the same environment and real providers as the normal release CLI."""
    validate_target(args.name, args.container)
    settings = Settings.from_environment()
    engine = registry_engine(settings.database_url, settings.registry_schema)
    storage = None
    try:
        storage = await asyncio.to_thread(BlobStorageAdapter.from_environment)
        controller = DatasetController(
            storage, async_sessionmaker(engine), args.container
        )
        if args.action == "seed":
            return await seed_fixture(controller, args.name)
        if args.action == "verify":
            return await verify_fixture(
                controller, args.name, args.expected_manifest_sha256
            )
        return await cleanup_fixture(controller, args.name)
    finally:
        await engine.dispose()
        if storage is not None:
            storage.close()


def main() -> None:
    """Run a smoke stage without logging credentials or connection strings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--name", required=True)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("seed")
    verify = commands.add_parser("verify")
    verify.add_argument("--expected-manifest-sha256", required=True)
    commands.add_parser("cleanup")
    args = parser.parse_args()
    try:
        result = asyncio.run(run_command(args))
    except SmokeCheckError as error:
        raise SystemExit(f"Dataset smoke failed: {error}") from None
    except Exception as error:  # noqa: BLE001 - redact unexpected SDK/SQL errors
        raise SystemExit(f"Dataset smoke failed: {type(error).__name__}") from None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
