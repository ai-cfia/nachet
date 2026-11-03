"""Migrate only the MLOps registry, with a separate Alembic version table."""

import asyncio
import os

from alembic import context
from dotenv import load_dotenv

from dataset_release.registry import Base, registry_engine
from dataset_release.settings import Settings

load_dotenv(os.environ.get("DATASET_ENV_FILE", ".env"))
settings = Settings.from_environment()


def options() -> dict:
    """Configure MLOps metadata and its separate migration version table."""
    return {
        "target_metadata": Base.metadata,
        "version_table": "dataset_release_version",
        "version_table_schema": settings.registry_schema,
    }


def migrate(connection):
    """Run registry migrations in a transaction on the supplied sync connection."""
    context.configure(connection=connection, **options())
    with context.begin_transaction():
        context.run_migrations()


async def online():
    """Open the configured registry connection, migrate, and dispose of the engine."""
    engine = registry_engine(settings.database_url, settings.registry_schema)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(url=settings.database_url, literal_binds=True, **options())
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    migrate(context.config.attributes["connection"])
else:
    asyncio.run(online())
