"""Migrate only the MLOps registry, with a separate Alembic version table."""

import asyncio
import os

from alembic import context
from dataset_controller.config.dataset_config import Settings
from dataset_controller.repositories.registry import Base, registry_engine
from dotenv import load_dotenv

load_dotenv(os.environ.get("DATASET_ENV_FILE", ".env"))
settings = Settings.from_environment()


def options() -> dict:
    return {
        "target_metadata": Base.metadata,
        "version_table": "dataset_release_version",
        "version_table_schema": settings.registry_schema,
    }


def migrate(connection):
    context.configure(connection=connection, **options())
    with context.begin_transaction():
        context.run_migrations()


async def online():
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
