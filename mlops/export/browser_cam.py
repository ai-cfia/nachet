#!/usr/bin/env python
"""Prepare Swin ONNX features and head weights for browser CAM.

Adapted from nachet-model-ccds/exporter/dff_add_feature_output.py and
dff_make_browser_model.py. Head extraction is new; the historical command
has not been recovered.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnxconverter_common import float16
from safetensors import safe_open


FEATURE_TENSOR = "/swin/layernorm/Add_1_output_0"
FUSED_FEATURE_TENSOR = "/swin/layernorm/LayerNormalization_output_0"
FEATURE_OUTPUT_NAME = "swin_layernorm"


def run(path, pixels, optimization=ort.GraphOptimizationLevel.ORT_ENABLE_ALL):
    options = ort.SessionOptions()
    options.graph_optimization_level = optimization
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
    config = json.loads((checkpoint / "config.json").read_text())
    if config.get("model_type") != "swin":
        raise ValueError("Browser CAM export requires a Swin classifier")
    index_path = checkpoint / "model.safetensors.index.json"
    index = json.loads(index_path.read_text())["weight_map"] if index_path.exists() else None
    tensors = {}
    for name in ("classifier.weight", "classifier.bias"):
        filename = index[name] if index is not None else "model.safetensors"
        if Path(filename).name != filename:
            raise ValueError(f"Invalid weight shard name: {filename!r}")
        with safe_open(checkpoint / filename, framework="np") as weights:
            tensors[name] = weights.get_tensor(name).astype(np.float32)
    weight, bias = tensors["classifier.weight"], tensors["classifier.bias"]
    labels = config.get("id2label", {})
    if weight.ndim != 2 or bias.shape != (weight.shape[0],):
        raise ValueError("Classifier head must contain a weight matrix and one bias per class")
    if set(labels) != {str(i) for i in range(weight.shape[0])}:
        raise ValueError("Class IDs must cover every classifier-head row")
    if not np.isfinite(weight).all() or not np.isfinite(bias).all():
        raise ValueError("Classifier head contains non-finite values")
    return weight, bias


def prepare_browser_model(source, checkpoint, output, pixels):
    if pixels.dtype != np.float32 or pixels.ndim != 4 or pixels.shape[1] != 3:
        raise ValueError("Pixels must be a float32 NCHW RGB batch")
    if not pixels.size or not np.isfinite(pixels).all():
        raise ValueError("Pixels must be nonempty and finite")
    source = Path(source).resolve(strict=True)
    checkpoint = Path(checkpoint).resolve(strict=True)
    output = Path(output).absolute()
    if output.resolve().is_relative_to(checkpoint):
        raise ValueError("Browser output must be outside the checkpoint")
    weight, bias = load_classifier_head(checkpoint)
    output.mkdir(parents=True, exist_ok=False)
    fp32 = output / "model_with_features.onnx"
    optimized = output / "model_with_features.opt.onnx"
    browser = output / "model.onnx"
    candidate = output / "model.candidate.onnx"
    add_feature_output(source, fp32, weight.shape[1])
    original = run(source, pixels)
    reference = run(fp32, pixels)
    np.testing.assert_allclose(reference["logits"], original["logits"], atol=1e-5, rtol=1e-4)
    features = reference[FEATURE_OUTPUT_NAME]
    if features.ndim != 3 or features.shape[2] != weight.shape[1]:
        raise ValueError(f"Unexpected feature shape: {features.shape}")
    # Check that the features and checkpoint head reproduce logits on these inputs.
    reconstructed = features.mean(axis=1) @ weight.T + bias
    np.testing.assert_allclose(reconstructed, reference["logits"], atol=1e-5, rtol=1e-4)

    # Fuse LayerNorm before FP16 conversion to avoid the historical cast/fusion failure.
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    options.optimized_model_filepath = str(optimized)
    ort.InferenceSession(str(fp32), options, providers=["CPUExecutionProvider"])
    model = onnx.load(optimized)
    model_fp16 = float16.convert_float_to_float16(model, keep_io_types=True, disable_shape_infer=True)
    # Failed checks retain an intermediate graph, never the final model filename.
    onnx.save(model_fp16, candidate)
    actual = run(candidate, pixels)
    for name in ("logits", FEATURE_OUTPUT_NAME):
        np.testing.assert_allclose(actual[name], reference[name], atol=1e-3, rtol=1e-2)
    np.testing.assert_array_equal(actual["logits"].argmax(axis=-1), reference["logits"].argmax(axis=-1))
    head = output / f"classifier_head_{weight.shape[0]}spp.f32.bin"
    weight.astype("<f4").tofile(head)
    candidate.rename(browser)
    return browser, head


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pixels", required=True, type=Path,
                        help="NPY array of preprocessed FP32 images, shaped (batch, 3, height, width)")
    args = parser.parse_args()
    pixels = np.load(args.pixels, allow_pickle=False)
    browser, head = prepare_browser_model(args.onnx, args.checkpoint, args.output, pixels)
    print(f"Wrote {browser} and {head}; real browser validation is still required.")


if __name__ == "__main__":
    main()
