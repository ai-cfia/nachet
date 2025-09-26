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
                directories = await DirectoryDataService(
                    session
                ).get_user_directories_count(user_id)

            return {
                "directories": [directory._asdict() for directory in directories]
                if directories
                else []
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def create_directory(
        user_id: str, name: str, folder_prefix: str, description: str = ""
    ) -> str:
        try:
            async with sessionmanager.get_session() as session:
                new_directory = await DirectoryDataService(session).create_directory(
                    user_id, name, folder_prefix, description
                )
                await session.commit()
                return new_directory._asdict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def rename_directory(directory_id: str, new_name: str) -> str:
        try:
            async with sessionmanager.get_session() as session:
                updated_directory = await DirectoryDataService(
                    session
                ).rename_directory(directory_id, new_name)
                await session.commit()
                return updated_directory
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
