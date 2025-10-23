import os
import pytest
import asyncio
from unittest.mock import patch, Mock
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import pytest_asyncio

from app.db.utils import (
    initialize_database,
    sessionmanager,
    reset_database_engine,
    cleanup_temp_db,
)
from app.api.config import Settings

# Load test environment variables
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv("../../.env.test.local")


# SQLite database file cleanup
SQLITE_DB_FILES = [
    "test_migration.db.local",
    "test.db",
    "test1.db",
    "test2.db",
    "first.db",
    "second.db",
]


@pytest.fixture(scope="session", autouse=True)
def cleanup_sqlite_db():
    """Auto-cleanup fixture that runs at the end of the test session."""
    yield  # Run tests
    # Use the utils cleanup function for all potential SQLite files
    for db_file in SQLITE_DB_FILES:
        cleanup_temp_db(f"sqlite+aiosqlite:///{db_file}")


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


@pytest.fixture
def mock_settings():
    """Create a mock Settings instance."""
    settings = Mock(spec=Settings)
    settings.db_conn_info = {
        "url": "sqlite+aiosqlite:///:memory:",
        "echo": False,
    }
    return settings


@pytest.fixture
def postgresql_settings():
    """Create Settings instance for PostgreSQL testing."""
    settings = Mock(spec=Settings)
    settings.db_conn_info = {
        "url": "postgresql+psycopg://user:pass@localhost:5432/test",
        "echo": True,
        "pool_recycle": 3600,
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_pre_ping": True,
    }
    return settings


