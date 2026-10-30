"""Validate reviewed membership, PNG bytes, manifests and crop relationships."""

from __future__ import annotations

from numpy import uint8
from numpy.typing import NDArray

from ..errors import ReleaseConflict
from ..models.dataset import Dataset, DatasetMember, ReviewedCoco, sha256
from ..models.manifest import FileReference, ReleaseManifest
from ..repositories.blob_repository import BlobRepository
from ..utility.crop import decode_png, pixel_box


class ValidationService:
    def __init__(self, blobs: BlobRepository):
        self.blobs = blobs

    @staticmethod
    def validate_spec(dataset: Dataset) -> Dataset:
        # Recheck nested mutable lists before calculating the request identity.
        return Dataset.model_validate(dataset.model_dump(mode="json"))

    @staticmethod
    def validate_image(
        image: DatasetMember, data: bytes
    ) -> tuple[NDArray[uint8], FileReference]:
        digest = sha256(data)
        if image.file_name != f"png/detection/{digest}.png":
            raise ValueError(f"PNG bytes do not match hash filename: {image.file_name}")
        try:
            decoded = decode_png(data, (image.width, image.height))
        except ValueError as error:
            raise ValueError(
                f"Image dimensions/format do not match COCO: {image.id}"
            ) from error
        return decoded, FileReference(
            key=image.file_name, sha256=digest, size=len(data)
        )

    async def read_file(self, reference: FileReference) -> bytes:
        data = await self.blobs.download(reference.key)
        if len(data) != reference.size or sha256(data) != reference.sha256:
            raise ReleaseConflict(f"Object checksum/size mismatch: {reference.key}")
        return data

    async def validate(self, manifest: ReleaseManifest, coco: ReviewedCoco) -> None:
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
