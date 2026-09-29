#!/usr/bin/env python
"""Prepare Swin ONNX features and head weights for browser CAM."""

import argparse
import hashlib
import json
from pathlib import Path
from shutil import rmtree
import sys

import numpy as np
import onnx
import onnxruntime as ort
from onnxconverter_common import float16
from safetensors import safe_open

if __package__:
    from .export_model import checkpoint_files, staged_output
else:
    from export_model import checkpoint_files, staged_output


FEATURE_TENSOR = "/swin/layernorm/Add_1_output_0"
FUSED_FEATURE_TENSOR = "/swin/layernorm/LayerNormalization_output_0"
FEATURE_OUTPUT_NAME = "swin_layernorm"
# Diagnostic limits; these have not been calibrated for release approval.
FP16_ATOL = 1e-3
FP16_RTOL = 1e-2


def run_onnx(path, pixels):
    """Run all ONNX outputs on CPU and reject non-finite results."""
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
    values = session.run(None, {session.get_inputs()[0].name: pixels})
    # Matching NaNs or infinities must not count as agreement between models.
    if any(not np.isfinite(value).all() for value in values):
        raise ValueError(f"Model produced non-finite outputs: {path}")
    return dict(zip([output.name for output in session.get_outputs()], values))


def add_feature_output(source, destination, channels):
    model = onnx.load(source)
    # Exporters emit the final normalization as arithmetic or one fused operator.
    # Accept only the known final-layer outputs; reconstruction below checks the head.
    outputs = {output for node in model.graph.node for output in node.output}
    candidates = outputs.intersection((FEATURE_TENSOR, FUSED_FEATURE_TENSOR))
    if len(candidates) != 1:
        raise ValueError("Export has no final Swin feature tensor or has ambiguous candidates")
    feature_tensor = candidates.pop()
    if FEATURE_OUTPUT_NAME in outputs:
        raise ValueError(f"Graph already defines {FEATURE_OUTPUT_NAME!r}")
    model.graph.node.append(onnx.helper.make_node(
        "Identity", inputs=[feature_tensor], outputs=[FEATURE_OUTPUT_NAME],
        name="dff_feature_identity",
    ))
    model.graph.output.append(onnx.helper.make_tensor_value_info(
        FEATURE_OUTPUT_NAME, onnx.TensorProto.FLOAT, [None, None, channels],
    ))
    onnx.checker.check_model(model)
    onnx.save(model, destination)


def load_classifier_head(checkpoint):
    """Load the final classification layer and check its shape and class IDs."""
    config = json.loads((checkpoint / "config.json").read_text())
    if config.get("model_type") != "swin":
        raise ValueError("Browser CAM export requires a Swin classifier")

    model_files = checkpoint_files(checkpoint)
    parameter_to_file = {
        "classifier.weight": "model.safetensors",
        "classifier.bias": "model.safetensors",
    }
    index_file = checkpoint / "model.safetensors.index.json"
    if index_file in model_files:
        weight_index = json.loads(index_file.read_text())
        parameter_to_file = weight_index["weight_map"]

    head_tensors = {}
    for parameter_name in ("classifier.weight", "classifier.bias"):
        if parameter_name not in parameter_to_file:
            raise ValueError(f"Weight index has no entry for {parameter_name!r}")
        filename = parameter_to_file[parameter_name]
        # Accept filenames only, so the index cannot select another directory.
        if Path(filename).name != filename:
            raise ValueError(f"Invalid weight shard name: {filename!r}")
        weights_file = checkpoint / filename
        with safe_open(weights_file, framework="pt", device="cpu") as saved_weights:
            if parameter_name not in saved_weights.keys():
                raise ValueError(f"Missing {parameter_name!r} in {weights_file}")
            tensor = saved_weights.get_tensor(parameter_name)
            # NumPy cannot read BF16 directly; widen the saved tensor first.
            head_tensors[parameter_name] = tensor.float().numpy()

    classifier_weights = head_tensors["classifier.weight"]
    classifier_bias = head_tensors["classifier.bias"]

    # Each class has one row of feature weights and one bias value.
    if classifier_weights.ndim != 2:
        raise ValueError("Classifier weights must be a two-dimensional matrix")
    class_count = classifier_weights.shape[0]
    if classifier_bias.shape != (class_count,):
        raise ValueError(f"Classifier bias must have shape ({class_count},), got {classifier_bias.shape}")
    labels = config.get("id2label", {})
    expected_class_ids = {str(class_id) for class_id in range(class_count)}
    if set(labels) != expected_class_ids:
        raise ValueError("Class IDs must cover every classifier-head row")
    if not np.isfinite(classifier_weights).all():
        raise ValueError("Classifier head contains non-finite values")
    if not np.isfinite(classifier_bias).all():
        raise ValueError("Classifier head contains non-finite values")
    return classifier_weights, classifier_bias


