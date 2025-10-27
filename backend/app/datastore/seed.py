from typing import Type, TypedDict, Optional
from uuid import UUID
from sqlalchemy import select
from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import Seed


class SeedDataRow(TypedDict):
    """Row type for seed data query results."""
    seed_id: UUID
    name_code: str
    family: str
    genus: str
    species: str
    seed_metadata: Optional[dict]


class SeedDataService(BaseCRUDDataService[Seed]):
    """Data access layer for seed database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Seed]:
        return Seed

    async def get_seed_data(self) -> list[SeedDataRow]:
        """
        Get active seed data with subset of columns.

        Returns only specific columns (seed_id, name_code, family, genus, species, seed_metadata)
        for active seeds only.

        Returns:
            List of dictionaries with seed data
        """
        query = select(
            Seed.id.label("seed_id"),
            Seed.name_code,
            Seed.family,
            Seed.genus,
            Seed.species,
            Seed.seed_metadata,
        ).where(Seed.active.is_(True))
        result = await self.session.execute(query)
        return [row._asdict() for row in result.all()]  # type: ignore[misc]
