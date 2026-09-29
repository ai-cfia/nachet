#!/usr/bin/env python
"""Prepare Swin ONNX features and head weights for browser CAM."""

import argparse
import json
from pathlib import Path
from shutil import rmtree

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


def prepare_browser_model(source, checkpoint, output, pixels):
    """Add CAM features, convert to FP16, and save files after verification."""
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
        browser_model_path = staging / "model.onnx"

        # Expose the CAM features without changing the model's classification scores.
        add_feature_output(source, feature_model_path, feature_channels)
        original_outputs = run_onnx(source, pixels)
        fp32_outputs = run_onnx(feature_model_path, pixels)
        np.testing.assert_allclose(
            fp32_outputs["logits"], original_outputs["logits"],
            atol=1e-5, rtol=1e-4,
            err_msg="Adding the CAM feature output changed the logits",
        )
        features = fp32_outputs[FEATURE_OUTPUT_NAME]
        if features.ndim != 3 or features.shape[2] != feature_channels:
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

        # Compare both outputs on the same images and check that the winning classes agree.
        fp16_outputs = run_onnx(candidate_model_path, pixels)
        for output_name in ("logits", FEATURE_OUTPUT_NAME):
            np.testing.assert_allclose(
                fp16_outputs[output_name], fp32_outputs[output_name],
                atol=1e-3, rtol=1e-2,
                err_msg=f"FP16 {output_name} differs from the FP32 reference",
            )
        fp16_predictions = fp16_outputs["logits"].argmax(axis=-1)
        fp32_predictions = fp32_outputs["logits"].argmax(axis=-1)
        np.testing.assert_array_equal(
            fp16_predictions, fp32_predictions,
            err_msg="FP16 top-1 predictions differ from the FP32 reference",
        )

        # The browser reads one little-endian FP32 row per species ("spp").
        # Keep the candidate filename until all checks and the head write succeed.
        head_path = staging / f"classifier_head_{class_count}spp.f32.bin"
        # Spatial CAM uses weights only; the ONNX logits already include the bias.
        classifier_weights.astype("<f4").tofile(head_path)
        candidate_model_path.rename(browser_model_path)
        rmtree(diagnostics)
    return output / "model.onnx", output / head_path.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pixels", required=True, type=Path,
                        help="NPY array of preprocessed FP32 images, shaped (batch, 3, height, width). "
                             "Use representative images for validation; synthetic inputs are smoke tests only.")
    args = parser.parse_args()
    pixels = np.load(args.pixels, allow_pickle=False)
    browser, head = prepare_browser_model(args.onnx, args.checkpoint, args.output, pixels)
    print(f"Wrote {browser} and {head}; real browser validation is still required.")


if __name__ == "__main__":
    main()
