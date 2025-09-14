from app.db.model import Base
from app.api.config import Settings
from app.db.utils import cleanup_temp_db
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio


def get_table_names_sync(engine):
    inspector = inspect(engine)
    return inspector.get_table_names()


def validate_orm_classes_sync(db_url: str, debug: bool = False):
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

        print(f"Using DB URL: {db_url}" if debug else "Using DB URL: [HIDDEN]")
        engine = create_engine(db_url, echo=debug)
        # This will raise exceptions if there are mapping issues
        Base.metadata.create_all(
            engine
        )  # Accessing this attribute triggers mapper configuration
        print("✅ All ORM classes are valid")

        # print table list to confirm connection
        tables = get_table_names_sync(engine)
        print(f"Tables in the database: {tables}")
        return True
    except Exception as e:
        print(f"❌ ORM validation failed: {e}")
        return False


async def get_table_names_async(engine):
    async with engine.connect() as conn:
        result = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        return result


async def validate_orm_classes_async(db_url: str, debug: bool = False):
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

        print(
            f"Using async DB URL: {db_url}" if debug else "Using async DB URL: [HIDDEN]"
        )
        engine = create_async_engine(db_url, echo=debug)

        # Create all tables - this will validate ORM mappings
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ All ORM classes are valid (async)")

        # Get table list to confirm connection
        tables = await get_table_names_async(engine)
        print(f"Tables in the database: {tables}")

        # Clean up
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ Async ORM validation failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Running runtime ORM validation with database connection...")
    print("=" * 50)

    db_url = Settings().db_conn_info["url"]
    cleanup_temp_db(db_url)

    DEBUG = False
    sync_valid = validate_orm_classes_sync(db_url=db_url, debug=DEBUG)
    print()
    async_valid = asyncio.run(validate_orm_classes_async(db_url=db_url, debug=DEBUG))

    cleanup_temp_db(db_url)
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Synchronous validation: {'✅ PASSED' if sync_valid else '❌ FAILED'}")
    print(f"Asynchronous validation: {'✅ PASSED' if async_valid else '❌ FAILED'}")
    print(
        f"Overall result: {'✅ ALL TESTS PASSED' if sync_valid and async_valid else '❌ SOME TESTS FAILED'}"
    )
    print("=" * 50)
