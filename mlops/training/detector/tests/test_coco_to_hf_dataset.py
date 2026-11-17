"""Check the COCO split assignments received by the detector."""

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from coco_to_hf_dataset import load_coco_as_hf_dataset


class CocoDatasetSplitTest(unittest.TestCase):
    def load(self, splits, *, missing=(), **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = []
            for image_id, split in enumerate(splits, start=1):
                name = f"{image_id}.png"
                if image_id not in missing:
                    Image.new("RGB", (8, 8)).save(root / name)
                images.append(
                    {
                        "id": image_id,
                        "file_name": name,
                        "width": 8,
                        "height": 8,
                        "split": split,
                    }
                )
            coco = root / "images.json"
            data = {
                "images": images,
                "categories": [{"id": 1, "name": "seed"}],
                "annotations": [
                    {"id": i, "image_id": i, "bbox": [1, 1, 4, 4], "category_id": 1}
                    for i in range(1, len(images) + 1)
                ],
            }
            coco.write_text(json.dumps(data))
            dataset, _ = load_coco_as_hf_dataset(str(root), str(coco), **kwargs)
            return {name: list(split["image_id"]) for name, split in dataset.items()}

    def test_preserves_reviewed_splits_and_excludes_test_images(self):
        splits = ["validation", "train", "test", "validation", "train", "test"]
        expected = {"train": [2, 5], "validation": [1, 4]}
        self.assertEqual(self.load(splits), expected)
        self.assertEqual(
            self.load(splits, missing=(3, 6), fail_on_missing_images=True), expected
        )

    def test_loads_declared_partitions_with_one_split_per_source(self):
        for name, other in (("train", "validation"), ("validation", "train")):
            with self.subTest(split=name):
                self.assertEqual(self.load([name, "test"]), {name: [1], other: []})

    def test_rejects_invalid_split_inputs(self):
        for splits, message in (
            (["train", "validation", None], "split.*image 3"),
            (["train", "validation", "unspecified"], "split.*image 3"),
            (["test", "test"], "No usable COCO images"),
        ):
            with self.subTest(splits=splits):
                with self.assertRaisesRegex(ValueError, message):
                    self.load(splits)

    def test_keeps_seeded_split_for_unassigned_inputs(self):
        splits = [None] * 5
        result = self.load(splits, train_val_split=0.4, seed=42)
        self.assertEqual(result, {"train": [4, 2, 1], "validation": [5, 3]})

    def test_whole_source_modes_keep_the_caller_selected_partition(self):
        splits = ["test", "test"]
        self.assertEqual(
            self.load(splits, train_val_split=1), {"train": [], "validation": [1, 2]}
        )
        self.assertEqual(
            self.load(splits, train_val_split=0), {"train": [1, 2], "validation": []}
        )
