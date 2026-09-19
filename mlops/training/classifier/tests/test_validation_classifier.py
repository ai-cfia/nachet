"""Regression tests for the migrated classifier evaluator."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

import matplotlib

matplotlib.use("Agg")

from PIL import Image
import numpy as np
import torch
from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor
from torchvision.transforms import (
    CenterCrop,
    Compose,
    Normalize,
    Resize,
    ToTensor,
)


SRC = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SRC))
from validation_classifier import (  # noqa: E402
    get_parser,
    load_image_processor,
    map_dataset_class_ids,
    process_model,
)
sys.path.pop(0)


class ValidationClassifierTest(unittest.TestCase):
    def test_original_cli_defaults_are_preserved(self):
        args = get_parser().parse_args(
            ["--model_path", "model", "--test_data_path", "Validation"]
        )
        self.assertEqual(args.batch_size, 4)
        self.assertEqual(args.output_path, "output")
        self.assertEqual(args.parent, "false")
        self.assertEqual(args.chkstart, 0)
        self.assertEqual(args.chkend, float("inf"))
        self.assertEqual(args.figsize, 10)
        self.assertEqual(args.test_name, "")

    def test_class_mapping_normalizes_names_and_rejects_unknowns(self):
        self.assertEqual(
            map_dataset_class_ids(
                {0: "species_a", 1: "  SPECIES   B "},
                {0: "Species B", 1: "Species A", 2: "Species C"},
            ),
            {0: 1, 1: 0},
        )
        with self.assertRaisesRegex(ValueError, "missing from model id2label"):
            map_dataset_class_ids({0: "unknown"}, {0: "known"})

    def test_class_mapping_rejects_normalization_collisions(self):
        with self.assertRaisesRegex(ValueError, "ambiguous model class names"):
            map_dataset_class_ids(
                {0: "species a"}, {0: "Species_A", 1: "species a"}
            )
        with self.assertRaisesRegex(
            ValueError, "ambiguous external-validation class names"
        ):
            map_dataset_class_ids(
                {0: "Species_A", 1: "species a"}, {0: "Species A"}
            )

    def test_swin_and_swinv2_preprocessing_matches_original(self):
        pixels = (np.arange(45 * 37 * 3, dtype=np.uint16) % 256).astype(np.uint8)
        image = Image.fromarray(pixels.reshape(45, 37, 3), mode="RGB")

        # Both checkpoint sizes must produce the same tensor as the original
        # evaluator's resize, crop and normalization sequence.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for model_name, size in (("swin", 224), ("swinv2", 256)):
                with self.subTest(model_name=model_name):
                    checkpoint = root / model_name
                    processor = ViTImageProcessor(
                        size={"height": size, "width": size},
                        image_mean=(0.485, 0.456, 0.406),
                        image_std=(0.229, 0.224, 0.225),
                    )
                    processor.save_pretrained(checkpoint)
                    original = Compose(
                        [
                            Resize((size, size)),
                            CenterCrop((size, size)),
                            ToTensor(),
                            Normalize(
                                mean=processor.image_mean, std=processor.image_std
                            ),
                        ]
                    )
                    migrated = load_image_processor(checkpoint)
                    torch.testing.assert_close(
                        migrated(image), original(image), rtol=0, atol=0
                    )

    def test_swin_checkpoint_uses_full_model_label_space_and_writes_reports(self):
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "checkpoint"
            config = SwinConfig(
                image_size=32,
                patch_size=4,
                embed_dim=8,
                depths=[1, 1],
                num_heads=[1, 2],
                window_size=4,
                num_labels=3,
                id2label={0: "Beta", 1: "Alpha", 2: "Gamma"},
                label2id={"Beta": 0, "Alpha": 1, "Gamma": 2},
            )
            model = SwinForImageClassification(config)

            # A fixed model-only winner proves evaluation does not subset logits
            # to the two classes represented by external-validation folders.
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.zero_()
                model.classifier.bias[2] = 1
            model.save_pretrained(checkpoint)
            ViTImageProcessor(size={"height": 32, "width": 32}).save_pretrained(
                checkpoint
            )

            validation = root / "Validation"
            for class_name, color in (("alpha", "red"), ("beta", "blue")):
                directory = validation / class_name
                directory.mkdir(parents=True)
                Image.new("RGB", (40, 40), color).save(directory / "seed.png")

            output = root / "reports"
            process_model(
                str(checkpoint), str(validation), str(output), 2, 4, "_external"
            )

            matrix = output / "reports_confusion_matrix.png"
            report_path = output / "reports_external_classification_report.json"
            self.assertGreater(matrix.stat().st_size, 0)
            report = json.loads(report_path.read_text())
            self.assertEqual(report["Alpha"]["support"], 1.0)
            self.assertEqual(report["Beta"]["support"], 1.0)
            self.assertEqual(report["Gamma"]["support"], 0.0)
            self.assertEqual(report["Gamma"]["accuracy"], 0.0)
            self.assertEqual(report["accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
