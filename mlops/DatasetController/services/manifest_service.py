"""Build deterministic release identities and manifests."""

from typing import Any

from ..models.dataset import (
    Dataset,
    DatasetDescription,
    ReleaseRegistration,
    canonical_json,
    sha256,
)
from ..models.manifest import CropReference, FileReference, ReleaseManifest
from ..repositories.catalog import ReleaseCatalog


class ManifestService:
    def __init__(self, catalog: ReleaseCatalog):
        self.catalog = catalog

    async def from_database(
        self, registration: ReleaseRegistration, spec: Dataset
    ) -> ReleaseManifest:
        images, crops, recipe = await self.catalog.outputs(registration, spec)
        coco = canonical_json(spec.coco.model_dump(mode="json"))
        reference = FileReference(
            key=f"releases/{spec.name}/{spec.version}/coco.json",
            sha256=sha256(coco),
            size=len(coco),
        )
        return self.build(registration, spec, recipe, reference, images, crops)

    @staticmethod
    def request_hash(spec: Dataset, recipe: dict[str, Any] | None) -> str:
        request_spec = spec.model_dump(mode="json")
        # Preserve request hashes from before optional descriptive metadata.
        for field in DatasetDescription.model_fields:
            if request_spec[field] is None:
                del request_spec[field]
        return sha256(canonical_json({"spec": request_spec, "crop_recipe": recipe}))

    @staticmethod
    def build(
        registration: ReleaseRegistration,
        spec: Dataset,
        recipe: dict[str, Any] | None,
        coco: FileReference,
        images: dict[str, FileReference],
        crops: list[CropReference],
    ) -> ReleaseManifest:
        return ReleaseManifest(
            **registration.metadata().model_dump(),
            release_id=registration.id,
            name=spec.name,
            version=spec.version,
            author=spec.author,
            created_at=registration.created_at,
            request_sha256=registration.request_sha256,
            conversion=spec.conversion,
            crop_recipe=recipe,
            coco=coco,
            images=sorted(images.values(), key=lambda item: item.key),
            crops=crops,
        )

    @staticmethod
    def serialize(manifest: ReleaseManifest) -> bytes:
        return manifest.document()
