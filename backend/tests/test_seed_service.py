"""
Tests for SeedService - CRUD operations for seeds.

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

from app.service.seed import SeedService
from app.db.model import Seed

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


class TestSeedServiceGetAll:
    """Test SeedService.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all seeds."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        seed1_id = uuid4()
        seed2_id = uuid4()

        # Mock seeds
        seed1 = Mock(spec=Seed)
        seed1.id = seed1_id
        seed1.name_code = "ARATH"
        seed1.family = "Brassicaceae"
        seed1.genus = "Arabidopsis"
        seed1.species = "thaliana"
        seed1.seed_metadata = {"color": "brown"}
        seed1.original_ista_2025 = "ARATH"
        seed1.active = True
        seed1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        seed1.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        seed2 = Mock(spec=Seed)
        seed2.id = seed2_id
        seed2.name_code = "ZEAMA"
        seed2.family = "Poaceae"
        seed2.genus = "Zea"
        seed2.species = "mays"
        seed2.seed_metadata = {"color": "yellow"}
        seed2.original_ista_2025 = "ZEAMA"
        seed2.active = True
        seed2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)
        seed2.date_updated = datetime(2024, 2, 1, tzinfo=timezone.utc)

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
        mock_data_service.get_all = AsyncMock(return_value=([seed1, seed2], 2))
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await SeedService.get_all(user_id)

        # Verify - should have 'seeds' key instead of 'items'
        assert "seeds" in result
        assert len(result["seeds"]) == 2
        assert result["seeds"][0]["name_code"] == "ARATH"
        assert result["seeds"][1]["name_code"] == "ZEAMA"
        assert result["total"] == 2