def output_errors(reference, actual):
    """Describe one image's output; relative error is undefined for a zero reference."""
    outside_tolerance = ~np.isclose(actual, reference, atol=FP16_ATOL, rtol=FP16_RTOL)
    reference = reference.astype(np.float64)
    actual = actual.astype(np.float64)
    difference = actual - reference
    reference_norm = float(np.linalg.norm(reference.ravel()))
    error_norm = float(np.linalg.norm(difference.ravel()))
    return {
        "max_absolute_error": float(np.abs(difference).max()),
        "reference_l2": reference_norm,
        "error_l2": error_norm,
        "relative_l2_error": error_norm / reference_norm if reference_norm else None,
        "values_outside_tolerance": int(np.count_nonzero(outside_tolerance)),
    }


def measure_fp16(reference, actual):
    """Measure each image's output errors and class rankings."""
    images = []
    for index in range(len(reference["logits"])):
        fp32_logits = reference["logits"][index]
        fp16_logits = actual["logits"][index]
        # Lower class IDs win ties, matching argmax's first-maximum rule.
        fp32_top5 = np.argsort(-fp32_logits, kind="stable")[:5]
        fp16_top5 = np.argsort(-fp16_logits, kind="stable")[:5]
        margin = (float(fp32_logits[fp32_top5[0]]) - float(fp32_logits[fp32_top5[1]])
                  if len(fp32_top5) > 1 else None)
        images.append({
            "index": index,
            "errors": {
                name: output_errors(reference[name][index], actual[name][index])
                for name in ("logits", FEATURE_OUTPUT_NAME)
            },
            "fp32_top5": fp32_top5.tolist(),
            "fp16_top5": fp16_top5.tolist(),
            "fp32_top1_margin": margin,
            "top1_changed": bool(fp32_top5[0] != fp16_top5[0]),
            "ordered_top5_changed": not np.array_equal(fp32_top5, fp16_top5),
        })
    return images


