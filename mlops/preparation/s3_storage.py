"""S3 operations used by dataset preparation."""

import logging
import os
from contextlib import closing
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import boto3
from blob.exceptions import BlobNotFoundError, BlobStorageError
from blob.s3.utils.error_handling import ErrorHandler
from blob.validation import (
    CONTROL_CHARS,
    validate_blob_name,
    validate_container_name,
)
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
MODEL_RECEIPT = ".nachet-model-source.json"


class PreparationStorage:
    """Use one S3 client for preparation."""

    def __init__(self, client):
        self._client = client

    def stage_model(
        self, bucket: str, prefix: str, directory: Path, identity: str
    ) -> None:
        """Publish a complete snapshot on the workspace and reuse it on retries."""
        receipt = directory / MODEL_RECEIPT
        if not directory.exists():
            directory.parent.mkdir(parents=True, exist_ok=True)
            logger.info(
                "Downloading SAM3 model from s3://%s/%s to %s",
                bucket,
                prefix,
                directory,
            )
            with TemporaryDirectory(prefix=".sam3-", dir=directory.parent) as temp:
                snapshot = Path(temp) / "snapshot"
                self._download_model(bucket, prefix, snapshot)
                (snapshot / MODEL_RECEIPT).write_text(identity, encoding="utf-8")
                try:
                    snapshot.rename(directory)
                except OSError:
                    if not receipt.exists():
                        raise
        if not receipt.is_file() or receipt.read_text(encoding="utf-8") != identity:
            raise FileExistsError(
                f"Model directory has a different or untracked snapshot: {directory}"
            )

    def _download_model(self, bucket: str, prefix: str, directory: Path) -> None:
        """Copy an S3 model snapshot into a fresh local directory."""
        validate_container_name(bucket)
        pages = self._client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix
        )
        downloaded = False
        for page in pages:
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                name = key.removeprefix(prefix)
                parts = name.split("/")
                if (
                    CONTROL_CHARS.intersection(name)
                    or "\\" in name
                    or parts[0] == MODEL_RECEIPT
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise BlobStorageError(f"Invalid S3 model key: {key!r}")
                target = directory.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                response = self._client.get_object(Bucket=bucket, Key=key)
                with closing(response["Body"]) as body, target.open("wb") as output:
                    copyfileobj(body, output)
                downloaded = True
        if not downloaded:
            raise BlobStorageError(f"No model files found under s3://{bucket}/{prefix}")

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
        # Existing S3 keys may contain punctuation rejected by portable blob names.
        # Keep path checks here; boto3 encodes the unchanged key for the request.
        if (
            len(key.encode("utf-8")) > 1024
            or CONTROL_CHARS.intersection(key)
            or "\\" in key
            or any(part in {"", ".", ".."} for part in key.split("/"))
        ):
            raise BlobStorageError(f"Invalid S3 image key: {key!r}")
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
        except ClientError as error:
            if error.response["Error"]["Code"] == "404":
                raise BlobNotFoundError(bucket, key) from error
            raise
        with closing(response["Body"]) as body:
            return body.read()

    @ErrorHandler.handle_service_errors("upload prepared PNG")
    async def upload_png(self, bucket: str, key: str, data: bytes) -> None:
        """Write verified, hash-named PNG bytes and allow identical retries."""
        validate_container_name(bucket)
        validate_blob_name(key)
        try:
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType="image/png",
                IfNoneMatch="*",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] not in {"PreconditionFailed", "412"}:
                raise

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
