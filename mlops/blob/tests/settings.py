"""Storage-only environment settings for opt-in live-service tests."""

from pydantic_settings import BaseSettings


class StorageSettings(BaseSettings):
    blob_storage_provider: str | None = None
    blob_storage_name: str | None = None
    blob_storage_key: str | None = None
    blob_storage_endpoint_protocol: str | None = None
    blob_storage_endpoint_suffix: str | None = None
    blob_storage_endpoint_base: str | None = None
    blob_storage_connection_timeout: int = 5
    blob_storage_read_timeout: int = 10
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region_name: str | None = None
    s3_endpoint_url: str | None = None
    s3_use_ssl: bool = False
    s3_verify: bool = True

    @property
    def blob_storage_config(self) -> dict:
        """Configuration for blob storage initialization."""
        return {
            "blob_storage_provider": self.blob_storage_provider,
            "blob_storage_name": self.blob_storage_name,
            "blob_storage_key": self.blob_storage_key,
            "blob_storage_endpoint_protocol": self.blob_storage_endpoint_protocol,
            "blob_storage_endpoint_suffix": self.blob_storage_endpoint_suffix,
            "blob_storage_endpoint_base": self.blob_storage_endpoint_base,
            "connection_timeout": self.blob_storage_connection_timeout,
            "read_timeout": self.blob_storage_read_timeout,
        }

    @property
    def s3_storage_config(self) -> dict:
        """Configuration for s3 blob storage initialization."""
        return {
            "s3_endpoint_url": self.s3_endpoint_url,
            "s3_access_key": self.s3_access_key,
            "s3_secret_key": self.s3_secret_key,
            "s3_region_name": self.s3_region_name,
            "s3_use_ssl": self.s3_use_ssl,
            "s3_verify": self.s3_verify,
            "s3_connect_timeout": self.blob_storage_connection_timeout,
            "s3_read_timeout": self.blob_storage_read_timeout,
        }


def get_settings() -> StorageSettings:
    return StorageSettings()
