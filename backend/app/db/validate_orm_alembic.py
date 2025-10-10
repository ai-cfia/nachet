import os
import asyncio
from dotenv import load_dotenv
from app.api.config import get_settings
from app.db.utils import sessionmanager, check_if_new_migration_file_needed
from app.service.logs import LogService


async def check_migration_file_needed(logger=None):
    """Check if a new migration file is needed."""

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    if logger:
        logger.info("\n" + "=" * 60)

    # Initialize SessionManager
    if logger:
        logger.info("Initializing database SessionManager...")
    sessionmanager.init(**settings.db_conn_info)
    async_engine = sessionmanager.get_engine()

    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"

    if logger:
        logger.info("Checking if a new migration file is needed to match the current ORM state")
    await check_if_new_migration_file_needed(async_engine)


if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")

    asyncio.run(check_migration_file_needed(logger=logger))
