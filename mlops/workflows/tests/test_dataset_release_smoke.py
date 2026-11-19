"""Exercise Argo fixtures with real SQL and providers, replacing SDK transports."""

import importlib.util
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, call
from uuid import uuid4

import pytest
import pytest_asyncio
from blob.exceptions import PermissionError as BlobPermissionError
from botocore.exceptions import ClientError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from dataset_release.contract import ReleaseDefinition
from dataset_release.registry import (
    Base,
    DatasetCrop,
    DatasetMembership,
    DatasetRelease,
)
from dataset_release.release import DatasetController
from dataset_release.storage import BlobStorageAdapter

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
async def test_shared_bucket_smoke_leaves_production_and_other_runs_untouched(
    smoke_env, blob_provider, monkeypatch
):
    controller, objects, sessions = smoke_env
    bucket = "vault-smoke-fixtures"
    monkeypatch.setenv("DATASET_SMOKE_ROOT", f"{bucket}/smoke")
    workflow_uid = uuid4()
    name = f"dataset-smoke-{workflow_uid}"
    monkeypatch.setenv("DATASET_DATABASE_URL", str(sessions.kw["bind"].url))
    monkeypatch.setenv("DATASET_BLOB_PROVIDER", "s3")
    monkeypatch.setenv("DATASET_SMOKE_RUN_ID", str(workflow_uid))
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)
    monkeypatch.setattr(
        "dataset_release.storage.create_dataset_blob_storage_client",
        lambda *args: controller.storage.provider,
    )
    unrelated = {
        (bucket, "png/detection/production.png"): b"production",
        (bucket, f"smoke/{uuid4()}/fixture.png"): b"other run",
    }
    objects.update(unrelated)
    if blob_provider.kind == "s3":
        client = blob_provider.client
        get_object = client.get_object.side_effect

        def denied_missing_read(*, Bucket, Key):
            if (Bucket, Key) not in objects:
                raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
            return get_object(Bucket=Bucket, Key=Key)

        def list_objects(*, Bucket, Prefix, MaxKeys):
            matches = sum(
                container == Bucket and key.startswith(Prefix)
                for container, key in objects
            )
            return {"KeyCount": min(MaxKeys, matches)}

        client.get_object.side_effect = denied_missing_read
        client.list_objects_v2.side_effect = list_objects

    seeded = await smoke.run_command(Namespace(container="", name=name, action="seed"))
    assert seeded["container"] == bucket
    release_storage = BlobStorageAdapter.from_environment()
    release = DatasetController(release_storage, sessions, seeded["container"])
    try:
        published = await release.publish_release(name, smoke.VERSION)
    finally:
        release_storage.close()
    await smoke.run_command(
        Namespace(
            container=bucket,
            name=name,
            action="verify",
            expected_manifest_sha256=published.manifest_sha256,
        )
    )
    run_keys = objects.keys() - unrelated.keys()
    assert len(run_keys) == 7
    assert all(
        container == bucket and key.startswith(f"smoke/{workflow_uid}/")
        for container, key in run_keys
    )
    assert all(objects[key] == data for key, data in unrelated.items())

    monkeypatch.delenv("DATASET_SMOKE_RUN_ID")
    await smoke.run_command(Namespace(container="", name=name, action="cleanup"))
    await smoke.run_command(Namespace(container="", name=name, action="cleanup"))
    assert objects == unrelated
    if blob_provider.kind == "s3":
        missing = next(reversed(smoke.build_fixture(name)[2]))
        client.list_objects_v2.assert_called_once_with(
            Bucket=bucket, Prefix=f"smoke/{workflow_uid}/{missing}", MaxKeys=1
        )
        client.head_bucket.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("blob_provider", ["s3"], indirect=True)
async def test_seed_propagates_read_denial_for_a_different_fixture(
    smoke_env, blob_provider
):
    controller, _, _ = smoke_env
    client = blob_provider.client
    client.get_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "GetObject"
    )
    with pytest.raises(BlobPermissionError):
        await smoke.seed_fixture(controller, f"dataset-smoke-{uuid4()}")
    client.list_objects_v2.assert_not_called()


@pytest.mark.asyncio
async def test_shared_bucket_seed_rejects_a_template_without_the_run_id(monkeypatch):
    monkeypatch.delenv("DATASET_SMOKE_RUN_ID", raising=False)
    monkeypatch.setenv("DATASET_SMOKE_ROOT", "vault-smoke-fixtures/smoke")
    with pytest.raises(RuntimeError, match="updated workflow template"):
        await smoke.run_command(
            Namespace(
                container="",
                name=f"dataset-smoke-{uuid4()}",
                action="seed",
            )
        )


@pytest.mark.parametrize("root", ["", "vault-fixtures", "vault-fixtures/production"])
def test_smoke_requires_the_smoke_root_prefix(monkeypatch, root):
    monkeypatch.setenv("DATASET_SMOKE_ROOT", root)
    with pytest.raises(ValueError, match="<bucket>/smoke"):
        smoke.validate_target(f"dataset-smoke-{uuid4()}", "")


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


@pytest.mark.asyncio
async def test_postgres_smoke_migrates_and_cleans_only_the_uuid_schema(monkeypatch):
    database_url = "postgresql+psycopg://test@localhost/mlops-test"
    monkeypatch.setenv("DATASET_DATABASE_URL", database_url)
    monkeypatch.setenv("DATASET_REGISTRY_SCHEMA", "unrelated_schema")
    engine = MagicMock()
    connection = engine.begin.return_value.__aenter__.return_value
    connection.execute = AsyncMock()
    connection.run_sync = AsyncMock()
    engine.dispose = AsyncMock()
    registry_engine = Mock(return_value=engine)
    monkeypatch.setattr(smoke, "registry_engine", registry_engine)
    monkeypatch.setattr(smoke.BlobStorageAdapter, "from_environment", Mock())
    monkeypatch.setattr(smoke, "seed_fixture", AsyncMock())
    delete_blobs = AsyncMock()
    monkeypatch.setattr(smoke, "delete_fixture_blobs", delete_blobs)

    uid = uuid4()
    name = f"dataset-smoke-{uid}"
    schema = f"nachet_smoke_{uid.hex}"
    await smoke.run_command(Namespace(container=CONTAINER, name=name, action="seed"))
    await smoke.run_command(Namespace(container=CONTAINER, name=name, action="cleanup"))

    assert registry_engine.call_args_list == [call(database_url, schema)] * 2
    create, drop = [item.args[0] for item in connection.execute.await_args_list]
    assert isinstance(create, CreateSchema) and create.element == schema
    assert isinstance(drop, DropSchema) and drop.element == schema
    assert drop.cascade and drop.if_exists
    connection.run_sync.assert_awaited_once()
    delete_blobs.assert_awaited_once()


def test_fixture_identity_is_recoverable_but_unique_per_workflow():
    name = f"dataset-smoke-{uuid4()}"
    smoke.validate_target(name, CONTAINER)
    smoke.validate_target(name, f"{CONTAINER}-ceph")
    assert smoke.build_fixture(name) == smoke.build_fixture(name)
    first = smoke.build_fixture(name)[2]
    second = smoke.build_fixture(f"dataset-smoke-{uuid4()}")[2]
    assert first.keys().isdisjoint(second)
