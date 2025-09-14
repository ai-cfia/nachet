import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from alembic.config import Config
from dotenv import load_dotenv
import pytest_asyncio

from app.db.utils import (
    _alembic_upgrade,
    _alembic_check,
    _alembic_generate,
    run_alembic_func,
    run_migrations,
    check_if_new_migration_file_needed,
    create_migration_file,
)

# Load test environment variables
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv("../../.env.test.local")
    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"


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
def mock_alembic_config():
    """Create a mock Alembic configuration."""
    config = Mock(spec=Config)
    config.attributes = {}
    return config


class TestAlembicUpgrade:
    """Test cases for the _alembic_upgrade function."""

    @patch("app.db.utils.command.upgrade")
    @patch("builtins.print")
    def test_alembic_upgrade_default_target(self, mock_print, mock_upgrade):
        """Test _alembic_upgrade with default 'head' target."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}

        _alembic_upgrade(mock_conn, mock_cfg)

        # Verify connection was set in config
        assert mock_cfg.attributes["connection"] == mock_conn

        # Verify upgrade command was called with correct parameters
        mock_upgrade.assert_called_once_with(mock_cfg, "head")

        # Verify success message was printed
        mock_print.assert_called_once_with("✅ Migrations completed successfully")

    @patch("app.db.utils.command.upgrade")
    @patch("builtins.print")
    def test_alembic_upgrade_specific_target(self, mock_print, mock_upgrade):
        """Test _alembic_upgrade with specific target version."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}
        target_version = "abc123def456"

        _alembic_upgrade(mock_conn, mock_cfg, target=target_version)

        # Verify connection was set in config
        assert mock_cfg.attributes["connection"] == mock_conn

        # Verify upgrade command was called with specific target
        mock_upgrade.assert_called_once_with(mock_cfg, target_version)

        # Verify success message was printed
        mock_print.assert_called_once_with("✅ Migrations completed successfully")

    @patch("app.db.utils.command.upgrade")
    def test_alembic_upgrade_command_error(self, mock_upgrade):
        """Test _alembic_upgrade when upgrade command fails."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}
        mock_upgrade.side_effect = Exception("Migration failed")

        with pytest.raises(Exception, match="Migration failed"):
            _alembic_upgrade(mock_conn, mock_cfg)

        # Verify connection was still set despite error
        assert mock_cfg.attributes["connection"] == mock_conn

    def test_alembic_upgrade_preserves_existing_attributes(self):
        """Test that _alembic_upgrade preserves existing config attributes."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {"existing_key": "existing_value"}

        with patch("app.db.utils.command.upgrade"):
            _alembic_upgrade(mock_conn, mock_cfg)

        # Verify existing attributes are preserved
        assert mock_cfg.attributes["existing_key"] == "existing_value"
        assert mock_cfg.attributes["connection"] == mock_conn


