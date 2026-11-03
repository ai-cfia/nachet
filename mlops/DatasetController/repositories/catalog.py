"""Database entities for release preparation and generated JSON documents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import ReleaseConflict, ReleaseNotReady
from ..models.dataset import (
    ConversionRecipe,
    ImageMembership,
    ReleaseDefinition,
    ReleaseMetadata,
    ReleaseSpec,
    ReviewedCoco,
)
from ..models.manifest import CropReference, FileReference
from .registry import DatasetCrop, DatasetMembership, DatasetRelease

if TYPE_CHECKING:
    from ..models.dataset import ReleaseRegistration


def definition(row: DatasetRelease) -> ReleaseDefinition:
    return ReleaseDefinition(
        name=row.name,
        version=row.version,
        author=row.author,
        description=row.description,
        dataset_cutoff_date=row.dataset_cutoff_date,
        previous_version=row.previous_version,
        conversion=ConversionRecipe(
            code_revision=row.conversion_revision, settings=row.conversion_settings
        ),
        generate_crops=row.generate_crops,
    )


def new_release(value: ReleaseDefinition, container: str) -> DatasetRelease:
    return DatasetRelease(
        id=uuid4(),
        name=value.name,
        version=value.version,
        author=value.author,
        description=value.description,
        dataset_cutoff_date=value.dataset_cutoff_date,
        previous_version=value.previous_version,
        conversion_revision=value.conversion.code_revision,
        conversion_settings=value.conversion.settings,
        generate_crops=value.generate_crops,
        container=container,
        date_created=datetime.now(UTC),
        manifest_key=f"releases/{value.name}/{value.version}/release.json",
        database_backed=True,
        status="draft",
    )


class ReleaseCatalog:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], container: str):
        self.sessions = sessions
        self.container = container

    async def row(
        self, session: AsyncSession, name: str, version: str, *, lock: bool = False
    ) -> DatasetRelease:
        query = select(DatasetRelease).where(
            DatasetRelease.name == name, DatasetRelease.version == version
        )
        if lock:
            query = query.with_for_update()
        row = await session.scalar(query)
        if row is None:
            raise ReleaseNotReady(f"Unknown release {name}/{version}")
        if row.container != self.container:
            raise ReleaseConflict("Release belongs to a different container")
        return row

    @staticmethod
    def require_draft(row: DatasetRelease) -> None:
        if row.status != "draft" or not row.database_backed:
            raise ReleaseConflict("Only draft releases can be prepared or edited")

    async def create(self, value: ReleaseDefinition) -> None:
        value = ReleaseDefinition.model_validate(value.model_dump(mode="json"))
        try:
            async with self.sessions.begin() as session:
                session.add(new_release(value, self.container))
        except IntegrityError as error:
            raise ReleaseConflict("Release name/version already exists") from error

    async def metadata(self, name: str, version: str) -> ReleaseDefinition:
        async with self.sessions() as session:
            row = await self.row(session, name, version)
            if not row.database_backed:
                raise ReleaseNotReady("Legacy release metadata lives in its snapshot")
            return definition(row)

    async def members(
        self, session: AsyncSession, row: DatasetRelease
    ) -> list[DatasetMembership]:
        return list(
            await session.scalars(
                select(DatasetMembership)
                .where(DatasetMembership.release_id == row.id)
                .order_by(DatasetMembership.position)
            )
        )

    async def memberships(self, name: str, version: str) -> list[ImageMembership]:
        async with self.sessions() as session:
            row = await self.row(session, name, version)
            return [
                ImageMembership(
                    file_name=member.file_name,
                    sha256=member.sha256,
                    split=member.split,
                    sources=member.sources,
                )
                for member in await self.members(session, row)
            ]

    async def add_membership(
        self, name: str, version: str, member: ImageMembership
    ) -> None:
        member = ImageMembership.model_validate(member.model_dump(mode="json"))
        from ..models.dataset import path_identity

        async with self.sessions.begin() as session:
            row = await self.row(session, name, version, lock=True)
            self.require_draft(row)
            if row.coco_annotations is not None:
                raise ReleaseConflict(
                    "Membership is fixed after reviewed labels are prepared"
                )
            members = await self.members(session, row)
            if any(
                item.file_name == path_identity(member.file_name) for item in members
            ):
                raise ReleaseConflict("Duplicate membership path")
            session.add(
                DatasetMembership(
                    release_id=row.id,
                    position=len(members),
                    **member.model_dump(mode="json", exclude={"file_name"}),
                    file_name=path_identity(member.file_name),
                )
            )

    async def prepare(
        self,
        name: str,
        version: str,
        coco: ReviewedCoco,
        memberships: list[ImageMembership] | None = None,
    ) -> None:
        """Atomically save reviewed labels and their per-image entities."""
        coco = ReviewedCoco.model_validate(coco.model_dump(mode="json"))
        from ..models.dataset import path_identity

        async with self.sessions.begin() as session:
            row = await self.row(session, name, version, lock=True)
            self.require_draft(row)
            existing = await self.members(session, row)
            if memberships is None:
                memberships = [
                    ImageMembership(
                        file_name=image.file_name,
                        sha256=image.file_name.rsplit("/", 1)[1][:-4],
                        split=image.split,
                        sources=image.sources,
                    )
                    for image in coco.images
                ]
            if len(memberships) != len(coco.images):
                raise ValueError(
                    "Membership must contain one record per reviewed image"
                )
            # Matching by image ID/order is confined to this already-remapped
            # result; raw offline COCO must be joined by explicit exported paths.
            values = []
            for position, (image, member) in enumerate(zip(coco.images, memberships)):
                if (
                    image.file_name != f"png/detection/{member.sha256}.png"
                    or image.split != member.split
                    or image.sources != member.sources
                ):
                    raise ValueError("Prepared image differs from its membership")
                data = image.model_dump(mode="json")
                for field in ("id", "file_name", "width", "height", "split", "sources"):
                    data.pop(field)
                values.append(
                    DatasetMembership(
                        release_id=row.id,
                        position=position,
                        file_name=path_identity(member.file_name),
                        sha256=member.sha256,
                        split=member.split,
                        sources=[
                            source.model_dump(mode="json") for source in member.sources
                        ],
                        image_id=image.id,
                        width=image.width,
                        height=image.height,
                        attributes=data,
                    )
                )
            # Preserve registered paths and splits. Empty sources may be filled
            # from reviewed COCO, but existing provenance cannot be replaced.
            if existing:
                by_path = {item.file_name: item for item in values}
                if len(existing) != len(values):
                    raise ReleaseConflict(
                        "Reviewed images differ from stored membership"
                    )
                for item in existing:
                    prepared = by_path.get(item.file_name)
                    if (
                        prepared is None
                        or prepared.sha256 != item.sha256
                        or prepared.split != item.split
                        or (item.sources and prepared.sources != item.sources)
                    ):
                        raise ReleaseConflict(
                            "Reviewed images differ from stored membership"
                        )
            await session.execute(
                delete(DatasetMembership).where(DatasetMembership.release_id == row.id)
            )
            await session.flush()
            session.add_all(values)
            payload = coco.model_dump(mode="json")
            row.coco_categories = payload.pop("categories")
            row.coco_annotations = payload.pop("annotations")
            payload.pop("images")
            row.coco_attributes = payload
            for field, value in (
                ReleaseMetadata.from_spec(
                    ReleaseSpec(**definition(row).model_dump(), coco=coco)
                )
                .model_dump()
                .items()
            ):
                setattr(row, field, value)

    async def spec(self, name: str, version: str) -> ReleaseSpec:
        async with self.sessions() as session:
            row = await self.row(session, name, version)
            if not row.database_backed or row.coco_annotations is None:
                raise ReleaseNotReady(
                    "Reviewed labels have not been prepared in the database"
                )
            images = []
            for member in await self.members(session, row):
                images.append(
                    {
                        **(member.attributes or {}),
                        "id": member.image_id,
                        "file_name": f"png/detection/{member.sha256}.png",
                        "width": member.width,
                        "height": member.height,
                        "split": member.split,
                        "sources": member.sources,
                    }
                )
            return ReleaseSpec(
                **definition(row).model_dump(),
                coco=ReviewedCoco.model_validate(
                    {
                        **row.coco_attributes,
                        "images": images,
                        "categories": row.coco_categories,
                        "annotations": row.coco_annotations,
                    }
                ),
            )

    async def record_outputs(
        self,
        release_id: UUID,
        images: dict[str, FileReference],
        crops: list[CropReference],
    ) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(DatasetRelease, release_id, with_for_update=True)
            if row.status == "ready":
                return
            for member in await self.members(session, row):
                member.size = images[f"png/detection/{member.sha256}.png"].size
            # Concurrent retries record identical outputs under the row lock.
            await session.execute(
                delete(DatasetCrop).where(DatasetCrop.release_id == release_id)
            )
            await session.flush()
            session.add_all(
                [
                    DatasetCrop(
                        release_id=release_id,
                        position=position,
                        annotation_id=crop.annotation_id,
                        pixel_box=list(crop.pixel_box),
                        sha256=crop.file.sha256,
                        size=crop.file.size,
                    )
                    for position, crop in enumerate(crops)
                ]
            )

    async def outputs(
        self, registration: ReleaseRegistration, spec: ReleaseSpec
    ) -> tuple[dict[str, FileReference], list[CropReference], dict | None]:
        async with self.sessions() as session:
            row = await session.get(DatasetRelease, registration.id)
            images = {}
            for member in await self.members(session, row):
                key = f"png/detection/{member.sha256}.png"
                images[key] = FileReference(
                    key=key, sha256=member.sha256, size=member.size
                )
            by_image = {image.id: image for image in spec.coco.images}
            by_annotation = {item.id: item for item in spec.coco.annotations}
            crops = []
            for item in await session.scalars(
                select(DatasetCrop)
                .where(DatasetCrop.release_id == row.id)
                .order_by(DatasetCrop.position)
            ):
                annotation = by_annotation[item.annotation_id]
                crops.append(
                    CropReference(
                        image_id=annotation.image_id,
                        annotation_id=item.annotation_id,
                        category_id=annotation.category_id,
                        split=by_image[annotation.image_id].split,
                        pixel_box=item.pixel_box,
                        file=FileReference(
                            key=f"png/classification/{item.sha256}.png",
                            sha256=item.sha256,
                            size=item.size,
                        ),
                    )
                )
            return images, crops, row.crop_recipe
