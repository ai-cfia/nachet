"""Exercise preparation storage with a fake S3 SDK."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def s3_provider():
    from botocore.exceptions import ClientError

    from s3_storage import PreparationStorage

    objects = {}
    client = Mock()

    def put_object(*, Bucket, Key, Body, **options):
        if (Bucket, Key) in objects and options.get("IfNoneMatch") == "*":
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        objects[Bucket, Key] = Body
        return {}

    def get_object(*, Bucket, Key):
        try:
            return {"Body": BytesIO(objects[Bucket, Key])}
        except KeyError as error:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject") from error

    def paginate(*, Bucket, Prefix):
        yield {
            "Contents": [
                {"Key": key}
                for bucket, key in sorted(objects)
                if bucket == Bucket and key.startswith(Prefix)
            ]
        }

    client.put_object.side_effect = put_object
    client.get_object.side_effect = get_object
    client.get_paginator.return_value.paginate.side_effect = paginate
    storage = PreparationStorage(client)
    try:
        yield SimpleNamespace(storage=storage, client=client, objects=objects)
    finally:
        storage.close()
