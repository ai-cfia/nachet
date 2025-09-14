import sys
import os
from typing import TYPE_CHECKING, Optional, AsyncGenerator
from tqdm import tqdm
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.sql import text
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime import migration

if TYPE_CHECKING:
    from app.api.config import Settings


class SessionManager:
    """Manages asynchronous DB sessions with connection pooling."""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None

    def init(self, url: str, **engine_kwargs):
        """Initialize the SessionManager with database URL and engine options."""
        self.engine = create_async_engine(url, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
        print("🔌 Database SessionManager initialized")

    def get_session_factory(self) -> async_sessionmaker:
        """Get the async sessionmaker factory."""
        if not self._sessionmaker:
            raise RuntimeError("SessionManager not initialized. Call init() first.")
        return self._sessionmaker

    async def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self._sessionmaker:
            raise RuntimeError("SessionManager not initialized. Call init() first.")
        return self._sessionmaker()

    def get_engine(self) -> AsyncEngine:
        """Get the async engine."""
        if not self.engine:
            raise RuntimeError("SessionManager not initialized. Call init() first.")
        return self.engine

    async def close(self):
        """Close the database engine and cleanup resources."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self._sessionmaker = None
            print("🔌 Database SessionManager closed")


# Global SessionManager singleton
sessionmanager = SessionManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.

    Usage in routes:
        @app.get("/")
        async def read_root(db: AsyncSession = Depends(get_db)):
            # Use db session here
    """
    async with sessionmanager.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database_engine():
    """
    Close the database engine and cleanup resources.
    Should be called during application shutdown.
    """
    # Close SessionManager
    await sessionmanager.close()


def reset_database_engine():
    """
    Reset the SessionManager instance (useful for testing).
    """
    sessionmanager.engine = None
    sessionmanager._sessionmaker = None


async def validate_database_startup(async_engine: AsyncEngine):
    """
    Lightweight startup validation - just check migration version.
    Ensures database is migrated to the expected version.
    https://alembic.sqlalchemy.org/en/latest/cookbook.html
    """
    try:
        # Change to the correct directory for alembic to find migrations
        original_cwd = os.getcwd()
        db_dir = os.path.dirname(__file__)  # This is the app/db directory
        os.chdir(db_dir)
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
        os.chdir(original_cwd)
        if "async_engine" in locals():
            await async_engine.dispose()


async def initialize_database(settings: "Settings" = None):
    """
    Initialize and validate database on application startup.

    This function should be called during application initialization
    to ensure the database is properly set up and schema is current.

    Args:
        settings: Settings instance containing database connection info.
    """
    print("🔧 Initializing database...")

    if settings is None:
        raise ValueError("Settings instance must be provided")

    # Initialize the SessionManager
    sessionmanager.init(**settings.db_conn_info)

    # Get engine for validation
    engine = sessionmanager.get_engine()

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


async def run_migrations(async_engine: AsyncEngine, target_version: str = "head"):
    """Run migrations using the provided async engine."""
    # Change to the correct directory for alembic to find migrations
    original_cwd = os.getcwd()
    db_dir = os.path.dirname(__file__)  # This is the app/db directory
    os.chdir(db_dir)

    try:
        alembic_cfg = Config("alembic.ini")
    except Exception as e:
        print(f"❌ Failed to configure Alembic: {e}")
        raise
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
            print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await async_engine.dispose()


def run_upgrade(connection, cfg, target="head"):
    """Run alembic upgrade within a synchronous connection context."""
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, target)


async def reset_database_schema(async_engine):
    """
    Reset the database by dropping and recreating the schema.
    This ensures a clean state for development.
    """
    print("🗑️  Resetting database schema...")

    async with async_engine.begin() as conn:
        # Drop and recreate the schema
        db_schema = os.getenv("NACHET_SCHEMA")
        db_user = os.getenv("DB_USER")
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {db_schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {db_schema}"))
        # Restore default permissions
        await conn.execute(text(f"GRANT ALL ON SCHEMA {db_schema} TO {db_user}"))
        await conn.execute(text(f"GRANT ALL ON SCHEMA {db_schema} TO public"))

    print("✅ Database schema reset complete")


async def execute_sql_file(async_engine, sql_file_path):
    """Execute a SQL file using the provided async engine."""
    print(f"📄 Executing SQL file: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as file:
        sql_content = file.read()

    # remove comments
    sql_content = "\n".join(
        line for line in sql_content.splitlines() if not line.strip().startswith("--")
    )
    # Split SQL statements (basic splitting on semicolons)
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    async with async_engine.begin() as conn:
        with tqdm(
            total=len(statements), desc="   Executing SQL statements", unit="stmt"
        ) as pbar:
            for i, statement in enumerate(statements):
                if statement:  # Skip empty statements
                    try:
                        await conn.execute(text(statement))
                        pbar.update(1)
                    except Exception as e:
                        print(f"\n❌ Error executing statement {i + 1}: {e}")
                        print(f"   Statement: {statement[:100]}...")
                        raise

    print(f"✅ Successfully executed {len(statements)} SQL statements")