class TestInitializeDatabase:
    """Test cases for the initialize_database function."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()
        # Clean up any SQLite database files that might have been created
        for db_file in SQLITE_DB_FILES:
            cleanup_temp_db(f"sqlite+aiosqlite:///{db_file}")

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("app.db.utils._get_logger")
    async def test_initialize_database_success(
        self, mock_get_logger, mock_validate, mock_settings
    ):
        """Test successful database initialization."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        await initialize_database(mock_settings)

        # Verify logger was called (3 times: init start, SessionManager init, init complete)
        assert mock_logger.info.call_count == 3

        # Check for start message
        first_call = mock_logger.info.call_args_list[0]
        assert first_call[0][0] == "Initializing database..."

        # Second call is from SessionManager
        second_call = mock_logger.info.call_args_list[1]
        assert second_call[0][0] == "Database SessionManager initialized"

        # Check for completion message
        third_call = mock_logger.info.call_args_list[2]
        assert third_call[0][0] == "Database initialization completed successfully"

        # Verify sessionmanager was initialized
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    async def test_initialize_database_none_settings(self):
        """Test initialize_database with None settings."""
        with pytest.raises(ValueError, match="Settings instance must be provided"):
            await initialize_database(None)

        # Verify sessionmanager was not initialized
        assert sessionmanager.engine is None
        assert sessionmanager._sessionmaker is None

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("builtins.print")
    async def test_initialize_database_different_db_configs(
        self, mock_print, mock_validate, postgresql_settings
    ):
        """Test initialize_database with different database configurations."""
        # Test with SQLite config
        sqlite_settings = Mock(spec=Settings)
        sqlite_settings.db_conn_info = {
            "url": "sqlite+aiosqlite:///test.db",
            "echo": True,
        }

        await initialize_database(sqlite_settings)

        # Verify sessionmanager was initialized
        assert sessionmanager.engine is not None

        # Reset for next test
        reset_database_engine()

        # Test with PostgreSQL config
        await initialize_database(postgresql_settings)

        # Verify sessionmanager was initialized with new settings
        assert sessionmanager.engine is not None

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("builtins.print")
    async def test_initialize_database_with_engine_kwargs(
        self, mock_print, mock_validate
    ):
        """Test initialize_database with additional engine kwargs."""
        settings = Mock(spec=Settings)
        settings.db_conn_info = {
            "url": "sqlite+aiosqlite:///:memory:",
            "echo": True,
            "connect_args": {"check_same_thread": False},
        }

        await initialize_database(settings)

        # Verify sessionmanager was initialized
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_sessionmanager_init_error(self, mock_validate):
        """Test initialize_database when sessionmanager.init fails."""
        settings = Mock(spec=Settings)
        # Invalid URL to cause initialization error
        settings.db_conn_info = {
            "url": "invalid://database/url",
            "echo": False,
        }

        with pytest.raises(Exception):
            await initialize_database(settings)

        # Verify validation was not called due to init failure
        mock_validate.assert_not_called()

        # Verify sessionmanager state
        assert sessionmanager.engine is None
        assert sessionmanager._sessionmaker is None

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("builtins.print")
    async def test_initialize_database_validation_error(
        self, mock_print, mock_validate, mock_settings
    ):
        """Test initialize_database when database validation fails."""
        mock_validate.side_effect = RuntimeError("Database validation failed")

        with pytest.raises(RuntimeError, match="Database validation failed"):
            await initialize_database(mock_settings)

        # Verify sessionmanager was initialized but validation failed
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("builtins.print")
    async def test_initialize_database_sqlalchemy_validation_error(
        self, mock_print, mock_validate, mock_settings
    ):
        """Test initialize_database when validation fails with SQLAlchemy error."""
        mock_validate.side_effect = SQLAlchemyError("Connection failed")

        with pytest.raises(SQLAlchemyError, match="Connection failed"):
            await initialize_database(mock_settings)

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_get_engine_error(
        self, mock_validate, mock_settings
    ):
        """Test initialize_database when get_engine fails."""
        # Mock sessionmanager to fail on get_engine
        with patch.object(
            sessionmanager,
            "get_engine",
            side_effect=RuntimeError("Engine not available"),
        ):
            with pytest.raises(RuntimeError, match="Engine not available"):
                await initialize_database(mock_settings)

        # Verify validation was not called due to get_engine failure
        mock_validate.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("app.db.utils._get_logger")
    async def test_initialize_database_print_messages_format(
        self, mock_get_logger, mock_validate, mock_settings
    ):
        """Test that initialize_database logs correctly formatted messages."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        await initialize_database(mock_settings)

        # Verify logger was called with expected messages (3 times total)
        assert mock_logger.info.call_count == 3

        # Check messages
        first_call = mock_logger.info.call_args_list[0]
        second_call = mock_logger.info.call_args_list[1]
        third_call = mock_logger.info.call_args_list[2]

        assert first_call[0][0] == "Initializing database..."
        assert second_call[0][0] == "Database SessionManager initialized"
        assert third_call[0][0] == "Database initialization completed successfully"

    @pytest.mark.asyncio
    async def test_initialize_database_real_settings_instance(self):
        """Test initialize_database with a real Settings instance."""
        # Create real Settings instance with invalid connection values
        with patch.dict(
            os.environ,
            {
                "DB_USER": "nonexistent_user",
                "DB_PASSWORD": "invalid_password",
                "DB_HOST": "nonexistent.host.invalid",
                "DB_PORT": "5432",
                "DB_NAME": "nonexistent_db",
                "NACHET_SCHEMA": "nonexistent_schema",
            },
        ):
            settings = Settings(testing=False)  # Use production db_conn_info

            # Since we can't connect to the nonexistent database, expect connection error
            with pytest.raises(Exception):
                await initialize_database(settings)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_settings_with_testing_true(self, mock_validate):
        """Test initialize_database with Settings in testing mode."""
        settings = Settings(testing=True)  # Uses SQLite

        await initialize_database(settings)

        # Verify sessionmanager was initialized
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    @patch("builtins.print")
    async def test_initialize_database_multiple_calls(self, mock_print, mock_validate):
        """Test calling initialize_database multiple times (reinitializing)."""
        settings1 = Mock(spec=Settings)
        settings1.db_conn_info = {
            "url": "sqlite+aiosqlite:///test1.db",
            "echo": False,
        }

        settings2 = Mock(spec=Settings)
        settings2.db_conn_info = {
            "url": "sqlite+aiosqlite:///test2.db",
            "echo": True,
        }

        # First initialization
        await initialize_database(settings1)
        first_engine = sessionmanager.engine

        # Second initialization (should replace first)
        await initialize_database(settings2)
        second_engine = sessionmanager.engine

        # Verify engines are different (reinitialized)
        assert first_engine is not second_engine
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called twice
        assert mock_validate.call_count == 2


class TestInitializeDatabaseIntegration:
    """Integration tests for initialize_database with real components."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_initialize_database_sqlite_integration(self):
        """Integration test with real SQLite database."""
        settings = Settings(testing=True)  # Uses SQLite configuration

        try:
            await initialize_database(settings)

            # Verify sessionmanager is properly initialized
            assert sessionmanager.engine is not None
            assert sessionmanager._sessionmaker is not None

            # Verify we can get sessions
            session = sessionmanager.get_session()
            assert session is not None
            await session.close()

            # Clean up
            await sessionmanager.close()

        except (RuntimeError, Exception) as e:
            # If Alembic is not set up or database validation fails, this is expected
            error_msg = str(e).lower()
            if (
                "alembic" in error_msg
                or "migration" in error_msg
                or "target db is not up to date" in error_msg
                or "database startup validation failed" in error_msg
            ):
                pytest.skip(
                    "Alembic configuration or database migrations not available for testing"
                )
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_initialize_database_postgresql_integration(self, postgresql_engine):
        """Integration test with real PostgreSQL database."""
        # Create settings that match the test engine
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        nachet_schema = os.getenv("NACHET_SCHEMA")

        settings = Mock(spec=Settings)
        settings.db_conn_info = {
            "url": f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?options=-csearch_path={nachet_schema}",
            "echo": False,
            "pool_pre_ping": True,
        }

        try:
            await initialize_database(settings)

            # Verify sessionmanager is properly initialized
            assert sessionmanager.engine is not None
            assert sessionmanager._sessionmaker is not None

            # Verify we can get sessions
            session = sessionmanager.get_session()
            assert session is not None
            await session.close()

            # Clean up
            await sessionmanager.close()

        except (RuntimeError, Exception) as e:
            # If Alembic is not set up or database schema issues, this is expected
            error_msg = str(e).lower()
            if (
                "alembic" in error_msg
                or "migration" in error_msg
                or "schema" in error_msg
                or "target db is not up to date" in error_msg
                or "database startup validation failed" in error_msg
            ):
                pytest.skip("Alembic/schema configuration not available for testing")
            else:
                raise


