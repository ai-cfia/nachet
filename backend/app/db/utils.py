import sys
import os
from typing import TYPE_CHECKING, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.sql import text
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime import migration

if TYPE_CHECKING:
    from app.api.config import Settings

# Global engine instance for reuse
_engine_instance: Optional[AsyncEngine] = None


def get_database_engine(
    url: str = None,
    echo: bool = False,
    pool_recycle: Optional[int] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[int] = None,
    pool_pre_ping: Optional[bool] = None,
) -> AsyncEngine:
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
        if url is None:
            raise ValueError(
                "Database URL must be provided for initial engine creation"
            )

        _engine_instance = create_async_engine(url, echo=echo)

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


async def validate_database_startup(async_engine: AsyncEngine):
    """
    Lightweight startup validation - just check migration version.
    Ensures database is migrated to the expected version.
    https://alembic.sqlalchemy.org/en/latest/cookbook.html
    """
    try:
        # Get expected version from alembic
        alembic_cfg = Config("alembic.ini")
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        async with async_engine.begin() as connection:
            context = migration.MigrationContext.configure(connection)
            if set(context.get_current_heads()) == set(script_dir.get_heads()):
                print("✅ Target DB is up to date")
            else:
                print("❌ Target DB is NOT up to date")
                raise RuntimeError("Database schema is not up to date")

    except Exception as e:
        print(f"❌ Database startup validation failed: {e}")
        print("🚨 Application cannot start with invalid database state")
        sys.exit(1)
    finally:
        if "async_engine" in locals():
            await async_engine.dispose()


async def initialize_database(settings: "Settings" = None):
    """
    Initialize and validate database on application startup.

    This function should be called during application initialization
    to ensure the database is properly set up and schema is current.

    Args:
        db_url: Database connection URL. If None, will get from Settings.
    """
    print("🔧 Initializing database...")

    if settings is None:
        raise ValueError("Settings instance must be provided")

    # Initialize the engine
    engine = get_database_engine(**settings.db_conn_info)

    # Validate database schema version
    await validate_database_startup(engine)

    print("✅ Database initialization completed successfully")
    print("\n" + "=" * 60)
    print("\n\n\n")


def cleanup_temp_db(db_url: str):
    """Cleanup temporary database file if using SQLite."""
    if db_url.startswith("sqlite"):
        temp_db_name = db_url.split("///")[-1]
        print(f"Cleanup temporary database at: {temp_db_name}")
        # Ensure clean slate by removing file if it exists (for idempotent tests)
        try:
            os.unlink(temp_db_name)
        except FileNotFoundError:
            pass  # File doesn't exist, which is what we want


async def run_migrations(
    async_engine: AsyncEngine, url: str, target_version: str = "head"
):
    """Run migrations using the provided async engine."""
    # Change to the correct directory for alembic to find migrations
    original_cwd = os.getcwd()
    db_dir = os.path.dirname(__file__)  # This is the app/db directory
    os.chdir(db_dir)

    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", url)
    finally:
        os.chdir(original_cwd)
    try:
        # First, run migrations in their own transaction
        async with async_engine.begin() as conn:
            # Check current alembic version before migration
            try:
                current_version = await conn.run_sync(
                    lambda sync_conn: sync_conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).fetchone()
                )
                print(f"Current alembic version before migration: {current_version}")
            except Exception:
                print("No alembic_version table exists yet")

            await conn.run_sync(run_upgrade, alembic_cfg, target=target_version)
            print("✅ Migrations completed successfully \n\n\n")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await async_engine.dispose()


def run_upgrade(connection, cfg, target="head"):
    """Run alembic upgrade within a synchronous connection context."""
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, target)
