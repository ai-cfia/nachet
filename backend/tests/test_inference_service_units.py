"""
Unit tests for InferenceService dependency methods.

These tests use mocks to test individual methods in isolation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid6 import uuid7
from datetime import datetime, timezone

from app.service.inference import InferenceService
from app.service.constants import ProcessingStatus
from app.db.model import ImageProcessingState


@pytest.mark.asyncio
class TestCreateProcessingState:
    """Unit tests for InferenceService.create_processing_state()."""

    async def test_create_processing_state_success(self):
        """Test successful creation of ImageProcessingState."""
        # Arrange
        picture_id = uuid7()
        workflow_id = "test-workflow-123"
        status = ProcessingStatus.PENDING
        created_at = datetime.now(timezone.utc)

        # Create a real ImageProcessingState instance that will be returned
        _expected_state = ImageProcessingState(
            picture_id=picture_id,
            status=status,
            created_at=created_at,
            progress_percentage=0,
            workflow_id=workflow_id,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Mock sessionmanager.get_session() context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("app.service.inference.sessionmanager") as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                picture_id=picture_id,
                status=status,
                created_at=created_at,
                workflow_id=workflow_id,
                progress_percentage=0,
            )

            # Assert
            assert result is not None
            assert result.picture_id == picture_id
            assert result.workflow_id == workflow_id
            assert result.status == ProcessingStatus.PENDING.value
            assert result.progress_percentage == 0

            # Verify session operations
            mock_session.add.assert_called_once()
            mock_session.commit.assert_awaited_once()
            mock_session.refresh.assert_awaited_once()

    async def test_create_processing_state_with_custom_progress(self):
        """Test creating processing state with custom progress."""
        # Arrange
        picture_id = uuid7()
        workflow_id = "test-workflow-456"
        status = ProcessingStatus.UPLOADED
        created_at = datetime.now(timezone.utc)
        custom_progress = 25

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("app.service.inference.sessionmanager") as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                picture_id=picture_id,
                status=status,
                created_at=created_at,
                workflow_id=workflow_id,
                progress_percentage=custom_progress,
            )

            # Assert
            assert result.picture_id == picture_id
            assert result.workflow_id == workflow_id
            assert result.progress_percentage == custom_progress

    async def test_create_processing_state_without_workflow_id(self):
        """Test creating processing state without workflow_id (optional)."""
        # Arrange
        picture_id = uuid7()
        status = ProcessingStatus.PENDING
        created_at = datetime.now(timezone.utc)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("app.service.inference.sessionmanager") as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                picture_id=picture_id,
                status=status,
                created_at=created_at,
                workflow_id=None,
                progress_percentage=0,
            )

            # Assert
            assert result.picture_id == picture_id
            assert result.workflow_id is None
            assert result.status == ProcessingStatus.PENDING.value

    async def test_create_processing_state_database_error(self):
        """Test that database errors are properly raised."""
        # Arrange
        picture_id = uuid7()
        workflow_id = "test-workflow-789"
        status = ProcessingStatus.PENDING
        created_at = datetime.now(timezone.utc)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("app.service.inference.sessionmanager") as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act & Assert - should raise ImageProcessingError wrapping the original exception
            with pytest.raises(Exception) as exc_info:
                await InferenceService.create_processing_state(
                    picture_id=picture_id,
                    status=status,
                    created_at=created_at,
                    workflow_id=workflow_id,
                    progress_percentage=0,
                )

            # The original exception might be wrapped, so just check it's raised
            assert exc_info.value is not None

    async def test_create_processing_state_with_different_status(self):
        """Test that status parameter is respected."""
        # Arrange
        picture_id = uuid7()
        workflow_id = "test-workflow-status"
        status = ProcessingStatus.UPLOADED  # Different status
        created_at = datetime.now(timezone.utc)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch("app.service.inference.sessionmanager") as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                picture_id=picture_id,
                status=status,
                created_at=created_at,
                workflow_id=workflow_id,
                progress_percentage=0,
            )

            # Assert - status should be what we passed
            assert result.status == ProcessingStatus.UPLOADED.value
            assert result.status != ProcessingStatus.PENDING.value
            assert result.status != ProcessingStatus.COMPLETED.value
