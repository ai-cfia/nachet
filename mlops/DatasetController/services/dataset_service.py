"""Coordinate recoverable publication of immutable reviewed datasets."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import ReleaseConflict
from ..models.dataset import Dataset, ReleaseRegistration, canonical_json, sha256
from ..models.manifest import CropReference, FileReference
from ..repositories.blob_repository import BlobRepository
from ..repositories.registry import DatasetRelease
from ..utility.crop import crop_image, crop_recipe
from .manifest_service import ManifestService
from .query_service import QueryService
from .validation_service import ValidationService


class DatasetService:
    """Reserve a staging identity, write snapshots, then mark the release ready.

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
    ):
        self.blobs = blobs
        self.sessions = sessions
        self.container = blobs.container
        self.queries = queries
        self.manifests = manifests
        self.validation = validation

    async def _claim(self, spec: Dataset, request_hash: str) -> ReleaseRegistration:
        try:
            async with self.sessions.begin() as session:
                row = DatasetRelease(
                    id=uuid4(),
                    name=spec.name,
                    version=spec.version,
                    author=spec.author,
                    date_created=datetime.now(UTC),
                    container=self.container,
                    request_sha256=request_hash,
                    manifest_key=f"releases/{spec.name}/{spec.version}/release.json",
                    status="staging",
                )
                session.add(row)
                await session.flush()
        except IntegrityError:
            # The unique constraint also serializes concurrent initial claims.
            existing = await self.queries.registration(spec.name, spec.version)
            if existing.request_sha256 != request_hash:
                raise ReleaseConflict("This name/version already has different inputs")
            return existing
        return await self.queries.registration(spec.name, spec.version)

    async def publish(self, spec: Dataset) -> ReleaseRegistration:
        spec = self.validation.validate_spec(spec)
        recipe = crop_recipe() if spec.generate_crops else None
        request_hash = self.manifests.request_hash(spec, recipe)
        registration = await self._claim(spec, request_hash)
        if registration.status == "ready":
            await self.queries.resolve(
                spec.name, spec.version, registration.manifest_sha256
            )
            return registration

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
        coco = await self.blobs.put_file(
            f"releases/{spec.name}/{spec.version}/coco.json",
            canonical_json(spec.coco.model_dump(mode="json")),
            "application/json",
        )
        manifest = self.manifests.build(registration, spec, recipe, coco, images, crops)
        manifest_bytes = self.manifests.serialize(manifest)
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
