from __future__ import annotations

import os
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    AsyncGenerator,
    Protocol,
    runtime_checkable,
    Union,
)
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
    pass


@runtime_checkable
class SettingsProtocol(Protocol):
    """Protocol defining the Settings interface needed by this module.

    This allows us to avoid circular imports while maintaining type safety.
    Any object with a db_conn_info property that returns a dict will satisfy this protocol.
    """

    @property
    def db_conn_info(self) -> dict:
        """Database connection configuration dictionary."""
        ...


@runtime_checkable
class AsyncEngineProtocol(Protocol):
    """Protocol for AsyncEngine-like objects.

    This protocol allows mocks and real AsyncEngine objects to be used interchangeably.
    """

    def begin(self) -> Any: ...
    async def dispose(self) -> None: ...


@runtime_checkable
class AsyncSessionMakerProtocol(Protocol):
    """Protocol for async_sessionmaker-like objects.

    This protocol allows mocks and real async_sessionmaker objects to be used interchangeably.
    """

    def __call__(self) -> AsyncSession: ...
    def begin(self) -> Any: ...


# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        # Import here to avoid circular dependency
        from app.service import LogService

        _logger = LogService.get_logger()
    return _logger


class SessionManager:
    """Manages asynchronous DB sessions with connection pooling."""

    def __init__(self) -> None:
        self.engine: Optional[Union[AsyncEngine, AsyncEngineProtocol]] = None
        self._sessionmaker: Optional[
            Union[async_sessionmaker, AsyncSessionMakerProtocol]
        ] = None

    def init(self, url: str, **engine_kwargs):
        """Initialize the SessionManager with database URL and engine options."""
        self.engine = create_async_engine(url, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
        _get_logger().info(
            "Database SessionManager initialized", database_url=url.split("@")[-1]
        )  # Hide credentials

    def get_session_factory(
        self,
    ) -> Union[async_sessionmaker, AsyncSessionMakerProtocol]:
        """Get the async sessionmaker factory."""
        if not self._sessionmaker:
            raise RuntimeError("SessionManager not initialized. Call init() first.")
        return self._sessionmaker

    def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self._sessionmaker:
            raise RuntimeError("SessionManager not initialized. Call init() first.")
        return self._sessionmaker()

    def get_engine(self) -> Union[AsyncEngine, AsyncEngineProtocol]:
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
            _get_logger().info("Database SessionManager closed")


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
    session = sessionmanager.get_session()
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


async def initialize_database(settings: Optional[SettingsProtocol] = None):
    """
    Initialize and validate database on application startup.

    This function should be called during application initialization
    to ensure the database is properly set up and schema is current.

    Args:
        settings: Settings instance containing database connection info.
    """
    _get_logger().info("Initializing database...")

    if settings is None:
        raise ValueError("Settings instance must be provided")

    # Initialize the SessionManager
    sessionmanager.init(**settings.db_conn_info)

    # Get engine for validation
    engine = sessionmanager.get_engine()

    # Validate database schema version
    await validate_database_startup(engine)

    _get_logger().info("Database initialization completed successfully")


def cleanup_temp_db(db_url: str):
    """Cleanup temporary database file if using SQLite."""
    if db_url.startswith("sqlite"):
        temp_db_name = db_url.split("///")[-1]
        _get_logger().info("Cleanup temporary database", database_file=temp_db_name)
        # Ensure clean slate by removing file if it exists (for idempotent tests)
        try:
            os.unlink(temp_db_name)
        except FileNotFoundError:
            pass  # File doesn't exist, which is what we want


async def reset_database_schema(async_engine):
    """
    Reset the database by dropping and recreating the schema.
    This ensures a clean state for development.
    """
    db_schema = os.getenv("NACHET_SCHEMA")
    db_user = os.getenv("DB_USER")

    _get_logger().info("Resetting database schema", schema=db_schema)

    async with async_engine.begin() as conn:
        # Use SQLAlchemy's quote_identifier for safe identifier quoting
        dialect = conn.dialect
        quoted_schema = dialect.identifier_preparer.quote_identifier(db_schema)
        quoted_user = dialect.identifier_preparer.quote_identifier(db_user)

        # Execute DDL statements with properly quoted identifiers
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {quoted_schema}"))
        # Restore default permissions
        await conn.execute(
            text(f"GRANT ALL ON SCHEMA {quoted_schema} TO {quoted_user}")
        )
        await conn.execute(text(f"GRANT ALL ON SCHEMA {quoted_schema} TO public"))

    _get_logger().info("Database schema reset complete", schema=db_schema)


async def execute_sql_file(async_engine, sql_file_path):
    """Execute a SQL file using the provided async engine."""
    _get_logger().info("Executing SQL file", file_path=sql_file_path)

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
                        _get_logger().error(
                            f"Error executing statement {i + 1}",
                            error=str(e),
                            statement_preview=statement[:100],
                            statement_number=i + 1,
                        )
                        raise

    _get_logger().info(
        "Successfully executed SQL statements",
        file_path=sql_file_path,
        statement_count=len(statements),
    )


##########################################################################################
# Alembic command wrappers
##########################################################################################


@contextmanager
def alembic_directory_context():
    """Context manager for changing to alembic directory and back."""
    original_cwd = os.getcwd()
    db_dir = os.path.dirname(__file__)  # This is the app/db directory
    os.chdir(db_dir)
    try:
        yield db_dir
    finally:
        os.chdir(original_cwd)


def _check_migration_version_sync(connection, script_dir):
    """Synchronous helper function to check migration version."""
    context = migration.MigrationContext.configure(connection)
    current_heads = set(context.get_current_heads())
    expected_heads = set(script_dir.get_heads())
    return current_heads, expected_heads


async def validate_database_startup(
    async_engine: Union[AsyncEngine, AsyncEngineProtocol],
):
    """
    Lightweight startup validation - just check migration version.
    Ensures database is migrated to the expected version.
    https://alembic.sqlalchemy.org/en/latest/cookbook.html
    """

    with alembic_directory_context():
        alembic_cfg = Config("alembic.ini")
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        async with async_engine.begin() as connection:
            current_heads, expected_heads = await connection.run_sync(
                _check_migration_version_sync, script_dir
            )
            if current_heads == expected_heads:
                _get_logger().info(
                    "Target DB is up to date - Database startup validation passed",
                    current_versions=list(current_heads),
                    expected_versions=list(expected_heads),
                )
            else:
                _get_logger().error(
                    "Target DB is NOT up to date - Database startup validation failed",
                    current_versions=list(current_heads),
                    expected_versions=list(expected_heads),
                )
                raise RuntimeError(f"""
                ❌ Target DB is NOT up to date
                Current DB version(s) : {current_heads}
                Expected DB version(s): {expected_heads}
                ❌ Database startup validation failed
                ❌ Application cannot start with invalid database state
                """)


def _alembic_upgrade(connection, cfg, target="head"):
    """Run alembic upgrade within a synchronous connection context."""
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, target)
    _get_logger().info("Migrations completed successfully", target=target)


