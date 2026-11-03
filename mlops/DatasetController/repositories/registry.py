"""MLOps release registrations; no backend models or application tables."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DatasetRelease(Base):
    """Authoritative release metadata and reviewed labels."""

    __tablename__ = "dataset_release"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_dataset_release_name_version"),
        CheckConstraint(
            "status IN ('draft', 'staging', 'ready')", name="ck_dataset_release_status"
        ),
        CheckConstraint(
            "status != 'ready' OR manifest_sha256 IS NOT NULL",
            name="ck_dataset_release_ready_manifest",
        ),
        CheckConstraint(
            "status = 'draft' OR request_sha256 IS NOT NULL",
            name="ck_dataset_release_request",
        ),
        CheckConstraint("num_classes >= 0", name="ck_dataset_release_num_classes"),
        CheckConstraint(
            "num_multi_object_images >= 0",
            name="ck_dataset_release_num_multi_object_images",
        ),
        CheckConstraint(
            "num_single_object_images >= 0",
            name="ck_dataset_release_num_single_object_images",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    has_bounding_boxes: Mapped[bool | None] = mapped_column(Boolean)
    has_classes: Mapped[bool | None] = mapped_column(Boolean)
    num_classes: Mapped[int | None] = mapped_column(Integer)
    num_multi_object_images: Mapped[int | None] = mapped_column(Integer)
    num_single_object_images: Mapped[int | None] = mapped_column(Integer)
    dataset_cutoff_date: Mapped[date | None] = mapped_column(Date)
    previous_version: Mapped[str | None] = mapped_column(Text)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    container: Mapped[str] = mapped_column(Text, nullable=False)
    request_sha256: Mapped[str | None] = mapped_column(String(64))
    manifest_key: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="staging")
    database_backed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="false"
    )
    conversion_revision: Mapped[str | None] = mapped_column(Text)
    conversion_settings: Mapped[dict | None] = mapped_column(JSON)
    generate_crops: Mapped[bool | None] = mapped_column(Boolean)
    coco_attributes: Mapped[dict | None] = mapped_column(JSON)
    coco_categories: Mapped[list | None] = mapped_column(JSON)
    coco_annotations: Mapped[list | None] = mapped_column(JSON)
    crop_recipe: Mapped[dict | None] = mapped_column(JSON)


class DatasetMembership(Base):
    """One release image; the exported path is an explicit join key."""

    __tablename__ = "dataset_membership"
    __table_args__ = (
        UniqueConstraint("release_id", "image_id", name="uq_membership_image"),
        UniqueConstraint("release_id", "position", name="uq_membership_position"),
        CheckConstraint(
            "split IN ('train', 'validation', 'test')", name="ck_membership_split"
        ),
        CheckConstraint("length(sha256) = 64", name="ck_membership_hash"),
        CheckConstraint("width > 0 AND height > 0", name="ck_membership_dimensions"),
        CheckConstraint("size > 0", name="ck_membership_size"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    release_id: Mapped[UUID] = mapped_column(
        ForeignKey("dataset_release.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    split: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSON, nullable=False)
    image_id: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    attributes: Mapped[dict | None] = mapped_column(JSON)
    size: Mapped[int | None] = mapped_column(Integer)


class DatasetCrop(Base):
    """Generated crop identity and lineage for a release."""

    __tablename__ = "dataset_crop"
    __table_args__ = (
        UniqueConstraint("release_id", "annotation_id", name="uq_crop_annotation"),
        UniqueConstraint("release_id", "position", name="uq_crop_position"),
        CheckConstraint("size > 0", name="ck_crop_size"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    release_id: Mapped[UUID] = mapped_column(
        ForeignKey("dataset_release.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    annotation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pixel_box: Mapped[list] = mapped_column(JSON, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)


def registry_engine(database_url: str, schema: str | None) -> AsyncEngine:
    return create_async_engine(
        database_url, execution_options={"schema_translate_map": {None: schema}}
    )
