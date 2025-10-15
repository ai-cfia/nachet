from typing import Type, List, Dict, Any
from sqlalchemy import select
from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import Seed


class SeedDataService(BaseCRUDDataService[Seed]):
    """Data access layer for seed database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Seed]:
        return Seed

    async def get_seed_data(self) -> List[Dict[str, Any]]:
        """
        Get active seed data with subset of columns.
        
        Returns only specific columns (seed_id, name_code, family, genus, species, seed_metadata)
        for active seeds only.
        
        Returns:
            List[Dict[str, Any]]: List of seed records with subset of columns as SQLAlchemy Row objects
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
        return result.all()
