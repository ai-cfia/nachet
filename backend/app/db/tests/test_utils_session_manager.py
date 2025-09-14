import pytest
import os
from dotenv import load_dotenv
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from app.db.utils import (
    SessionManager,
    sessionmanager,
    get_db,
    close_database_engine,
    reset_database_engine,
)

# Load test environment variables
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv("../../.env.test.local")

class TestSessionManager:
    """Test cases for the SessionManager class."""

    def test_session_manager_init_state(self):
        """Test initial state of SessionManager."""
        sm = SessionManager()
        assert sm.engine is None
        assert sm._sessionmaker is None

    @patch("app.db.utils.create_async_engine")
    @patch("app.db.utils.async_sessionmaker")
    @patch("builtins.print")
    def test_session_manager_init_success(
        self, mock_print, mock_sessionmaker, mock_create_engine
    ):
        """Test successful initialization of SessionManager."""
        # Setup mocks
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        mock_sm = Mock(spec=async_sessionmaker)
        mock_sessionmaker.return_value = mock_sm

        # Create and initialize SessionManager
        sm = SessionManager()
        sm.init("sqlite+aiosqlite:///:memory:", echo=True, pool_size=5)

        # Verify engine creation
        mock_create_engine.assert_called_once_with(
            "sqlite+aiosqlite:///:memory:", echo=True, pool_size=5
        )

        # Verify sessionmaker creation
        mock_sessionmaker.assert_called_once_with(mock_engine, expire_on_commit=False)

        # Verify state
        assert sm.engine == mock_engine
        assert sm._sessionmaker == mock_sm

        # Verify print message
        mock_print.assert_called_once_with("🔌 Database SessionManager initialized")

    def test_session_manager_get_session_factory_success(self):
        """Test successful get_session_factory."""
        sm = SessionManager()
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        sm._sessionmaker = mock_sessionmaker

        result = sm.get_session_factory()
        assert result == mock_sessionmaker

    def test_session_manager_get_session_factory_not_initialized(self):
        """Test get_session_factory when not initialized."""
        sm = SessionManager()

        with pytest.raises(
            RuntimeError, match="SessionManager not initialized. Call init\\(\\) first."
        ):
            sm.get_session_factory()

    @pytest.mark.asyncio
    async def test_session_manager_get_session_success(self):
        """Test successful get_session."""
        sm = SessionManager()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        mock_sessionmaker.return_value = mock_session
        sm._sessionmaker = mock_sessionmaker

        result = await sm.get_session()

        mock_sessionmaker.assert_called_once()
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_session_manager_get_session_not_initialized(self):
        """Test get_session when not initialized."""
        sm = SessionManager()

        with pytest.raises(
            RuntimeError, match="SessionManager not initialized. Call init\\(\\) first."
        ):
            await sm.get_session()

    def test_session_manager_get_engine_success(self):
        """Test successful get_engine."""
        sm = SessionManager()
        mock_engine = AsyncMock(spec=AsyncEngine)
        sm.engine = mock_engine

        result = sm.get_engine()
        assert result == mock_engine

    def test_session_manager_get_engine_not_initialized(self):
        """Test get_engine when not initialized."""
        sm = SessionManager()

        with pytest.raises(
            RuntimeError, match="SessionManager not initialized. Call init\\(\\) first."
        ):
            sm.get_engine()

    @pytest.mark.asyncio
    @patch("builtins.print")
    async def test_session_manager_close_with_engine(self, mock_print):
        """Test close when engine exists."""
        sm = SessionManager()
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        sm.engine = mock_engine
        sm._sessionmaker = mock_sessionmaker

        await sm.close()

        # Verify engine dispose was called
        mock_engine.dispose.assert_called_once()

        # Verify cleanup
        assert sm.engine is None
        assert sm._sessionmaker is None

        # Verify print message
        mock_print.assert_called_once_with("🔌 Database SessionManager closed")

    @pytest.mark.asyncio
    @patch("builtins.print")
    async def test_session_manager_close_without_engine(self, mock_print):
        """Test close when no engine exists."""
        sm = SessionManager()

        await sm.close()

        # Should not print anything if no engine to close
        mock_print.assert_not_called()

        # State should remain None
        assert sm.engine is None
        assert sm._sessionmaker is None

    @pytest.mark.asyncio
    async def test_session_manager_close_dispose_error(self):
        """Test close when engine dispose raises an error."""
        sm = SessionManager()
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose.side_effect = Exception("Dispose failed")
        sm.engine = mock_engine

        # Should propagate the exception
        with pytest.raises(Exception, match="Dispose failed"):
            await sm.close()


