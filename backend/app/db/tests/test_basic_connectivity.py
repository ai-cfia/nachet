"""
Basic connectivity tests for SQLite and PostgreSQL databases.
"""

import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load test environment variables
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv("../../.env.test.local")


@pytest_asyncio.fixture(scope="function")
async def sqlite_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def postgresql_engine():
    """Create PostgreSQL engine using test environment variables."""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    nachet_schema = os.getenv("NACHET_SCHEMA")

    if not all([db_user, db_password, db_host, db_port, db_name, nachet_schema]):
        pytest.skip("PostgreSQL test database env vars missing")

    engine = create_async_engine(
        f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?options=-csearch_path={nachet_schema}",
        echo=False,
        pool_pre_ping=True,
    )

    yield engine
    await engine.dispose()


class TestBasicConnectivity:
    """Test basic database connectivity and operations."""

    @pytest.mark.asyncio
    async def test_sqlite_connectivity(self, sqlite_engine):
        """Test SQLite connection and table listing."""
        async with sqlite_engine.begin() as conn:
            # Query tables in SQLite
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';")
            )
            tables = [row[0] for row in result.fetchall()]

        assert isinstance(tables, list)

    @pytest.mark.asyncio
    async def test_postgresql_connectivity(self, postgresql_engine):
        """Test PostgreSQL connection and table listing."""
        async with postgresql_engine.begin() as conn:
            # Query tables in PostgreSQL
            result = await conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
            """)
            )
            tables = [row[0] for row in result.fetchall()]

        assert isinstance(tables, list)

    @pytest.mark.asyncio
    async def test_sqlite_create_drop_table(self, sqlite_engine):
        """Test creating and dropping a table in SQLite."""
        async with sqlite_engine.begin() as conn:
            # Create table
            await conn.execute(
                text("""
                CREATE TABLE test_connectivity (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """)
            )

            # Verify table exists
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_connectivity';"
                )
            )
            assert result.fetchone() is not None

            # Drop table
            await conn.execute(text("DROP TABLE test_connectivity"))

            # Verify table is gone
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_connectivity';"
                )
            )
            assert result.fetchone() is None

    @pytest.mark.asyncio
    async def test_postgresql_create_drop_table(self, postgresql_engine):
        """Test creating and dropping a table in PostgreSQL."""
        async with postgresql_engine.begin() as conn:
            # Create table
            await conn.execute(
                text("""
                CREATE TABLE test_connectivity (
                    id SERIAL PRIMARY KEY,
                    name TEXT
                )
            """)
            )

            # Verify table exists
            result = await conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                AND table_name = 'test_connectivity'
            """)
            )
            assert result.fetchone() is not None

            # Drop table
            await conn.execute(text("DROP TABLE test_connectivity"))

            # Verify table is gone
            result = await conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                AND table_name = 'test_connectivity'
            """)
            )
            assert result.fetchone() is None
