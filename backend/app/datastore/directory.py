from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects import postgresql
from sqlalchemy import select, func
from app.db.model import Folder, Picture


class DirectoryDataService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_directories_count(self, user_id: str) -> List[Folder]:
        """
        Retrieve all directories for a given user and number of pictures from the database.

        Args:
            user_id: The ID of the user whose directories are to be fetched.
        Returns:
            List of Folder objects.
        """
        stmt = (
            select(
                Folder.id,
                Folder.name,
                Folder.folder_prefix,
                Folder.description,
                func.count(Picture.id).label("picture_count"),
            )
            .join(Picture, isouter=True)
            .where(Folder.user_id == user_id)
            .where(Folder.active.is_(True))
            .group_by(Folder.id, Folder.name, Folder.folder_prefix, Folder.description)
        )
        print(stmt.compile(dialect=postgresql.dialect()))
        result = await self.session.execute(stmt)
        return result.all()
