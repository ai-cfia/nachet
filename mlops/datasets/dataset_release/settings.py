"""Explicit registry configuration for the standalone MLOps runtime."""

import os
import re
from dataclasses import dataclass

from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    database_url: str
    registry_schema: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("DATASET_DATABASE_URL")
        if not database_url:
            raise ValueError("DATASET_DATABASE_URL is required")
        dialect = make_url(database_url).drivername
        if dialect == "sqlite+aiosqlite":
            return cls(database_url, None)
        if dialect != "postgresql+psycopg":
            raise ValueError(
                "Use postgresql+psycopg or sqlite+aiosqlite for the registry"
            )
        schema = os.environ.get("DATASET_REGISTRY_SCHEMA", "nachet_datasets")
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
            raise ValueError(
                "DATASET_REGISTRY_SCHEMA must be a lowercase PostgreSQL schema name"
            )
        return cls(database_url, schema)
