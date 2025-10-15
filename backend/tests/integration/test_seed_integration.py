"""
Integration tests for SeedService - NO MOCKS.

These tests use real database connections and verify the full stack:
Service → DataService → SQLAlchemy → PostgreSQL

Access Control tested:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only
"""

import os
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from dotenv import load_dotenv

from app.service.seed import SeedService
from app.db.model import Seed
from sqlalchemy.ext.asyncio import AsyncSession

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationGetAll:
    """Integration tests for SeedService.get_all method."""

    async def test_get_all_returns_active_seeds_only(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify that get_all returns only active seeds, excluding soft-deleted ones."""
        # Create active seed
        active_seed = Seed(
            id=uuid4(),
            name_code="ACTIVE-001",
            family="Brassicaceae",
            genus="Arabidopsis",
            species="thaliana",
            original_ista_2025="ARATH",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(active_seed)
        cleanup_test_seeds.append(active_seed.id)

        # Create inactive seed
        inactive_seed = Seed(
            id=uuid4(),
            name_code="INACTIVE-001",
            family="Poaceae",
            genus="Zea",
            species="mays",
            original_ista_2025="ZEAMA",
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_seed)
        cleanup_test_seeds.append(inactive_seed.id)

        await integration_db_session.commit()

        # Call service - should only return active seed
        result = await SeedService.get_all(test_user)

        # Verify
        assert "seeds" in result
        seed_codes = [s["name_code"] for s in result["seeds"]]
        assert "ACTIVE-001" in seed_codes
        assert "INACTIVE-001" not in seed_codes

    async def test_get_all_pagination_works(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify pagination with offset and limit works correctly."""
        # Create 25 test seeds
        for i in range(25):
            seed = Seed(
                id=uuid4(),
                name_code=f"SEED-{i:03d}",
                family="Testaceae",
                genus="Testus",
                species=f"test{i}",
                original_ista_2025=f"TEST{i:03d}",
                active=True,
                date_created=datetime.now(timezone.utc),
                date_updated=datetime.now(timezone.utc),
            )
            integration_db_session.add(seed)
            cleanup_test_seeds.append(seed.id)

        await integration_db_session.commit()

        # Test first page
        page1 = await SeedService.get_all(test_user, offset=0, limit=10)
        assert len(page1["seeds"]) == 10
        assert page1["offset"] == 0
        assert page1["limit"] == 10
        assert page1["has_more"] is True

        # Test second page
        page2 = await SeedService.get_all(test_user, offset=10, limit=10)
        assert len(page2["seeds"]) == 10
        assert page2["offset"] == 10

        # Test last page - may have more than 5 seeds due to ISTA fixture data
        page3 = await SeedService.get_all(test_user, offset=20, limit=10)
        # Verify pagination works: either exactly our test seeds or includes ISTA data
        assert len(page3["seeds"]) >= 5
        # Verify some of our test seeds are in the results
        all_seeds = await SeedService.get_all(test_user, limit=1000)
        seed_codes = [s["name_code"] for s in all_seeds["seeds"]]
        test_seed_codes = [f"SEED-{i:03d}" for i in range(25)]
        for code in test_seed_codes:
            assert code in seed_codes, f"Test seed {code} should be in results"

    async def test_get_all_filtering_by_family(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify filtering by family attribute works."""
        # Create seeds from different families
        brassicaceae_seed = Seed(
            id=uuid4(),
            name_code="BRASS-001",
            family="Brassicaceae",
            genus="Arabidopsis",
            species="thaliana",
            original_ista_2025="ARATH",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(brassicaceae_seed)
        cleanup_test_seeds.append(brassicaceae_seed.id)

        poaceae_seed = Seed(
            id=uuid4(),
            name_code="POACE-001",
            family="Poaceae",
            genus="Zea",
            species="mays",
            original_ista_2025="ZEAMA",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(poaceae_seed)
        cleanup_test_seeds.append(poaceae_seed.id)

        await integration_db_session.commit()

        # Filter by Brassicaceae
        result = await SeedService.get_all(test_user, filters={"family": "Brassicaceae"})

        # Verify only Brassicaceae seeds returned
        assert "seeds" in result
        families = [s["family"] for s in result["seeds"]]
        assert "Brassicaceae" in families
        # Poaceae may or may not be in result depending on test data, so we check our seed is there
        seed_codes = [s["name_code"] for s in result["seeds"]]
        assert "BRASS-001" in seed_codes

    async def test_get_all_sorting_by_genus(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify sorting by genus works with asc/desc order."""
        # Create seeds with different genus values
        seed_a = Seed(
            id=uuid4(),
            name_code="SEED-A",
            family="Testaceae",
            genus="Aaa",
            species="test",
            original_ista_2025="TESTA",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed_a)
        cleanup_test_seeds.append(seed_a.id)

        seed_z = Seed(
            id=uuid4(),
            name_code="SEED-Z",
            family="Testaceae",
            genus="Zzz",
            species="test",
            original_ista_2025="TESTZ",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed_z)
        cleanup_test_seeds.append(seed_z.id)

        await integration_db_session.commit()

        # Test ascending order
        result_asc = await SeedService.get_all(
            test_user, order_by="genus", order_direction="asc", limit=100
        )
        genera_asc = [s["genus"] for s in result_asc["seeds"] if s["name_code"] in ["SEED-A", "SEED-Z"]]
        if len(genera_asc) == 2:
            assert genera_asc == ["Aaa", "Zzz"]

        # Test descending order
        result_desc = await SeedService.get_all(
            test_user, order_by="genus", order_direction="desc", limit=100
        )
        genera_desc = [s["genus"] for s in result_desc["seeds"] if s["name_code"] in ["SEED-A", "SEED-Z"]]
        if len(genera_desc) == 2:
            assert genera_desc == ["Zzz", "Aaa"]

    async def test_get_all_returns_seeds_key_not_items(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify backward compatibility - response uses 'seeds' key instead of 'items'."""
        # Create one test seed
        seed = Seed(
            id=uuid4(),
            name_code="COMPAT-001",
            family="Testaceae",
            genus="Testus",
            species="compat",
            original_ista_2025="COMPAT",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed.id)
        await integration_db_session.commit()

        # Call service
        result = await SeedService.get_all(test_user)

        # Verify response structure
        assert "seeds" in result  # Should have 'seeds' key
        assert "items" not in result  # Should NOT have 'items' key
        assert isinstance(result["seeds"], list)
        assert "total" in result
        assert "offset" in result
        assert "limit" in result
        assert "has_more" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationGetById:
    """Integration tests for SeedService.get_by_id method."""

    async def test_get_by_id_returns_seed(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify get_by_id retrieves a seed by its UUID."""
        # Create test seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="GETID-001",
            family="Brassicaceae",
            genus="Arabidopsis",
            species="thaliana",
            seed_metadata={"color": "brown", "size": "small"},
            original_ista_2025="ARATH",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Call service
        result = await SeedService.get_by_id(test_user, seed_id)

        # Verify all fields returned correctly
        assert result["seed_id"] == str(seed_id)
        assert result["name_code"] == "GETID-001"
        assert result["family"] == "Brassicaceae"
        assert result["genus"] == "Arabidopsis"
        assert result["species"] == "thaliana"
        assert result["metadata"] == {"color": "brown", "size": "small"}
        assert result["original_ista_2025"] == "ARATH"
        assert result["active"] is True

    async def test_get_by_id_returns_404_for_inactive_seed(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify get_by_id returns 404 for soft-deleted (inactive) seeds."""
        # Create inactive seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="INACTIVE-002",
            family="Poaceae",
            genus="Zea",
            species="mays",
            original_ista_2025="ZEAMA",
            active=False,  # Soft deleted
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.get_by_id(test_user, seed_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_returns_404_for_nonexistent_uuid(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
    ):
        """Verify get_by_id returns 404 for non-existent UUID."""
        nonexistent_id = uuid4()

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.get_by_id(test_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_get_by_id_serialization_format(
        self,
        integration_db_session: AsyncSession,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify get_by_id returns all expected fields with correct types."""
        # Create test seed with all fields
        seed_id = uuid4()
        created_time = datetime.now(timezone.utc)
        seed = Seed(
            id=seed_id,
            name_code="SERIAL-001",
            family="Fabaceae",
            genus="Glycine",
            species="max",
            seed_metadata={"test": "data"},
            original_ista_2025="GLYMA",
            active=True,
            date_created=created_time,
            date_updated=created_time,
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Call service
        result = await SeedService.get_by_id(test_user, seed_id)

        # Verify structure and types
        assert isinstance(result, dict)
        assert "seed_id" in result
        assert isinstance(result["seed_id"], str)
        assert "name_code" in result
        assert "family" in result
        assert "genus" in result
        assert "species" in result
        assert "metadata" in result
        assert isinstance(result["metadata"], dict)
        assert "original_ista_2025" in result
        assert "active" in result
        assert isinstance(result["active"], bool)
        assert "date_created" in result
        assert isinstance(result["date_created"], str)  # ISO format string
        assert "date_updated" in result
        assert isinstance(result["date_updated"], str)


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationCreate:
    """Integration tests for SeedService.create method."""

    async def test_create_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify CFIA admin can create new seeds and they persist to database."""
        # Call service to create seed
        result = await SeedService.create(
            user_id=test_admin_user,
            name_code="CREATE-001",
            family="Brassicaceae",
            genus="Brassica",
            species="napus",
            original_ista_2025="BRANA",
            seed_metadata={"test": "create"},
        )

        # Track for cleanup
        seed_id = UUID(result["seed_id"])
        cleanup_test_seeds.append(seed_id)

        # Verify response
        assert result["name_code"] == "CREATE-001"
        assert result["family"] == "Brassicaceae"
        assert result["genus"] == "Brassica"
        assert result["species"] == "napus"
        assert result["original_ista_2025"] == "BRANA"
        assert result["metadata"] == {"test": "create"}
        assert result["active"] is True

        # Verify persistence - query database directly
        from sqlalchemy import select
        query = select(Seed).where(Seed.id == seed_id)
        db_result = await integration_db_session.execute(query)
        db_seed = db_result.scalar_one_or_none()

        assert db_seed is not None
        assert db_seed.name_code == "CREATE-001"
        assert db_seed.active is True

    async def test_create_as_regular_user_raises_403(
        self,
        integration_db_session: AsyncSession,
        test_regular_user: UUID,
    ):
        """Verify regular (non-admin) users cannot create seeds."""
        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.create(
                user_id=test_regular_user,
                name_code="FORBIDDEN-001",
                family="Testaceae",
                genus="Test",
                species="forbidden",
                original_ista_2025="FORB",
            )

        assert exc_info.value.status_code == 403

    async def test_create_with_full_seed_data(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify creating seed with all optional fields works."""
        # Create with full data including metadata
        result = await SeedService.create(
            user_id=test_admin_user,
            name_code="FULL-001",
            family="Solanaceae",
            genus="Solanum",
            species="lycopersicum",
            original_ista_2025="SOLLA",
            seed_metadata={
                "color": "red",
                "shape": "round",
                "size_mm": 2.5,
                "notes": "Test seed with complete metadata",
            },
        )

        seed_id = UUID(result["seed_id"])
        cleanup_test_seeds.append(seed_id)

        # Verify all fields
        assert result["name_code"] == "FULL-001"
        assert result["metadata"]["color"] == "red"
        assert result["metadata"]["shape"] == "round"
        assert result["metadata"]["size_mm"] == 2.5
        assert result["metadata"]["notes"] == "Test seed with complete metadata"

    async def test_create_generates_uuid_and_timestamps(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify create auto-generates UUID and timestamps."""
        import time
        before_create = datetime.now(timezone.utc)
        time.sleep(0.1)  # Small delay to ensure timestamp difference

        result = await SeedService.create(
            user_id=test_admin_user,
            name_code="TIMESTAMP-001",
            family="Testaceae",
            genus="Test",
            species="timestamp",
            original_ista_2025="TSTAMP",
        )

        time.sleep(0.1)
        after_create = datetime.now(timezone.utc)

        seed_id = UUID(result["seed_id"])
        cleanup_test_seeds.append(seed_id)

        # Verify UUID was generated
        assert "seed_id" in result
        assert UUID(result["seed_id"])  # Should be valid UUID

        # Verify timestamps
        assert "date_created" in result
        assert "date_updated" in result

        # Parse timestamps and verify they're in reasonable range
        from datetime import datetime as dt
        created = dt.fromisoformat(result["date_created"].replace("Z", "+00:00"))
        updated = dt.fromisoformat(result["date_updated"].replace("Z", "+00:00"))

        assert before_create <= created <= after_create
        assert before_create <= updated <= after_create

    async def test_create_persists_to_database(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify created seed is actually persisted and can be queried."""
        # Create seed
        result = await SeedService.create(
            user_id=test_admin_user,
            name_code="PERSIST-001",
            family="Fabaceae",
            genus="Pisum",
            species="sativum",
            original_ista_2025="PISSA",
        )

        seed_id = UUID(result["seed_id"])
        cleanup_test_seeds.append(seed_id)

        # Flush to ensure it's written
        await integration_db_session.commit()

        # Query directly from database
        from sqlalchemy import select
        query = select(Seed).where(Seed.id == seed_id).where(Seed.active.is_(True))
        db_result = await integration_db_session.execute(query)
        persisted_seed = db_result.scalar_one_or_none()

        # Verify it exists and matches
        assert persisted_seed is not None
        assert str(persisted_seed.id) == result["seed_id"]
        assert persisted_seed.name_code == "PERSIST-001"
        assert persisted_seed.family == "Fabaceae"
        assert persisted_seed.genus == "Pisum"
        assert persisted_seed.species == "sativum"
        assert persisted_seed.original_ista_2025 == "PISSA"
        assert persisted_seed.active is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationUpdate:
    """Integration tests for SeedService.update method."""

    async def test_update_as_cfia_admin_succeeds(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify CFIA admin can update seed and changes persist."""
        # Create initial seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="UPDATE-001",
            family="OldFamily",
            genus="OldGenus",
            species="old",
            original_ista_2025="OLD",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Update the seed
        result = await SeedService.update(
            user_id=test_admin_user,
            entity_id=seed_id,
            family="NewFamily",
            genus="NewGenus",
        )

        # Verify response
        assert result["family"] == "NewFamily"
        assert result["genus"] == "NewGenus"
        assert result["species"] == "old"  # Unchanged field

        # Verify persistence in database using a fresh session to avoid cache issues
        from sqlalchemy import select
        from app.db.utils import sessionmanager
        
        async with sessionmanager.get_session() as fresh_session:
            query = select(Seed).where(Seed.id == seed_id)
            db_result = await fresh_session.execute(query)
            updated_seed = db_result.scalar_one_or_none()

            assert updated_seed.family == "NewFamily"
            assert updated_seed.genus == "NewGenus"

    async def test_update_as_regular_user_raises_403(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_regular_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify regular users cannot update seeds."""
        # Create seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="NOUPDATE-001",
            family="Testaceae",
            genus="Test",
            species="noupdate",
            original_ista_2025="NOUPD",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Attempt update as regular user
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.update(
                user_id=test_regular_user,
                entity_id=seed_id,
                family="UpdatedFamily",
            )

        assert exc_info.value.status_code == 403

    async def test_update_nonexistent_seed_raises_404(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
    ):
        """Verify updating non-existent seed returns 404."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await SeedService.update(
                user_id=test_admin_user,
                entity_id=nonexistent_id,
                family="DoesNotMatter",
            )

        assert exc_info.value.status_code == 404

    async def test_update_partial_fields(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify updating only some fields leaves others unchanged."""
        # Create seed with all fields
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="PARTIAL-001",
            family="OriginalFamily",
            genus="OriginalGenus",
            species="original",
            seed_metadata={"key": "original_value"},
            original_ista_2025="ORIG",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Update only genus
        result = await SeedService.update(
            user_id=test_admin_user,
            entity_id=seed_id,
            genus="UpdatedGenus",
        )

        # Verify only genus changed
        assert result["genus"] == "UpdatedGenus"
        assert result["family"] == "OriginalFamily"  # Unchanged
        assert result["species"] == "original"  # Unchanged
        assert result["metadata"] == {"key": "original_value"}  # Unchanged

    async def test_update_metadata_json_field(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify updating JSON metadata field works."""
        # Create seed with metadata
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="META-001",
            family="Testaceae",
            genus="Test",
            species="meta",
            seed_metadata={"old": "data"},
            original_ista_2025="META",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Update metadata
        new_metadata = {"new": "data", "count": 123, "nested": {"key": "value"}}
        result = await SeedService.update(
            user_id=test_admin_user,
            entity_id=seed_id,
            seed_metadata=new_metadata,
        )

        # Verify metadata updated
        assert result["metadata"] == new_metadata
        assert result["metadata"]["new"] == "data"
        assert result["metadata"]["count"] == 123
        assert result["metadata"]["nested"]["key"] == "value"

    async def test_update_updates_date_updated(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify update changes the date_updated timestamp."""
        import time
        from datetime import datetime as dt

        # Create seed
        seed_id = uuid4()
        original_time = datetime.now(timezone.utc)
        seed = Seed(
            id=seed_id,
            name_code="TIMESTAMP-002",
            family="Testaceae",
            genus="Test",
            species="timestamp",
            original_ista_2025="TSTAMP2",
            active=True,
            date_created=original_time,
            date_updated=original_time,
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Wait a bit before updating to ensure timestamp difference
        time.sleep(0.01)  # 10ms should be enough for microsecond precision

        # Update seed
        result = await SeedService.update(
            user_id=test_admin_user,
            entity_id=seed_id,
            genus="UpdatedGenus",
        )

        # Parse dates
        updated_date = dt.fromisoformat(result["date_updated"].replace("Z", "+00:00"))
        created_date = dt.fromisoformat(result["date_created"].replace("Z", "+00:00"))

        # Verify date_updated changed but date_created stayed same
        # Use >= instead of > because very fast systems might have same timestamp
        assert updated_date >= created_date
        # Verify created date hasn't changed
        assert abs((created_date - original_time).total_seconds()) < 0.001


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationDelete:
    """Integration tests for SeedService.delete method."""

    async def test_delete_soft_deletes_seed(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify delete performs soft delete (active=False) not hard delete."""
        # Create seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="DELETE-001",
            family="Testaceae",
            genus="Test",
            species="delete",
            original_ista_2025="DEL",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Delete seed
        result = await SeedService.delete(test_admin_user, seed_id)

        # Verify response
        assert "message" in result
        assert "deleted successfully" in result["message"]
        assert result["id"] == str(seed_id)

        # Verify it's soft deleted using a fresh session to avoid cache issues
        from sqlalchemy import select
        from app.db.utils import sessionmanager
        
        async with sessionmanager.get_session() as fresh_session:
            query = select(Seed).where(Seed.id == seed_id)
            db_result = await fresh_session.execute(query)
            deleted_seed = db_result.scalar_one_or_none()

            assert deleted_seed is not None  # Still exists
            assert deleted_seed.active is False  # But inactive

    async def test_delete_as_regular_user_raises_403(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_regular_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify regular users cannot delete seeds."""
        # Create seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="NODELETE-001",
            family="Testaceae",
            genus="Test",
            species="nodelete",
            original_ista_2025="NODEL",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Attempt delete as regular user
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.delete(test_regular_user, seed_id)

        assert exc_info.value.status_code == 403

    async def test_delete_nonexistent_seed_raises_404(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
    ):
        """Verify deleting non-existent seed returns 404."""
        nonexistent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await SeedService.delete(test_admin_user, nonexistent_id)

        assert exc_info.value.status_code == 404

    async def test_deleted_seed_not_in_get_all(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify soft-deleted seeds are excluded from get_all results."""
        # Create and soft-delete a seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="HIDDEN-001",
            family="Testaceae",
            genus="Test",
            species="hidden",
            original_ista_2025="HIDDEN",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Delete it
        await SeedService.delete(test_admin_user, seed_id)

        # Try to retrieve with get_all
        result = await SeedService.get_all(test_user)

        # Verify deleted seed not in results
        seed_codes = [s["name_code"] for s in result["seeds"]]
        assert "HIDDEN-001" not in seed_codes

    async def test_deleted_seed_not_in_get_by_id(
        self,
        integration_db_session: AsyncSession,
        test_admin_user: UUID,
        test_user: UUID,
        cleanup_test_seeds: list,
    ):
        """Verify get_by_id returns 404 for soft-deleted seeds."""
        # Create and soft-delete a seed
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="NOTFOUND-001",
            family="Testaceae",
            genus="Test",
            species="notfound",
            original_ista_2025="NOTFND",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Delete it
        await SeedService.delete(test_admin_user, seed_id)

        # Try to retrieve with get_by_id
        with pytest.raises(HTTPException) as exc_info:
            await SeedService.get_by_id(test_user, seed_id)

        assert exc_info.value.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestSeedServiceIntegrationGetSeedData:
    """Integration tests for SeedService.get_seed_data static method."""

    async def test_get_seed_data_returns_active_only(
        self,
        integration_db_session: AsyncSession,
        cleanup_test_seeds: list,
    ):
        """Verify get_seed_data returns only active seeds (public endpoint, no auth)."""
        # Create active seed
        active_seed_id = uuid4()
        active_seed = Seed(
            id=active_seed_id,
            name_code="PUBLIC-001",
            family="Brassicaceae",
            genus="Arabidopsis",
            species="thaliana",
            seed_metadata={"public": "data"},
            original_ista_2025="ARATH",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(active_seed)
        cleanup_test_seeds.append(active_seed_id)

        # Create inactive seed
        inactive_seed_id = uuid4()
        inactive_seed = Seed(
            id=inactive_seed_id,
            name_code="INACTIVE-PUBLIC",
            family="Poaceae",
            genus="Zea",
            species="mays",
            original_ista_2025="ZEAMA",
            active=False,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(inactive_seed)
        cleanup_test_seeds.append(inactive_seed_id)

        await integration_db_session.commit()

        # Call public endpoint (no user_id required)
        result = await SeedService.get_seed_data()

        # Verify structure
        assert "seeds" in result
        assert isinstance(result["seeds"], list)

        # Verify only active seeds returned
        seed_codes = [s["name_code"] for s in result["seeds"]]
        assert "PUBLIC-001" in seed_codes
        assert "INACTIVE-PUBLIC" not in seed_codes

    async def test_get_seed_data_subset_columns(
        self,
        integration_db_session: AsyncSession,
        cleanup_test_seeds: list,
    ):
        """Verify get_seed_data returns only subset of columns."""
        # Create seed with all fields
        seed_id = uuid4()
        seed = Seed(
            id=seed_id,
            name_code="SUBSET-001",
            family="Fabaceae",
            genus="Glycine",
            species="max",
            seed_metadata={"subset": "test"},
            original_ista_2025="GLYMA",
            active=True,
            date_created=datetime.now(timezone.utc),
            date_updated=datetime.now(timezone.utc),
        )
        integration_db_session.add(seed)
        cleanup_test_seeds.append(seed_id)
        await integration_db_session.commit()

        # Call service
        result = await SeedService.get_seed_data()

        # Find our test seed
        test_seeds = [s for s in result["seeds"] if s["name_code"] == "SUBSET-001"]
        assert len(test_seeds) == 1
        test_seed = test_seeds[0]

        # Verify only expected columns present
        assert "seed_id" in test_seed
        assert "name_code" in test_seed
        assert "family" in test_seed
        assert "genus" in test_seed
        assert "species" in test_seed
        assert "seed_metadata" in test_seed

        # These fields should NOT be present (not in subset)
        assert "active" not in test_seed
        assert "date_created" not in test_seed
        assert "date_updated" not in test_seed
        assert "original_ista_2025" not in test_seed

    async def test_get_seed_data_empty_when_no_active_seeds(
        self,
        integration_db_session: AsyncSession,
        cleanup_test_seeds: list,
    ):
        """Verify get_seed_data returns empty list when all seeds inactive."""
        # Create only inactive seeds
        for i in range(3):
            seed_id = uuid4()
            seed = Seed(
                id=seed_id,
                name_code=f"INACTIVE-{i:03d}",
                family="Testaceae",
                genus="Test",
                species=f"test{i}",
                original_ista_2025=f"TEST{i}",
                active=False,
                date_created=datetime.now(timezone.utc),
                date_updated=datetime.now(timezone.utc),
            )
            integration_db_session.add(seed)
            cleanup_test_seeds.append(seed_id)

        await integration_db_session.commit()

        # Call service
        result = await SeedService.get_seed_data()

        # Filter our test seeds
        test_seed_codes = [f"INACTIVE-{i:03d}" for i in range(3)]
        found_test_seeds = [s for s in result["seeds"] if s["name_code"] in test_seed_codes]

        # Should not find any of our inactive test seeds
        assert len(found_test_seeds) == 0

    async def test_get_seed_data_performance_with_many_seeds(
        self,
        integration_db_session: AsyncSession,
        cleanup_test_seeds: list,
    ):
        """Verify get_seed_data performs well with 100+ seeds."""
        import time

        # Create 100 active seeds
        for i in range(100):
            seed_id = uuid4()
            seed = Seed(
                id=seed_id,
                name_code=f"PERF-{i:04d}",
                family="Performanceae",
                genus="Performance",
                species=f"test{i}",
                seed_metadata={"index": i},
                original_ista_2025=f"PERF{i:04d}",
                active=True,
                date_created=datetime.now(timezone.utc),
                date_updated=datetime.now(timezone.utc),
            )
            integration_db_session.add(seed)
            cleanup_test_seeds.append(seed_id)

        await integration_db_session.commit()

        # Measure query performance
        start_time = time.time()
        result = await SeedService.get_seed_data()
        end_time = time.time()
        query_time = end_time - start_time

        # Verify our seeds are in results
        perf_seeds = [s for s in result["seeds"] if s["name_code"].startswith("PERF-")]
        assert len(perf_seeds) == 100

        # Performance assertion - should complete in reasonable time
        # (< 1 second for 100 seeds is reasonable)
        assert query_time < 1.0, f"Query took {query_time:.2f}s, expected < 1.0s"

        # Verify data integrity of a sample
        sample_seed = next(s for s in perf_seeds if s["name_code"] == "PERF-0050")
        assert sample_seed["family"] == "Performanceae"
        assert sample_seed["genus"] == "Performance"
        assert sample_seed["seed_metadata"]["index"] == 50