class TestGlobalSessionManager:
    """Test cases for the global sessionmanager singleton."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    def test_sessionmanager_is_singleton(self):
        """Test that sessionmanager is a singleton instance."""
        from app.db.utils import sessionmanager as sm1
        from app.db.utils import sessionmanager as sm2

        assert sm1 is sm2
        assert isinstance(sm1, SessionManager)

    @patch("app.db.utils.create_async_engine")
    @patch("app.db.utils.async_sessionmaker")
    def test_sessionmanager_init_affects_global(
        self, mock_sessionmaker, mock_create_engine
    ):
        """Test that initializing sessionmanager affects the global instance."""
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine
        mock_sm = Mock(spec=async_sessionmaker)
        mock_sessionmaker.return_value = mock_sm

        # Initialize global sessionmanager
        sessionmanager.init("sqlite+aiosqlite:///:memory:")

        # Verify global state
        assert sessionmanager.engine == mock_engine
        assert sessionmanager._sessionmaker == mock_sm


class TestGetDb:
    """Test cases for the get_db function."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    async def test_get_db_success(self):
        """Test successful get_db operation."""
        # Setup mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the get_session method to return our mock session as a coroutine
        async def mock_get_session():
            return mock_session

        with patch.object(sessionmanager, 'get_session', side_effect=mock_get_session):
            # Test get_db
            async_gen = get_db()
            yielded_session = await async_gen.__anext__()

            assert yielded_session == mock_session

            # Verify session operations weren't called yet
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_not_called()
            mock_session.close.assert_not_called()

            # Complete the generator
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

            # Verify commit and close were called
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_exception_rollback(self):
        """Test get_db rollback on exception."""
        # Setup mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the get_session method to return our mock session as a coroutine
        async def mock_get_session():
            return mock_session

        with patch.object(sessionmanager, 'get_session', side_effect=mock_get_session):
            # Test get_db with exception
            async_gen = get_db()
            await async_gen.__anext__()

            # Simulate exception during usage
            with pytest.raises(ValueError, match="Test exception"):
                try:
                    raise ValueError("Test exception")
                except ValueError as e:
                    await async_gen.athrow(e)

            # Verify rollback was called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_db_not_initialized(self):
        """Test get_db when sessionmanager is not initialized."""
        # Mock get_session to raise RuntimeError as it would when not initialized
        with patch.object(sessionmanager, 'get_session', side_effect=RuntimeError("SessionManager not initialized. Call init() first.")):
            with pytest.raises(RuntimeError, match="SessionManager not initialized"):
                async_gen = get_db()
                await async_gen.__anext__()


