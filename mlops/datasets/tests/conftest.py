"""Real copied blob providers with deterministic, in-memory SDK transports."""

from datetime import UTC, datetime
from io import BytesIO
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceExistsError
from botocore.exceptions import ClientError

from dataset_release.storage import BlobStorageAdapter
from mlops_blob import create_blob_storage_client


@pytest.fixture(params=["s3", "azure"])
def blob_provider(request, monkeypatch):
    objects = {}
    write_lock = Lock()
    client = Mock()
    now = datetime.now(UTC)

    if request.param == "s3":
        client.meta.endpoint_url = "https://storage.example.test"

        def put_object(*, Bucket, Key, Body, **options):
            with write_lock:
                if options.get("IfNoneMatch") == "*" and (Bucket, Key) in objects:
                    raise ClientError(
                        {"Error": {"Code": "PreconditionFailed"}}, "PutObject"
                    )
                objects[Bucket, Key] = Body
            return {"ETag": '"etag"'}

        def get_object(*, Bucket, Key, **options):
            if (Bucket, Key) not in objects:
                raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
            return {"Body": BytesIO(objects[Bucket, Key])}

        def head_object(*, Bucket, Key):
            if (Bucket, Key) not in objects:
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
            return {"ContentLength": len(objects[Bucket, Key]), "LastModified": now}

        client.put_object.side_effect = put_object
        client.get_object.side_effect = get_object
        client.head_object.side_effect = head_object
        monkeypatch.setattr(
            "mlops_blob.s3.storage.create_s3_client", lambda config: client
        )
        config = {}
    else:
        blob_clients = {}

        def get_blob_client(*, container, blob):
            key = (container, blob)
            if key in blob_clients:
                return blob_clients[key]
            blob_client = Mock()
            blob_client.url = f"https://storage.example.test/{container}/{blob}"
            blob_client.exists.side_effect = lambda: key in objects

            def upload_blob(data, **options):
                with write_lock:
                    if not options.get("overwrite", True) and key in objects:
                        raise ResourceExistsError("Blob already exists")
                    objects[key] = data
                return {"etag": "etag", "last_modified": now}

            blob_client.upload_blob.side_effect = upload_blob
            blob_client.download_blob.return_value.readall.side_effect = lambda: (
                objects[key]
            )
            blob_client.get_blob_properties.side_effect = lambda: SimpleNamespace(
                size=len(objects[key]),
                content_settings=SimpleNamespace(content_md5=None),
            )
            blob_clients[key] = blob_client
            return blob_client

        client.get_blob_client.side_effect = get_blob_client
        client.get_container_client.return_value.exists.return_value = True
        monkeypatch.setattr(
            "mlops_blob.azure.storage.create_blob_service_client",
            lambda *args, **kwargs: client,
        )
        config = {"connection_string": "test-only"}

    storage = BlobStorageAdapter(create_blob_storage_client(request.param, config))
    try:
        yield SimpleNamespace(
            storage=storage, objects=objects, client=client, kind=request.param
        )
    finally:
        storage.close()
