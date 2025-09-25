from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.model import Seed


class SeedDataService:
    """Repository class for seed data database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_seed_data(self) -> List[Dict[str, Any]]:
        query = select(
            Seed.id,
            Seed.name_code,
            Seed.family,
            Seed.genus,
            Seed.species,
            Seed.seed_metadata,
        ).where(Seed.active.is_(True))
        result = await self.session.execute(query)
        return result.all()
