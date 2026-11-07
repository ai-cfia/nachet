"""S3 operations used by dataset preparation."""

import os
from contextlib import closing
from urllib.parse import urlsplit

import boto3
from blob.exceptions import BlobNotFoundError, BlobStorageError
from blob.s3.utils.error_handling import ErrorHandler
from blob.validation import validate_blob_name, validate_container_name
from botocore.config import Config
from botocore.exceptions import ClientError


class PreparationStorage:
    """Use one bucket-scoped S3 client for preparation."""

    def __init__(self, client):
        self._client = client

    @ErrorHandler.handle_service_errors("list collection")
    async def list_collection_keys(self, bucket: str, prefix: str) -> list[str]:
        validate_container_name(bucket)
        pages = self._client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix
        )
        return [item["Key"] for page in pages for item in page.get("Contents", [])]

    @ErrorHandler.handle_service_errors("read image")
    async def read_image(self, bucket: str, key: str) -> bytes:
        validate_container_name(bucket)
        if key != key.strip():
            raise BlobStorageError(
                "Image key cannot have leading or trailing whitespace"
            )
        # Check the shared rules with spaces masked. S3 receives the original key.
        validate_blob_name(key.replace(" ", "_"))
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
        except ClientError as error:
            if error.response["Error"]["Code"] == "404":
                raise BlobNotFoundError(bucket, key) from error
            raise
        with closing(response["Body"]) as body:
            return body.read()

    def close(self) -> None:
        self._client.close()


def create_storage(
    endpoint_url: str, region: str, *, allow_http: bool = False
) -> PreparationStorage:
    """Use the SDK credential chain with no account-wide bucket probe."""
    scheme = urlsplit(endpoint_url).scheme
    if scheme != "https" and not (scheme == "http" and allow_http):
        raise ValueError(
            "Use an HTTPS endpoint, or --allow-http for a trusted HTTP endpoint"
        )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        verify=os.environ.get("AWS_CA_BUNDLE") or True,
        config=Config(
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )
    return PreparationStorage(client)