class TestInitializeDatabaseErrorScenarios:
    """Test various error scenarios and edge cases."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    async def test_initialize_database_missing_db_conn_info(self):
        """Test initialize_database when settings lacks db_conn_info."""
        settings = Mock(spec=Settings)
        del settings.db_conn_info  # Remove the attribute

        with pytest.raises(AttributeError):
            await initialize_database(settings)

    @pytest.mark.asyncio
    async def test_initialize_database_empty_db_conn_info(self):
        """Test initialize_database with empty db_conn_info."""
        settings = Mock(spec=Settings)
        settings.db_conn_info = {}

        with pytest.raises(Exception):  # Should fail during engine creation
            await initialize_database(settings)

    @pytest.mark.asyncio
    async def test_initialize_database_invalid_url_format(self):
        """Test initialize_database with invalid URL format."""
        settings = Mock(spec=Settings)
        settings.db_conn_info = {
            "url": "not-a-valid-database-url",
            "echo": False,
        }

        with pytest.raises(Exception):
            await initialize_database(settings)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_engine_disposal_on_validation_error(
        self, mock_validate, mock_settings
    ):
        """Test that engine is properly handled when validation fails."""
        mock_validate.side_effect = Exception("Validation failed")

        with pytest.raises(Exception, match="Validation failed"):
            await initialize_database(mock_settings)

        # Engine should still be available in sessionmanager despite validation failure
        # (it's up to the caller to handle cleanup)
        assert sessionmanager.engine is not None

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_concurrent_initialization(
        self, mock_validate, mock_settings
    ):
        """Test concurrent initialization attempts."""
        import asyncio

        async def init_task():
            await initialize_database(mock_settings)

        # Create multiple concurrent initialization tasks
        tasks = [init_task() for _ in range(3)]

        # All should complete (though only the last one's settings will be active)
        await asyncio.gather(*tasks)

        # Sessionmanager should be initialized
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

    @pytest.mark.asyncio
    @patch("app.db.utils._get_logger")
    async def test_initialize_database_print_exception_handling(
        self, mock_get_logger, mock_settings
    ):
        """Test that logger failures during initialization are handled properly."""
        # Make logger fail on info calls
        mock_logger = Mock()
        mock_logger.info.side_effect = Exception("Logger failed")
        mock_get_logger.return_value = mock_logger

        # Should raise the logger exception
        with pytest.raises(Exception, match="Logger failed"):
            await initialize_database(mock_settings)

    @pytest.mark.asyncio
    async def test_initialize_database_with_malformed_settings(self):
        """Test initialize_database with malformed settings object."""

        # Create object that looks like Settings but behaves unexpectedly
        class MalformedSettings:
            @property
            def db_conn_info(self):
                raise Exception("Settings access failed")

        malformed_settings = MalformedSettings()

        with pytest.raises(Exception, match="Settings access failed"):
            await initialize_database(malformed_settings)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_validation_timeout(
        self, mock_validate, mock_settings
    ):
        """Test initialize_database when validation times out."""

        async def slow_validation(engine):
            import asyncio

            await asyncio.sleep(0.1)  # Simulate slow validation
            raise asyncio.TimeoutError("Validation timed out")

        mock_validate.side_effect = slow_validation

        with pytest.raises(asyncio.TimeoutError, match="Validation timed out"):
            await initialize_database(mock_settings)


class TestInitializeDatabaseEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_with_all_engine_options(self, mock_validate):
        """Test initialize_database with comprehensive engine configuration."""
        # Test with SQLite and its supported options only
        settings = Mock(spec=Settings)
        settings.db_conn_info = {
            "url": "sqlite+aiosqlite:///:memory:",
            "echo": True,
            "connect_args": {"check_same_thread": False, "timeout": 30},
        }

        await initialize_database(settings)

        # Verify sessionmanager was initialized
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Verify validation was called
        mock_validate.assert_called_once_with(sessionmanager.engine)

    @pytest.mark.asyncio
    async def test_initialize_database_empty_string_settings(self):
        """Test initialize_database with empty string as settings."""
        with pytest.raises(AttributeError):
            await initialize_database("")

    @pytest.mark.asyncio
    async def test_initialize_database_numeric_settings(self):
        """Test initialize_database with numeric value as settings."""
        with pytest.raises(AttributeError):
            await initialize_database(123)

    @pytest.mark.asyncio
    @patch("app.db.utils.validate_database_startup")
    async def test_initialize_database_preserve_sessionmanager_state(
        self, mock_validate
    ):
        """Test that initialize_database properly manages sessionmanager state."""
        settings1 = Mock(spec=Settings)
        settings1.db_conn_info = {
            "url": "sqlite+aiosqlite:///first.db",
            "echo": False,
        }

        # First initialization
        await initialize_database(settings1)
        first_engine = sessionmanager.engine
        first_sessionmaker = sessionmanager._sessionmaker

        # Verify initial state
        assert first_engine is not None
        assert first_sessionmaker is not None

        # Second initialization with different settings
        settings2 = Mock(spec=Settings)
        settings2.db_conn_info = {
            "url": "sqlite+aiosqlite:///second.db",
            "echo": True,
        }

        await initialize_database(settings2)
        second_engine = sessionmanager.engine
        second_sessionmaker = sessionmanager._sessionmaker

        # Verify state changed
        assert second_engine is not first_engine
        assert second_sessionmaker is not first_sessionmaker
        assert second_engine is not None
        assert second_sessionmaker is not None
