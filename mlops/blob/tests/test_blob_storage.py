"""Provider contracts independent of backend and dataset release code."""

from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from mlops_blob import BlobStorageInterface, create_blob_storage_client
from mlops_blob.exceptions import (
    BlobAlreadyExistsError,
    BlobNotFoundError,
    BlobStorageError,
    InvalidConfigurationError,
)
from mlops_blob.exceptions import PermissionError as BlobPermissionError


def s3_storage(client):
    with patch("mlops_blob.s3.storage.create_s3_client", return_value=client):
        return create_blob_storage_client("s3", {})


@pytest.mark.asyncio
async def test_copied_provider_conflicts_missing_objects_and_cleanup(blob_provider):
    storage = blob_provider.storage
    assert isinstance(storage, BlobStorageInterface)
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
    storage = create_blob_storage_client("s3", {})
    client.put_object.side_effect = ClientError({"Error": {"Code": code}}, "PutObject")
    with pytest.raises(BlobStorageError) as error:
        await storage.upload_blob("datasets", "file.json", b"data", overwrite=False)
    assert not isinstance(error.value, BlobAlreadyExistsError)
    if code == "AccessDenied":
        assert isinstance(error.value, BlobPermissionError)
    client.put_object.assert_called_once()
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    storage.close()


def test_copied_factory_rejects_unknown_provider():
    with pytest.raises(InvalidConfigurationError):
        create_blob_storage_client("unknown", {})


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


def test_s3_factory_preserves_credential_chain_and_avoids_list_buckets(monkeypatch):
    from mlops_blob.s3 import client as s3_client

    factory = Mock()
    monkeypatch.setattr(s3_client.boto3, "client", factory)
    storage = create_blob_storage_client("s3", {"s3_region_name": "garage"})
    assert factory.call_args.kwargs["region_name"] == "garage"
    assert "aws_access_key_id" not in factory.call_args.kwargs
    factory.return_value.list_buckets.assert_not_called()
    storage.close()
    factory.return_value.close.assert_called_once()


def test_imports_do_not_load_backend_or_dataset_release():
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import mlops_blob.s3.storage, mlops_blob.azure.storage; "
                + "assert not any(n == 'app' or n.startswith('app.') or "
                + "n == 'dataset_release' or n.startswith('dataset_release.') for n in sys.modules)"
            ),
        ],
        check=True,
    )
