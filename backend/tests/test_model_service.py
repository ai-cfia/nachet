"""
Tests for ModelService - CRUD operations for ML models.

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

from app.service.model import ModelService
from app.db.model import Model, ModelTask

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


# ============================================================================
# ModelService Tests
# ============================================================================


class TestModelServiceGetAll:
    """Test ModelService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all models."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model1_id = uuid4()
        model2_id = uuid4()
        task_id = 1

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock models
        model1 = Mock(spec=Model)
        model1.id = model1_id
        model1.task_id = task_id
        model1.model_task = task
        model1.name = "Model v1"
        model1.endpoint_name = "endpoint1"
        model1.api_url = "http://localhost:8000/api/v1"
        model1.created_by = "user1"
        model1.date_model_training = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model1.content_type = "application/json"
        model1.deployment_platform = "on-prem"
        model1.version = "1.0.0"
        model1.description = "Test model 1"
        model1.job_name = "job1"
        model1.dataset = "dataset1"
        model1.artifacts_url = "http://artifacts.com/model1"
        model1.sha256 = "abc123"
        model1.active = True
        model1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model1.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        model2 = Mock(spec=Model)
        model2.id = model2_id
        model2.task_id = task_id
        model2.model_task = task
        model2.name = "Model v2"
        model2.endpoint_name = "endpoint2"
        model2.api_url = "http://localhost:8000/api/v2"
        model2.created_by = "user2"
        model2.date_model_training = datetime(2024, 2, 1, tzinfo=timezone.utc)
        model2.content_type = "application/json"
        model2.deployment_platform = "on-prem"
        model2.version = "2.0.0"
        model2.description = "Test model 2"
        model2.job_name = "job2"
        model2.dataset = "dataset2"
        model2.artifacts_url = "http://artifacts.com/model2"
        model2.sha256 = "def456"
        model2.active = True
        model2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)
        model2.date_updated = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService - just verify user exists
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=[model1, model2])
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.get_all(user_id)

        # Verify
        assert "models" in result
        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "Model v1"
        assert result["models"][1]["name"] == "Model v2"
        assert result["models"][0]["task_name"] == "Classification"
        assert result["models"][0]["active"] is True


