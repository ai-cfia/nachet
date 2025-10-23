"""
Tests for the generic base CRUD service.

This test module creates concrete test implementations of the generic base
classes to verify all CRUD functionality works correctly.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Type, Dict, Any

from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.exceptions import (
    ModelNotFoundError,
    ModelCreationError,
    ModelUpdateError,
    ModelDeletionError,
)
from fastapi import HTTPException


# Mock entity class for testing
class MockEntity:
    """Mock SQLAlchemy entity for testing."""

    def __init__(self, id: UUID, name: str, active: bool = True, **kwargs):
        self.id = id
        self.name = name
        self.active = active
        for key, value in kwargs.items():
            setattr(self, key, value)


# Concrete implementations for testing
class MockEntityDataService(BaseCRUDDataService[MockEntity]):
    """Concrete data service for testing."""

    @classmethod
    def get_model_class(cls) -> Type[MockEntity]:
        return MockEntity


class MockEntityService(BaseCRUDService[MockEntity]):
    """Concrete service for testing."""

    @classmethod
    def get_entity_name(cls) -> str:
        return "Model"

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[MockEntity]]:
        return MockEntityDataService

    @classmethod
    def serialize_entity(cls, entity: MockEntity) -> Dict[str, Any]:
        return {
            "id": str(entity.id),
            "name": entity.name,
            "active": entity.active,
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return ModelNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return ModelCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return ModelUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return ModelDeletionError


# Test fixtures
@pytest.fixture
def mock_user_id():
    return uuid4()


@pytest.fixture
def mock_entity_id():
    return uuid4()


@pytest.fixture
def mock_entity(mock_entity_id):
    return MockEntity(id=mock_entity_id, name="Test Entity", active=True)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# Tests for BaseCRUDService.get_all
@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_all_success(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity
):
    """Test successful retrieval of all entities with pagination."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    mock_data_service = AsyncMock()
    mock_data_service.get_all.return_value = ([mock_entity], 1)

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(
            MockEntityDataService, "get_all", return_value=([mock_entity], 1)
        ):
            # Act
            result = await MockEntityService.get_all(mock_user_id)

            # Assert
            assert "items" in result
            assert "total" in result
            assert "offset" in result
            assert "limit" in result
            assert "has_more" in result
            assert len(result["items"]) == 1
            assert result["items"][0]["id"] == str(mock_entity.id)
            assert result["items"][0]["name"] == mock_entity.name
            assert result["total"] == 1
            assert result["offset"] == 0
            assert result["limit"] == 100
            assert result["has_more"] is False
            mock_get_org_id.assert_called_once_with(mock_user_id)
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
async def test_get_all_rbac_failure(mock_get_org_id, mock_user_id):
    """Test get_all fails when RBAC check fails."""
    # Arrange
    mock_get_org_id.side_effect = HTTPException(status_code=401, detail="Unauthorized")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MockEntityService.get_all(mock_user_id)

    assert exc_info.value.status_code == 401
    mock_get_org_id.assert_called_once_with(mock_user_id)


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_all_with_pagination(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity
):
    """Test get_all with custom pagination parameters."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Create multiple entities for pagination test
    entities = [mock_entity, mock_entity]

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(
            MockEntityDataService, "get_all", return_value=(entities, 150)
        ) as mock_get_all:
            # Act
            result = await MockEntityService.get_all(mock_user_id, offset=50, limit=50)

            # Assert
            assert result["total"] == 150
            assert result["offset"] == 50
            assert result["limit"] == 50
            assert result["has_more"] is True  # 50 + 50 < 150
            assert len(result["items"]) == 2
            mock_get_all.assert_called_once()
            call_kwargs = mock_get_all.call_args[1]
            assert call_kwargs["offset"] == 50
            assert call_kwargs["limit"] == 50


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_all_with_filters(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity
):
    """Test get_all with filtering parameters."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(
            MockEntityDataService, "get_all", return_value=([mock_entity], 1)
        ) as mock_get_all:
            # Act
            filters = {"name": "Test Entity", "active": True}
            result = await MockEntityService.get_all(mock_user_id, filters=filters)

            # Assert
            assert result["total"] == 1
            assert len(result["items"]) == 1
            mock_get_all.assert_called_once()
            call_kwargs = mock_get_all.call_args[1]
            assert call_kwargs["filters"] == filters


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_all_with_sorting(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity
):
    """Test get_all with sorting parameters."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(
            MockEntityDataService, "get_all", return_value=([mock_entity], 1)
        ) as mock_get_all:
            # Act
            result = await MockEntityService.get_all(
                mock_user_id, order_by="name", order_direction="desc"
            )

            # Assert
            assert result["total"] == 1
            mock_get_all.assert_called_once()
            call_kwargs = mock_get_all.call_args[1]
            assert call_kwargs["order_by"] == "name"
            assert call_kwargs["order_direction"] == "desc"


# Tests for BaseCRUDService.get_by_id
@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_by_id_success(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity_id, mock_entity
):
    """Test successful retrieval of entity by ID."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "get_by_id", return_value=mock_entity):
            # Act
            result = await MockEntityService.get_by_id(mock_user_id, mock_entity_id)

            # Assert
            assert result["id"] == str(mock_entity.id)
            assert result["name"] == mock_entity.name
            mock_get_org_id.assert_called_once_with(mock_user_id)
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.get_user_organization_id")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_get_by_id_not_found(
    mock_get_session, mock_get_org_id, mock_user_id, mock_entity_id
):
    """Test get_by_id returns 404 when entity not found."""
    # Arrange
    mock_get_org_id.return_value = uuid4()
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "get_by_id", return_value=None):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await MockEntityService.get_by_id(mock_user_id, mock_entity_id)

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail).lower()


