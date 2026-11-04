"""Exercise the shared S3 provider without contacting an object store."""

from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def s3_provider(monkeypatch):
    from botocore.exceptions import ClientError
    from mlops_blob import create_blob_storage_client

    objects = {}
    metadata = {}
    client = Mock()
    client.meta.endpoint_url = "https://storage.example.test"

    def put_object(*, Bucket, Key, Body, **options):
        if (Bucket, Key) in objects and options.get("IfNoneMatch") == "*":
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        objects[Bucket, Key] = Body
        metadata[Bucket, Key] = options.get("Metadata", {})
        return {"ETag": '"test-etag"'}

    client.put_object.side_effect = put_object
    client.get_object.side_effect = lambda **args: {
        "Body": BytesIO(objects[args["Bucket"], args["Key"]])
    }
    client.head_object.side_effect = lambda **args: {
        "ContentLength": len(objects[args["Bucket"], args["Key"]]),
        "LastModified": datetime.now(UTC),
        "Metadata": metadata.get((args["Bucket"], args["Key"]), {}),
    }
    client.list_objects_v2.side_effect = lambda **args: {
        "Contents": [
            {"Key": key, "Size": len(data), "LastModified": datetime.now(UTC)}
            for (bucket, key), data in sorted(objects.items())
            if bucket == args["Bucket"] and key.startswith(args.get("Prefix", ""))
        ],
        "IsTruncated": False,
    }
    monkeypatch.setattr("mlops_blob.s3.storage.create_s3_client", lambda config: client)
    storage = create_blob_storage_client("s3", {})
    try:
        yield SimpleNamespace(storage=storage, client=client, objects=objects)
    finally:
        storage.close()
