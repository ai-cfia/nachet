"""Explicit registry configuration for the standalone MLOps runtime."""

import os
import re
from dataclasses import dataclass

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from .errors import ConfigurationError


@dataclass(frozen=True)
class Settings:
    database_url: str
    registry_schema: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
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
