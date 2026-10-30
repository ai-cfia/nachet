"""Build deterministic release identities and manifests."""

from typing import Any

from ..models.dataset import Dataset, ReleaseRegistration, canonical_json, sha256
from ..models.manifest import CropReference, FileReference, ReleaseManifest


class ManifestService:
    @staticmethod
    def request_hash(spec: Dataset, recipe: dict[str, Any] | None) -> str:
        return sha256(
            canonical_json(
                {"spec": spec.model_dump(mode="json"), "crop_recipe": recipe}
            )
        )

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
        return canonical_json(manifest.model_dump(mode="json"))