def verify_fp16(candidate, pixels, reference, report_path, *, strict=False):
    """Require valid CPU outputs; record numerical failures and reject them in strict mode."""
    report = {
        "schema_version": 3,
        "output_checks": "failed",
        "fp16_checks": "not_performed",
        "strict": strict,
        "release_evaluation": "not_performed",
        "runtime": {"onnxruntime": ort.__version__, "provider": "CPUExecutionProvider"},
        "pixels": {
            "shape": list(pixels.shape), "dtype": str(pixels.dtype),
            "sha256": hashlib.sha256(pixels.tobytes(order="C")).hexdigest(),
        },
        "criteria": {"atol": FP16_ATOL, "rtol": FP16_RTOL, "require_same_top1": True},
    }
    try:
        actual = run_onnx(candidate, pixels)
        report["outputs"] = {
            name: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for name, value in actual.items()
        }
        if actual.keys() != reference.keys():
            raise ValueError("FP16 output names differ from the FP32 reference")
        for name, expected in reference.items():
            value = actual[name]
            # allclose allows broadcasting; the browser requires the exact shape.
            if value.shape != expected.shape:
                raise ValueError(f"FP16 {name} shape {value.shape} differs from {expected.shape}")
            if value.dtype != np.float32:
                raise ValueError(f"FP16 {name} output must remain float32, got {value.dtype}")

        report["output_checks"] = "passed"
        report["images"] = measure_fp16(reference, actual)

        mismatches = []
        for name in ("logits", FEATURE_OUTPUT_NAME):
            if any(image["errors"][name]["values_outside_tolerance"] for image in report["images"]):
                mismatches.append(f"FP16 {name} differs from the FP32 reference")
        if any(image["top1_changed"] for image in report["images"]):
            mismatches.append("FP16 top-1 predictions differ from the FP32 reference")
        report["fp16_checks"] = "failed" if mismatches else "passed"
        if mismatches:
            report["fp16_mismatch"] = "; ".join(mismatches)
            if strict:
                raise AssertionError(report["fp16_mismatch"])
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def prepare_browser_model(source, checkpoint, output, pixels, *, strict=False):
    """Save an FP16 candidate and report; strict mode also requires numerical agreement."""
    # Verification uses preprocessed images: batch, RGB channels, height, width.
    if pixels.dtype != np.float32 or pixels.ndim != 4 or pixels.shape[1] != 3:
        raise ValueError("Pixels must be a float32 NCHW RGB batch")
    if not pixels.size or not np.isfinite(pixels).all():
        raise ValueError("Pixels must be nonempty and finite")
    source = Path(source).resolve(strict=True)
    checkpoint = Path(checkpoint).resolve(strict=True)
    output = Path(output).absolute()
    if output.resolve().is_relative_to(checkpoint):
        raise ValueError("Browser output must be outside the checkpoint")
    classifier_weights, classifier_bias = load_classifier_head(checkpoint)
    class_count, feature_channels = classifier_weights.shape
    with staged_output(output) as staging:
        diagnostics = staging / "diagnostics"
        diagnostics.mkdir()
        feature_model_path = diagnostics / "model_with_features.onnx"
        optimized_model_path = diagnostics / "model_with_features.opt.onnx"
        candidate_model_path = diagnostics / "model.candidate.onnx"
        browser_model_path = staging / "model.candidate.onnx"

        # Expose the CAM features without changing the model's classification scores.
        add_feature_output(source, feature_model_path, feature_channels)
        original_outputs = run_onnx(source, pixels)
        fp32_outputs = run_onnx(feature_model_path, pixels)
        if fp32_outputs["logits"].shape != (len(pixels), class_count):
            raise ValueError("FP32 logits must have one row per image and one column per class")
        for name in ("logits", FEATURE_OUTPUT_NAME):
            if fp32_outputs[name].dtype != np.float32:
                raise ValueError(f"FP32 {name} output must be float32")
        np.testing.assert_allclose(
            fp32_outputs["logits"], original_outputs["logits"],
            atol=1e-5, rtol=1e-4,
            err_msg="Adding the CAM feature output changed the logits",
        )
        features = fp32_outputs[FEATURE_OUTPUT_NAME]
        if (features.ndim != 3 or features.shape[0] != len(pixels)
                or not features.shape[1] or features.shape[2] != feature_channels):
            raise ValueError(f"Unexpected feature shape: {features.shape}")

        # Swin averages the spatial features before applying its classification layer.
        # Repeating that calculation checks the selected features and head on these inputs.
        pooled_features = features.mean(axis=1)
        reconstructed_logits = pooled_features @ classifier_weights.T + classifier_bias
        np.testing.assert_allclose(
            reconstructed_logits, fp32_outputs["logits"], atol=1e-5, rtol=1e-4,
            err_msg="CAM features and checkpoint head do not reproduce the logits",
        )

        # Fuse LayerNorm first: converting its unfused casts can crash ORT's
        # SimplifiedLayerNormFusion pass.
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        options.optimized_model_filepath = str(optimized_model_path)
        ort.InferenceSession(
            str(feature_model_path), options, providers=["CPUExecutionProvider"],
        )

        # Convert internal operations to FP16 while keeping browser inputs and outputs FP32.
        optimized_model = onnx.load(optimized_model_path)
        fp16_model = float16.convert_float_to_float16(
            optimized_model,
            keep_io_types=True,
            disable_shape_infer=True,
        )
        onnx.save(fp16_model, candidate_model_path)

        verify_fp16(candidate_model_path, pixels, fp32_outputs,
                    staging / "validation.json", strict=strict)

        # The browser reads one little-endian FP32 row per species ("spp").
        # Release packaging must evaluate and approve this candidate before deployment.
        head_path = staging / f"classifier_head_{class_count}spp.f32.bin"
        # Spatial CAM uses weights only; the ONNX logits already include the bias.
        classifier_weights.astype("<f4").tofile(head_path)
        candidate_model_path.rename(browser_model_path)
        rmtree(diagnostics)
    return output / "model.candidate.onnx", output / head_path.name


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Exports are candidates for evaluation. Neither mode approves a model for deployment.",
    )
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pixels", required=True, type=Path,
                        help="NPY array of preprocessed FP32 images, shaped (batch, 3, height, width). "
                             "Use representative images for validation; synthetic inputs are smoke tests only.")
    parser.add_argument("--strict", action="store_true",
                        help="Reject FP16 numerical mismatches or changed top-1 predictions. "
                             "By default these are reported without stopping export.")
    args = parser.parse_args()
    pixels = np.load(args.pixels, allow_pickle=False)
    browser, head = prepare_browser_model(args.onnx, args.checkpoint, args.output, pixels, strict=args.strict)
    report_path = browser.parent / "validation.json"
    report = json.loads(report_path.read_text())
    print(f"Wrote FP16 candidate {browser} and CAM head {head}.")
    print(f"FP16 numerical checks: {report['fp16_checks']}. Report: {report_path}")
    if report["fp16_checks"] == "failed":
        print("WARNING: FP16 numerical checks failed; review the report before using this candidate.", file=sys.stderr)
    print("Release evaluation has not been performed; this candidate is not approved for deployment.")


if __name__ == "__main__":
    main()
