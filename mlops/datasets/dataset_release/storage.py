"""Dataset-facing adapter to the standalone copy of backend app.blob."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Protocol

from mlops_blob import BlobStorageInterface, create_blob_storage_client
from mlops_blob.exceptions import BlobAlreadyExistsError as BlobAlreadyExistsError
from mlops_blob.exceptions import BlobNotFoundError as BlobNotFoundError


class BlobStorage(Protocol):
    """The two operations required by the dataset release and reader."""

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        pass

    async def download_blob(self, container: str, name: str, **kwargs: Any) -> bytes:
        pass


def environment_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() not in ("true", "false", "1", "0"):
        raise ValueError(f"{name} must be true or false")
    return value.lower() in ("true", "1")


def s3_configuration() -> dict[str, Any]:
    endpoint = os.environ.get("S3_ENDPOINT_URL") or os.environ.get(
        "AWS_ENDPOINT_URL_S3"
    )
    access_key = os.environ.get("S3_ACCESS_KEY")
    secret_key = os.environ.get("S3_SECRET_KEY")
    if bool(access_key) != bool(secret_key):
        raise ValueError("S3_ACCESS_KEY and S3_SECRET_KEY must be supplied together")
    config: dict[str, Any] = {
        "s3_endpoint_url": endpoint,
        "s3_region_name": os.environ.get("S3_REGION_NAME")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        "s3_use_ssl": environment_flag(
            "S3_USE_SSL", not (endpoint or "").startswith("http://")
        ),
        "s3_verify": environment_flag("S3_VERIFY", True),
        "s3_connect_timeout": 5,
        "s3_read_timeout": 30,
    }
    if access_key:
        config["s3_access_key"] = access_key
        config["s3_secret_key"] = secret_key
        if os.environ.get("S3_SESSION_TOKEN"):
            config["s3_session_token"] = os.environ["S3_SESSION_TOKEN"]
    return config


class BlobStorageAdapter:
    """Delegate storage behavior to a copied app.blob provider.

    Those providers expose async methods around synchronous SDKs. Execute each
    operation, including stream consumption, in a worker's event loop so that
    storage calls do not block the controller's event loop. No backend manager,
    application startup or global storage account registry is needed.
    """

    def __init__(self, provider: BlobStorageInterface):
        self.provider = provider

    @classmethod
    def from_environment(cls) -> BlobStorageAdapter:
        provider = os.environ.get("DATASET_BLOB_PROVIDER", "s3").strip().lower()
        if provider == "s3":
            config = s3_configuration()
        elif provider == "azure":
            connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                raise ValueError(
                    "AZURE_STORAGE_CONNECTION_STRING is required for Azure"
                )
            config = {"connection_string": connection_string}
        else:
            raise ValueError("DATASET_BLOB_PROVIDER must be s3 or azure")
        return cls(create_blob_storage_client(provider, config))

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        def upload() -> dict[str, Any]:
            return asyncio.run(
                self.provider.upload_blob(container, name, data, **kwargs)
            )

        return await asyncio.to_thread(upload)

    async def download_blob(self, container: str, name: str, **kwargs: Any) -> bytes:
        def download() -> bytes:
            return asyncio.run(self.provider.download_blob(container, name, **kwargs))

        return await asyncio.to_thread(download)

    def close(self) -> None:
        self.provider.close()