class TestSeedServiceGetById:
    """Test SeedService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a seed by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        seed_id = uuid4()

        # Mock seed
        seed = Mock(spec=Seed)
        seed.id = seed_id
        seed.name_code = "ARATH"
        seed.family = "Brassicaceae"
        seed.genus = "Arabidopsis"
        seed.species = "thaliana"
        seed.seed_metadata = {"color": "brown"}
        seed.original_ista_2025 = "ARATH"
        seed.active = True
        seed.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        seed.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

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
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=seed)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await SeedService.get_by_id(user_id, seed_id)

        # Verify
        assert result["name_code"] == "ARATH"
        assert result["seed_id"] == str(seed_id)
        assert result["family"] == "Brassicaceae"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if seed not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        seed_id = uuid4()

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

        # Mock data service - seed not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.get_by_id(user_id, seed_id)

        assert exc_info.value.status_code == 404


class TestSeedServiceCreate:
    """Test SeedService.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new seeds."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        seed_id = uuid4()

        # Mock seed
        seed = Mock(spec=Seed)
        seed.id = seed_id
        seed.name_code = "ARATH"
        seed.family = "Brassicaceae"
        seed.genus = "Arabidopsis"
        seed.species = "thaliana"
        seed.seed_metadata = {"color": "brown"}
        seed.original_ista_2025 = "ARATH"
        seed.active = True
        seed.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        seed.date_updated = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value=seed)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await SeedService.create(
            user_id=user_id,
            name_code="ARATH",
            family="Brassicaceae",
            genus="Arabidopsis",
            species="thaliana",
            original_ista_2025="ARATH",
        )

        # Verify
        assert result["name_code"] == "ARATH"
        assert result["seed_id"] == str(seed_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.create(
                user_id=user_id,
                name_code="ARATH",
                family="Brassicaceae",
                genus="Arabidopsis",
                species="thaliana",
                original_ista_2025="ARATH",
            )

        assert exc_info.value.status_code == 403


class TestSeedServiceUpdate:
    """Test SeedService.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update seeds."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        seed_id = uuid4()

        # Mock updated seed
        seed = Mock(spec=Seed)
        seed.id = seed_id
        seed.name_code = "ARATH"
        seed.family = "Brassicaceae Updated"
        seed.genus = "Arabidopsis"
        seed.species = "thaliana"
        seed.seed_metadata = {"color": "brown"}
        seed.original_ista_2025 = "ARATH"
        seed.active = True
        seed.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)
        seed.date_updated = datetime(2024, 1, 2, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=seed)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await SeedService.update(user_id, seed_id, family="Brassicaceae Updated")

        # Verify
        assert result["family"] == "Brassicaceae Updated"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if seed not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        seed_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.update(user_id, seed_id, family="Updated")

        assert exc_info.value.status_code == 404


class TestSeedServiceDelete:
    """Test SeedService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete seeds."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        seed_id = uuid4()

        # Mock seed
        seed = Mock(spec=Seed)
        seed.id = seed_id

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=seed)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await SeedService.delete(user_id, seed_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if seed not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        seed_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.seed.SeedDataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.delete(user_id, seed_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when deleting."""
        user_id = uuid4()
        seed_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.rbac.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.delete(user_id, seed_id)

        assert exc_info.value.status_code == 403


class TestSeedServiceGetSeedData:
    """Test SeedService.get_seed_data method."""

    @pytest.mark.asyncio
    async def test_get_seed_data_returns_active_seeds(self, monkeypatch):
        """Test get_seed_data returns active seeds with subset of columns"""
        from app.db.utils import sessionmanager

        # Mock seed data as SQLAlchemy Row objects
        class MockRow:
            def __init__(self, data):
                self._data = data
            
            def _asdict(self):
                return self._data

        mock_rows = [
            MockRow({
                "seed_id": "seed-123",
                "name_code": "WHEAT-001",
                "family": "Poaceae",
                "genus": "Triticum",
                "species": "aestivum",
                "seed_metadata": {"color": "golden"}
            }),
            MockRow({
                "seed_id": "seed-456",
                "name_code": "CORN-001",
                "family": "Poaceae",
                "genus": "Zea",
                "species": "mays",
                "seed_metadata": {"color": "yellow"}
            })
        ]

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock SeedDataService.get_seed_data
        async def mock_get_seed_data(self):
            return mock_rows

        monkeypatch.setattr(
            "app.datastore.seed.SeedDataService.get_seed_data",
            mock_get_seed_data
        )

        # Call service method
        result = await SeedService.get_seed_data()

        # Verify response structure
        assert "seeds" in result
        assert len(result["seeds"]) == 2

        # Verify first seed
        assert result["seeds"][0]["seed_id"] == "seed-123"
        assert result["seeds"][0]["name_code"] == "WHEAT-001"
        assert result["seeds"][0]["family"] == "Poaceae"
        assert result["seeds"][0]["genus"] == "Triticum"
        assert result["seeds"][0]["species"] == "aestivum"
        assert result["seeds"][0]["seed_metadata"] == {"color": "golden"}

        # Verify second seed
        assert result["seeds"][1]["seed_id"] == "seed-456"
        assert result["seeds"][1]["name_code"] == "CORN-001"

    @pytest.mark.asyncio
    async def test_get_seed_data_empty_result(self, monkeypatch):
        """Test get_seed_data returns empty list when no active seeds"""
        from app.db.utils import sessionmanager

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock empty result
        async def mock_get_seed_data_empty(self):
            return []

        monkeypatch.setattr(
            "app.datastore.seed.SeedDataService.get_seed_data",
            mock_get_seed_data_empty
        )

        result = await SeedService.get_seed_data()

        assert result == {"seeds": []}

    @pytest.mark.asyncio
    async def test_get_seed_data_handles_errors(self, monkeypatch):
        """Test get_seed_data raises SeedError on failure"""
        from app.db.utils import sessionmanager
        from app.exceptions import SeedError

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service to raise exception
        async def mock_get_seed_data_error(self):
            raise Exception("Database connection failed")

        monkeypatch.setattr(
            "app.datastore.seed.SeedDataService.get_seed_data",
            mock_get_seed_data_error
        )

        # Verify SeedError is raised
        with pytest.raises(SeedError) as exc_info:
            await SeedService.get_seed_data()

        assert "Failed to retrieve seed data" in str(exc_info.value)