class TestCloseDatabaseEngine:
    """Test cases for the close_database_engine function."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    async def test_close_database_engine(self):
        """Test close_database_engine function."""
        # Setup mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        sessionmanager.engine = mock_engine
        sessionmanager._sessionmaker = AsyncMock()

        with patch.object(sessionmanager, "close") as mock_close:
            await close_database_engine()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_database_engine_not_initialized(self):
        """Test close_database_engine when not initialized."""
        # Should not raise error
        with patch.object(sessionmanager, "close") as mock_close:
            await close_database_engine()
            mock_close.assert_called_once()


class TestResetDatabaseEngine:
    """Test cases for the reset_database_engine function."""

    def test_reset_database_engine(self):
        """Test reset_database_engine function."""
        # Setup initial state
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        sessionmanager.engine = mock_engine
        sessionmanager._sessionmaker = mock_sessionmaker

        # Verify initial state
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Reset
        reset_database_engine()

        # Verify reset state
        assert sessionmanager.engine is None
        assert sessionmanager._sessionmaker is None

    def test_reset_database_engine_already_none(self):
        """Test reset_database_engine when already None."""
        # Ensure initial state is None
        sessionmanager.engine = None
        sessionmanager._sessionmaker = None

        # Should not raise error
        reset_database_engine()

        # Verify still None
        assert sessionmanager.engine is None
        assert sessionmanager._sessionmaker is None


class TestSessionManagerIntegration:
    """Integration tests for SessionManager with real components."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    async def test_sessionmanager_full_lifecycle(self):
        """Test full lifecycle of SessionManager with SQLite."""
        # Initialize
        sessionmanager.init("sqlite+aiosqlite:///:memory:", echo=False)

        # Verify initialization
        assert sessionmanager.engine is not None
        assert sessionmanager._sessionmaker is not None

        # Get session factory
        factory = sessionmanager.get_session_factory()
        assert factory is not None

        # Get engine
        engine = sessionmanager.get_engine()
        assert engine is not None

        # Get session
        session = await sessionmanager.get_session()
        assert session is not None
        await session.close()

        # Close
        await sessionmanager.close()

        # Verify cleanup
        assert sessionmanager.engine is None
        assert sessionmanager._sessionmaker is None

    @pytest.mark.asyncio
    async def test_get_db_full_lifecycle(self):
        """Test full lifecycle of get_db function."""
        # Initialize sessionmanager
        sessionmanager.init("sqlite+aiosqlite:///:memory:", echo=False)

        # Use get_db
        async for session in get_db():
            assert session is not None
            # Session should be usable here
            break

        # Clean up
        await sessionmanager.close()

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test creating multiple sessions."""
        # Initialize
        sessionmanager.init("sqlite+aiosqlite:///:memory:", echo=False)

        # Get multiple sessions
        session1 = await sessionmanager.get_session()
        session2 = await sessionmanager.get_session()

        assert session1 is not session2

        await session1.close()
        await session2.close()
        await sessionmanager.close()

    @pytest.mark.asyncio
    async def test_sessionmanager_reinitialization(self):
        """Test reinitializing SessionManager."""
        # First initialization
        sessionmanager.init("sqlite+aiosqlite:///:memory:", echo=False)
        first_engine = sessionmanager.engine

        # Second initialization (should replace first)
        sessionmanager.init("sqlite+aiosqlite:///:memory:", echo=True)
        second_engine = sessionmanager.engine

        assert first_engine is not second_engine

        # Clean up
        await sessionmanager.close()


class TestErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Reset sessionmanager state before each test."""
        reset_database_engine()

    def teardown_method(self):
        """Clean up after each test."""
        reset_database_engine()

    @pytest.mark.asyncio
    async def test_session_manager_methods_not_initialized(self):
        """Test all SessionManager methods when not initialized."""
        sm = SessionManager()

        # Test all methods that should raise RuntimeError
        with pytest.raises(RuntimeError):
            sm.get_session_factory()

        with pytest.raises(RuntimeError):
            await sm.get_session()

        with pytest.raises(RuntimeError):
            sm.get_engine()

        # close() should not raise error even when not initialized
        await sm.close()

    @patch("app.db.utils.create_async_engine")
    def test_session_manager_init_engine_creation_error(self, mock_create_engine):
        """Test SessionManager.init when engine creation fails."""
        mock_create_engine.side_effect = Exception("Database connection failed")

        sm = SessionManager()

        with pytest.raises(Exception, match="Database connection failed"):
            sm.init("invalid://url")

        # Verify state remains uninitialized
        assert sm.engine is None
        assert sm._sessionmaker is None
