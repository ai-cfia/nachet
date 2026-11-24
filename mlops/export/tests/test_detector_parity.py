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


def validate(reference, actual, *, confidence_threshold=0.5):
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
            validate_detector_export(
                Path(tmp), onnx_path, report_path,
                confidence_threshold=confidence_threshold,
            )
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
        report = compare_detections(self.reference, reordered, confidence_threshold=0.5)
        self.assertTrue(report["passed"])
        self.assertEqual(report["matches"], [[0, 1], [1, 0]])
        self.assertGreater(report["matched_min_box_iou"], 0.99)

    def test_missing_extra_shifted_and_relabelled_predictions_fail(self):
        for change in ("missing", "extra", "shifted", "label"):
            with self.subTest(change=change):
                actual = {name: values.copy() for name, values in self.reference.items()}
                if change == "missing":
                    actual = {name: values[:1] for name, values in actual.items()}
                elif change == "extra":
                    actual = {name: np.concatenate([values, values[:1]])
                              for name, values in actual.items()}
                elif change == "shifted":
                    # IoU is approximately 0.891 with the reference box.
                    actual["boxes"][0] += 0.01
                else:
                    actual["scores"][0] = actual["scores"][0, ::-1].copy()
                report = compare_detections(self.reference, actual, confidence_threshold=0.5)
                self.assertFalse(report["passed"])
                self.assertTrue(report["unmatched_reference"] or report["unmatched_onnx"])

    def test_small_box_shift_fails_where_a_large_box_shift_passes(self):
        shift = 0.00009
        for side, passed in ((0.3, True), (0.002, False)):
            with self.subTest(side=side):
                reference = detections([[0.1, 0.1, 0.1 + side, 0.1 + side]], [0.9], [0])
                actual = {name: values.copy() for name, values in reference.items()}
                actual["boxes"] += shift
                report = compare_detections(reference, actual, confidence_threshold=0.5)
                self.assertEqual(report["passed"], passed)

    def test_global_matching_handles_ambiguous_box_overlap(self):
        reference = detections(
            [[0.1, 0.1, 0.4, 0.5], [0.10176, 0.1, 0.40176, 0.5]],
            [0.9, 0.9], [0, 0],
        )
        actual = detections(
            [[0.1009, 0.1, 0.4009, 0.5], [0.099, 0.1, 0.399, 0.5]],
            [0.9, 0.9], [0, 0],
        )
        # Reference 0 can use either box; reference 1 can only use ONNX box 0.
        report = compare_detections(reference, actual, confidence_threshold=0.5)
        self.assertTrue(report["passed"])
        self.assertEqual(report["matches"], [[0, 1], [1, 0]])

    def test_only_confidence_gate_crossings_fail(self):
        for before, after, passed in (
            (0.90, 0.89, True), (0.20, 0.21, True),
            (0.501, 0.499, False), (0.499, 0.501, False),
            (0.50, 0.49, True), (0.50, 0.501, False), (0.501, 0.50, False),
        ):
            with self.subTest(before=before, after=after):
                reference = detections([[0.1, 0.1, 0.4, 0.5]], [before], [0])
                actual = detections(reference["boxes"], [after], [0])
                report = compare_detections(reference, actual, confidence_threshold=0.5)
                self.assertEqual(report["passed"], passed)
                if passed:
                    self.assertAlmostEqual(report["matched_max_score_difference"], abs(before - after))

    def test_each_class_is_compared_only_against_the_gate(self):
        for before, after, passed in (
            ([0.9, 0.49], [0.9, 0.51], False),  # Nonwinning class crosses the gate.
            ([0.9, 0.7], [0.7, 0.9], True),  # Ranking alone does not change the gate.
        ):
            with self.subTest(before=before, after=after):
                reference = {"boxes": self.reference["boxes"][:1], "scores": [before]}
                actual = {"boxes": reference["boxes"], "scores": [after]}
                report = compare_detections(reference, actual, confidence_threshold=0.5)
                self.assertEqual(report["passed"], passed)

    def test_validation_uses_and_records_the_configured_cutoff(self):
        reference = SimpleNamespace(
            logits=torch.logit(torch.tensor([[[0.74]]])),
            pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1]]]),
        )
        actual = SimpleNamespace(
            logits=torch.logit(torch.tensor([[[0.76]]])), pred_boxes=reference.pred_boxes,
        )
        self.assertTrue(validate(reference, actual)["passed"])
        report = validate(reference, actual, confidence_threshold=0.75)
        self.assertFalse(report["passed"])
        self.assertEqual(report["confidence_threshold"], 0.75)

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
        report = compare_detections(before, after, confidence_threshold=0.5)
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
                self.assertEqual(report["confidence_threshold"], 0.5)

    def test_empty_lists_agree_but_cannot_absorb_a_detection(self):
        empty = detections([], [], [])
        self.assertTrue(compare_detections(empty, empty, confidence_threshold=0.5)["passed"])
        self.assertFalse(compare_detections(empty, self.reference, confidence_threshold=0.5)["passed"])
        self.assertFalse(compare_detections(self.reference, empty, confidence_threshold=0.5)["passed"])

    def test_non_finite_outputs_are_rejected(self):
        actual = {name: values.copy() for name, values in self.reference.items()}
        actual["scores"][0] = np.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            compare_detections(self.reference, actual, confidence_threshold=0.5)
        infinite = SimpleNamespace(logits=torch.tensor([[[float("inf")]]]),
                                   pred_boxes=torch.tensor([[[0.2, 0.2, 0.1, 0.1]]]))
        with self.assertRaisesRegex(ValueError, "non-finite"):
            _detections(infinite)


if __name__ == "__main__":
    unittest.main()
