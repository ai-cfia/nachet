"""Exercise Argo fixtures with real SQL and providers, replacing SDK transports."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dataset_release.contract import ReleaseDefinition
from dataset_release.registry import (
    Base,
    DatasetCrop,
    DatasetMembership,
    DatasetRelease,
)
from dataset_release.release import DatasetController

pytest_plugins = ["mlops.datasets.tests.dataset_blob_fixtures"]

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/dataset_release_smoke.py"
SPEC = importlib.util.spec_from_file_location("dataset_release_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)

CONTAINER = "nachet-dataset-smoke"


def test_workflow_script_runs_outside_the_package_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--help"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "{seed,verify,cleanup}" in result.stdout


@pytest_asyncio.fixture
async def smoke_env(tmp_path, blob_provider):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'registry.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine)
    if blob_provider.kind == "s3":
        blob_provider.client.delete_object.side_effect = lambda *, Bucket, Key: (
            blob_provider.objects.pop((Bucket, Key), None)
        )
    else:
        get_blob_client = blob_provider.client.get_blob_client.side_effect

        def deletable_blob_client(*, container, blob):
            client = get_blob_client(container=container, blob=blob)
            client.delete_blob.side_effect = lambda **kwargs: blob_provider.objects.pop(
                (container, blob), None
            )
            return client

        blob_provider.client.get_blob_client.side_effect = deletable_blob_client
    controller = DatasetController(blob_provider.storage, sessions, CONTAINER)
    try:
        yield controller, blob_provider.objects, sessions
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_smoke_recovers_reads_rejects_bad_data_and_cleans_only_its_fixtures(
    smoke_env,
):
    controller, objects, sessions = smoke_env
    name = f"dataset-smoke-{uuid4()}"
    unrelated = ReleaseDefinition(
        name="unrelated",
        version="v1",
        author="another reviewer",
        conversion={"code_revision": "other", "settings": {}},
    )
    await controller.create_release(unrelated)
    objects[CONTAINER, "unrelated.png"] = b"keep"

    seeded = await smoke.seed_fixture(controller, name)
    assert seeded["status"] == "staging"
    published = await controller.publish_release(name, smoke.VERSION)
    saved_objects = dict(objects)
    report = await smoke.verify_fixture(controller, name, published.manifest_sha256)
    assert report["dataset_release_id"] == str(published.id)
    assert report["dataset_manifest_sha256"] == published.manifest_sha256
    assert objects == saved_objects  # Corruption checks restore the original bytes.
    assert len(objects) == 8  # Four PNGs, three crops, and the unrelated object.

    await smoke.cleanup_fixture(controller, name)
    await smoke.cleanup_fixture(controller, name)  # Exit-handler retries are harmless.
    assert objects == {(CONTAINER, "unrelated.png"): b"keep"}
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(DatasetRelease)) == 1
        )
        for model in (DatasetMembership, DatasetCrop):
            assert await session.scalar(select(func.count()).select_from(model)) == 0
    assert (
        await controller.get_release_registration("unrelated", "v1")
    ).author != smoke.AUTHOR


@pytest.mark.asyncio
async def test_cleanup_handles_partial_seed_without_labels_or_outputs(smoke_env):
    controller, objects, _ = smoke_env
    name = f"dataset-smoke-{uuid4()}"
    await controller.create_release(
        ReleaseDefinition(
            name=name,
            version=smoke.VERSION,
            author=smoke.AUTHOR,
            conversion={"code_revision": "argo-smoke-v1", "settings": {}},
        )
    )
    _, _, blobs = smoke.build_fixture(name)
    key, data = next(iter(blobs.items()))
    objects[CONTAINER, key] = data
    await smoke.cleanup_fixture(controller, name)
    assert not objects


@pytest.mark.asyncio
async def test_cleanup_refuses_another_release_owner_before_deleting_blobs(smoke_env):
    controller, objects, _ = smoke_env
    name = f"dataset-smoke-{uuid4()}"
    await controller.create_release(
        ReleaseDefinition(
            name=name,
            version=smoke.VERSION,
            author="another reviewer",
            conversion={"code_revision": "other", "settings": {}},
        )
    )
    _, _, blobs = smoke.build_fixture(name)
    objects.update({(CONTAINER, key): data for key, data in blobs.items()})
    saved = dict(objects)
    with pytest.raises(RuntimeError, match="not owned"):
        await smoke.cleanup_fixture(controller, name)
    assert objects == saved


@pytest.mark.parametrize(
    ("name", "container"),
    [
        ("real-release", CONTAINER),
        ("dataset-smoke-not-a-uuid", CONTAINER),
        (f"dataset-smoke-{uuid4()}", "training-datasets"),
        (f"dataset-smoke-{uuid4()}", "nachet-dataset-smokeproduction"),
    ],
)
def test_smoke_target_rejects_non_fixture_names_and_buckets(name, container):
    with pytest.raises(ValueError):
        smoke.validate_target(name, container)


def test_fixture_identity_is_recoverable_but_unique_per_workflow():
    name = f"dataset-smoke-{uuid4()}"
    smoke.validate_target(name, CONTAINER)
    smoke.validate_target(name, f"{CONTAINER}-ceph")
    assert smoke.build_fixture(name) == smoke.build_fixture(name)
    first = smoke.build_fixture(name)[2]
    second = smoke.build_fixture(f"dataset-smoke-{uuid4()}")[2]
    assert first.keys().isdisjoint(second)
