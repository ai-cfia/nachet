# Test database setup script to initialize the database with necessary tables and data.
# This is intended for ci test use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.
import os
import asyncio

# import logging
from app.db.utils import (
    run_migrations,
    sessionmanager,
    reset_database_schema,
    execute_sql_file,
)
from app.api.config import get_settings
from app.db.data.data_seed_test import seed_test_data
from app.service.logs import LogService


async def load_database(logger=None):
    """
    Set up the testing database by resetting, running migrations and seeding data.
    This function is idempotent - it can be run multiple times safely.
    """
    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    db_url = settings.db_conn_info["url"]

    db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

    if logger:
        logger.info("\n" + "=" * 60)
        logger.info("Starting testing database setup", database=db_name)

    # Initialize SessionManager
    if logger:
        logger.info("Initializing database SessionManager...")
    sessionmanager.init(**settings.db_conn_info)
    async_engine = sessionmanager.get_engine()

    # Reset database to ensure clean state
    await reset_database_schema(async_engine)

    if logger:
        logger.info("Running migrations...")
    # Set environment variable to control SQLAlchemy logging during migrations

    # os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    # os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"
    await run_migrations(async_engine=async_engine, target_version="head")

    # logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    if logger:
        logger.info("Loading ISTA seed data...")
    sql_file_path = os.path.join(
        os.path.dirname(__file__), "data", "seed_data_ista_test.sql"
    )
    await execute_sql_file(async_engine, sql_file_path)

    if logger:
        logger.info("Seeding test data...")
    await seed_test_data(sessionmanager)
    if logger:
        logger.info("Testing database setup complete")
        logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    asyncio.run(load_database(logger=logger))
