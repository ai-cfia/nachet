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
        user_id = uuid7()
        org_user_role_id = uuid7()
        org_admin_role_id = uuid7()
        workflow_id = "test-workflow-123"
        status = ProcessingStatus.PENDING
        created_at = datetime.now(timezone.utc)

        # Create a real ImageProcessingState instance that will be returned
        _expected_state = ImageProcessingState(
            picture_id=picture_id,
            user_id=user_id,
            org_user_role_id=org_user_role_id,
            org_admin_role_id=org_admin_role_id,
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

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                workflow_id=workflow_id,
                picture_id=picture_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                status=status,
                created_at=created_at,
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
        user_id = uuid7()
        org_user_role_id = uuid7()
        org_admin_role_id = uuid7()
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

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                workflow_id=workflow_id,
                picture_id=picture_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                status=status,
                created_at=created_at,
                progress_percentage=custom_progress,
            )

            # Assert
            assert result.picture_id == picture_id
            assert result.workflow_id == workflow_id
            assert result.progress_percentage == custom_progress

    async def test_create_processing_state_with_required_workflow_id(self):
        """Test creating processing state with required workflow_id (primary key)."""
        # Arrange
        picture_id = uuid7()
        user_id = uuid7()
        org_user_role_id = uuid7()
        org_admin_role_id = uuid7()
        workflow_id = "test-workflow-required-123"
        status = ProcessingStatus.PENDING
        created_at = datetime.now(timezone.utc)

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                workflow_id=workflow_id,
                picture_id=picture_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                status=status,
                created_at=created_at,
                progress_percentage=0,
            )

            # Assert
            assert result.picture_id == picture_id
            assert result.workflow_id == workflow_id
            assert result.status == ProcessingStatus.PENDING.value

    async def test_create_processing_state_database_error(self):
        """Test that database errors are properly raised."""
        # Arrange
        picture_id = uuid7()
        user_id = uuid7()
        org_user_role_id = uuid7()
        org_admin_role_id = uuid7()
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

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act & Assert - should raise ImageProcessingError wrapping the original exception
            with pytest.raises(Exception) as exc_info:
                await InferenceService.create_processing_state(
                    workflow_id=workflow_id,
                    picture_id=picture_id,
                    user_id=user_id,
                    org_user_role_id=org_user_role_id,
                    org_admin_role_id=org_admin_role_id,
                    status=status,
                    created_at=created_at,
                    progress_percentage=0,
                )

            # The original exception might be wrapped, so just check it's raised
            assert exc_info.value is not None

    async def test_create_processing_state_with_different_status(self):
        """Test that status parameter is respected."""
        # Arrange
        picture_id = uuid7()
        user_id = uuid7()
        org_user_role_id = uuid7()
        org_admin_role_id = uuid7()
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

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await InferenceService.create_processing_state(
                workflow_id=workflow_id,
                picture_id=picture_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                status=status,
                created_at=created_at,
                progress_percentage=0,
            )

            # Assert - status should be what we passed
            assert result.status == ProcessingStatus.UPLOADED.value
            assert result.status != ProcessingStatus.PENDING.value
            assert result.status != ProcessingStatus.COMPLETED.value


@pytest.mark.asyncio
class TestUpdateProcessingStateStep:
    """Unit tests for update_processing_state_step()."""

    async def test_update_processing_state_single_field(self):
        """Test updating a single field in ImageProcessingState."""
        # Arrange
        from app.service.inference.state_management import update_processing_state_step
        from datetime import timezone

        workflow_id = "test-workflow-123"
        new_status = "uploaded"
        uploaded_at = datetime.now(timezone.utc)

        # Mock ImageProcessingState
        mock_state = MagicMock()
        mock_state.workflow_id = workflow_id
        mock_state.picture_id = uuid7()
        mock_state.status = "pending"
        mock_state.progress_percentage = 0

        # Mock session and result
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_processing_state_step(
                workflow_id=workflow_id, status=new_status, uploaded_at=uploaded_at
            )

            # Assert
            assert result["workflow_id"] == workflow_id
            assert result["status"] == new_status
            assert mock_state.status == new_status
            assert mock_state.uploaded_at == uploaded_at
            mock_session.commit.assert_awaited_once()
            mock_session.refresh.assert_awaited_once()

    async def test_update_processing_state_multiple_fields(self):
        """Test updating multiple fields at once."""
        # Arrange
        from app.service.inference.state_management import update_processing_state_step
        from datetime import timezone

        workflow_id = "test-workflow-456"
        defender_result = {"status": "clean", "scan_id": "12345"}

        # Mock ImageProcessingState
        mock_state = MagicMock()
        mock_state.workflow_id = workflow_id
        mock_state.picture_id = uuid7()
        mock_state.status = "defender_scanning"
        mock_state.progress_percentage = 40

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_processing_state_step(
                workflow_id=workflow_id,
                status="defender_scanned",
                defender_scan_completed_at=datetime.now(timezone.utc),
                defender_scan_result=defender_result,
                malware_detected=False,
                progress_percentage=50,
            )

            # Assert
            assert result["workflow_id"] == workflow_id
            assert result["status"] == "defender_scanned"
            assert mock_state.defender_scan_result == defender_result
            assert mock_state.malware_detected is False
            assert mock_state.progress_percentage == 50

    async def test_update_processing_state_not_found(self):
        """Test updating a non-existent processing state returns error dict."""
        # Arrange
        from app.service.inference.state_management import update_processing_state_step

        workflow_id = "nonexistent-workflow"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not found
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_processing_state_step(
                workflow_id=workflow_id, status="uploaded"
            )

            # Assert - should return error dict, not crash
            assert "error" in result

    async def test_update_processing_state_idempotent(self):
        """Test that updating the same field multiple times is safe (idempotency)."""
        # Arrange
        from app.service.inference.state_management import update_processing_state_step

        workflow_id = "test-workflow-idempotent"

        mock_state = MagicMock()
        mock_state.workflow_id = workflow_id
        mock_state.picture_id = uuid7()
        mock_state.status = "uploaded"
        mock_state.progress_percentage = 25

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act - call twice with same values
            result1 = await update_processing_state_step(
                workflow_id=workflow_id, status="uploaded", progress_percentage=25
            )
            result2 = await update_processing_state_step(
                workflow_id=workflow_id, status="uploaded", progress_percentage=25
            )

            # Assert - both should succeed
            assert result1["workflow_id"] == workflow_id
            assert result2["workflow_id"] == workflow_id
            assert mock_state.status == "uploaded"
            assert mock_state.progress_percentage == 25