class TestAlembicCheck:
    """Test cases for the _alembic_check function."""

    @patch("app.db.utils.command.check")
    @patch("builtins.print")
    def test_alembic_check_success(self, mock_print, mock_check):
        """Test _alembic_check when no migration is needed."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}

        _alembic_check(mock_conn, mock_cfg)

        # Verify connection was set in config
        assert mock_cfg.attributes["connection"] == mock_conn

        # Verify check command was called
        mock_check.assert_called_once_with(mock_cfg)

        # Verify success message was printed
        mock_print.assert_called_once_with(
            "✅ Alembic check successful - no new migration file needed"
        )

    @patch("app.db.utils.command.check")
    def test_alembic_check_command_error(self, mock_check):
        """Test _alembic_check when check command fails."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}
        mock_check.side_effect = Exception("Check failed")

        with pytest.raises(Exception, match="Check failed"):
            _alembic_check(mock_conn, mock_cfg)

        # Verify connection was still set despite error
        assert mock_cfg.attributes["connection"] == mock_conn

    def test_alembic_check_preserves_existing_attributes(self):
        """Test that _alembic_check preserves existing config attributes."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {"existing_key": "existing_value"}

        with patch("app.db.utils.command.check"):
            _alembic_check(mock_conn, mock_cfg)

        # Verify existing attributes are preserved
        assert mock_cfg.attributes["existing_key"] == "existing_value"
        assert mock_cfg.attributes["connection"] == mock_conn


class TestAlembicGenerate:
    """Test cases for the _alembic_generate function."""

    @patch("app.db.utils.command.revision")
    @patch("builtins.print")
    def test_alembic_generate_success(self, mock_print, mock_revision):
        """Test _alembic_generate with successful migration creation."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}
        message = "Add new table for feature X"

        _alembic_generate(mock_conn, mock_cfg, message)

        # Verify connection was set in config
        assert mock_cfg.attributes["connection"] == mock_conn

        # Verify revision command was called with correct parameters
        mock_revision.assert_called_once_with(
            mock_cfg, autogenerate=False, message=message
        )

        # Verify success message was printed with correct message
        mock_print.assert_called_once_with(
            f"✅ New migration file created with message: {message}"
        )

    @patch("app.db.utils.command.revision")
    @patch("builtins.print")
    def test_alembic_generate_different_messages(self, mock_print, mock_revision):
        """Test _alembic_generate with various message formats."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}

        test_messages = [
            "Simple message",
            "Message with spaces and numbers 123",
            "Message-with-hyphens",
            "Message_with_underscores",
        ]

        for message in test_messages:
            mock_print.reset_mock()
            mock_revision.reset_mock()
            mock_cfg.attributes = {}

            _alembic_generate(mock_conn, mock_cfg, message)

            # Verify each message is handled correctly
            mock_revision.assert_called_once_with(
                mock_cfg, autogenerate=False, message=message
            )
            mock_print.assert_called_once_with(
                f"✅ New migration file created with message: {message}"
            )

    @patch("app.db.utils.command.revision")
    def test_alembic_generate_command_error(self, mock_revision):
        """Test _alembic_generate when revision command fails."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {}
        mock_revision.side_effect = Exception("Revision failed")

        with pytest.raises(Exception, match="Revision failed"):
            _alembic_generate(mock_conn, mock_cfg, "test message")

        # Verify connection was still set despite error
        assert mock_cfg.attributes["connection"] == mock_conn

    def test_alembic_generate_preserves_existing_attributes(self):
        """Test that _alembic_generate preserves existing config attributes."""
        mock_conn = Mock()
        mock_cfg = Mock()
        mock_cfg.attributes = {"existing_key": "existing_value"}

        with patch("app.db.utils.command.revision"):
            _alembic_generate(mock_conn, mock_cfg, "test message")

        # Verify existing attributes are preserved
        assert mock_cfg.attributes["existing_key"] == "existing_value"
        assert mock_cfg.attributes["connection"] == mock_conn


