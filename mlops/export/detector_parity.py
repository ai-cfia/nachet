"""Compare RT-DETR detections without assuming that proposal rows keep their order."""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy.optimize import linear_sum_assignment
import torch
from torchvision.ops import box_convert, box_iou
from transformers import RTDetrImageProcessor, RTDetrV2ForObjectDetection

# IoU scales with box size; a coordinate tolerance would not.
MIN_BOX_IOU = 0.99


def compare_detections(reference, converted, *, confidence_threshold):
    """Match every box one to one while preserving each class confidence gate."""
    ref = {name: np.asarray(value) for name, value in reference.items()}
    actual = {name: np.asarray(value) for name, value in converted.items()}
    for detections in (ref, actual):
        if not all(np.isfinite(value).all() for value in detections.values()):
            raise ValueError("Detector outputs contain non-finite values")

    rows, columns = np.array([], dtype=int), np.array([], dtype=int)
    if len(ref["boxes"]) and len(actual["boxes"]):
        iou = box_iou(torch.as_tensor(ref["boxes"]), torch.as_tensor(actual["boxes"])).numpy()
        # Score differences matter only when they cross the confidence gate.
        same_gate = (
            (ref["scores"][:, None] > confidence_threshold)
            == (actual["scores"] > confidence_threshold)
        ).all(axis=2)
        equivalent = same_gate & (iou >= MIN_BOX_IOU)
        # Any valid pairing is acceptable; keep as many as possible.
        rows, columns = linear_sum_assignment(equivalent, maximize=True)
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
        "matched_max_score_difference": float(
            np.abs(ref["scores"][rows] - actual["scores"][columns]).max()
        ) if len(rows) else 0.0,
        "matched_min_box_iou": float(iou[rows, columns].min()) if len(rows) else 1.0,
    }


def _detections(output):
    """Keep every query with its box and its score for each class."""
    # Sigmoid would turn an infinite logit into a valid-looking score.
    if not torch.isfinite(output.logits).all():
        raise ValueError("Detector outputs contain non-finite values")
    return {
        "boxes": box_convert(output.pred_boxes[0], in_fmt="cxcywh", out_fmt="xyxy"),
        "scores": output.logits[0].sigmoid(),
    }


def validate_detector_export(checkpoint, onnx_path, report_path, *, confidence_threshold):
    """Run one synthetic image through PyTorch and ONNX Runtime and compare outputs.

    A mismatch writes a failed report and raises before quantization.
    """
    checkpoint, report_path = Path(checkpoint), Path(report_path)
    pixels = np.random.default_rng(2438).integers(0, 256, (96, 128, 3), dtype=np.uint8)
    # Model-only checkpoints remain exportable; processor defaults are used only
    # for this shared numerical probe, not as deployment preprocessing settings.
    processor = (
        RTDetrImageProcessor.from_pretrained(checkpoint, local_files_only=True)
        if (checkpoint / "preprocessor_config.json").is_file()
        else RTDetrImageProcessor()
    )
    model = RTDetrV2ForObjectDetection.from_pretrained(checkpoint, local_files_only=True).eval()
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inputs = processor(images=Image.fromarray(pixels), return_tensors="pt")
    feed = {item.name: inputs[item.name] for item in session.get_inputs()}
    with torch.inference_mode():
        expected = model(**feed, return_dict=True)
    actual = SimpleNamespace(**{
        name: torch.from_numpy(value)
        for name, value in zip(
            (item.name for item in session.get_outputs()),
            session.run(None, {name: value.numpy() for name, value in feed.items()}),
        )
    })
    shapes = {
        name: [list(getattr(result, name).shape) for result in (expected, actual)]
        for name in ("logits", "pred_boxes")
    }
    report = {
        "minimum_box_iou": MIN_BOX_IOU,
        "confidence_threshold": confidence_threshold,
    }
    if any(reference != converted for reference, converted in shapes.values()):
        # A different batch, query or class count is a different model.
        report.update(passed=False, output_shapes=shapes)
    else:
        # Keep every query: a low score cannot excuse a moved or missing box.
        report.update(compare_detections(
            _detections(expected), _detections(actual),
            confidence_threshold=confidence_threshold,
        ))
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if not report["passed"]:
        raise ValueError(f"RT-DETR export detections differ; see {report_path}")
    return report
