"""Registry and smoke storage configuration for the standalone MLOps runtime."""

import os
import re
from dataclasses import dataclass

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from .errors import ConfigurationError


def smoke_bucket_from_environment() -> str | None:
    """Read the bucket from the Vault-backed smoke root setting."""
    root = os.environ.get("DATASET_SMOKE_ROOT")
    if root is None:
        return None
    bucket, _, prefix = root.partition("/")
    if prefix != "smoke" or not re.fullmatch(
        r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket
    ):
        raise ConfigurationError("DATASET_SMOKE_ROOT must be <bucket>/smoke")
    return bucket


def is_dedicated_smoke_bucket(bucket: str) -> bool:
    """Recognize the supported standalone smoke bucket names."""
    return bucket == "nachet-dataset-smoke" or bucket.startswith(
        "nachet-dataset-smoke-"
    )


@dataclass(frozen=True)
class Settings:
    database_url: str
    registry_schema: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        """Validate the async registry URL and select its dedicated schema.

        PostgreSQL defaults to nachet_datasets; local SQLite uses no schema.
        Invalid settings raise ConfigurationError without exposing their values.
        """
        database_url = os.environ.get("DATASET_DATABASE_URL")
        if not database_url:
            raise ConfigurationError("DATASET_DATABASE_URL is required")
        try:
            dialect = make_url(database_url).drivername
        except (ArgumentError, ValueError):
            raise ConfigurationError(
                "DATASET_DATABASE_URL must be a valid SQLAlchemy database URL"
            ) from None
        if dialect == "sqlite+aiosqlite":
            return cls(database_url, None)
        if dialect != "postgresql+psycopg":
            raise ConfigurationError(
                "DATASET_DATABASE_URL must use postgresql+psycopg or sqlite+aiosqlite"
            )
        schema = os.environ.get("DATASET_REGISTRY_SCHEMA", "nachet_datasets")
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
            raise ConfigurationError(
                "DATASET_REGISTRY_SCHEMA must be a lowercase PostgreSQL schema name"
            )
        return cls(database_url, schema)
