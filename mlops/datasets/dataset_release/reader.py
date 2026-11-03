"""S3-aware sample readers and the detector's COCO-to-HF record contract."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from dataset_controller import DatasetController, ReleaseNotReady
from dataset_controller.models.dataset import Split, canonical_json


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
    ) -> ReleasedDataset:
        reader = cls()
        reader.controller = controller
        reader.registration, reader.manifest, reader.coco = await controller.resolve(
            name, version, expected_manifest_sha256
        )
        reader.images = {image.id: image for image in reader.coco.images}
        reader.files = {file.key: file for file in reader.manifest.images}
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
        reference = self.registration.training_reference()
        reference["dataset_run_settings"] = canonical_json(run_settings or {}).decode(
            "utf-8"
        )
        return reference

    async def detector_records(self, split: Split) -> AsyncIterator[dict[str, Any]]:
        """Yield the record shape used by HFTrainer_detector_2026012601_js.py.

        The image field uses HuggingFace Image's bytes representation. Cast that
        column to datasets.Image in the training adapter to decode PIL images.
        COCO category IDs are mapped to zero-based IDs in sorted-ID order.
        """
        for image in self.coco.images:
            if image.split != split:
                continue
            annotations = self.annotations[image.id]
            yield {
                "image_id": image.id,
                "image": {
                    "path": image.file_name,
                    "bytes": await self.controller.read_file(
                        self.files[image.file_name]
                    ),
                },
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

    async def classifier_records(self, split: Split) -> AsyncIterator[dict[str, Any]]:
        if self.manifest.crop_recipe is None:
            raise ReleaseNotReady("This release is not classifier-ready")
        for crop in self.manifest.crops:
            if crop.split != split:
                continue
            yield {
                "image": {
                    "path": crop.file.key,
                    "bytes": await self.controller.read_file(crop.file),
                },
                "label": self.category_indices[crop.category_id],
                "image_id": crop.image_id,
                "annotation_id": crop.annotation_id,
                "dataset_release_id": str(self.registration.id),
            }
