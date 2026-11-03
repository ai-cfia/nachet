"""Coordinate recoverable publication of immutable reviewed datasets."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import ReleaseConflict
from ..models.dataset import (
    Dataset,
    ReleaseDefinition,
    ReleaseMetadata,
    ReleaseRegistration,
    canonical_json,
    path_identity,
    sha256,
)
from ..models.manifest import CropReference, FileReference
from ..repositories.blob_repository import BlobRepository
from ..repositories.catalog import ReleaseCatalog, new_release
from ..repositories.registry import DatasetMembership, DatasetRelease
from ..utility.crop import crop_image, crop_recipe
from .manifest_service import ManifestService
from .preparation_service import remap_coco
from .query_service import QueryService
from .validation_service import ValidationService


class DatasetService:
    """Freeze prepared records, verify outputs, then mark the release ready.

    Only registry changes hold transactions; blob reads and cropping happen
    outside them. Identical retries recover incomplete publications.
    """

    def __init__(
        self,
        blobs: BlobRepository,
        sessions: async_sessionmaker[AsyncSession],
        queries: QueryService,
        manifests: ManifestService,
        validation: ValidationService,
        catalog: ReleaseCatalog,
    ):
        self.blobs = blobs
        self.sessions = sessions
        self.container = blobs.container
        self.queries = queries
        self.manifests = manifests
        self.validation = validation
        self.catalog = catalog

    async def create_release(self, metadata: ReleaseDefinition) -> ReleaseRegistration:
        await self.catalog.create(metadata)
        return await self.queries.registration(metadata.name, metadata.version)

    async def prepare_coco(self, name: str, version: str, coco: dict) -> Dataset:
        """Join offline labels to membership entities, then store reviewed labels."""
        members = await self.catalog.memberships(name, version)
        reviewed = remap_coco(coco, members)
        by_path = {path_identity(member.file_name): member for member in members}
        ordered = [
            by_path[path_identity(image["file_name"])].model_copy(
                update={"sources": reviewed.images[index].sources}
            )
            for index, image in enumerate(coco["images"])
        ]
        await self.catalog.prepare(name, version, reviewed, ordered)
        return await self.catalog.spec(name, version)

    async def _claim(
        self, spec: Dataset, request_hash: str, recipe
    ) -> ReleaseRegistration:
        try:
            async with self.sessions.begin() as session:
                row = await session.scalar(
                    select(DatasetRelease)
                    .where(
                        DatasetRelease.name == spec.name,
                        DatasetRelease.version == spec.version,
                    )
                    .with_for_update()
                )
                if row is not None:
                    if row.container != self.container:
                        raise ReleaseConflict(
                            "Release belongs to a different container"
                        )
                    if row.status == "draft":
                        stored = await self.catalog.spec(spec.name, spec.version)
                        if stored != spec:
                            raise ReleaseConflict(
                                "Publication differs from the prepared database release"
                            )
                    elif row.request_sha256 != request_hash:
                        raise ReleaseConflict(
                            "This name/version already has different inputs"
                        )
                else:
                    row = new_release(
                        ReleaseDefinition.model_validate(
                            spec.model_dump(mode="json", exclude={"coco"})
                        ),
                        self.container,
                    )
                    payload = spec.coco.model_dump(mode="json")
                    row.coco_categories = payload.pop("categories")
                    row.coco_annotations = payload.pop("annotations")
                    payload.pop("images")
                    row.coco_attributes = payload
                    session.add(row)
                    await session.flush()
                    for position, image in enumerate(spec.coco.images):
                        data = image.model_dump(mode="json")
                        for field in (
                            "id",
                            "file_name",
                            "width",
                            "height",
                            "split",
                            "sources",
                        ):
                            data.pop(field)
                        session.add(
                            DatasetMembership(
                                release_id=row.id,
                                position=position,
                                file_name=image.file_name,
                                sha256=image.file_name.rsplit("/", 1)[1][:-4],
                                split=image.split,
                                sources=[
                                    source.model_dump(mode="json")
                                    for source in image.sources
                                ],
                                image_id=image.id,
                                width=image.width,
                                height=image.height,
                                attributes=data,
                            )
                        )
                if row.status == "draft":
                    row.request_sha256 = request_hash
                    row.crop_recipe = recipe
                    row.status = "staging"
                    for field, value in (
                        ReleaseMetadata.from_spec(spec).model_dump().items()
                    ):
                        setattr(row, field, value)
        except IntegrityError:
            # The unique constraint also serializes concurrent initial claims.
            existing = await self.queries.registration(spec.name, spec.version)
            if existing.request_sha256 != request_hash:
                raise ReleaseConflict("This name/version already has different inputs")
            return existing
        return await self.queries.registration(spec.name, spec.version)

    async def publish(
        self, spec: Dataset | str, version: str | None = None
    ) -> ReleaseRegistration:
        if isinstance(spec, str):
            if version is None:
                raise ValueError("Publishing by name requires a version")
            spec = await self.catalog.spec(spec, version)
        spec = self.validation.validate_spec(spec)
        recipe = crop_recipe() if spec.generate_crops else None
        request_hash = self.manifests.request_hash(spec, recipe)
        registration = await self._claim(spec, request_hash, recipe)
        if registration.status == "ready":
            await self.queries.resolve(
                spec.name, spec.version, registration.manifest_sha256
            )
            return registration

        if registration.database_backed:
            spec = await self.catalog.spec(spec.name, spec.version)

        annotations: dict[int, list] = {}
        for annotation in spec.coco.annotations:
            annotations.setdefault(annotation.image_id, []).append(annotation)
        images: dict[str, FileReference] = {}
        crops: list[CropReference] = []
        for image in spec.coco.images:
            data = await self.blobs.download(image.file_name)
            decoded, images[image.file_name] = self.validation.validate_image(
                image, data
            )
            if spec.generate_crops:
                for annotation in annotations.get(image.id, []):
                    box, crop = crop_image(decoded, annotation.bbox)
                    key = f"png/classification/{sha256(crop)}.png"
                    reference = await self.blobs.put_file(key, crop, "image/png")
                    crops.append(
                        CropReference(
                            image_id=image.id,
                            annotation_id=annotation.id,
                            category_id=annotation.category_id,
                            split=image.split,
                            pixel_box=box,
                            file=reference,
                        )
                    )
        if spec.generate_crops and not crops:
            raise ValueError("A classifier-ready release requires at least one crop")
        if registration.database_backed:
            await self.catalog.record_outputs(registration.id, images, crops)
            manifest = await self.manifests.from_database(registration, spec)
        else:
            coco = await self.blobs.put_file(
                f"releases/{spec.name}/{spec.version}/coco.json",
                canonical_json(spec.coco.model_dump(mode="json")),
                "application/json",
            )
            manifest = self.manifests.build(
                registration, spec, recipe, coco, images, crops
            )
        manifest_bytes = self.manifests.serialize(manifest)
        if not registration.database_backed:
            await self.blobs.put_unchanged(
                registration.manifest_key,
                manifest_bytes,
                "application/json",
                conflict_message="Release manifest already has different content",
            )
        await self.validation.validate(manifest, spec.coco)
        async with self.sessions.begin() as session:
            row = await session.get(
                DatasetRelease, registration.id, with_for_update=True
            )
            if row is None or row.request_sha256 != request_hash:
                raise ReleaseConflict("Release registration changed during publication")
            if row.status == "ready" and row.manifest_sha256 != sha256(manifest_bytes):
                raise ReleaseConflict("Published manifest cannot be replaced")
            row.manifest_sha256 = sha256(manifest_bytes)
            row.status = "ready"
        return await self.queries.registration(spec.name, spec.version)
