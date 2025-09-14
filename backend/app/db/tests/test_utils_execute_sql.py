import os
import pytest
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import pytest_asyncio

from app.db.utils import execute_sql_file

# Load test environment variables
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv("../../.env.test.local")


@pytest_asyncio.fixture(scope="function")
async def sqlite_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create a simple test table for validation
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)
        )

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def postgresql_engine():
    """Create PostgreSQL engine using test environment variables."""
    # Only create if test database variables are available
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    nachet_schema = os.getenv("NACHET_SCHEMA")
    if not all([db_user, db_password, db_host, db_port, db_name, nachet_schema]):
        pytest.skip("PostgreSQL test database not available")

    engine = create_async_engine(
        f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?options=-csearch_path={nachet_schema}",
        echo=False,
        pool_pre_ping=True,
    )

    yield engine

    # Cleanup
    await engine.dispose()


class TestExecuteSqlFile:
    """Test cases for the execute_sql_file function."""

    @pytest.mark.asyncio
    async def test_execute_sql_file_success(self, sqlite_engine):
        """Test successful execution of valid SQL file."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('test1', 100);
        INSERT INTO test_table (name, value) VALUES ('test2', 200);
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                # Verify data was inserted
                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 2

                    result = await conn.execute(
                        text("SELECT name, value FROM test_table ORDER BY name")
                    )
                    rows = result.fetchall()
                    assert len(rows) == 2
                    assert rows[0] == ("test1", 100)
                    assert rows[1] == ("test2", 200)
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_multiple_statements(self, sqlite_engine):
        """Test file with multiple SQL statements."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('multi1', 10);
        INSERT INTO test_table (name, value) VALUES ('multi2', 20);
        INSERT INTO test_table (name, value) VALUES ('multi3', 30);
        UPDATE test_table SET value = value * 2 WHERE name = 'multi2';
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                # Verify all operations completed
                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT value FROM test_table WHERE name = 'multi2'")
                    )
                    value = result.scalar()
                    assert value == 40  # 20 * 2

                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 3
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_with_comments(self, sqlite_engine):
        """Test comment removal functionality."""
        sql_content = """
        -- This is a comment and should be ignored
        INSERT INTO test_table (name, value) VALUES ('comment_test', 999);
        -- Another comment
        -- Multiple comment lines
        INSERT INTO test_table (name, value) VALUES ('comment_test2', 888);
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                # Verify only SQL statements were executed, not comments
                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 2

                    result = await conn.execute(
                        text("SELECT value FROM test_table WHERE name = 'comment_test'")
                    )
                    value = result.scalar()
                    assert value == 999
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_empty_file(self, sqlite_engine):
        """Test handling of empty SQL files."""
        sql_content = ""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                # Should not raise an exception
                await execute_sql_file(sqlite_engine, f.name)

                # Verify no changes to database
                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 0
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_mixed_content(self, sqlite_engine):
        """Test files with comments, empty lines, and statements."""
        sql_content = """
        -- Initial comment

        INSERT INTO test_table (name, value) VALUES ('mixed1', 100);

        -- Middle comment

        INSERT INTO test_table (name, value) VALUES ('mixed2', 200);

        -- Final comment
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 2
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_unicode_content(self, sqlite_engine):
        """Test files with Unicode characters."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('��m�', 123);
        INSERT INTO test_table (name, value) VALUES ('B5AB', 456);
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sql", delete=False, encoding="utf-8"
        ) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT name FROM test_table ORDER BY value")
                    )
                    names = [row[0] for row in result.fetchall()]
                    assert "��m�" in names
                    assert "B5AB" in names
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_single_statement(self, sqlite_engine):
        """Test file with single statement."""
        sql_content = "INSERT INTO test_table (name, value) VALUES ('single', 42);"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(
                        text("SELECT value FROM test_table WHERE name = 'single'")
                    )
                    value = result.scalar()
                    assert value == 42
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_missing_file(self, sqlite_engine):
        """Test FileNotFoundError handling."""
        non_existent_file = "/path/that/does/not/exist.sql"

        with pytest.raises(FileNotFoundError):
            await execute_sql_file(sqlite_engine, non_existent_file)

    @pytest.mark.asyncio
    async def test_execute_sql_file_invalid_sql(self, sqlite_engine):
        """Test behavior with invalid SQL syntax."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('valid', 100);
        INVALID SQL STATEMENT THAT WILL FAIL;
        INSERT INTO test_table (name, value) VALUES ('after_error', 200);
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                with pytest.raises(Exception):  # Should raise database error
                    await execute_sql_file(sqlite_engine, f.name)

                # Verify transaction was rolled back (no data should be inserted)
                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 0  # Transaction should have been rolled back
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    @patch("builtins.open", side_effect=IOError("Permission denied"))
    async def test_execute_sql_file_file_read_error(
        self, mock_file_open, sqlite_engine
    ):
        """Test handling of file read errors."""
        with pytest.raises(IOError, match="Permission denied"):
            await execute_sql_file(sqlite_engine, "some_file.sql")

    @pytest.mark.asyncio
    @patch("app.db.utils.tqdm")
    async def test_execute_sql_file_progress_tracking(self, mock_tqdm, sqlite_engine):
        """Test that progress tracking is properly initialized."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('progress1', 1);
        INSERT INTO test_table (name, value) VALUES ('progress2', 2);
        """

        mock_progress = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = mock_progress

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                # Verify tqdm was called with correct parameters
                mock_tqdm.assert_called_once()
                args, kwargs = mock_tqdm.call_args
                assert kwargs["total"] == 2  # Two SQL statements
                assert kwargs["desc"] == "   Executing SQL statements"
                assert kwargs["unit"] == "stmt"

                # Verify progress was updated for each statement
                assert mock_progress.update.call_count == 2
                mock_progress.update.assert_called_with(1)
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_transaction_behavior(self, sqlite_engine):
        """Test that all statements execute within a single transaction."""
        sql_content = """
        INSERT INTO test_table (name, value) VALUES ('trans1', 1);
        INSERT INTO test_table (name, value) VALUES ('trans2', 2);
        """

        # Create a mock engine that fails on the second execute
        mock_conn = AsyncMock()
        execute_calls = []

        async def mock_execute(statement):
            execute_calls.append(statement)
            if len(execute_calls) == 2:  # Fail on second statement
                raise SQLAlchemyError("Simulated database error")
            return MagicMock()

        mock_conn.execute = mock_execute

        # Create a proper async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                with pytest.raises(SQLAlchemyError):
                    await execute_sql_file(mock_engine, f.name)

                # Verify both statements were attempted
                assert len(execute_calls) == 2
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_execute_sql_file_with_postgresql(self, postgresql_engine):
        """Integration test with actual PostgreSQL database."""
        # Get schema name from environment
        schema_name = os.getenv("NACHET_SCHEMA")

        # Create schema and test table
        async with postgresql_engine.begin() as conn:
            # Create schema if it doesn't exist
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

            # Create test table in the schema
            await conn.execute(
                text(f"""
                CREATE TABLE IF NOT EXISTS "{schema_name}".integration_test (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

        sql_content = f"""
        INSERT INTO "{schema_name}".integration_test (name) VALUES ('pg_test1');
        INSERT INTO "{schema_name}".integration_test (name) VALUES ('pg_test2');
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(postgresql_engine, f.name)

                # Verify data was inserted
                async with postgresql_engine.begin() as conn:
                    result = await conn.execute(
                        text(f'SELECT COUNT(*) FROM "{schema_name}".integration_test')
                    )
                    count = result.scalar()
                    assert count >= 2  # May have data from other tests

                    result = await conn.execute(
                        text(f"""
                        SELECT name FROM "{schema_name}".integration_test
                        WHERE name IN ('pg_test1', 'pg_test2')
                        ORDER BY name
                    """)
                    )
                    names = [row[0] for row in result.fetchall()]
                    assert "pg_test1" in names
                    assert "pg_test2" in names
            finally:
                os.unlink(f.name)
                # Cleanup test data
                async with postgresql_engine.begin() as conn:
                    await conn.execute(
                        text(f'DROP TABLE IF EXISTS "{schema_name}".integration_test')
                    )

    @pytest.mark.asyncio
    async def test_execute_sql_file_whitespace_handling(self, sqlite_engine):
        """Test handling of various whitespace scenarios."""
        sql_content = """


        INSERT INTO test_table (name, value) VALUES ('whitespace1', 1);


        INSERT INTO test_table (name, value) VALUES ('whitespace2', 2);


        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 2
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_sql_file_statement_splitting(self, sqlite_engine):
        """Test correct statement splitting on semicolons."""
        sql_content = """INSERT INTO test_table (name, value) VALUES ('split1', 1);INSERT INTO test_table (name, value) VALUES ('split2', 2);"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(sql_content)
            f.flush()

            try:
                await execute_sql_file(sqlite_engine, f.name)

                async with sqlite_engine.begin() as conn:
                    result = await conn.execute(text("SELECT COUNT(*) FROM test_table"))
                    count = result.scalar()
                    assert count == 2

                    result = await conn.execute(
                        text("SELECT name FROM test_table ORDER BY name")
                    )
                    names = [row[0] for row in result.fetchall()]
                    assert names == ["split1", "split2"]
            finally:
                os.unlink(f.name)