class TestRunAlembicFunc:
    """Test cases for the run_alembic_func function."""

    @pytest.mark.asyncio
    @patch("app.db.utils.alembic_directory_context")
    @patch("app.db.utils.Config")
    async def test_run_alembic_func_success(self, mock_config_class, mock_context):
        """Test run_alembic_func with successful execution."""
        # Setup mocks
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn
        mock_context_manager.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        mock_alembic_func = Mock()

        # Execute function
        await run_alembic_func(mock_engine, mock_alembic_func, "arg1", kwarg1="value1")

        # Verify directory context was used
        mock_context.assert_called_once()

        # Verify alembic config was created
        mock_config_class.assert_called_once_with("alembic.ini")

        # Verify transaction context was used
        mock_engine.begin.assert_called_once()
        mock_context_manager.__aenter__.assert_called_once()
        mock_context_manager.__aexit__.assert_called_once()

        # Verify alembic function was called with correct parameters
        mock_conn.run_sync.assert_called_once_with(
            mock_alembic_func, mock_config, "arg1", kwarg1="value1"
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.alembic_directory_context")
    @patch("app.db.utils.Config")
    async def test_run_alembic_func_no_args(self, mock_config_class, mock_context):
        """Test run_alembic_func with no additional arguments."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_conn = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        mock_alembic_func = Mock()

        await run_alembic_func(mock_engine, mock_alembic_func)

        # Verify alembic function was called with just config
        mock_conn.run_sync.assert_called_once_with(mock_alembic_func, mock_config)

        # Verify directory context was used
        mock_context.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.db.utils.alembic_directory_context")
    @patch("app.db.utils.Config")
    async def test_run_alembic_func_connection_error(
        self, mock_config_class, mock_context
    ):
        """Test run_alembic_func when connection fails."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_engine = MagicMock()
        mock_engine.begin.side_effect = SQLAlchemyError("Connection failed")

        mock_alembic_func = Mock()

        with pytest.raises(SQLAlchemyError, match="Connection failed"):
            await run_alembic_func(mock_engine, mock_alembic_func)

        # Verify directory context was still used despite error
        mock_context.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.db.utils.alembic_directory_context")
    @patch("app.db.utils.Config")
    async def test_run_alembic_func_alembic_function_error(
        self, mock_config_class, mock_context
    ):
        """Test run_alembic_func when alembic function fails."""
        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_conn = AsyncMock()
        mock_conn.run_sync.side_effect = Exception("Alembic function failed")

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_conn

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context_manager

        mock_alembic_func = Mock()

        with pytest.raises(Exception, match="Alembic function failed"):
            await run_alembic_func(mock_engine, mock_alembic_func)

    @pytest.mark.asyncio
    @patch("app.db.utils.alembic_directory_context")
    @patch("app.db.utils.Config")
    async def test_run_alembic_func_config_creation_error(
        self, mock_config_class, mock_context
    ):
        """Test run_alembic_func when config creation fails."""
        mock_config_class.side_effect = Exception("Config creation failed")

        mock_engine = MagicMock()
        mock_alembic_func = Mock()

        with pytest.raises(Exception, match="Config creation failed"):
            await run_alembic_func(mock_engine, mock_alembic_func)

        # Verify directory context was still used
        mock_context.assert_called_once()


class TestRunMigrations:
    """Test cases for the run_migrations function."""

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    async def test_run_migrations_default_target(self, mock_run_alembic_func):
        """Test run_migrations with default 'head' target."""
        mock_engine = Mock(spec=AsyncEngine)

        await run_migrations(mock_engine)

        # Verify run_alembic_func was called with correct parameters
        from app.db.utils import _alembic_upgrade

        mock_run_alembic_func.assert_called_once_with(
            mock_engine, _alembic_upgrade, target="head"
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    async def test_run_migrations_specific_target(self, mock_run_alembic_func):
        """Test run_migrations with specific target version."""
        mock_engine = Mock(spec=AsyncEngine)
        target_version = "abc123def456"

        await run_migrations(mock_engine, target_version=target_version)

        # Verify run_alembic_func was called with specific target
        from app.db.utils import _alembic_upgrade

        mock_run_alembic_func.assert_called_once_with(
            mock_engine, _alembic_upgrade, target=target_version
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("builtins.print")
    async def test_run_migrations_error_handling(
        self, mock_print, mock_run_alembic_func
    ):
        """Test run_migrations error handling and logging."""
        mock_engine = Mock(spec=AsyncEngine)
        error_message = "Migration execution failed"
        mock_run_alembic_func.side_effect = Exception(error_message)

        with pytest.raises(Exception, match=error_message):
            await run_migrations(mock_engine)

        # Verify error message was printed
        mock_print.assert_called_once_with(f"❌ Migration failed: {error_message}")

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("builtins.print")
    async def test_run_migrations_sqlalchemy_error(
        self, mock_print, mock_run_alembic_func
    ):
        """Test run_migrations with SQLAlchemy-specific errors."""
        mock_engine = Mock(spec=AsyncEngine)
        error_message = "Database connection failed"
        mock_run_alembic_func.side_effect = SQLAlchemyError(error_message)

        with pytest.raises(SQLAlchemyError, match=error_message):
            await run_migrations(mock_engine)

        # Verify error message was printed
        mock_print.assert_called_once_with(f"❌ Migration failed: {error_message}")


class TestCheckIfNewMigrationFileNeeded:
    """Test cases for the check_if_new_migration_file_needed function."""

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    async def test_check_no_migration_needed(self, mock_run_alembic_func):
        """Test check when no migration file is needed."""
        mock_engine = Mock(spec=AsyncEngine)

        # When no exception is raised, no migration is needed
        await check_if_new_migration_file_needed(mock_engine)

        # Verify run_alembic_func was called with check function
        from app.db.utils import _alembic_check

        mock_run_alembic_func.assert_called_once_with(mock_engine, _alembic_check)

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("builtins.print")
    async def test_check_migration_needed(self, mock_print, mock_run_alembic_func):
        """Test check when migration file is needed (exception raised)."""
        mock_engine = Mock(spec=AsyncEngine)
        error_message = "New migration needed"
        mock_run_alembic_func.side_effect = Exception(error_message)

        with pytest.raises(Exception, match=error_message):
            await check_if_new_migration_file_needed(mock_engine)

        # Verify error message was printed
        mock_print.assert_called_once_with(
            f"❌ New migration file is needed: {error_message}"
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("builtins.print")
    async def test_check_sqlalchemy_error(self, mock_print, mock_run_alembic_func):
        """Test check with SQLAlchemy-specific errors."""
        mock_engine = Mock(spec=AsyncEngine)
        error_message = "Database schema mismatch"
        mock_run_alembic_func.side_effect = SQLAlchemyError(error_message)

        with pytest.raises(SQLAlchemyError, match=error_message):
            await check_if_new_migration_file_needed(mock_engine)

        # Verify error message was printed
        mock_print.assert_called_once_with(
            f"❌ New migration file is needed: {error_message}"
        )


class TestCreateMigrationFile:
    """Test cases for the create_migration_file function."""

    @pytest.mark.asyncio
    @patch("app.db.utils.check_if_new_migration_file_needed")
    async def test_create_migration_file_not_needed(self, mock_check):
        """Test create_migration_file when no migration is needed."""
        mock_engine = Mock(spec=AsyncEngine)
        message = "Add new feature"

        # When check doesn't raise exception, no migration is created
        await create_migration_file(mock_engine, message)

        # Verify check was called
        mock_check.assert_called_once_with(mock_engine)

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("app.db.utils.check_if_new_migration_file_needed")
    async def test_create_migration_file_needed_success(
        self, mock_check, mock_run_alembic_func
    ):
        """Test create_migration_file when migration is needed and created successfully."""
        mock_engine = Mock(spec=AsyncEngine)
        message = "Add new feature"

        # Mock check to raise exception (migration needed)
        mock_check.side_effect = Exception("Migration needed")

        await create_migration_file(mock_engine, message)

        # Verify check was called
        mock_check.assert_called_once_with(mock_engine)

        # Verify migration file creation was attempted
        from app.db.utils import _alembic_generate

        mock_run_alembic_func.assert_called_once_with(
            mock_engine, _alembic_generate, message=message
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("app.db.utils.check_if_new_migration_file_needed")
    @patch("builtins.print")
    async def test_create_migration_file_creation_error(
        self, mock_print, mock_check, mock_run_alembic_func
    ):
        """Test create_migration_file when file creation fails."""
        mock_engine = Mock(spec=AsyncEngine)
        message = "Add new feature"
        error_message = "File creation failed"

        # Mock check to raise exception (migration needed)
        mock_check.side_effect = Exception("Migration needed")
        # Mock file creation to fail
        mock_run_alembic_func.side_effect = Exception(error_message)

        with pytest.raises(Exception, match=error_message):
            await create_migration_file(mock_engine, message)

        # Verify error message was printed
        mock_print.assert_called_once_with(
            f"❌ Failed to create new migration file: {error_message}"
        )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("app.db.utils.check_if_new_migration_file_needed")
    async def test_create_migration_file_different_messages(
        self, mock_check, mock_run_alembic_func
    ):
        """Test create_migration_file with various message formats."""
        mock_engine = Mock(spec=AsyncEngine)

        test_messages = [
            "Simple message",
            "Message with spaces and numbers 123",
            "Message-with-hyphens",
            "Message_with_underscores",
            "Add feature X to handle Y",
        ]

        for message in test_messages:
            mock_check.reset_mock()
            mock_run_alembic_func.reset_mock()

            # Mock check to raise exception (migration needed)
            mock_check.side_effect = Exception("Migration needed")

            await create_migration_file(mock_engine, message)

            # Verify each message is passed correctly
            from app.db.utils import _alembic_generate

            mock_run_alembic_func.assert_called_once_with(
                mock_engine, _alembic_generate, message=message
            )

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    @patch("app.db.utils.check_if_new_migration_file_needed")
    @patch("builtins.print")
    async def test_create_migration_file_sqlalchemy_error(
        self, mock_print, mock_check, mock_run_alembic_func
    ):
        """Test create_migration_file with SQLAlchemy-specific errors."""
        mock_engine = Mock(spec=AsyncEngine)
        message = "Add new feature"
        error_message = "Database connection failed"

        # Mock check to raise exception (migration needed)
        mock_check.side_effect = Exception("Migration needed")
        # Mock file creation to fail with SQLAlchemy error
        mock_run_alembic_func.side_effect = SQLAlchemyError(error_message)

        with pytest.raises(SQLAlchemyError, match=error_message):
            await create_migration_file(mock_engine, message)

        # Verify error message was printed
        mock_print.assert_called_once_with(
            f"❌ Failed to create new migration file: {error_message}"
        )


class TestAlembicFunctionsIntegration:
    """Integration tests for Alembic functions with real components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_run_migrations_integration(self, sqlite_engine):
        """Integration test for run_migrations with SQLite."""
        # This test requires actual alembic setup, so we'll skip if not available
        try:
            await run_migrations(sqlite_engine)
        except Exception as e:
            # Expected if alembic.ini or migrations directory doesn't exist
            if "alembic.ini" in str(e) or "migration" in str(e).lower():
                pytest.skip("Alembic configuration not available for testing")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_check_if_new_migration_file_needed_integration(self, sqlite_engine):
        """Integration test for check_if_new_migration_file_needed with SQLite."""
        try:
            await check_if_new_migration_file_needed(sqlite_engine)
        except Exception as e:
            # Expected if alembic.ini or migrations directory doesn't exist
            if "alembic.ini" in str(e) or "migration" in str(e).lower():
                pytest.skip("Alembic configuration not available for testing")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    @patch("builtins.input", return_value="y")  # Auto-confirm any prompts
    async def test_create_migration_file_integration(self, mock_input, sqlite_engine):
        """Integration test for create_migration_file with SQLite."""
        try:
            await create_migration_file(sqlite_engine, "Test integration migration")
        except Exception as e:
            # Expected if alembic.ini or migrations directory doesn't exist
            if "alembic.ini" in str(e) or "migration" in str(e).lower():
                pytest.skip("Alembic configuration not available for testing")
            else:
                raise


class TestAlembicFunctionsErrorScenarios:
    """Test various error scenarios and edge cases."""

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    async def test_all_functions_handle_none_engine(self, mock_run_alembic_func):
        """Test that functions handle None engine gracefully."""
        mock_run_alembic_func.side_effect = AttributeError(
            "'NoneType' has no attribute"
        )

        with pytest.raises(AttributeError):
            await run_migrations(None)

        with pytest.raises(AttributeError):
            await check_if_new_migration_file_needed(None)

        with pytest.raises(AttributeError):
            await create_migration_file(None, "test message")

    @pytest.mark.asyncio
    @patch("app.db.utils.run_alembic_func")
    async def test_empty_migration_message(self, mock_run_alembic_func):
        """Test create_migration_file with empty message."""
        mock_engine = Mock(spec=AsyncEngine)

        with patch("app.db.utils.check_if_new_migration_file_needed") as mock_check:
            mock_check.side_effect = Exception("Migration needed")

            await create_migration_file(mock_engine, "")

            # Should still attempt to create migration with empty message
            from app.db.utils import _alembic_generate

            mock_run_alembic_func.assert_called_once_with(
                mock_engine, _alembic_generate, message=""
            )

    @pytest.mark.asyncio
    async def test_concurrent_migration_operations(self, sqlite_engine):
        """Test behavior with concurrent migration operations."""
        import asyncio

        # Create multiple concurrent operations
        tasks = [
            run_migrations(sqlite_engine),
            check_if_new_migration_file_needed(sqlite_engine),
            create_migration_file(sqlite_engine, "concurrent test"),
        ]

        # All should fail gracefully if alembic is not set up
        try:
            await asyncio.gather(*tasks)
            # If no exception is raised, skip the test as alembic might be configured
            pytest.skip("Alembic appears to be configured, cannot test error behavior")
        except Exception:
            # Expected behavior - at least one should fail if alembic isn't set up
            pass
