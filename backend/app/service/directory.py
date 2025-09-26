from typing import List, Dict, Any
from app.datastore import DirectoryDataService
from fastapi import HTTPException
from app.db.utils import sessionmanager


class DirectoryService:
    """Service operations on directories."""

    @staticmethod
    async def get_user_directories(user_id: str) -> List[Dict[str, Any]]:
        try:
            directories = None
            async with sessionmanager.get_session() as session:
                directories = await DirectoryDataService(session).get_user_directories(
                    user_id
                )

            return {
                "directories": [directory._asdict() for directory in directories]
                if directories
                else []
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
