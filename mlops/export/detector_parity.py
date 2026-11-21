"""Compare RT-DETR detections without assuming that proposal rows keep their order."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy.optimize import linear_sum_assignment
import torch
from torchvision.ops import box_iou
from transformers import RTDetrImageProcessor, RTDetrV2ForObjectDetection

ATOL = 1e-4
MIN_IOU = 0.99


def compare_detections(reference, converted, *, atol=ATOL, min_iou=MIN_IOU):
    """Find one-to-one matches within class, overlap, score and coordinate tolerances."""
    ref = {name: np.asarray(value) for name, value in reference.items()}
    actual = {name: np.asarray(value) for name, value in converted.items()}
    for detections in (ref, actual):
        if not all(np.isfinite(value).all() for value in detections.values()):
            raise ValueError("Detector outputs contain non-finite values")

    rows, columns = np.array([], dtype=int), np.array([], dtype=int)
    if len(ref["boxes"]) and len(actual["boxes"]):
        overlap = box_iou(torch.from_numpy(ref["boxes"]),
                          torch.from_numpy(actual["boxes"])).numpy()
        score_delta = np.abs(ref["scores"][:, None] - actual["scores"])
        box_delta = np.abs(ref["boxes"][:, None] - actual["boxes"]).max(axis=2)
        equivalent = (
            (ref["labels"][:, None] == actual["labels"])
            & (overlap >= min_iou)
            & (score_delta <= atol)
            & (box_delta <= atol)
        )
        # An invalid pair must cost more than every possible valid pair combined.
        # This maximizes valid matches before choosing the closest overlapping boxes.
        invalid_cost = max(len(ref["boxes"]), len(actual["boxes"])) + 1
        rows, columns = linear_sum_assignment(np.where(equivalent, 1 - overlap, invalid_cost))
        valid = equivalent[rows, columns]
        rows, columns = rows[valid], columns[valid]

    missing = sorted(set(range(len(ref["boxes"]))) - set(rows.tolist()))
    extra = sorted(set(range(len(actual["boxes"]))) - set(columns.tolist()))
    return {
        "passed": not missing and not extra,
        "reference_count": len(ref["boxes"]),
        "onnx_count": len(actual["boxes"]),
        "matches": [[int(row), int(column)] for row, column in zip(rows, columns)],
        "unmatched_reference": missing,
        "unmatched_onnx": extra,
        "matched_max_score_difference": float(score_delta[rows, columns].max()) if len(rows) else 0.0,
        "matched_max_coordinate_difference": float(box_delta[rows, columns].max()) if len(rows) else 0.0,
        "matched_min_iou": float(overlap[rows, columns].min()) if len(rows) else None,
    }


def validate_detector_export(checkpoint, onnx_path, report_path, *, images=None):
    """Run identical pixels and post-processing through PyTorch and ONNX Runtime.

    The export command uses a deterministic synthetic image. Callers can supply
    representative PIL images for an additional local parity check.
    """
    checkpoint, onnx_path, report_path = map(Path, (checkpoint, onnx_path, report_path))
    supplied_images = images is not None
    if images is None:
        pixels = np.random.default_rng(2438).integers(0, 256, (96, 128, 3), dtype=np.uint8)
        images = [Image.fromarray(pixels)]
    if not images:
        raise ValueError("At least one parity image is required")
    # Model-only checkpoints remain exportable; processor defaults are used only
    # for this shared numerical probe, not as deployment preprocessing settings.
    processor = (
        RTDetrImageProcessor.from_pretrained(checkpoint, local_files_only=True)
        if (checkpoint / "preprocessor_config.json").is_file()
        else RTDetrImageProcessor()
    )
    model = RTDetrV2ForObjectDetection.from_pretrained(checkpoint, local_files_only=True).eval()
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    comparisons = []
    for image in images:
        inputs = processor(images=image.convert("RGB"), return_tensors="pt")
        feed = {item.name: inputs[item.name] for item in session.get_inputs()}
        with torch.inference_mode():
            expected = model(**feed)
            actual = SimpleNamespace(**{
                name: torch.from_numpy(value)
                for name, value in zip(
                    (item.name for item in session.get_outputs()),
                    session.run(None, {name: value.numpy() for name, value in feed.items()}),
                )
            })
            for result in (expected, actual):
                if not torch.isfinite(result.logits).all() or not torch.isfinite(result.pred_boxes).all():
                    raise ValueError("Detector outputs contain non-finite values")
            # Include all top-k proposals, so low-scoring models cannot pass via
            # two empty detection lists. Boxes remain in normalized coordinates.
            before, after = (
                processor.post_process_object_detection(result, threshold=0.0,
                                                        use_focal_loss=model.config.use_focal_loss)[0]
                for result in (expected, actual)
            )
        comparisons.append({
            "pixel_values_sha256": hashlib.sha256(feed["pixel_values"].numpy().tobytes()).hexdigest(),
            "rowwise_max_logit_difference": float((expected.logits - actual.logits).abs().max()),
            "rowwise_max_box_difference": float((expected.pred_boxes - actual.pred_boxes).abs().max()),
            **compare_detections(before, after),
        })
    report = {
        "passed": all(item["passed"] for item in comparisons),
        "input_kind": "provided_images" if supplied_images else "seeded_synthetic_image",
        "onnx_sha256": hashlib.sha256(onnx_path.read_bytes()).hexdigest(),
        "absolute_tolerance": ATOL,
        "minimum_iou": MIN_IOU,
        "comparisons": comparisons,
    }
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not report["passed"]:
        raise ValueError(f"RT-DETR export detections differ; see {report_path}")
    return report
