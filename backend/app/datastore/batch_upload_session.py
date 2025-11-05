"""Data access layer for batch upload session database operations."""

from beartype.typing import Type, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, update
from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import BatchUploadSession


class BatchUploadSessionDataService(BaseCRUDDataService[BatchUploadSession]):
    """Data access layer for batch upload session database operations."""

    @classmethod
    def get_model_class(cls) -> Type[BatchUploadSession]:
        return BatchUploadSession

    async def create_session(
        self,
        session_id: UUID,
        user_id: UUID,
        folder_id: UUID,
        file_count: int,
        ttl_hours: int = 24,
    ) -> BatchUploadSession:
        """
        Create a new batch upload session.

        Args:
            session_id: Unique session identifier
            user_id: User who owns the session
            folder_id: Target folder for uploads
            file_count: Expected number of files to upload (max 1000)
            ttl_hours: Time-to-live in hours (default: 24)

        Returns:
            Created BatchUploadSession instance
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        session = BatchUploadSession(
            id=session_id,
            user_id=user_id,
            folder_id=folder_id,
            file_count=file_count,
            uploaded_count=0,
            duplicate_count=0,
            active=True,
            expires_at=expires_at,
        )

        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        return session

    async def get_by_id(self, entity_id: UUID) -> Optional[BatchUploadSession]:
        """
        Get batch upload session by ID.

        Args:
            entity_id: Session UUID

        Returns:
            BatchUploadSession instance or None if not found
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug(
            "Fetching batch upload session",
            session_id=str(entity_id),
        )

        start_time = time.time()

        query = select(BatchUploadSession).where(BatchUploadSession.id == entity_id)
        result = await self.session.execute(query)
        session = result.scalar_one_or_none()

        elapsed_ms = (time.time() - start_time) * 1000

        if session:
            logger.debug(
                "Session found",
                session_id=str(entity_id),
                active=session.active,
                uploaded_count=session.uploaded_count,
                duplicate_count=session.duplicate_count,
                file_count=session.file_count,
                duration_ms=round(elapsed_ms, 2),
            )
        else:
            logger.debug(
                "Session not found",
                session_id=str(entity_id),
                duration_ms=round(elapsed_ms, 2),
            )

        return session

    async def increment_uploaded_count(self, session_id: UUID) -> None:
        """
        Increment the uploaded_count for a session.

        Args:
            session_id: Session UUID
        """
        stmt = (
            update(BatchUploadSession)
            .where(BatchUploadSession.id == session_id)
            .values(uploaded_count=BatchUploadSession.uploaded_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def increment_duplicate_count(self, session_id: UUID) -> None:
        """
        Increment the duplicate_count for a session.

        Args:
            session_id: Session UUID
        """
        stmt = (
            update(BatchUploadSession)
            .where(BatchUploadSession.id == session_id)
            .values(duplicate_count=BatchUploadSession.duplicate_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_counts(
        self, session_id: UUID, uploaded_delta: int = 0, duplicate_delta: int = 0
    ) -> None:
        """
        Update uploaded_count and duplicate_count atomically.

        Args:
            session_id: Session UUID
            uploaded_delta: Amount to add to uploaded_count (default: 0)
            duplicate_delta: Amount to add to duplicate_count (default: 0)
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug(
            "Updating session counts",
            session_id=str(session_id),
            uploaded_delta=uploaded_delta,
            duplicate_delta=duplicate_delta,
        )

        start_time = time.time()

        updates = {}
        if uploaded_delta != 0:
            updates["uploaded_count"] = (
                BatchUploadSession.uploaded_count + uploaded_delta
            )
        if duplicate_delta != 0:
            updates["duplicate_count"] = (
                BatchUploadSession.duplicate_count + duplicate_delta
            )

        if updates:
            stmt = (
                update(BatchUploadSession)
                .where(BatchUploadSession.id == session_id)
                .values(**updates)
            )
            await self.session.execute(stmt)
            await self.session.flush()

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Session counts updated",
                session_id=str(session_id),
                duration_ms=round(elapsed_ms, 2),
            )
        else:
            logger.debug(
                "No counts to update (both deltas are 0)",
                session_id=str(session_id),
            )

    async def mark_inactive(self, session_id: UUID) -> None:
        """
        Mark a session as inactive (completed or cancelled).

        Args:
            session_id: Session UUID
        """
        from app.service.logs import LogService

        logger = LogService.get_logger()

        logger.debug(
            "Marking session inactive",
            session_id=str(session_id),
        )

        stmt = (
            update(BatchUploadSession)
            .where(BatchUploadSession.id == session_id)
            .values(active=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        logger.debug(
            "Session marked inactive",
            session_id=str(session_id),
        )

    async def is_expired(self, session_id: UUID) -> bool:
        """
        Check if a session has expired (past its TTL).

        Args:
            session_id: Session UUID

        Returns:
            True if expired, False otherwise
        """
        session = await self.get_by_id(session_id)
        if not session:
            return True
        return datetime.now(timezone.utc) > session.expires_at

    async def is_complete(self, session_id: UUID) -> bool:
        """
        Check if a session has reached its file_count limit.

        Args:
            session_id: Session UUID

        Returns:
            True if uploaded_count >= file_count, False otherwise
        """
        session = await self.get_by_id(session_id)
        if not session:
            return True
        return session.uploaded_count >= session.file_count