@pytest.mark.asyncio
class TestUpdateInferenceStateStep:
    """Unit tests for update_inference_state_step()."""

    async def test_update_inference_state_status(self):
        """Test updating inference state status."""
        # Arrange
        from app.service.inference.state_management import update_inference_state_step
        from datetime import timezone

        inference_id = uuid7()
        started_at = datetime.now(timezone.utc)

        mock_state = MagicMock()
        mock_state.id = inference_id
        mock_state.status = "pending"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_inference_state_step(
                inference_request_state_id=inference_id,
                status="in_progress",
                started_at=started_at,
            )

            # Assert
            assert result["inference_request_state_id"] == str(inference_id)
            assert result["status"] == "in_progress"
            assert mock_state.status == "in_progress"
            assert mock_state.started_at == started_at

    async def test_update_inference_state_completion(self):
        """Test updating inference state with completion data."""
        # Arrange
        from app.service.inference.state_management import update_inference_state_step
        from datetime import timezone

        inference_id = uuid7()
        completed_at = datetime.now(timezone.utc)
        response_payload = {"boxes": [], "labels": [], "scores": []}

        mock_state = MagicMock()
        mock_state.id = inference_id
        mock_state.status = "in_progress"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_inference_state_step(
                inference_request_state_id=inference_id,
                status="completed",
                completed_at=completed_at,
                response_payload=response_payload,
            )

            # Assert
            assert result["status"] == "completed"
            assert mock_state.completed_at == completed_at
            assert mock_state.response_payload == response_payload

    async def test_update_inference_state_not_found(self):
        """Test updating non-existent inference state returns error dict."""
        # Arrange
        from app.service.inference.state_management import update_inference_state_step

        inference_id = uuid7()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await update_inference_state_step(
                inference_request_state_id=inference_id, status="completed"
            )

            # Assert
            assert "error" in result


@pytest.mark.asyncio
class TestMarkProcessingFailedStep:
    """Unit tests for mark_processing_failed_step()."""

    async def test_mark_processing_failed_basic(self):
        """Test marking processing state as failed."""
        # Arrange
        from app.service.inference.state_management import mark_processing_failed_step

        workflow_id = "test-workflow-failed"
        error_message = "Defender scan timeout"

        mock_state = MagicMock()
        mock_state.workflow_id = workflow_id
        mock_state.picture_id = uuid7()
        mock_state.status = "defender_scanning"
        mock_state.progress_percentage = 40

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await mark_processing_failed_step(
                workflow_id=workflow_id, error_message=error_message
            )

            # Assert
            assert result["status"] == "failed"
            assert result["error_message"] == error_message
            assert mock_state.status == "failed"
            assert mock_state.error_message == error_message
            assert mock_state.failed_at is not None
            assert mock_state.progress_percentage == 0

    async def test_mark_processing_failed_with_details(self):
        """Test marking processing state as failed with error details."""
        # Arrange
        from app.service.inference.state_management import mark_processing_failed_step

        workflow_id = "test-workflow-failed-details"
        error_message = "Sanitization failed"
        error_details = {"error_type": "SanitizationError", "code": 500}

        mock_state = MagicMock()
        mock_state.workflow_id = workflow_id
        mock_state.picture_id = uuid7()
        mock_state.status = "sanitizing"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await mark_processing_failed_step(
                workflow_id=workflow_id,
                error_message=error_message,
                error_details=error_details,
            )

            # Assert
            assert result["status"] == "failed"
            assert mock_state.error_details == error_details


@pytest.mark.asyncio
class TestMarkInferenceFailedStep:
    """Unit tests for mark_inference_failed_step()."""

    async def test_mark_inference_failed_basic(self):
        """Test marking inference state as failed."""
        # Arrange
        from app.service.inference.state_management import mark_inference_failed_step

        inference_id = uuid7()
        error_message = "Model endpoint timeout"

        mock_state = MagicMock()
        mock_state.id = inference_id
        mock_state.status = "in_progress"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await mark_inference_failed_step(
                inference_request_state_id=inference_id, error_message=error_message
            )

            # Assert
            assert result["status"] == "failed"
            assert result["error_message"] == error_message
            assert mock_state.status == "failed"
            assert mock_state.error_message == error_message
            assert mock_state.failed_at is not None

    async def test_mark_inference_failed_not_found(self):
        """Test marking non-existent inference as failed returns error dict."""
        # Arrange
        from app.service.inference.state_management import mark_inference_failed_step

        inference_id = uuid7()
        error_message = "Model error"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        with patch(
            "app.service.inference.state_management.sessionmanager"
        ) as mock_sessionmanager:
            mock_sessionmanager.get_session.return_value = mock_context_manager

            # Act
            result = await mark_inference_failed_step(
                inference_request_state_id=inference_id, error_message=error_message
            )

            # Assert
            assert "error" in result
