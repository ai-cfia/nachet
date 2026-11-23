"""Detection equivalence, including permutations that defeat row-wise comparison."""

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parents[1]))
from detector_parity import _detections, compare_detections, validate_detector_export  # noqa: E402


def detections(boxes, scores, labels):
    """Two-class detections whose other class scores zero."""
    class_scores = np.zeros((len(scores), 2))
    class_scores[range(len(scores)), labels] = scores
    return {"boxes": np.asarray(boxes, dtype=np.float64).reshape(-1, 4),
            "scores": class_scores}


def validate(reference, actual):
    """Run validation on fixed PyTorch and ONNX outputs; return the written report."""
    model = Mock(return_value=reference)
    model.eval.return_value = model
    session = Mock()
    session.get_inputs.return_value = [SimpleNamespace(name="pixel_values")]
    session.get_outputs.return_value = [SimpleNamespace(name=name)
                                       for name in ("logits", "pred_boxes")]
    session.run.return_value = [actual.logits.numpy(), actual.pred_boxes.numpy()]
    with (
        tempfile.TemporaryDirectory() as tmp,
        patch("detector_parity.RTDetrV2ForObjectDetection.from_pretrained", return_value=model),
        patch("detector_parity.ort.InferenceSession", return_value=session),
    ):
        onnx_path = Path(tmp) / "model.onnx"
        onnx_path.write_bytes(b"inference session is supplied by the test")
        report_path = Path(tmp) / "detector-parity.json"
        raised = False
        try:
            validate_detector_export(Path(tmp), onnx_path, report_path)
        except ValueError as error:
            assert "export detections differ" in str(error), error
            raised = True
        report = json.loads(report_path.read_text())
        # A failed report must also stop the export.
        assert raised != report["passed"], report
        return report


class DetectionParityTest(unittest.TestCase):
    def setUp(self):
        self.reference = detections(
            [[0.1, 0.1, 0.4, 0.5], [0.6, 0.2, 0.8, 0.6]],
            [0.9, 0.75], [0, 1],
        )

    def test_reordered_equivalent_detections_pass(self):
        reordered = {name: values[::-1].copy() for name, values in self.reference.items()}
        reordered["boxes"] += 0.00002
        reordered["scores"] += 0.00002
        self.assertGreater(np.max(np.abs(reordered["boxes"] - self.reference["boxes"])), 0.1)
        report = compare_detections(self.reference, reordered)
        self.assertTrue(report["passed"])
        self.assertEqual(report["matches"], [[0, 1], [1, 0]])
        self.assertAlmostEqual(report["matched_max_coordinate_difference"], 0.00002)

    def test_missing_extra_shifted_and_changed_predictions_fail(self):
        for change in ("missing", "extra", "shifted", "label", "score", "other class"):
            with self.subTest(change=change):
                actual = {name: values.copy() for name, values in self.reference.items()}
                if change == "missing":
                    actual = {name: values[:1] for name, values in actual.items()}
                elif change == "extra":
                    actual = {name: np.concatenate([values, values[:1]])
                              for name, values in actual.items()}
                elif change == "shifted":
                    # A small shift outside the coordinate tolerance.
                    actual["boxes"][0] += 0.001
                elif change == "label":
                    actual["scores"][0] = actual["scores"][0, ::-1].copy()
                elif change == "score":
                    actual["scores"][0, 0] += 0.001
                else:
                    # The winning class and its score are unchanged.
                    actual["scores"][0, 1] += 0.001
                report = compare_detections(self.reference, actual)
                self.assertFalse(report["passed"])
                self.assertTrue(report["unmatched_reference"] or report["unmatched_onnx"])

    def test_global_matching_handles_duplicate_boxes_and_ambiguous_scores(self):
        boxes = [[0.1, 0.1, 0.4, 0.5]] * 2
        reference = detections(boxes, [0.5, 0.50012], [0, 0])
        actual = detections(boxes, [0.50004, 0.49994], [0, 0])
        # The first reference can use either prediction. The second needs index 0.
        report = compare_detections(reference, actual)
        self.assertTrue(report["passed"])
        self.assertEqual(report["matches"], [[0, 1], [1, 0]])

    def test_multiclass_check_retains_each_query_used_by_evaluation(self):
        reference = SimpleNamespace(
            logits=torch.logit(torch.tensor([[[0.95, 0.94], [0.90, 0.10]]])),
            pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1], [0.4, 0.4, 0.1, 0.1]]]),
        )
        changed = SimpleNamespace(
            logits=torch.logit(torch.tensor([[[0.95, 0.94], [0.70, 0.10]]])),
            pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1], [0.8, 0.8, 0.1, 0.1]]]),
        )
        # Global top-2 query/class selection would take both classes from query 0.
        before, after = _detections(reference), _detections(changed)
        np.testing.assert_allclose(before["scores"].max(dim=1).values, [0.95, 0.90])
        report = compare_detections(before, after)
        self.assertFalse(report["passed"])
        self.assertEqual(report["unmatched_reference"], [1])

    def test_validation_rejects_a_moved_lowest_scoring_query(self):
        reference = SimpleNamespace(
            logits=torch.logit(torch.tensor([[[0.9], [0.01]]])),
            pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1], [0.4, 0.4, 0.1, 0.1]]]),
        )
        moved = reference.pred_boxes.clone()
        moved[0, 1, 0] += 0.25
        report = validate(reference, SimpleNamespace(logits=reference.logits, pred_boxes=moved))
        self.assertFalse(report["passed"])
        self.assertEqual(report["unmatched_reference"], [1])

    def test_validation_reports_a_different_output_shape(self):
        reference = SimpleNamespace(
            logits=torch.tensor([[[2.0, 0.0], [0.0, 2.0]]]),
            pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1], [0.4, 0.4, 0.1, 0.1]]]),
        )
        self.assertTrue(validate(reference, reference)["passed"])
        changes = {
            "class": SimpleNamespace(logits=reference.logits[..., :1], pred_boxes=reference.pred_boxes),
            "query": SimpleNamespace(logits=reference.logits[:, :1], pred_boxes=reference.pred_boxes[:, :1]),
            "score rows": SimpleNamespace(logits=reference.logits, pred_boxes=reference.pred_boxes[:, :1]),
            "batch": SimpleNamespace(logits=reference.logits.repeat(2, 1, 1),
                                     pred_boxes=reference.pred_boxes.repeat(2, 1, 1)),
        }
        for change, actual in changes.items():
            with self.subTest(change=change):
                report = validate(reference, actual)
                self.assertFalse(report["passed"])
                self.assertIn("output_shapes", report)

    def test_empty_lists_agree_but_cannot_absorb_a_detection(self):
        empty = detections([], [], [])
        self.assertTrue(compare_detections(empty, empty)["passed"])
        self.assertFalse(compare_detections(empty, self.reference)["passed"])
        self.assertFalse(compare_detections(self.reference, empty)["passed"])

    def test_non_finite_outputs_are_rejected(self):
        actual = {name: values.copy() for name, values in self.reference.items()}
        actual["scores"][0] = np.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            compare_detections(self.reference, actual)


if __name__ == "__main__":
    unittest.main()
