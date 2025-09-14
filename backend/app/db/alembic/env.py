import asyncio
import os
from logging.config import dictConfig

# for typing purposes
from collections.abc import Iterable

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine  # async_engine_from_config

from alembic import context
from alembic.environment import MigrationContext

# this typing-only import requires alembic 1.12.1 or above
from alembic.operations import MigrationScript

from app.db.model import Base
from app.api.config import Settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# Configure logging using dictConfig with environment variable support
alembic_log_level = os.getenv("ALEMBIC_MIGRATION_LOG_LEVEL", "INFO")
sqlalchemy_log_level = os.getenv("SQLALCHEMY_MIGRATION_LOG_LEVEL", "INFO")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(levelname)-5.5s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "level": "NOTSET",
            "formatter": "generic",
        },
    },
    "loggers": {
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
        "sqlalchemy.engine": {
            "level": sqlalchemy_log_level,
            "handlers": ["console"],
            "qualname": "sqlalchemy.engine",
            "propagate": False,
        },
        "alembic": {
            "level": alembic_log_level,
            "handlers": ["console"],
            "qualname": "alembic",
            "propagate": False,
        },
    },
}

dictConfig(LOGGING_CONFIG)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Prevent Alembic from generating empty migration scripts
# This is important to avoid cluttering the migration history with no-op files
# def process_revision_directives(
#     context: MigrationContext,
#     revision: str | Iterable[str | None] | Iterable[str],
#     directives: list[MigrationScript],
# ):
#     # assert config.cmd_opts is not None
#     # if getattr(config.cmd_opts, "autogenerate", False):
#     if config.cmd_opts is not None and getattr(config.cmd_opts, "autogenerate", False):
#         script = directives[0]
#         assert script.upgrade_ops is not None
#         if script.upgrade_ops.is_empty():
#             directives[:] = []
#             print("No changes in schema detected.")


# Prevent Alembic from trying to drop tables that aren't in the ORM
# This is important for avoiding accidental drops of legacy or unmanaged tables
# This will prevent autogenerate from detecting tables removed from the
# local metadata as well however this is only a small caveat
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and compare_to is None:
        return False
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = Settings().db_conn_info["url"]
    # url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        # process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        # process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = create_async_engine(
        Settings().db_conn_info["url"],
        # prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    try:
        # Check if we're already in an event loop
        asyncio.get_running_loop()
        # If we reach here, we're in an event loop already
        # We need to run the coroutine differently
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, run_async_migrations())
            future.result()
    except RuntimeError:
        # No event loop is running, safe to use asyncio.run()
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
