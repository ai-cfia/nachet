"""Detection equivalence, including permutations that defeat row-wise comparison."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from detector_parity import compare_detections  # noqa: E402


def detections(boxes, scores, labels):
    return {"boxes": np.asarray(boxes, dtype=np.float64).reshape(-1, 4),
            "scores": np.asarray(scores), "labels": np.asarray(labels)}


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
        for change in ("missing", "extra", "shifted", "label", "score"):
            with self.subTest(change=change):
                actual = {name: values.copy() for name, values in self.reference.items()}
                if change == "missing":
                    actual = {name: values[:1] for name, values in actual.items()}
                elif change == "extra":
                    actual = {name: np.concatenate([values, values[:1]])
                              for name, values in actual.items()}
                elif change == "shifted":
                    # Still high overlap, but outside the coordinate tolerance.
                    actual["boxes"][0] += 0.001
                elif change == "label":
                    actual["labels"][0] = 1
                else:
                    actual["scores"][0] += 0.001
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

    def test_top_k_cutoff_swap_passes_only_for_the_lowest_scores(self):
        reference = detections([[0.1, 0.1, 0.4, 0.5], [0.6, 0.2, 0.8, 0.6]],
                               [0.9, 0.01001], [0, 1])
        # The last top-k slot holds a different, near-tied proposal.
        swapped = detections([[0.1, 0.1, 0.4, 0.5], [0.2, 0.6, 0.3, 0.9]],
                             [0.9, 0.01000], [0, 2])
        self.assertFalse(compare_detections(reference, swapped)["passed"])
        report = compare_detections(reference, swapped, top_k=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["unmatched_at_top_k_cutoff"], [[1], [1]])

        swapped["labels"][0] = 1
        report = compare_detections(reference, swapped, top_k=True)
        self.assertFalse(report["passed"])
        self.assertEqual(report["unmatched_reference"], [0])

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