# Tests for BaseCRUDService.create
@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_create_success(
    mock_get_session, mock_verify_cfia_admin, mock_user_id, mock_entity
):
    """Test successful entity creation."""
    # Arrange
    cfia_org_id = uuid4()
    mock_verify_cfia_admin.return_value = cfia_org_id
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "create", return_value=mock_entity):
            # Act
            result = await MockEntityService.create(
                mock_user_id, name="Test Entity", active=True
            )

            # Assert
            assert result["id"] == str(mock_entity.id)
            assert result["name"] == mock_entity.name
            mock_verify_cfia_admin.assert_called_once_with(mock_user_id)
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
async def test_create_rbac_failure(mock_verify_cfia_admin, mock_user_id):
    """Test create fails when user is not admin."""
    # Arrange
    mock_verify_cfia_admin.side_effect = HTTPException(
        status_code=403, detail="Forbidden"
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MockEntityService.create(mock_user_id, name="Test Entity")

    assert exc_info.value.status_code == 403
    mock_verify_cfia_admin.assert_called_once_with(mock_user_id)


# Tests for BaseCRUDService.update
@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_update_success(
    mock_get_session, mock_verify_cfia_admin, mock_user_id, mock_entity_id, mock_entity
):
    """Test successful entity update."""
    # Arrange
    cfia_org_id = uuid4()
    mock_verify_cfia_admin.return_value = cfia_org_id
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    updated_entity = MockEntity(id=mock_entity_id, name="Updated Entity", active=True)

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "update", return_value=updated_entity):
            # Act
            result = await MockEntityService.update(
                mock_user_id, mock_entity_id, name="Updated Entity"
            )

            # Assert
            assert result["id"] == str(mock_entity_id)
            assert result["name"] == "Updated Entity"
            mock_verify_cfia_admin.assert_called_once_with(mock_user_id)
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_update_not_found(
    mock_get_session, mock_verify_cfia_admin, mock_user_id, mock_entity_id
):
    """Test update returns 404 when entity not found."""
    # Arrange
    cfia_org_id = uuid4()
    mock_verify_cfia_admin.return_value = cfia_org_id
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "update", return_value=None):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await MockEntityService.update(
                    mock_user_id, mock_entity_id, name="Updated"
                )

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
async def test_update_rbac_failure(
    mock_verify_cfia_admin, mock_user_id, mock_entity_id
):
    """Test update fails when user is not admin."""
    # Arrange
    mock_verify_cfia_admin.side_effect = HTTPException(
        status_code=403, detail="Forbidden"
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MockEntityService.update(mock_user_id, mock_entity_id, name="Updated")

    assert exc_info.value.status_code == 403
    mock_verify_cfia_admin.assert_called_once_with(mock_user_id)


# Tests for BaseCRUDService.delete
@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_delete_success(
    mock_get_session, mock_verify_cfia_admin, mock_user_id, mock_entity_id, mock_entity
):
    """Test successful entity soft deletion."""
    # Arrange
    cfia_org_id = uuid4()
    mock_verify_cfia_admin.return_value = cfia_org_id
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    deleted_entity = MockEntity(id=mock_entity_id, name="Deleted", active=False)

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(
            MockEntityDataService, "soft_delete", return_value=deleted_entity
        ):
            # Act
            result = await MockEntityService.delete(mock_user_id, mock_entity_id)

            # Assert
            assert "message" in result
            assert "soft deleted successfully" in result["message"]
            assert result["id"] == str(mock_entity_id)
            mock_verify_cfia_admin.assert_called_once_with(mock_user_id)
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
@patch("app.service.base_crud.sessionmanager.get_session")
async def test_delete_not_found(
    mock_get_session, mock_verify_cfia_admin, mock_user_id, mock_entity_id
):
    """Test delete returns 404 when entity not found."""
    # Arrange
    cfia_org_id = uuid4()
    mock_verify_cfia_admin.return_value = cfia_org_id
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    with patch.object(MockEntityDataService, "__init__", return_value=None):
        with patch.object(MockEntityDataService, "soft_delete", return_value=None):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await MockEntityService.delete(mock_user_id, mock_entity_id)

            assert exc_info.value.status_code == 404
            assert "not found" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
@patch("app.service.rbac.RbacService.verify_user_is_cfia_admin")
async def test_delete_rbac_failure(
    mock_verify_cfia_admin, mock_user_id, mock_entity_id
):
    """Test delete fails when user is not admin."""
    # Arrange
    mock_verify_cfia_admin.side_effect = HTTPException(
        status_code=403, detail="Forbidden"
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MockEntityService.delete(mock_user_id, mock_entity_id)

    assert exc_info.value.status_code == 403
    mock_verify_cfia_admin.assert_called_once_with(mock_user_id)


# Tests for BaseCRUDDataService
@pytest.mark.asyncio
async def test_data_service_get_model_class():
    """Test that get_model_class returns correct type."""
    assert MockEntityDataService.get_model_class() == MockEntity


@pytest.mark.asyncio
async def test_data_service_base_class_not_implemented():
    """Test that base class methods raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        BaseCRUDDataService.get_model_class()
