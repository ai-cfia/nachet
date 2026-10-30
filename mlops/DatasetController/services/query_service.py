"""Look up release metadata and resolve verified, optionally pinned snapshots."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import ReleaseConflict, ReleaseNotReady
from ..models.dataset import ReleaseRegistration, ReviewedCoco, sha256
from ..models.manifest import ReleaseManifest
from ..repositories.blob_repository import BlobRepository
from ..repositories.registry import DatasetRelease
from .validation_service import ValidationService


class QueryService:
    """Release-scoped querying by name/version with container isolation."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        blobs: BlobRepository,
        validation: ValidationService,
    ):
        self.sessions = sessions
        self.blobs = blobs
        self.container = blobs.container
        self.validation = validation

    async def registration(self, name: str, version: str) -> ReleaseRegistration:
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

    async def resolve(
        self,
        name: str,
        version: str,
        expected_manifest_sha256: str | None = None,
    ) -> tuple[ReleaseRegistration, ReleaseManifest, ReviewedCoco]:
        registration = await self.registration(name, version)
        if registration.status != "ready" or registration.manifest_sha256 is None:
            raise ReleaseNotReady(f"Release is incomplete: {name}/{version}")
        if (
            expected_manifest_sha256
            and expected_manifest_sha256 != registration.manifest_sha256
        ):
            raise ReleaseConflict("Pinned release differs from the selected version")
        data = await self.blobs.download(registration.manifest_key)
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
        ):
            raise ReleaseConflict("Manifest identity does not match its registration")
        coco = ReviewedCoco.model_validate_json(
            await self.validation.read_file(manifest.coco)
        )
        await self.validation.validate(manifest, coco)
        return registration, manifest, coco