class TestModelServiceGetById:
    """Test ModelService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a model by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()
        task_id = 1

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock model
        model = Mock(spec=Model)
        model.id = model_id
        model.task_id = task_id
        model.model_task = task
        model.name = "Model v1"
        model.endpoint_name = "endpoint1"
        model.api_url = "http://localhost:8000/api/v1"
        model.created_by = "user1"
        model.date_model_training = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.content_type = "application/json"
        model.deployment_platform = "on-prem"
        model.version = "1.0.0"
        model.description = "Test model"
        model.job_name = "job1"
        model.dataset = "dataset1"
        model.artifacts_url = "http://artifacts.com/model1"
        model.sha256 = "abc123"
        model.active = True
        model.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.get_by_id(user_id, model_id)

        # Verify
        assert result["name"] == "Model v1"
        assert result["id"] == str(model_id)
        assert result["task_name"] == "Classification"
        assert result["active"] is True

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if model not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - model not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await ModelService.get_by_id(user_id, model_id)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestModelServiceGetByTaskId:
    """Test ModelService.get_by_task_id method."""

    @pytest.mark.asyncio
    async def test_get_by_task_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve models by task ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        task_id = 1
        model1_id = uuid4()
        model2_id = uuid4()

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock models
        model1 = Mock(spec=Model)
        model1.id = model1_id
        model1.task_id = task_id
        model1.model_task = task
        model1.name = "Model v1"
        model1.endpoint_name = "endpoint1"
        model1.api_url = "http://localhost:8000/api/v1"
        model1.created_by = "user1"
        model1.date_model_training = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model1.content_type = "application/json"
        model1.deployment_platform = "on-prem"
        model1.version = "1.0.0"
        model1.description = "Test model 1"
        model1.job_name = "job1"
        model1.dataset = "dataset1"
        model1.artifacts_url = "http://artifacts.com/model1"
        model1.sha256 = "abc123"
        model1.active = True
        model1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model1.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        model2 = Mock(spec=Model)
        model2.id = model2_id
        model2.task_id = task_id
        model2.model_task = task
        model2.name = "Model v2"
        model2.endpoint_name = "endpoint2"
        model2.api_url = "http://localhost:8000/api/v2"
        model2.created_by = "user2"
        model2.date_model_training = datetime(2024, 2, 1, tzinfo=timezone.utc)
        model2.content_type = "application/json"
        model2.deployment_platform = "on-prem"
        model2.version = "2.0.0"
        model2.description = "Test model 2"
        model2.job_name = "job2"
        model2.dataset = "dataset2"
        model2.artifacts_url = "http://artifacts.com/model2"
        model2.sha256 = "def456"
        model2.active = True
        model2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)
        model2.date_updated = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_task_id = AsyncMock(return_value=[model1, model2])
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.get_by_task_id(user_id, task_id)

        # Verify
        assert "models" in result
        assert len(result["models"]) == 2
        assert result["models"][0]["task_id"] == task_id
        assert result["models"][1]["task_id"] == task_id
        assert result["models"][0]["task_name"] == "Classification"


class TestModelServiceCreate:
    """Test ModelService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new models."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()
        task_id = 1

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock model
        model = Mock(spec=Model)
        model.id = model_id
        model.task_id = task_id
        model.model_task = task
        model.name = "Model v1"
        model.endpoint_name = "endpoint1"
        model.api_url = "http://localhost:8000/api/v1"
        model.created_by = "user1"
        model.date_model_training = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.content_type = "application/json"
        model.deployment_platform = "on-prem"
        model.version = "1.0.0"
        model.description = "Test model"
        model.job_name = "job1"
        model.dataset = "dataset1"
        model.artifacts_url = "http://artifacts.com/model1"
        model.sha256 = "abc123"
        model.active = True
        model.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService - user is cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.create(
            user_id=user_id,
            task_id=task_id,
            name="Model v1",
            endpoint_name="endpoint1",
            api_url="http://localhost:8000/api/v1",
            api_key="secret_key",
            created_by="user1",
            date_model_training=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

        # Verify
        assert result["name"] == "Model v1"
        assert result["id"] == str(model_id)
        assert result["task_name"] == "Classification"
        assert result["active"] is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()
        user_org_id = uuid4()
        task_id = 1

        # Mock RbacService - user is NOT cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await ModelService.create(
                user_id=user_id,
                task_id=task_id,
                name="Model v1",
                endpoint_name="endpoint1",
                api_url="http://localhost:8000/api/v1",
                api_key="secret_key",
                created_by="user1",
                date_model_training=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

        assert exc_info.value.status_code == 403
        assert "role" in exc_info.value.detail


class TestModelServiceUpdate:
    """Test ModelService.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update models."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()
        task_id = 1

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock updated model
        model = Mock(spec=Model)
        model.id = model_id
        model.task_id = task_id
        model.model_task = task
        model.name = "Model v2"  # Updated name
        model.endpoint_name = "endpoint1"
        model.api_url = "http://localhost:8000/api/v1"
        model.created_by = "user1"
        model.date_model_training = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.content_type = "application/json"
        model.deployment_platform = "on-prem"
        model.version = "2.0.0"  # Updated version
        model.description = "Updated test model"  # Updated description
        model.job_name = "job1"
        model.dataset = "dataset1"
        model.artifacts_url = "http://artifacts.com/model1"
        model.sha256 = "abc123"
        model.active = True
        model.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        model.date_updated = datetime(2024, 1, 15, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.update(
            user_id=user_id,
            model_id=model_id,
            name="Model v2",
            version="2.0.0",
            description="Updated test model",
        )

        # Verify
        assert result["name"] == "Model v2"
        assert result["version"] == "2.0.0"
        assert result["description"] == "Updated test model"
        assert result["id"] == str(model_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if model not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - model not found
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await ModelService.update(user_id, model_id, name="Model v2")

        assert exc_info.value.status_code == 404


class TestModelServiceDelete:
    """Test ModelService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete models."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()
        task_id = 1

        # Mock task
        task = Mock(spec=ModelTask)
        task.id = task_id
        task.name = "Classification"

        # Mock model
        model = Mock(spec=Model)
        model.id = model_id
        model.task_id = task_id
        model.model_task = task

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=model)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await ModelService.delete(user_id, model_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if model not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass  # User is cfia_admin

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - model not found
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.model.ModelDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await ModelService.delete(user_id, model_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when deleting models."""
        user_id = uuid4()
        user_org_id = uuid4()
        model_id = uuid4()

        # Mock RbacService - user is NOT cfia_admin
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.model.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.model.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await ModelService.delete(user_id, model_id)

        assert exc_info.value.status_code == 403
