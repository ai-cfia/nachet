"""Small S3 adapter owned by MLOps, with atomic non-overwriting writes."""

from __future__ import annotations

import asyncio
import os
from contextlib import closing
from typing import Any, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class BlobAlreadyExistsError(FileExistsError):
    def __init__(self, container: str, key: str):
        super().__init__(f"Object already exists: {container}/{key}")


class BlobNotFoundError(FileNotFoundError):
    def __init__(self, container: str, key: str):
        super().__init__(f"Referenced object is missing: {container}/{key}")


class BlobStorage(Protocol):
    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        pass

    async def download_blob(
        self, container: str, name: str, **kwargs: Any
    ) -> bytes:
        pass


def environment_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() not in ("true", "false", "1", "0"):
        raise ValueError(f"{name} must be true or false")
    return value.lower() in ("true", "1")


class S3Storage:
    def __init__(self, client: Any):
        self.client = client

    @classmethod
    def from_environment(cls) -> S3Storage:
        endpoint = os.environ.get("S3_ENDPOINT_URL") or os.environ.get(
            "AWS_ENDPOINT_URL_S3"
        )
        options: dict[str, Any] = {
            "endpoint_url": endpoint,
            "region_name": os.environ.get("S3_REGION_NAME")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            "use_ssl": environment_flag(
                "S3_USE_SSL", not (endpoint or "").startswith("http://")
            ),
            "verify": environment_flag("S3_VERIFY", True),
            "config": Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"mode": "standard", "max_attempts": 3},
            ),
        }
        # Otherwise leave credentials to boto3's standard AWS environment,
        # profile, workload identity and role providers.
        if os.environ.get("S3_ACCESS_KEY") or os.environ.get("S3_SECRET_KEY"):
            if not os.environ.get("S3_ACCESS_KEY") or not os.environ.get(
                "S3_SECRET_KEY"
            ):
                raise ValueError(
                    "S3_ACCESS_KEY and S3_SECRET_KEY must be supplied together"
                )
            options["aws_access_key_id"] = os.environ["S3_ACCESS_KEY"]
            options["aws_secret_access_key"] = os.environ["S3_SECRET_KEY"]
        return cls(boto3.client("s3", **options))

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        overwrite = kwargs.get("overwrite", True)
        parameters = {
            "Bucket": container,
            "Key": name,
            "Body": data,
            "ContentType": kwargs.get("content_type", "application/octet-stream"),
        }
        if not overwrite:
            parameters["IfNoneMatch"] = "*"
        try:
            response = await asyncio.to_thread(self.client.put_object, **parameters)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if not overwrite and code in ("PreconditionFailed", "412"):
                raise BlobAlreadyExistsError(container, name) from error
            raise
        return {"size": len(data), "etag": response.get("ETag", "")}

    async def download_blob(self, container: str, name: str, **kwargs: Any) -> bytes:
        def download() -> bytes:
            try:
                response = self.client.get_object(Bucket=container, Key=name)
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                    raise BlobNotFoundError(container, name) from error
                raise
            with closing(response["Body"]) as stream:
                return stream.read()

        return await asyncio.to_thread(download)

    def close(self) -> None:
        self.client.close()