def _alembic_check(connection, cfg):
    """Check if revision command with autogenerate has pending upgrade ops."""
    cfg.attributes["connection"] = connection
    command.check(cfg)
    _get_logger().info("Alembic check successful - no new migration file needed")


def _alembic_generate(connection, cfg, message: str):
    """Run alembic revision with autogenerate within a synchronous connection context."""
    cfg.attributes["connection"] = connection
    command.revision(cfg, autogenerate=False, message=message)
    _get_logger().info("New migration file created", message=message)


async def run_alembic_func(
    async_engine: Union[AsyncEngine, AsyncEngineProtocol], alembic_func, *args, **kwargs
):
    """Run an Alembic function within the context of the async engine."""
    with alembic_directory_context():
        alembic_cfg = Config("alembic.ini")

        async with async_engine.begin() as conn:
            await conn.run_sync(alembic_func, alembic_cfg, *args, **kwargs)


async def run_migrations(
    async_engine: Union[AsyncEngine, AsyncEngineProtocol], target_version: str = "head"
):
    """Run migrations using the provided async engine."""
    try:
        await run_alembic_func(async_engine, _alembic_upgrade, target=target_version)
    except Exception as e:
        _get_logger().error(
            "Migration failed", error=str(e), target_version=target_version
        )
        raise


async def check_if_new_migration_file_needed(
    async_engine: Union[AsyncEngine, AsyncEngineProtocol],
):
    """Check if a new migration file is needed."""
    try:
        await run_alembic_func(async_engine, _alembic_check)
    except Exception as e:
        _get_logger().warning("New migration file is needed", error=str(e))
        raise


async def create_migration_file(
    async_engine: Union[AsyncEngine, AsyncEngineProtocol], message: str
):
    """Create a new migration file if needed."""
    # if exception is raised, new migration file is needed
    try:
        await check_if_new_migration_file_needed(async_engine)
        return
    except Exception:
        pass

    try:
        await run_alembic_func(async_engine, _alembic_generate, message=message)
    except Exception as e:
        _get_logger().error(
            "Failed to create new migration file", error=str(e), message=message
        )
        raise
