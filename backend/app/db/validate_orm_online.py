from app.db.model import Base
from app.api.config import Settings
from app.db.utils import cleanup_temp_db
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio
from app.service.logs import LogService


def get_table_names_sync(engine):
    inspector = inspect(engine)
    return inspector.get_table_names()


def validate_orm_classes_sync(db_url: str, debug: bool = False, logger=None):
    """Validate all registered ORM classes."""
    try:
        # Ensure sync URL format (remove async drivers if present)
        if "://" in db_url:
            protocol_end = db_url.find("://")
            rest_of_url = db_url[protocol_end:]

            if db_url.startswith("postgresql"):
                db_url = "postgresql+psycopg" + rest_of_url
            elif db_url.startswith("sqlite"):
                db_url = "sqlite+pysqlite" + rest_of_url

        if logger:
            logger.info("Using DB URL", hidden=not debug, url=db_url if debug else "[HIDDEN]")
        engine = create_engine(db_url, echo=debug)
        # This will raise exceptions if there are mapping issues
        Base.metadata.create_all(
            engine
        )  # Accessing this attribute triggers mapper configuration
        if logger:
            logger.info("All ORM classes are valid")

        # Get table list to confirm connection
        tables = get_table_names_sync(engine)
        if logger:
            logger.info("Tables found in database", tables=tables)
        return True
    except Exception as e:
        if logger:
            logger.error("ORM validation failed", error=str(e), error_type=type(e).__name__)
        return False


async def get_table_names_async(engine):
    async with engine.connect() as conn:
        result = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        return result


async def validate_orm_classes_async(db_url: str, debug: bool = False, logger=None):
    """Validate all registered ORM classes using async engine."""
    try:
        # Convert sync URL to async URL if needed
        if "://" in db_url:
            protocol_end = db_url.find("://")
            rest_of_url = db_url[protocol_end:]

            if db_url.startswith("postgresql"):
                db_url = "postgresql+psycopg" + rest_of_url
            elif db_url.startswith("sqlite"):
                db_url = "sqlite+aiosqlite" + rest_of_url

        if logger:
            logger.info("Using async DB URL", hidden=not debug, url=db_url if debug else "[HIDDEN]")
        engine = create_async_engine(db_url, echo=debug)

        # Create all tables - this will validate ORM mappings
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        if logger:
            logger.info("All ORM classes are valid (async)")

        # Get table list to confirm connection
        tables = await get_table_names_async(engine)
        if logger:
            logger.info("Tables found in database (async)", tables=tables)

        # Clean up
        await engine.dispose()
        return True
    except Exception as e:
        if logger:
            logger.error("Async ORM validation failed", error=str(e), error_type=type(e).__name__)
        return False


if __name__ == "__main__":
    # Initialize console-only logging for this script
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    logger.info("=" * 50)
    logger.info("Running runtime ORM validation with database connection")
    logger.info("=" * 50)

    db_url = Settings().db_conn_info["url"]
    cleanup_temp_db(db_url)

    DEBUG = False
    sync_valid = validate_orm_classes_sync(db_url=db_url, debug=DEBUG, logger=logger)
    logger.info("")
    async_valid = asyncio.run(validate_orm_classes_async(db_url=db_url, debug=DEBUG, logger=logger))

    cleanup_temp_db(db_url)
    logger.info("\n" + "=" * 50)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Synchronous validation: {'✅ PASSED' if sync_valid else '❌ FAILED'}")
    logger.info(f"Asynchronous validation: {'✅ PASSED' if async_valid else '❌ FAILED'}")
    logger.info(
        f"Overall result: {'✅ ALL TESTS PASSED' if sync_valid and async_valid else '❌ SOME TESTS FAILED'}"
    )
    logger.info("=" * 50)
