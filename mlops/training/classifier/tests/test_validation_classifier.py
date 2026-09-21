"""Offline checks for the classifier notebook's reports and label mapping."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import classification_report, roc_auc_score
from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import validation_classifier as evaluator  # noqa: E402


REPORTS = {
    "validation_metrics.json", "per_class_metrics.csv",
    "classification_report_heatmap.png", "confusion_matrix_normalized.png",
    "per_class_tp_fn_bar.png", "per_class_precision_bar.png",
    "sample_images_by_class.png", "mispredictions_by_metric.png",
}


def model_config(names):
    return SimpleNamespace(config=SimpleNamespace(
        id2label=dict(enumerate(names)), num_labels=len(names),
    ))


class ClassifierEvaluationTest(unittest.TestCase):
    def test_folder_names_map_to_model_ids(self):
        names = [evaluator.strip_class_prefix(name) for name in ["01 Alpha-beta", "02 GAMMA"]]
        mapping, indices, matching = evaluator.match_classes(
            [{"label": 0}, {"label": 1}], names,
            model_config(["gamma", "alpha_beta"]),
        )
        self.assertEqual(mapping, {0: 1, 1: 0})
        self.assertEqual(indices, [0, 1])
        self.assertEqual(matching["dataset_only_classes"], [])

    def test_collisions_are_rejected_on_either_side(self):
        for dataset_names, model_names in [
            (["Alpha-beta", "alpha_beta"], ["Alpha beta"]),
            (["Alpha beta"], ["Alpha-beta", "alpha_beta"]),
            (["Alpha", "Alpha"], ["Alpha"]),
        ]:
            with self.subTest(dataset=dataset_names, model=model_names):
                with self.assertRaises(ValueError):
                    evaluator.match_classes([{"label": 0}], dataset_names, model_config(model_names))

    def test_unmatched_dataset_classes_keep_notebook_skip_policy(self):
        mapping, indices, matching = evaluator.match_classes(
            [{"label": 0}, {"label": 1}, {"label": 0}],
            ["Alpha", "Unknown"], model_config(["Alpha", "Beta"]),
        )
        self.assertEqual(mapping, {0: 0})
        self.assertEqual(indices, [0, 2])
        self.assertEqual(matching["dataset_only_classes"], ["Unknown"])
        self.assertEqual(matching["model_only_classes"], ["Beta"])
        self.assertEqual(matching["evaluated_samples"], 2)
        self.assertEqual(matching["skipped_samples"], 1)
        with self.assertRaises(ValueError):
            evaluator.match_classes([{"label": 0}], ["Unknown"], model_config(["Alpha"]))

    def test_model_ids_must_cover_every_output(self):
        model = model_config(["Alpha", "Beta"])
        model.config.id2label = {0: "Alpha", 2: "Beta"}
        with self.assertRaises(ValueError):
            evaluator.match_classes([{"label": 0}], ["Alpha"], model)

    def test_predictions_keep_model_only_classes(self):
        # Gamma wins, although the external images contain only Alpha and Beta.
        class FixedModel:
            config = model_config(["Beta", "Alpha", "Gamma"]).config

            def __call__(self, pixel_values):
                return SimpleNamespace(logits=torch.tensor([[1., 2., 10.], [2., 1., 10.]]))

        model = FixedModel()
        batch = {"pixel_values": torch.zeros(2, 3, 4, 4), "labels": torch.tensor([0, 1])}
        logits, predictions, labels, topk, total, *_ = evaluator.evaluate_model(
            model, "cpu", [batch], {0: 1, 1: 0},
        )
        self.assertEqual(logits.shape, (2, 3))
        np.testing.assert_array_equal(predictions, [2, 2])
        np.testing.assert_array_equal(labels, [1, 0])
        self.assertEqual(topk[1], 0)
        self.assertEqual(topk[3], 2)
        self.assertEqual(total, 2)

    def test_processor_override_and_parent_lookup(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            checkpoint = parent / "checkpoint-1"
            checkpoint.mkdir()
            (parent / "preprocessor_config.json").write_text("{}")
            self.assertEqual(evaluator.find_processor_path(checkpoint), parent)
            with self.assertRaises(FileNotFoundError):
                evaluator.find_processor_path(checkpoint, parent / "missing")
            (checkpoint / "preprocessor_config.json").write_text("{}")
            self.assertEqual(evaluator.find_processor_path(checkpoint), checkpoint)

    def test_loader_uses_saved_processor_on_rgb_images(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "Alpha"
            folder.mkdir()
            image = Image.new("L", (43, 37), 128)
            image.save(folder / "sample.png")
            dataset, _ = evaluator.load_test_data(temporary)
            processor = ViTImageProcessor(size={"height": 32, "width": 32})
            batch = next(iter(evaluator.make_eval_loader(dataset, [0], processor, 1, 0)))
            expected = processor(images=[image.convert("RGB")], return_tensors="pt")["pixel_values"]
            torch.testing.assert_close(batch["pixel_values"], expected, rtol=0, atol=0)
            self.assertEqual(batch["labels"].tolist(), [0])

    def test_cli_defaults_and_checkpoint_names(self):
        args = evaluator.get_parser().parse_args(["--model_path", "model", "--test_data_path", "images"])
        self.assertEqual(args.num_workers, 0)
        self.assertFalse(evaluator.is_valid_checkpoint_dir("checkpoint-1-old", 0, 10))
        self.assertTrue(evaluator.is_valid_checkpoint_dir("checkpoint-1", 0, 10))

    def test_binary_and_absent_classes_produce_strict_json(self):
        for names, labels, logits in [
            (["Alpha", "Beta"], [0, 1], [[8., 0.], [0., 8.]]),
            (["Alpha", "Beta", "Gamma"], [0, 1], [[8., 0., 0.], [0., 8., 0.]]),
            (["Alpha", "Beta"], [0], [[8., 0.]]),
            (["Alpha"], [0], [[8.]]),
        ]:
            with self.subTest(names=names, labels=labels), tempfile.TemporaryDirectory() as temporary:
                scores = torch.tensor(logits)
                references = np.array(labels)
                predictions = scores.argmax(-1).numpy()
                evaluator.save_metrics(scores, predictions, references, {1: len(labels), 3: len(labels), 5: 0},
                                       len(labels), names, {}, Path(temporary))
                def reject_constant(value):
                    raise AssertionError(f"Non-JSON numeric value: {value}")
                report = json.loads((Path(temporary) / "validation_metrics.json").read_text(),
                                    parse_constant=reject_constant)
                self.assertEqual(report["top_k_accuracy"]["top_1"], 1)
                if len(set(labels)) == 1:
                    self.assertIsNone(report["roc_auc"]["macro"])
                else:
                    self.assertAlmostEqual(report["roc_auc"]["macro"], 1)
                    self.assertAlmostEqual(report["roc_auc"]["weighted"], 1)
                if "Gamma" in names:
                    self.assertIsNone(report["roc_auc"]["per_class"]["Gamma"])

    def test_all_class_metrics_match_notebook_formulas(self):
        # Unequal support makes macro and weighted AUC genuinely different checks.
        names = ["Beta", "Alpha", "Gamma"]
        labels = np.array([0, 0, 0, 1, 1, 2])
        logits = torch.tensor([[4., 1., 0.], [0., 4., 1.], [4., 0., 1.],
                               [4., 1., 0.], [0., 4., 1.], [0., 1., 4.]])
        predictions = logits.argmax(-1).numpy()
        probabilities = logits.softmax(-1).numpy()
        with tempfile.TemporaryDirectory() as temporary:
            evaluator.save_metrics(logits, predictions, labels, {1: 4, 3: 6, 5: 0},
                                   6, names, {}, Path(temporary))
            metrics = json.loads((Path(temporary) / "validation_metrics.json").read_text())
        self.assertEqual(metrics["top_k_accuracy"], {"top_1": 4 / 6, "top_3": 1.0})
        self.assertEqual(metrics["classification_report"], classification_report(
            labels, predictions, target_names=names, output_dict=True, zero_division=0))
        for average in ["macro", "weighted"]:
            expected = roc_auc_score(labels, probabilities, multi_class="ovr", average=average)
            self.assertAlmostEqual(metrics["roc_auc"][average], expected)
        expected = roc_auc_score(labels, probabilities, multi_class="ovr", average=None)
        np.testing.assert_allclose([metrics["roc_auc"]["per_class"][name] for name in names], expected)

    def test_real_checkpoint_cli_writes_all_eight_reports(self):
        # A tiny saved Swin exercises processor loading, inference and every plot.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "model" / "checkpoint-1"
            model = SwinForImageClassification(SwinConfig(
                image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
                num_heads=[1, 2], window_size=4, num_labels=3,
                id2label={0: "Beta", 1: "Alpha", 2: "Gamma"},
                label2id={"Beta": 0, "Alpha": 1, "Gamma": 2},
            ))
            with torch.no_grad():
                model.classifier.weight.zero_()
                model.classifier.bias.copy_(torch.tensor([0., 0., 10.]))
            model.save_pretrained(checkpoint)
            ViTImageProcessor(size={"height": 32, "width": 32}).save_pretrained(checkpoint.parent)
            for label, color in [("01 Alpha", "red"), ("02 Beta", "blue")]:
                folder = root / "images" / label
                folder.mkdir(parents=True)
                Image.new("RGB", (40, 36), color).save(folder / "sample.png")
            output = root / "reports"
            command = [sys.executable, str(Path(evaluator.__file__)),
                       "--model_path", str(checkpoint), "--test_data_path", str(root / "images"),
                       "--output_path", str(output), "--num_workers", "0"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({path.name for path in output.iterdir()}, REPORTS)
            for path in output.iterdir():
                self.assertGreater(path.stat().st_size, 0)
                if path.suffix == ".png":
                    with Image.open(path) as image:
                        image.verify()
            metrics = json.loads((output / "validation_metrics.json").read_text())
            self.assertEqual(metrics["top_k_accuracy"]["top_1"], 0)
            self.assertEqual(metrics["class_matching"]["model_only_classes"], ["Gamma"])
            table = pd.read_csv(output / "per_class_metrics.csv", index_col=0)
            self.assertEqual(list(table.index), ["Beta", "Alpha", "Gamma"])
            self.assertEqual(table.loc["Gamma", "support"], 0)
            self.assertTrue(np.isfinite(table[["precision", "recall", "f1-score", "accuracy"]]).all().all())


if __name__ == "__main__":
    unittest.main()
