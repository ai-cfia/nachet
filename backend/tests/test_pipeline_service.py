"""
Tests for PipelineService - CRUD operations for pipelines.

Access Control:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only
"""

import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.service.pipeline import PipelineService
from app.db.model import Pipeline

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


# ============================================================================
# PipelineService Tests (New CRUD Methods)
# ============================================================================


class TestPipelineServiceGetAll:
    """Test PipelineService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all pipelines."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline1_id = uuid4()
        pipeline2_id = uuid4()

        # Mock pipelines
        pipeline1 = Mock(spec=Pipeline)
        pipeline1.id = pipeline1_id
        pipeline1.name = "Pipeline 1"
        pipeline1.created_by = "user1"
        pipeline1.creation_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pipeline1.description = "Test pipeline 1"
        pipeline1.job_name = "job1"
        pipeline1.version = "1.0.0"
        pipeline1.dataset = "dataset1"
        pipeline1.identifiable = {"seed1": True}
        pipeline1.metrics = {"accuracy": 0.95}
        pipeline1.default = False
        pipeline1.active = True
        pipeline1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        pipeline2 = Mock(spec=Pipeline)
        pipeline2.id = pipeline2_id
        pipeline2.name = "Pipeline 2"
        pipeline2.created_by = "user2"
        pipeline2.creation_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        pipeline2.description = "Test pipeline 2"
        pipeline2.job_name = "job2"
        pipeline2.version = "2.0.0"
        pipeline2.dataset = "dataset2"
        pipeline2.identifiable = {"seed2": True}
        pipeline2.metrics = {"accuracy": 0.97}
        pipeline2.default = True
        pipeline2.active = True
        pipeline2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService - just verify user exists
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([pipeline1, pipeline2], 2))
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await PipelineService.get_all(user_id)

        # Verify - BaseCRUDService returns paginated response with "items" key
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "Pipeline 1"
        assert result["items"][1]["name"] == "Pipeline 2"
        assert result["total"] == 2
        assert result["offset"] == 0
        assert result["limit"] == 100
        assert result["has_more"] is False
        assert result["items"][0]["active"] is True
        assert result["items"][1]["default"] is True


class TestPipelineServiceGetById:
    """Test PipelineService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a pipeline by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock pipeline
        pipeline = Mock(spec=Pipeline)
        pipeline.id = pipeline_id
        pipeline.name = "Pipeline 1"
        pipeline.created_by = "user1"
        pipeline.creation_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pipeline.description = "Test pipeline"
        pipeline.job_name = "job1"
        pipeline.version = "1.0.0"
        pipeline.dataset = "dataset1"
        pipeline.identifiable = {"seed1": True}
        pipeline.metrics = {"accuracy": 0.95}
        pipeline.default = False
        pipeline.active = True
        pipeline.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=pipeline)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await PipelineService.get_by_id(user_id, pipeline_id)

        # Verify
        assert result["name"] == "Pipeline 1"
        assert result["id"] == str(pipeline_id)
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if pipeline not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - pipeline not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await PipelineService.get_by_id(user_id, pipeline_id)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestPipelineServiceCreate:
    """Test PipelineService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new pipelines."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock pipeline
        pipeline = Mock(spec=Pipeline)
        pipeline.id = pipeline_id
        pipeline.name = "Pipeline 1"
        pipeline.created_by = "user1"
        pipeline.creation_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pipeline.description = "Test pipeline"
        pipeline.job_name = "job1"
        pipeline.version = "1.0.0"
        pipeline.dataset = "dataset1"
        pipeline.identifiable = {"seed1": True}
        pipeline.metrics = {"accuracy": 0.95}
        pipeline.default = False
        pipeline.active = True
        pipeline.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=pipeline)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await PipelineService.create(
            user_id=user_id,
            name="Pipeline 1",
            data={"key": "value"},
            created_by="user1",
        )

        # Verify
        assert result["name"] == "Pipeline 1"
        assert result["id"] == str(pipeline_id)
        assert result["active"] is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()

        # Mock RbacService - user is NOT CFIA admin
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This operation requires CFIA administrator authority",
            )

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await PipelineService.create(
                user_id=user_id,
                name="Pipeline 1",
                data={"key": "value"},
            )

        assert exc_info.value.status_code == 403


class TestPipelineServiceUpdate:
    """Test PipelineService.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update pipelines."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock updated pipeline
        pipeline = Mock(spec=Pipeline)
        pipeline.id = pipeline_id
        pipeline.name = "Pipeline 1 Updated"  # Updated name
        pipeline.created_by = "user1"
        pipeline.creation_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        pipeline.description = "Updated test pipeline"  # Updated description
        pipeline.job_name = "job1"
        pipeline.version = "2.0.0"  # Updated version
        pipeline.dataset = "dataset1"
        pipeline.identifiable = {"seed1": True}
        pipeline.metrics = {"accuracy": 0.97}  # Updated metrics
        pipeline.default = False
        pipeline.active = True
        pipeline.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=pipeline)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await PipelineService.update(
            user_id,
            pipeline_id,
            name="Pipeline 1 Updated",
            version="2.0.0",
            description="Updated test pipeline",
        )

        # Verify
        assert result["name"] == "Pipeline 1 Updated"
        assert result["version"] == "2.0.0"
        assert result["description"] == "Updated test pipeline"
        assert result["id"] == str(pipeline_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if pipeline not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - pipeline not found
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await PipelineService.update(
                user_id, pipeline_id, name="Pipeline 1 Updated"
            )

        assert exc_info.value.status_code == 404


class TestPipelineServiceDelete:
    """Test PipelineService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete pipelines."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock pipeline
        pipeline = Mock(spec=Pipeline)
        pipeline.id = pipeline_id
        pipeline.name = "Pipeline 1"

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=pipeline)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await PipelineService.delete(user_id, pipeline_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if pipeline not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        pipeline_id = uuid4()

        # Mock RbacService - user is CFIA admin
        async def mock_verify_cfia_admin(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - pipeline not found
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.pipeline.PipelineDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await PipelineService.delete(user_id, pipeline_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when deleting pipelines."""
        user_id = uuid4()
        pipeline_id = uuid4()

        # Mock RbacService - user is NOT CFIA admin, raise 403
        async def mock_verify_cfia_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA administrator",
            )

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_cfia_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await PipelineService.delete(user_id, pipeline_id)

        assert exc_info.value.status_code == 403
