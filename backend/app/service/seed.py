from typing import List, Dict, Any
from app.datastore import SeedDataService
from fastapi import HTTPException
from app.db.utils import sessionmanager


class SeedService:
    """Service operations on seed data."""

    @staticmethod
    async def get_seed_data() -> List[Dict[str, Any]]:
        """
        Retrieve seed data from the database.
        """
        try:
            seeds = None
            async with sessionmanager.get_session() as session:
                seeds = await SeedDataService(session).get_seed_data()
            return [seed._asdict() for seed in seeds] if seeds else []
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
