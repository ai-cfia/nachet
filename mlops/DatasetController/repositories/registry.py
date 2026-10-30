"""MLOps release registrations; no backend models or application tables."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint, Uuid
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DatasetRelease(Base):
    """Labels, membership and crop relationships remain in the blob snapshot."""

    __tablename__ = "dataset_release"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_dataset_release_name_version"),
        CheckConstraint(
            "status IN ('staging', 'ready')", name="ck_dataset_release_status"
        ),
        CheckConstraint(
            "status != 'ready' OR manifest_sha256 IS NOT NULL",
            name="ck_dataset_release_ready_manifest",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    container: Mapped[str] = mapped_column(Text, nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_key: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="staging")


def registry_engine(database_url: str, schema: str | None) -> AsyncEngine:
    return create_async_engine(
        database_url, execution_options={"schema_translate_map": {None: schema}}
    )
