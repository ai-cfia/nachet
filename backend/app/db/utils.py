import sys
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.sql import text
from alembic.config import Config
from alembic.script import ScriptDirectory

# Global engine instance for reuse
_engine_instance: Optional[AsyncEngine] = None


async def validate_database_startup(db_url: str):
    """
    Lightweight startup validation - just check migration version.
    Ensures database is migrated to the expected version.
    """
    try:
        async_engine = create_async_engine(db_url, echo=False)

        async with async_engine.begin() as conn:
            # Check if migrations are up to date
            try:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                current_version_row = result.fetchone()
                current_version = (
                    current_version_row[0] if current_version_row else None
                )
            except Exception:
                raise Exception(
                    "No alembic_version table found - database may be uninitialized"
                )

            if not current_version:
                raise Exception("No migration version found - run migrations first")

            # Get expected version from alembic
            try:
                alembic_cfg = Config("alembic.ini")
                script_dir = ScriptDirectory.from_config(alembic_cfg)
                head_version = script_dir.get_current_head()
            except Exception as e:
                raise Exception(f"Failed to read alembic configuration: {e}")

            if current_version != head_version:
                raise Exception(
                    f"Migration version mismatch. "
                    f"Current: {current_version}, Expected: {head_version}. "
                    f"Please run 'alembic upgrade head'"
                )

            print(f"✅ Database migration version validated: {current_version}")
            return True

    except Exception as e:
        print(f"❌ Database startup validation failed: {e}")
        print("🚨 Application cannot start with invalid database state")
        sys.exit(1)
    finally:
        if "async_engine" in locals():
            await async_engine.dispose()


def get_database_engine(db_url: str = None, echo: bool = False) -> AsyncEngine:
    """
    Get the database engine instance (singleton pattern).

    Args:
        db_url: Database connection URL. If None, will get from Settings.
        echo: Whether to echo SQL statements for debugging.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance.
    """
    global _engine_instance

    if _engine_instance is None:
        if db_url is None:
            from app.api.config import Settings

            settings = Settings()
            db_url = settings.db_conn_info["url"]

        _engine_instance = create_async_engine(db_url, echo=echo)

    return _engine_instance


async def close_database_engine():
    """
    Close the database engine and cleanup resources.
    Should be called during application shutdown.
    """
    global _engine_instance

    if _engine_instance:
        await _engine_instance.dispose()
        _engine_instance = None
        print("🔌 Database engine closed")


def reset_database_engine():
    """
    Reset the engine instance (useful for testing).
    """
    global _engine_instance
    _engine_instance = None


async def initialize_database(db_url: str = None):
    """
    Initialize and validate database on application startup.

    This function should be called during application initialization
    to ensure the database is properly set up and schema is current.

    Args:
        db_url: Database connection URL. If None, will get from Settings.
    """
    print("🔧 Initializing database...")

    if db_url is None:
        from app.api.config import Settings

        settings = Settings()
        db_url = settings.db_conn_info["url"]

    # Initialize the engine
    get_database_engine(db_url)

    # Validate database schema version
    await validate_database_startup(db_url)

    print("✅ Database initialization completed successfully")
    print("\n" + "=" * 60)
    print("\n\n\n")
