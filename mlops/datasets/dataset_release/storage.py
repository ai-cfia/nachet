"""Dataset-facing adapter to the standalone copy of backend app.blob."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Protocol
from uuid import UUID

from blob.exceptions import PermissionError as BlobPermissionError

from .errors import ConfigurationError
from .providers import create_dataset_blob_storage_client
from .providers.s3 import DatasetS3BlobStorage
from .settings import is_dedicated_smoke_bucket, smoke_bucket_from_environment


class BlobStorage(Protocol):
    """The two operations required by the dataset release and reader."""

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        """Upload bytes using provider options such as overwrite and content type."""
        pass

    async def download_blob(self, container: str, name: str, **kwargs: Any) -> bytes:
        """Return the complete bytes of an object in the selected container."""
        pass


class DatasetBlobProvider(BlobStorage, Protocol):
    """A dataset provider also owns an SDK connection pool that can be closed."""

    async def delete_blob(self, container: str, name: str) -> bool:
        """Delete a fixture object; release publication never calls this operation."""
        pass

    def close(self) -> None:
        """Release provider resources when the dataset command finishes."""
        pass


def environment_flag(name: str, default: bool) -> bool:
    """Read a true/false or 1/0 setting, using the default only when it is absent."""
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() not in ("true", "false", "1", "0"):
        raise ConfigurationError(f"{name} must be true or false")
    return value.lower() in ("true", "1")


def s3_configuration() -> dict[str, Any]:
    """Build S3 settings from endpoint, region, TLS, and credential environment values.

    Explicit access and secret keys must be paired. When absent, the provider
    uses the SDK's normal credential chain.
    """
    endpoint = os.environ.get("S3_ENDPOINT_URL") or os.environ.get(
        "AWS_ENDPOINT_URL_S3"
    )
    access_key = os.environ.get("S3_ACCESS_KEY")
    secret_key = os.environ.get("S3_SECRET_KEY")
    if bool(access_key) != bool(secret_key):
        raise ConfigurationError(
            "S3_ACCESS_KEY and S3_SECRET_KEY must be supplied together"
        )
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

    def __init__(
        self,
        provider: DatasetBlobProvider,
        *,
        smoke_run_id: UUID | None = None,
        smoke_bucket: str | None = None,
    ):
        """Wrap an existing provider for use by the async dataset controller."""
        self.provider = provider
        self._smoke_run_id = smoke_run_id
        self._smoke_bucket = smoke_bucket

    @classmethod
    def from_environment(
        cls, *, smoke_run_id: UUID | None = None
    ) -> BlobStorageAdapter:
        """Create the configured S3 or Azure provider, defaulting to S3.

        Unsupported providers and missing Azure connection strings raise
        ConfigurationError before a controller starts using storage.
        """
        configured_run_id = os.environ.get("DATASET_SMOKE_RUN_ID")
        if smoke_run_id is None and configured_run_id is not None:
            try:
                smoke_run_id = UUID(configured_run_id)
            except ValueError:
                raise ConfigurationError(
                    "DATASET_SMOKE_RUN_ID must be a UUID"
                ) from None
        smoke_bucket = (
            smoke_bucket_from_environment() if smoke_run_id is not None else None
        )
        provider = os.environ.get("DATASET_BLOB_PROVIDER", "s3").strip().lower()
        if provider == "s3":
            config = s3_configuration()
        elif provider == "azure":
            connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                raise ConfigurationError(
                    "AZURE_STORAGE_CONNECTION_STRING is required for Azure"
                )
            config = {"connection_string": connection_string}
        else:
            raise ConfigurationError("DATASET_BLOB_PROVIDER must be s3 or azure")
        return cls(
            create_dataset_blob_storage_client(provider, config),
            smoke_run_id=smoke_run_id,
            smoke_bucket=smoke_bucket,
        )

    def _storage_key(self, container: str, name: str) -> str:
        """Confine shared-bucket smoke objects to the current workflow's prefix."""
        if self._smoke_run_id is None:
            return name
        if container != self._smoke_bucket:
            if is_dedicated_smoke_bucket(container):
                return name
            raise ConfigurationError(
                "Container does not match the configured smoke bucket"
            )
        if "\\" in name or any(part in ("", ".", "..") for part in name.split("/")):
            raise ConfigurationError("Smoke object names must be relative object keys")
        return f"smoke/{self._smoke_run_id}/{name}"

    async def upload_blob(
        self, container: str, name: str, data: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        """Upload in a worker thread to keep synchronous SDK calls off the event loop."""

        key = self._storage_key(container, name)

        def upload() -> dict[str, Any]:
            return asyncio.run(
                self.provider.upload_blob(container, key, data, **kwargs)
            )

        return await asyncio.to_thread(upload)

    async def download_blob(self, container: str, name: str, **kwargs: Any) -> bytes:
        """Download and consume object bytes in a worker thread's event loop."""

        key = self._storage_key(container, name)

        def download() -> bytes:
            return asyncio.run(self.provider.download_blob(container, key, **kwargs))

        return await asyncio.to_thread(download)

    async def delete_blob(self, container: str, name: str) -> bool:
        """Delete one smoke object within the same namespace used for uploads."""
        key = self._storage_key(container, name)
        if isinstance(self.provider, DatasetS3BlobStorage):
            return await asyncio.to_thread(
                lambda: asyncio.run(self.provider.delete_fixture(container, key))
            )
        return await asyncio.to_thread(
            lambda: asyncio.run(self.provider.delete_blob(container, key))
        )

    async def confirms_missing_fixture(
        self, container: str, name: str, error: BlobPermissionError
    ) -> bool:
        """Confirm a denied S3 read was for the exact, absent smoke fixture."""
        key = self._storage_key(container, name)
        if (
            not isinstance(self.provider, DatasetS3BlobStorage)
            or error.operation != "download blob"
            or error.details.get("container") != container
            or error.details.get("key") != key
        ):
            return False
        return await asyncio.to_thread(
            lambda: asyncio.run(self.provider.fixture_is_absent(container, key))
        )

    def close(self) -> None:
        """Release the wrapped provider's SDK connection pool."""
        self.provider.close()
