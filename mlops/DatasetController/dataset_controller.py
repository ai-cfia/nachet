"""Public facade for the reviewed dataset release workflow."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models.dataset import Dataset, ReleaseRegistration, ReviewedCoco
from .models.manifest import FileReference, ReleaseManifest
from .repositories.blob_repository import BlobRepository, BlobStorage
from .services.dataset_service import DatasetService
from .services.manifest_service import ManifestService
from .services.query_service import QueryService
from .services.validation_service import ValidationService


class DatasetController:
    """Coordinate release operations without backend application dependencies.

    Callers supply storage, a session factory and an existing container. Runtime
    configuration and resource cleanup remain the caller's responsibility.
    """

    def __init__(
        self,
        storage: BlobStorage,
        sessions: async_sessionmaker[AsyncSession],
        container: str,
    ):
        blobs = BlobRepository(storage, container)
        self._validation = ValidationService(blobs)
        self._queries = QueryService(sessions, blobs, self._validation)
        self._datasets = DatasetService(
            blobs, sessions, self._queries, ManifestService(), self._validation
        )

    async def publish(self, spec: Dataset) -> ReleaseRegistration:
        """Publish or resume an immutable reviewed release."""
        return await self._datasets.publish(spec)

    async def registration(self, name: str, version: str) -> ReleaseRegistration:
        """Look up a release, including an incomplete staging registration."""
        return await self._queries.registration(name, version)

    async def resolve(
        self,
        name: str,
        version: str,
        expected_manifest_sha256: str | None = None,
    ) -> tuple[ReleaseRegistration, ReleaseManifest, ReviewedCoco]:
        """Resolve a ready release and verify its identity and referenced files."""
        return await self._queries.resolve(name, version, expected_manifest_sha256)

    async def read_file(self, reference: FileReference) -> bytes:
        """Download a referenced file and verify its checksum and size."""
        return await self._validation.read_file(reference)
