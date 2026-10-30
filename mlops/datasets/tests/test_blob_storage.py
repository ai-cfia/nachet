"""Behavior at the copied app.blob provider boundary."""

import asyncio
from threading import Event, get_ident
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from dataset_controller.repositories.blob_repository import BlobStorageAdapter
from mlops_blob import BlobStorageInterface, create_blob_storage_client
from mlops_blob.exceptions import (
    BlobAlreadyExistsError,
    BlobNotFoundError,
    BlobStorageError,
    InvalidConfigurationError,
)
from mlops_blob.exceptions import (
    PermissionError as BlobPermissionError,
)


@pytest.mark.asyncio
async def test_copied_provider_conflicts_missing_objects_and_cleanup(blob_provider):
    storage = blob_provider.storage
    assert isinstance(storage.provider, BlobStorageInterface)
    await storage.upload_blob("datasets", "file.json", b"original", overwrite=False)
    with pytest.raises(BlobAlreadyExistsError):
        await storage.upload_blob("datasets", "file.json", b"changed", overwrite=False)
    assert await storage.download_blob("datasets", "file.json") == b"original"
    await storage.upload_blob("datasets", "file.json", b"changed", overwrite=True)
    assert await storage.download_blob("datasets", "file.json") == b"changed"
    with pytest.raises(BlobNotFoundError):
        await storage.download_blob("datasets", "missing.json")
    if blob_provider.kind == "azure":
        blob = blob_provider.client.get_blob_client(
            container="datasets", blob="file.json"
        )
        assert blob.upload_blob.call_args_list[0].kwargs["overwrite"] is False
    storage.close()
    blob_provider.client.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code", ["NotImplemented", "ConditionalRequestConflict", "AccessDenied"]
)
async def test_s3_conditional_failure_never_retries_with_overwrite(monkeypatch, code):
    client = Mock()
    monkeypatch.setattr("mlops_blob.s3.storage.create_s3_client", lambda config: client)
    storage = BlobStorageAdapter(create_blob_storage_client("s3", {}))
    client.put_object.side_effect = ClientError({"Error": {"Code": code}}, "PutObject")
    with pytest.raises(BlobStorageError) as error:
        await storage.upload_blob("datasets", "file.json", b"data", overwrite=False)
    assert not isinstance(error.value, BlobAlreadyExistsError)
    if code == "AccessDenied":
        assert isinstance(error.value, BlobPermissionError)
    client.put_object.assert_called_once()
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    storage.close()


@pytest.mark.asyncio
async def test_synchronous_provider_calls_do_not_block_controller_loop():
    started = Event()
    release = Event()
    loop_thread = get_ident()

    async def download(container, name, **kwargs):
        assert get_ident() != loop_thread
        started.set()
        if not release.wait(timeout=5):
            raise TimeoutError("Test did not release the worker")
        return b"image"

    provider = Mock(spec=BlobStorageInterface)
    provider.download_blob.side_effect = download
    adapter = BlobStorageAdapter(provider)
    pending = asyncio.create_task(adapter.download_blob("datasets", "image.png"))
    try:
        async with asyncio.timeout(2):
            while not started.is_set():
                await asyncio.sleep(0.01)
        # Reaching this point while the SDK worker waits proves loop progress.
        assert not pending.done()
    finally:
        release.set()
        assert await pending == b"image"


@pytest.mark.parametrize("provider", ["azure", "s3"])
def test_environment_selects_copied_provider(monkeypatch, provider):
    monkeypatch.setenv("DATASET_BLOB_PROVIDER", provider)
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "test-only")
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)
    factory = Mock()
    monkeypatch.setattr(
        "dataset_controller.repositories.blob_repository.create_blob_storage_client",
        factory,
    )
    storage = BlobStorageAdapter.from_environment()
    assert storage.provider is factory.return_value
    assert factory.call_args.args[0] == provider
    if provider == "azure":
        assert factory.call_args.args[1] == {"connection_string": "test-only"}


@pytest.mark.parametrize(
    "setting", ["provider", "azure-connection", "s3-pair", "s3-tls"]
)
def test_invalid_configuration_fails_before_creating_sdk(monkeypatch, setting):
    monkeypatch.setenv("DATASET_BLOB_PROVIDER", "s3")
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)
    monkeypatch.delenv("S3_VERIFY", raising=False)
    if setting == "provider":
        monkeypatch.setenv("DATASET_BLOB_PROVIDER", "unknown")
    elif setting == "azure-connection":
        monkeypatch.setenv("DATASET_BLOB_PROVIDER", "azure")
        monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    elif setting == "s3-pair":
        monkeypatch.setenv("S3_ACCESS_KEY", "test-key")
    else:
        monkeypatch.setenv("S3_VERIFY", "invalid")
    with pytest.raises(ValueError):
        BlobStorageAdapter.from_environment()


def test_copied_factory_rejects_unknown_provider():
    with pytest.raises(InvalidConfigurationError):
        create_blob_storage_client("unknown", {})
