# Setup script to initialize the ORM defined database using ORM models.
# This is intended for development and testing use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.

import os
import asyncio
from dotenv import load_dotenv

# import logging
from app.db.utils import (
    sessionmanager,
    reset_database_schema,
    # execute_sql_file,
)
from app.api.config import get_settings
from app.db.model import Base
from app.service.logs import LogService


async def load_database(logger=None):
    """
    Set up the ORM defined database by resetting and recreating the schema using the ORM models.
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

    # Create the database schema
    if logger:
        logger.info("Creating database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if logger:
        logger.info("ORM defined database setup complete")
        logger.info("=" * 60 + "\n")


if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")
    os.environ["NACHET_SCHEMA"] = "nachet_orm"

    asyncio.run(load_database(logger=logger))
