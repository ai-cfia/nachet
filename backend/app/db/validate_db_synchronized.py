import os
import asyncio
from dotenv import load_dotenv
from app.api.config import get_settings
from app.db.utils import sessionmanager, validate_database_startup
from app.service.logs import LogService


async def check_db_synchronization(logger=None):
    """Check if the database is synchronized with the alembic head."""

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    db_url = settings.db_conn_info["url"]

    db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

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
        logger.info("Checking if database is synchronized with alembic head", database=db_name)
    await validate_database_startup(async_engine)


if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")
    # os.environ["TESTING"] = "true" # for debugging the validate_database_startup function

    asyncio.run(check_db_synchronization(logger=logger))
