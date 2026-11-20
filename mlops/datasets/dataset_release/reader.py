"""S3-aware sample readers and the detector's COCO-to-HF record contract."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator, Iterator
from typing import Any

from .contract import Split, canonical_json
from .release import DatasetController, ReleaseNotReady


class ReleasedDataset:
    """Read a verified, pinned version without depending on a source PVC.

    Iterators fetch one image/crop at a time. A training runtime can adapt
    these records to its Dataset implementation without introducing local paths.
    No random split or silent missing-file fallback is performed here.
    """

    @classmethod
    async def open(
        cls,
        controller: DatasetController,
        name: str,
        version: str,
        expected_manifest_sha256: str | None = None,
        *,
        verify_media: bool = True,
    ) -> ReleasedDataset:
        """Verify a ready release and index its files, annotations, and categories.

        When supplied, the expected manifest digest pins the selected version.
        Category indices follow sorted COCO IDs so both readers use the same labels.
        """
        reader = cls()
        reader.controller = controller
        (
            reader.registration,
            reader.manifest,
            reader.coco,
        ) = await controller.load_verified_release(
            name, version, expected_manifest_sha256, verify_media=verify_media
        )
        reader.images = {image.id: image for image in reader.coco.images}
        reader.files = {file.key: file for file in reader.manifest.images}
        reader.files.update(
            {crop.file.key: crop.file for crop in reader.manifest.crops}
        )
        reader.annotations = defaultdict(list)
        for annotation in reader.coco.annotations:
            reader.annotations[annotation.image_id].append(annotation)
        reader.categories = {
            index: category.name
            for index, category in enumerate(
                sorted(reader.coco.categories, key=lambda c: c.id)
            )
        }
        reader.category_indices = {
            category.id: index
            for index, category in enumerate(
                sorted(reader.coco.categories, key=lambda c: c.id)
            )
        }
        return reader

    def training_reference(
        self, run_settings: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """Return the pinned release identifiers and canonical training settings."""
        reference = self.registration.training_reference()
        reference["dataset_run_settings"] = canonical_json(run_settings or {}).decode(
            "utf-8"
        )
        return reference

    async def read_media(self, key: str) -> bytes:
        """Read one sample's PNG, checking its size and hash against the manifest."""
        return await self.controller.read_file(self.files[key])

    def detector_index(self, split: Split) -> Iterator[dict[str, Any]]:
        """Yield detector records with image keys for on-demand media reads."""
        for image in self.coco.images:
            if image.split != split:
                continue
            annotations = self.annotations[image.id]
            yield {
                "image_id": image.id,
                "image": image.file_name,
                "width": image.width,
                "height": image.height,
                "objects": {
                    "id": [annotation.id for annotation in annotations],
                    "area": [
                        annotation.area or annotation.bbox[2] * annotation.bbox[3]
                        for annotation in annotations
                    ],
                    "bbox": [annotation.bbox for annotation in annotations],
                    "category": [
                        self.category_indices[annotation.category_id]
                        for annotation in annotations
                    ],
                },
            }

    def classifier_index(self, split: Split) -> Iterator[dict[str, Any]]:
        """Yield released crop keys and zero-based labels for the requested split."""
        if self.manifest.crop_recipe is None:
            raise ReleaseNotReady("This release is not classifier-ready")
        for crop in self.manifest.crops:
            if crop.split != split:
                continue
            yield {
                "image": crop.file.key,
                "label": self.category_indices[crop.category_id],
                "image_id": crop.image_id,
                "annotation_id": crop.annotation_id,
                "dataset_release_id": str(self.registration.id),
            }

    async def detector_records(self, split: Split) -> AsyncIterator[dict[str, Any]]:
        """Yield detector records with verified Hugging Face image bytes."""
        async for record in self._records(self.detector_index(split)):
            yield record

    async def classifier_records(self, split: Split) -> AsyncIterator[dict[str, Any]]:
        """Yield classifier records with verified Hugging Face crop bytes."""
        async for record in self._records(self.classifier_index(split)):
            yield record

    async def _records(
        self, index: Iterator[dict[str, Any]]
    ) -> AsyncIterator[dict[str, Any]]:
        for record in index:
            key = record["image"]
            record["image"] = {"path": key, "bytes": await self.read_media(key)}
            yield record
