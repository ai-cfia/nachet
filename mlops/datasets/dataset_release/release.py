"""Publish and resolve reviewed releases with recoverable blob/DB writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from blob.exceptions import BlobAlreadyExistsError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from utility.crop import crop_image, crop_recipe, decode_png, pixel_box

from .contract import (
    CropReference,
    DatasetDescription,
    FileReference,
    ReleaseManifest,
    ReleaseMetadata,
    ReleaseSpec,
    ReviewedCoco,
    canonical_json,
    sha256,
)
from .registry import DatasetRelease
from .storage import BlobStorage


class ReleaseConflict(ValueError):
    """An existing version or object contains different content."""


class ReleaseNotReady(ValueError):
    """A release has not completed publication."""


@dataclass(frozen=True)
class ReleaseRegistration:
    id: UUID
    name: str
    version: str
    author: str
    created_at: str
    container: str
    request_sha256: str
    manifest_key: str
    manifest_sha256: str | None
    status: str
    description: str | None
    has_bounding_boxes: bool | None
    has_classes: bool | None
    num_classes: int | None
    num_multi_object_images: int | None
    num_single_object_images: int | None
    dataset_cutoff_date: date | None
    previous_version: str | None

    @classmethod
    def from_row(cls, row: DatasetRelease) -> ReleaseRegistration:
        """Copy a registry row into an immutable registration with a UTC timestamp."""
        # SQLite returns naive timestamps; PostgreSQL returns aware timestamps.
        created_at = row.date_created
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        created_at = created_at.astimezone(UTC)
        return cls(
            row.id,
            row.name,
            row.version,
            row.author,
            created_at.isoformat(),
            row.container,
            row.request_sha256,
            row.manifest_key,
            row.manifest_sha256,
            row.status,
            row.description,
            row.has_bounding_boxes,
            row.has_classes,
            row.num_classes,
            row.num_multi_object_images,
            row.num_single_object_images,
            row.dataset_cutoff_date,
            row.previous_version,
        )

    def metadata(self) -> ReleaseMetadata:
        """Return descriptive metadata and recorded COCO statistics for this release."""
        return ReleaseMetadata.model_validate(self, from_attributes=True)

    def training_reference(self) -> dict[str, str]:
        """Persist these MLflow params and reuse them on resume/evaluation."""
        if self.status != "ready" or self.manifest_sha256 is None:
            raise ReleaseNotReady(f"{self.name}/{self.version}")
        return {
            "dataset_release_id": str(self.id),
            "dataset_name": self.name,
            "dataset_version": self.version,
            "dataset_manifest_key": self.manifest_key,
            "dataset_manifest_sha256": self.manifest_sha256,
            "dataset_container": self.container,
            "model_dataset": f"{self.id}@sha256:{self.manifest_sha256}",
        }


class DatasetController:
    """Administrative MLOps job API, independent of the backend application.

    The factory owns short transactions. Expensive blob reads/cropping happen
    outside them. A staging row reserves an identity before any writes; identical
    retries finish it after a crash. Only the last transaction makes it ready.
    """

    def __init__(
        self,
        storage: BlobStorage,
        sessions: async_sessionmaker[AsyncSession],
        container: str,
    ):
        """Bind storage, registry sessions, and the existing dataset container."""
        self.storage = storage
        self.sessions = sessions
        self.container = container

    async def get_release_registration(
        self, name: str, version: str
    ) -> ReleaseRegistration:
        """Look up a release, rejecting unknown versions and container mismatches.

        Staging registrations are returned so interrupted publications can resume.
        """
        async with self.sessions() as session:
            row = await session.scalar(
                select(DatasetRelease).where(
                    DatasetRelease.name == name, DatasetRelease.version == version
                )
            )
            if row is None:
                raise ReleaseNotReady(f"Unknown release {name}/{version}")
            if row.container != self.container:
                raise ReleaseConflict("Release belongs to a different container")
            return ReleaseRegistration.from_row(row)

    async def _claim(self, spec: ReleaseSpec, request_hash: str) -> ReleaseRegistration:
        """Reserve a staging registration or reuse one with identical inputs.

        The unique name/version constraint handles concurrent claims. Different
        inputs for an existing version raise ReleaseConflict.
        """
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
                    **ReleaseMetadata.from_spec(spec).model_dump(),
                )
                session.add(row)
                await session.flush()
        except IntegrityError:
            # The unique constraint also serializes concurrent initial claims.
            existing = await self.get_release_registration(spec.name, spec.version)
            if existing.request_sha256 != request_hash:
                raise ReleaseConflict("This name/version already has different inputs")
            return existing
        return await self.get_release_registration(spec.name, spec.version)

    async def _put_unchanged(
        self, key: str, data: bytes, content_type: str
    ) -> FileReference:
        """Create an object without overwriting and verify its exact stored bytes.

        Identical existing content is safe to reuse on retry; different content
        raises ReleaseConflict.
        """
        try:
            await self.storage.upload_blob(
                self.container, key, data, overwrite=False, content_type=content_type
            )
        except BlobAlreadyExistsError:
            # Expected for idempotent retries when the object is already present.
            # Integrity is validated below by downloading and comparing exact bytes.
            pass
        stored = await self.storage.download_blob(self.container, key)
        if stored != data:
            raise ReleaseConflict(f"Object already has different content: {key}")
        return FileReference(key=key, sha256=sha256(data), size=len(data))

    async def read_file(self, reference: FileReference) -> bytes:
        """Download a referenced object and verify its recorded size and SHA-256."""
        data = await self.storage.download_blob(self.container, reference.key)
        if len(data) != reference.size or sha256(data) != reference.sha256:
            raise ReleaseConflict(f"Object checksum/size mismatch: {reference.key}")
        return data

    async def publish_release(self, spec: ReleaseSpec) -> ReleaseRegistration:
        """Publish an immutable reviewed release from prepared hash-addressed PNGs.

        Validate images, optionally generate classification crops, and store COCO
        and manifest snapshots before marking the registration ready. Interrupted
        writes leave a staging registration that identical inputs can resume;
        a completed version is verified and reused.
        """
        # Re-validate at the boundary in case nested mutable lists were edited.
        spec = ReleaseSpec.model_validate(spec.model_dump(mode="json"))
        recipe = crop_recipe() if spec.generate_crops else None
        request_hash = self._request_hash(spec, recipe)

        # Reserve this version before writing objects, or verify a completed retry.
        registration = await self._claim(spec, request_hash)
        if registration.status == "ready":
            await self.load_verified_release(
                spec.name, spec.version, registration.manifest_sha256
            )
            return registration

        images, crops = await self._prepare_media(spec)
        coco = await self._put_unchanged(
            f"releases/{spec.name}/{spec.version}/coco.json",
            canonical_json(spec.coco.model_dump(mode="json")),
            "application/json",
        )
        manifest = ReleaseManifest(
            **registration.metadata().model_dump(),
            release_id=registration.id,
            name=spec.name,
            version=spec.version,
            author=spec.author,
            created_at=registration.created_at,
            request_sha256=request_hash,
            conversion=spec.conversion,
            crop_recipe=recipe,
            coco=coco,
            images=images,
            crops=crops,
        )
        manifest_sha256 = await self._store_manifest(
            registration.manifest_key, manifest
        )

        # Make the version selectable only after its complete snapshot is verified.
        await self._validate(manifest, spec.coco)
        return await self._mark_ready(registration, request_hash, manifest_sha256)

    @staticmethod
    def _request_hash(spec: ReleaseSpec, recipe: dict[str, Any] | None) -> str:
        """Hash publication inputs while preserving retries without optional metadata."""
        request_spec = spec.model_dump(mode="json")
        # Preserve request hashes for specifications written before these fields.
        for field in DatasetDescription.model_fields:
            if request_spec[field] is None:
                del request_spec[field]
        return sha256(
            canonical_json(
                {
                    "spec": request_spec,
                    "crop_recipe": recipe,
                }
            )
        )

    async def _prepare_media(
        self, spec: ReleaseSpec
    ) -> tuple[list[FileReference], list[CropReference]]:
        """Verify prepared PNGs and upload any requested classification crops.

        Return unique images in key order and crops in image order, retaining each
        image's annotation order and the bytes produced by identical retries.
        """
        annotations: dict[int, list] = {}
        for annotation in spec.coco.annotations:
            annotations.setdefault(annotation.image_id, []).append(annotation)
        images: dict[str, FileReference] = {}
        crops: list[CropReference] = []
        for image in spec.coco.images:
            data = await self.storage.download_blob(self.container, image.file_name)
            digest = sha256(data)
            if image.file_name != f"png/detection/{digest}.png":
                raise ValueError(
                    f"PNG bytes do not match hash filename: {image.file_name}"
                )
            try:
                decoded = decode_png(data, (image.width, image.height))
            except ValueError as error:
                raise ValueError(
                    f"Image dimensions/format do not match COCO: {image.id}"
                ) from error
            images[image.file_name] = FileReference(
                key=image.file_name, sha256=digest, size=len(data)
            )
            if spec.generate_crops:
                for annotation in annotations.get(image.id, []):
                    box, crop = crop_image(decoded, annotation.bbox)
                    key = f"png/classification/{sha256(crop)}.png"
                    reference = await self._put_unchanged(key, crop, "image/png")
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
        return sorted(images.values(), key=lambda item: item.key), crops

    async def _store_manifest(self, key: str, manifest: ReleaseManifest) -> str:
        """Write and verify immutable manifest bytes, returning their SHA-256 digest.

        Identical existing content is reused; different bytes raise ReleaseConflict.
        Unknown metadata is omitted so older staging publications remain retryable.
        """
        # Legacy staging registrations may already have an immutable manifest.
        # Omit unknown metadata to preserve its original bytes on retry.
        unknown_metadata = {
            field
            for field in ReleaseMetadata.model_fields
            if getattr(manifest, field) is None
        }
        manifest_bytes = canonical_json(
            manifest.model_dump(mode="json", exclude=unknown_metadata)
        )
        # release.json is intentionally separate from COCO: standard COCO has no
        # crop lineage or publication metadata. This is the v1 companion format.
        try:
            await self.storage.upload_blob(
                self.container,
                key,
                manifest_bytes,
                overwrite=False,
                content_type="application/json",
            )
        except BlobAlreadyExistsError:
            # Expected for idempotent publish/retry when manifest already exists.
            # Integrity is verified immediately below by downloading and comparing bytes.
            pass
        stored = await self.storage.download_blob(self.container, key)
        if stored != manifest_bytes:
            raise ReleaseConflict("Release manifest already has different content")
        return sha256(manifest_bytes)

    async def _mark_ready(
        self,
        registration: ReleaseRegistration,
        request_hash: str,
        manifest_sha256: str,
    ) -> ReleaseRegistration:
        """Commit the verified manifest digest under a lock without replacing a release."""
        async with self.sessions.begin() as session:
            row = await session.get(
                DatasetRelease, registration.id, with_for_update=True
            )
            if row is None or row.request_sha256 != request_hash:
                raise ReleaseConflict("Release registration changed during publication")
            if row.status == "ready" and row.manifest_sha256 != manifest_sha256:
                raise ReleaseConflict("Published manifest cannot be replaced")
            row.manifest_sha256 = manifest_sha256
            row.status = "ready"
        return await self.get_release_registration(
            registration.name, registration.version
        )

    async def load_verified_release(
        self,
        name: str,
        version: str,
        expected_manifest_sha256: str | None = None,
    ) -> tuple[ReleaseRegistration, ReleaseManifest, ReviewedCoco]:
        """Load a ready release and verify its identity, manifest, and files.

        An expected manifest digest pins the selection. Incomplete releases raise
        ReleaseNotReady; conflicting identities or checksums raise ReleaseConflict.
        """
        registration = await self.get_release_registration(name, version)
        if registration.status != "ready" or registration.manifest_sha256 is None:
            raise ReleaseNotReady(f"Release is incomplete: {name}/{version}")
        if (
            expected_manifest_sha256
            and expected_manifest_sha256 != registration.manifest_sha256
        ):
            raise ReleaseConflict("Pinned release differs from the selected version")
        data = await self.storage.download_blob(
            self.container, registration.manifest_key
        )
        if sha256(data) != registration.manifest_sha256:
            raise ReleaseConflict("Published release manifest checksum mismatch")
        manifest = ReleaseManifest.model_validate_json(data)
        if (
            manifest.release_id != registration.id
            or manifest.name != name
            or manifest.version != version
            or manifest.author != registration.author
            or manifest.created_at != registration.created_at
            or manifest.request_sha256 != registration.request_sha256
            or ReleaseMetadata.model_validate(
                manifest.model_dump(include=set(ReleaseMetadata.model_fields))
            )
            != registration.metadata()
        ):
            raise ReleaseConflict("Manifest identity does not match its registration")
        coco = ReviewedCoco.model_validate_json(await self.read_file(manifest.coco))
        await self._validate(manifest, coco)
        return registration, manifest, coco

    async def _validate(self, manifest: ReleaseManifest, coco: ReviewedCoco) -> None:
        """Verify snapshot statistics, image membership, crop lineage, and file bytes."""
        for field, expected in ReleaseMetadata.statistics(coco).items():
            recorded = getattr(manifest, field)
            if recorded is not None and recorded != expected:
                raise ValueError(f"Manifest {field} differs from reviewed COCO")
        files = {reference.key: reference for reference in manifest.images}
        if len(files) != len(manifest.images) or set(files) != {
            image.file_name for image in coco.images
        }:
            raise ValueError("Manifest image membership differs from COCO")
        for reference in files.values():
            if reference.key != f"png/detection/{reference.sha256}.png":
                raise ValueError("Manifest image hash differs from its key")
            await self.read_file(reference)
        parents = {image.id: image for image in coco.images}
        annotations = {annotation.id: annotation for annotation in coco.annotations}
        crop_ids = [crop.annotation_id for crop in manifest.crops]
        if manifest.crop_recipe is None:
            if crop_ids:
                raise ValueError("Crop mappings have no generation recipe")
        elif len(crop_ids) != len(set(crop_ids)) or set(crop_ids) != set(annotations):
            raise ValueError("Classifier crop mappings are incomplete or duplicated")
        for crop in manifest.crops:
            annotation = annotations[crop.annotation_id]
            parent = parents[annotation.image_id]
            if (
                crop.image_id != parent.id
                or crop.category_id != annotation.category_id
                or crop.split != parent.split
                or crop.pixel_box != pixel_box(annotation.bbox)
                or crop.file.key != f"png/classification/{crop.file.sha256}.png"
            ):
                raise ValueError("Crop mapping does not match its reviewed annotation")
            await self.read_file(crop.file)
