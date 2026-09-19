"""Migration checks for the original detector evaluator and its reports."""

from dataclasses import fields
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")

from PIL import Image
import pandas as pd
import torch
from transformers import RTDetrImageProcessor

import test_detector_evaluation
import validation_detector as validation
from validation_detector import (
    DetectorValidator,
    OverallMetrics,
    ValidationConfig,
    ValidationResults,
    get_parser,
)


class ValidationDetectorTest(unittest.TestCase):
    def test_required_images_fail_but_explicit_exclusions_and_training_still_work(self):
        # Keep one valid image so the default loader can demonstrate its old
        # skip behavior, then exercise the evaluator's stricter entry point.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (20, 20)).save(root / "present.png")
            annotations = root / "annotations.json"
            annotations.write_text(json.dumps({
                "categories": [{"id": 1, "name": "Species A"}],
                "images": [
                    {"id": i, "file_name": name, "width": 20, "height": 20}
                    for i, name in enumerate(["present.png", "missing.png"])
                ],
                "annotations": [
                    {"id": i, "image_id": i, "category_id": 1, "bbox": [0, 0, 5, 5]}
                    for i in range(2)
                ],
            }))
            config = root / "dataset.json"
            config.write_text(json.dumps({"sources": [{
                "images_dir": str(root), "json_path": str(annotations),
            }]}))
            validator = DetectorValidator(ValidationConfig(
                config_path=config, model_path=root, output_dir=root / "reports",
                device="cpu",
            ))
            with self.assertRaisesRegex(FileNotFoundError, "missing.png"):
                validator.load_data()

            dataset, _ = validation.load_coco_as_hf_dataset(
                str(root), str(annotations), train_val_split=1.0,
            )
            self.assertEqual(len(dataset["validation"]), 1)
            reject_list = root / "reject.txt"
            reject_list.write_text("missing.png\n")
            dataset, _ = validation.load_coco_as_hf_dataset(
                str(root), str(annotations), train_val_split=1.0,
                reject_list_path=str(reject_list), fail_on_missing_images=True,
            )
            self.assertEqual(len(dataset["validation"]), 1)

            # A file that exists but is not an image must not produce a score.
            (root / "missing.png").write_text("not an image")
            with self.assertRaises(OSError):
                validator.load_data()

    def test_multiclass_mapping_preserves_known_ids_and_rejects_unknown_species(self):
        self.assertEqual(
            validation.build_label_mapping(
                {0: "A", 1: "001 B"}, {"B": 0, "A": 1}
            ),
            {0: 1, 1: 0},
        )
        with self.assertRaisesRegex(ValueError, "Unknown.*not found"):
            validation.build_label_mapping({0: "Unknown"}, {"A": 0, "B": 1})

    def test_one_class_head_maps_species_without_relabeling_the_dataset(self):
        self.assertEqual(
            validation.build_label_mapping({0: "A", 1: "B"}, {"seed": 0}),
            {0: 0, 1: 0},
        )
        with self.assertRaisesRegex(ValueError, "exactly one label"):
            validation.build_label_mapping(
                {0: "A"}, {"A": 0, "B": 1}, single_category=True
            )

    def test_dataset_category_zero_uses_its_mapped_model_metrics(self):
        # Dataset A is category zero but model output one. Its report must use
        # output one's metrics even when the model's label ordering differs.
        validator = object.__new__(DetectorValidator)
        validator.config = SimpleNamespace(iou_threshold=0.5)
        validator._model = SimpleNamespace(
            config=SimpleNamespace(id2label={0: "B", 1: "A"})
        )
        validator._categories = {0: "A", 1: "B"}
        validator._coco_to_model = {0: 1, 1: 0}
        validator._annotations_by_image = {
            "image": [{"category_id": 0, "bbox": [0, 0, 10, 10]}]
        }
        predictions = [
            {
                "boxes": torch.tensor([[0.0, 0.0, 10.0, 10.0]]),
                "scores": torch.tensor([0.9]),
                "labels": torch.tensor([1]),
            }
        ]
        metrics, _ = validator._compute_subclass_metrics(
            predictions,
            ["image"],
            {
                "classes": torch.tensor([0, 1]),
                "map_per_class": torch.tensor([0.2, 0.8]),
                "mar_100_per_class": torch.tensor([0.3, 0.7]),
            },
        )
        self.assertEqual(metrics[0].subclass, "A")
        self.assertAlmostEqual(metrics[0].map, 0.8)
        self.assertAlmostEqual(metrics[0].mar, 0.7)

    def test_single_category_loading_preserves_species_for_reports(self):
        # The original loader collapsed B to zero, which the report then called
        # A. Keep both source species IDs while mapping both to the seed output.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (20, 20)).save(root / "seed.png")
            (root / "annotations.json").write_text(
                json.dumps({
                    "images": [
                        {"id": 1, "file_name": "seed.png", "width": 20, "height": 20}
                    ],
                    "categories": [{"id": 7, "name": "A"}, {"id": 3, "name": "B"}],
                    "annotations": [
                        {
                            "id": 1, "image_id": 1, "category_id": 3,
                            "bbox": [0, 0, 5, 5],
                        },
                        {
                            "id": 2, "image_id": 1, "category_id": 7,
                            "bbox": [10, 10, 5, 5],
                        },
                    ],
                })
            )
            config_path = root / "validation.json"
            config_path.write_text(
                json.dumps({
                    "sources": [{
                        "json_path": str(root / "annotations.json"),
                        "images_dir": str(root),
                    }],
                    "single_category": True,
                })
            )
            validator = DetectorValidator(
                ValidationConfig(
                    config_path=config_path,
                    model_path=root,
                    output_dir=root / "reports",
                    device="cpu",
                )
            )
            validator._model = SimpleNamespace(
                config=SimpleNamespace(label2id={"seed": 0})
            )
            validator.load_data()
            self.assertEqual(validator._categories, {0: "A", 1: "B"})
            self.assertEqual(
                [
                    annotation["category_id"]
                    for annotation in validator._annotations_by_image["img_0"]
                ],
                [1, 0],
            )
            self.assertEqual(validator._coco_to_model, {0: 0, 1: 0})

            # The loader accepts case-insensitive filters. Its first pass must
            # retain the same species instead of silently reusing a local ID.
            filtered_config = json.loads(config_path.read_text())
            filtered_config["include_classes"] = ["a", "B"]
            config_path.write_text(json.dumps(filtered_config))
            validator.load_data()
            self.assertEqual(validator._categories, {0: "A", 1: "B"})
            self.assertEqual(
                [
                    annotation["category_id"]
                    for annotation in validator._annotations_by_image["img_0"]
                ],
                [1, 0],
            )

            # A malformed source mapping must fail rather than reuse an ID that
            # may name a different species in the combined dataset.
            source_data, _ = validation.load_coco_as_hf_dataset(
                str(root), str(root / "annotations.json"), train_val_split=1.0
            )
            with patch.object(
                validation, "load_coco_as_hf_dataset",
                return_value=(source_data, {0: "B"}),
            ):
                with self.assertRaises(KeyError):
                    validator.load_data()

            validator._model.config.label2id = {"A": 0, "B": 1}
            with self.assertRaisesRegex(ValueError, "exactly one label"):
                validator.load_data()

    def test_missing_image_stops_inference_before_ids_and_predictions_diverge(self):
        with tempfile.TemporaryDirectory() as directory:
            validator = object.__new__(DetectorValidator)
            validator._images = {
                "missing": {"source_dir": Path(directory), "file_name": "gone.png"}
            }
            with self.assertRaisesRegex(FileNotFoundError, "gone.png"):
                validator._run_inference()

    def test_empty_plot_inputs_are_valid(self):
        self.assertIsNone(validation.plot_false_negatives_by_subclass({}, 0.5))
        self.assertIsNone(validation.plot_false_positives_by_subclass({}, 0.5))
        self.assertIsNone(
            validation.plot_confidence_distribution([{"scores": torch.empty(0)}], 0.5)
        )

    def test_original_cli_defaults_are_preserved(self):
        args = get_parser().parse_args(
            ["--config_path", "data.yaml", "--model_path", "model"]
        )
        self.assertEqual(args.confidence_threshold, 0.5)
        self.assertEqual(args.iou_threshold, 0.5)
        self.assertIsNone(args.preprocessing)
        self.assertFalse(args.no_visualizations)

    def test_saving_with_no_false_negatives(self):
        overall = OverallMetrics(**{field.name: 0 for field in fields(OverallMetrics)})
        result = ValidationResults(overall, [], [], [], [], {}, {}, [])
        with tempfile.TemporaryDirectory() as directory:
            result.save(Path(directory))
            frame = pd.read_csv(Path(directory) / "false_negatives_by_subclass.csv")
            self.assertEqual(list(frame.columns), ["subclass", "false_negatives"])
            self.assertTrue(frame.empty)

    def test_real_checkpoint_produces_original_reports_for_one_image(self):
        torch.set_num_threads(1)
        torch.manual_seed(2438)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (80, 40), (100, 20, 30)).save(root / "seed.png")
            annotations = {
                "images": [
                    {"id": 1, "file_name": "seed.png", "width": 80, "height": 40}
                ],
                "categories": [{"id": 1, "name": "Species A"}],
                "annotations": [
                    {
                        "id": 1,
                        "image_id": 1,
                        "category_id": 1,
                        "bbox": [4, 4, 16, 12],
                        "area": 192,
                        "iscrowd": 0,
                    }
                ],
            }
            (root / "annotations.json").write_text(json.dumps(annotations))
            config_path = root / "dataset.yaml"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "json_path": str(root / "annotations.json"),
                                "images_dir": str(root),
                            }
                        ]
                    }
                )
            )
            model = test_detector_evaluation.DetectorEvaluationTest().model()
            model.config.id2label = {0: "seed"}
            model.config.label2id = {"seed": 0}
            checkpoint = root / "checkpoint"
            model.save_pretrained(checkpoint)
            RTDetrImageProcessor(
                size={"max_height": 64, "max_width": 64},
                do_pad=True,
                pad_size={"height": 64, "width": 64},
            ).save_pretrained(checkpoint)
            weights_before = (checkpoint / "model.safetensors").read_bytes()
            # Retain the tiny model's predictions so confidence and threshold
            # charts run too. These random weights are not a quality benchmark.
            output = root / "reports"
            validator = DetectorValidator(
                ValidationConfig(
                    config_path=config_path,
                    model_path=checkpoint,
                    output_dir=output,
                    confidence_threshold=0.0,
                    device="cpu",
                )
            )
            result = validator.run()
            self.assertEqual(result.overall.num_images, 1)
            self.assertEqual(result.overall.total_ground_truth, 1)
            self.assertEqual(
                (checkpoint / "model.safetensors").read_bytes(), weights_before
            )
            for name in (
                "detection_metrics.json",
                "per_subclass_metrics.csv",
                "precision_recall_f1_metrics.json",
                "false_negatives_by_subclass.csv",
                "annotation_distribution.png",
                "per_subclass_heatmap.png",
                "per_subclass_metrics_table.png",
                "per_subclass_precision_recall.png",
                "detection_issues.png",
                "false_negatives_by_subclass.png",
                "false_negative_by_class.png",
                "map_summary.png",
                "sample_predictions.png",
                "confidence_distribution.png",
                "threshold_optimization.png",
            ):
                with self.subTest(report=name):
                    self.assertGreater((output / name).stat().st_size, 0)
            # These notebook-facing plots are not all called by run(), but must
            # also keep working when their subplot grid has just one image.
            self.assertIsNotNone(
                validation.plot_class_examples(
                    result.to_dataframe(),
                    validator._images,
                    result.predictions,
                    result.targets,
                    result.image_ids,
                    validator._annotations_by_image,
                    result.categories,
                    result.model_id2label,
                    num_examples=1,
                )
            )
            self.assertIsNotNone(
                validation.plot_worst_iou_examples(
                    validator._images,
                    result.predictions,
                    result.image_ids,
                    validator._annotations_by_image,
                    result.categories,
                    num_examples=1,
                )
            )
            self.assertIsNotNone(
                validation.plot_false_positive_examples(
                    result.false_negatives_by_image,
                    validator._images,
                    0.5,
                    examples_per_class=1,
                )
            )
            # A broken mapping must stop evaluation, not manufacture class zero.
            validator._coco_to_model = {}
            with self.assertRaises(KeyError):
                validator._run_inference()


if __name__ == "__main__":
    unittest.main()
