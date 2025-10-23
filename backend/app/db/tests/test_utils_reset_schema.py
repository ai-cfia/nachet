import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import pytest_asyncio

from app.db.utils import reset_database_schema

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
        f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
        echo=False,
        pool_pre_ping=True,
    )

    yield engine
    await engine.dispose()


class TestResetDatabaseSchema:
    """Test cases for the reset_database_schema function."""

    def _setup_mock_engine_with_dialect(self):
        """Helper method to set up mock engine with dialect and identifier preparer."""
        executed_statements = []

        # Create a regular mock instead of AsyncMock to avoid coroutine issues
        mock_conn = MagicMock()

        async def mock_execute(statement):
            executed_statements.append(str(statement))
            return MagicMock()

        mock_conn.execute = mock_execute

        # Mock the dialect and identifier preparer
        mock_dialect = MagicMock()
        mock_identifier_preparer = MagicMock()

        # Configure the quote_identifier method to return properly quoted identifiers
        def quote_identifier(name):
            return f'"{name}"'

        mock_identifier_preparer.quote_identifier = quote_identifier
        mock_dialect.identifier_preparer = mock_identifier_preparer
        mock_conn.dialect = mock_dialect

        # Create proper async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        return mock_engine, executed_statements

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NACHET_SCHEMA": "test_schema", "DB_USER": "test_user"})
    async def test_reset_database_schema_with_mock_engine(self):
        """Test reset_database_schema with mocked engine operations."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        # Execute the function
        await reset_database_schema(mock_engine)

        # Verify the correct SQL statements were executed
        assert len(executed_statements) == 4

        # Check DROP SCHEMA statement (identifiers are properly quoted)
        assert 'DROP SCHEMA IF EXISTS "test_schema" CASCADE' in executed_statements[0]

        # Check CREATE SCHEMA statement
        assert 'CREATE SCHEMA "test_schema"' in executed_statements[1]

        # Check GRANT statements
        assert (
            'GRANT ALL ON SCHEMA "test_schema" TO "test_user"' in executed_statements[2]
        )
        assert 'GRANT ALL ON SCHEMA "test_schema" TO public' in executed_statements[3]

    @pytest.mark.asyncio
    @patch.dict(
        os.environ, {"NACHET_SCHEMA": "test_schema_special", "DB_USER": "special_user"}
    )
    async def test_reset_database_schema_uses_environment_variables(self):
        """Test that the function uses correct environment variables."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        await reset_database_schema(mock_engine)

        # Verify environment variables are used correctly
        schema_statements = [
            stmt for stmt in executed_statements if "test_schema_special" in stmt
        ]
        user_statements = [
            stmt for stmt in executed_statements if "special_user" in stmt
        ]

        assert len(schema_statements) == 4  # All statements should reference the schema
        assert len(user_statements) == 1  # One statement should reference the user

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NACHET_SCHEMA": "test_schema", "DB_USER": "test_user"})
    async def test_reset_database_schema_database_error(self):
        """Test error handling when database operations fail."""
        mock_conn = MagicMock()

        # Mock the execute method to raise an error
        mock_conn.execute.side_effect = SQLAlchemyError("Database connection error")

        # Create proper async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        # Should raise the database error
        with pytest.raises(SQLAlchemyError, match="Database connection error"):
            await reset_database_schema(mock_engine)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NACHET_SCHEMA": "", "DB_USER": "test_user"})
    async def test_reset_database_schema_missing_schema_env(self):
        """Test behavior when NACHET_SCHEMA environment variable is missing."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        await reset_database_schema(mock_engine)

        # Should still execute with empty schema name
        assert len(executed_statements) == 4
        assert 'DROP SCHEMA IF EXISTS "" CASCADE' in executed_statements[0]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NACHET_SCHEMA": "test_schema", "DB_USER": ""})
    async def test_reset_database_schema_missing_user_env(self):
        """Test behavior when DB_USER environment variable is missing."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        await reset_database_schema(mock_engine)

        # Should still execute with empty user name
        assert len(executed_statements) == 4
        assert 'GRANT ALL ON SCHEMA "test_schema" TO ""' in executed_statements[2]

    @pytest.mark.asyncio
    async def test_reset_database_schema_sqlite_compatibility(self, sqlite_engine):
        """Test that the function handles SQLite gracefully (even though it's PostgreSQL-specific)."""
        # SQLite doesn't support schemas, so this should fail gracefully
        with pytest.raises(Exception):
            await reset_database_schema(sqlite_engine)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"NACHET_SCHEMA": "test_schema", "DB_USER": "test_user"})
    async def test_reset_database_schema_transaction_behavior(self):
        """Test that all operations happen within a single transaction."""
        mock_conn = MagicMock()
        execute_call_count = 0

        async def mock_execute(statement):
            nonlocal execute_call_count
            execute_call_count += 1
            # Fail on the third statement to test transaction rollback
            if execute_call_count == 3:
                raise SQLAlchemyError("Simulated failure on GRANT statement")
            return MagicMock()

        mock_conn.execute = mock_execute

        # Create proper async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        # Should raise error on third statement
        with pytest.raises(
            SQLAlchemyError, match="Simulated failure on GRANT statement"
        ):
            await reset_database_schema(mock_engine)

        # Verify transaction context manager was used
        mock_engine.begin.assert_called_once()
        mock_context_manager.__aenter__.assert_called_once()
        mock_context_manager.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    @patch.dict(
        os.environ, {"NACHET_SCHEMA": "schema-with-hyphens", "DB_USER": "test-user"}
    )
    async def test_reset_database_schema_special_characters_in_names(self):
        """Test that the function properly handles schema and user names with special characters."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        # Should now work with proper quoting
        await reset_database_schema(mock_engine)

        # Verify the correct quoted SQL statements were executed
        assert len(executed_statements) == 4
        assert (
            'DROP SCHEMA IF EXISTS "schema-with-hyphens" CASCADE'
            in executed_statements[0]
        )
        assert 'CREATE SCHEMA "schema-with-hyphens"' in executed_statements[1]
        assert (
            'GRANT ALL ON SCHEMA "schema-with-hyphens" TO "test-user"'
            in executed_statements[2]
        )
        assert (
            'GRANT ALL ON SCHEMA "schema-with-hyphens" TO public'
            in executed_statements[3]
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_reset_database_schema_integration(self, postgresql_engine):
        """Integration test with actual PostgreSQL database."""
        # Get environment variables
        schema_name = os.getenv("NACHET_SCHEMA")
        db_user = os.getenv("DB_USER")

        # Ensure schema exists before test
        async with postgresql_engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            # Create a test table to verify CASCADE works
            await conn.execute(
                text(f'''
                CREATE TABLE IF NOT EXISTS "{schema_name}".test_reset_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50)
                )
            ''')
            )

        # Execute reset_database_schema
        await reset_database_schema(postgresql_engine)

        # Verify schema was recreated (table should be gone)
        async with postgresql_engine.begin() as conn:
            # Check that schema exists
            result = await conn.execute(
                text("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name = :schema_name
            """),
                {"schema_name": schema_name},
            )
            schema_exists = result.fetchone() is not None
            assert schema_exists, f"Schema {schema_name} should exist after reset"

            # Check that the test table was dropped (CASCADE effect)
            result = await conn.execute(
                text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = :schema_name
                AND table_name = 'test_reset_table'
            """),
                {"schema_name": schema_name},
            )
            table_exists = result.fetchone() is not None
            assert not table_exists, "Test table should be dropped by CASCADE"

            # Verify permissions - check if user can create tables
            try:
                await conn.execute(
                    text(f'''
                    CREATE TABLE "{schema_name}".permission_test (id INTEGER)
                ''')
                )
                # Clean up
                await conn.execute(text(f'DROP TABLE "{schema_name}".permission_test'))
                permissions_work = True
            except Exception:
                permissions_work = False

            assert permissions_work, (
                f"User {db_user} should have permissions on schema {schema_name}"
            )

    @pytest.mark.asyncio
    @patch.dict(
        os.environ, {"NACHET_SCHEMA": "test_with_special_chars", "DB_USER": "test_user"}
    )
    async def test_reset_database_schema_sql_injection_safety(self):
        """Test that the function handles special characters safely with quoting."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()

        await reset_database_schema(mock_engine)

        # Verify that the schema name is properly quoted
        schema_statement = executed_statements[1]
        assert '"test_with_special_chars"' in schema_statement

        # Note: The function still uses f-strings, so it's still potentially vulnerable
        # to SQL injection if environment variables contain malicious SQL, but quoting
        # provides some protection for normal identifier characters

    @pytest.mark.asyncio
    @patch("app.db.utils._get_logger")
    @patch.dict(os.environ, {"NACHET_SCHEMA": "test_schema", "DB_USER": "test_user"})
    async def test_reset_database_schema_output_messages(self, mock_get_logger):
        """Test that the function logs appropriate status messages."""
        mock_engine, executed_statements = self._setup_mock_engine_with_dialect()
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        await reset_database_schema(mock_engine)

        # Verify logger was called
        assert mock_logger.info.call_count == 2

        # Check for start message
        first_call = mock_logger.info.call_args_list[0]
        assert first_call[0][0] == "Resetting database schema"
        assert first_call[1]["schema"] == "test_schema"

        # Check for completion message
        second_call = mock_logger.info.call_args_list[1]
        assert second_call[0][0] == "Database schema reset complete"
        assert second_call[1]["schema"] == "test_schema"
