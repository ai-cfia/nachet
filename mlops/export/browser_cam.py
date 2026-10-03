"""Prepare an exported Swin classifier for Class Activation Maps in Nachet Mini.

Follows exporter/DFF_EXPORT.md in nachet-model-ccds. ONNX Runtime Web only
returns declared graph outputs, so the final swin.layernorm features become a
second output. The model is then converted to FP16 and the classifier weights
are written separately for the browser to combine with those features.
"""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import onnx
import onnxruntime as ort
from onnxconverter_common import float16
from safetensors import safe_open


# Final swin.layernorm output in opset 16 exports from export_model.py.
FEATURE_TENSOR = "/swin/layernorm/Add_1_output_0"
FEATURE_OUTPUT_NAME = "swin_layernorm"


def add_feature_output(source, destination):
    """Expose the final Swin features as an extra output without changing logits."""
    model = onnx.load(source)
    if not any(FEATURE_TENSOR in node.output for node in model.graph.node):
        raise ValueError(f"{source} has no {FEATURE_TENSOR}; export it with export_model.py")
    model.graph.node.append(onnx.helper.make_node(
        "Identity", [FEATURE_TENSOR], [FEATURE_OUTPUT_NAME], name="dff_feature_identity",
    ))
    model.graph.output.append(onnx.helper.make_empty_tensor_value_info(FEATURE_OUTPUT_NAME))
    onnx.save(model, destination)


def convert_to_fp16(source, destination):
    """Fuse LayerNorms with ONNX Runtime, then convert to FP16 with FP32 inputs and outputs."""
    with TemporaryDirectory() as temporary_dir:
        optimized = Path(temporary_dir) / "model.opt.onnx"
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        options.optimized_model_filepath = str(optimized)
        ort.InferenceSession(str(source), options, providers=["CPUExecutionProvider"])
        # Converting before fusion makes ONNX Runtime's LayerNorm fusion crash.
        model = float16.convert_float_to_float16(
            onnx.load(optimized), keep_io_types=True, disable_shape_infer=True,
        )
    onnx.save(model, destination)


def run(path, pixels):
    """Run a model with full graph optimization, as ONNX Runtime Web does."""
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
    outputs = session.run(None, {session.get_inputs()[0].name: pixels})
    return dict(zip([output.name for output in session.get_outputs()], outputs))


def prepare_browser_model(source, checkpoint, output):
    """Write the FP16 browser model and classifier head weights to a new directory."""
    checkpoint = Path(checkpoint)
    output = Path(output)
    output.mkdir(parents=True)

    with safe_open(checkpoint / "model.safetensors", framework="pt") as weights:
        head = weights.get_tensor("classifier.weight").float().numpy()
    # Mini reads one little-endian float32 row of feature weights per class.
    head_path = output / f"classifier_head_{head.shape[0]}spp.f32.bin"
    head.astype("<f4").tofile(head_path)

    browser_path = output / "model_browser.fp16.onnx"
    with TemporaryDirectory() as temporary_dir:
        features_path = Path(temporary_dir) / "model_with_features.onnx"
        add_feature_output(source, features_path)
        convert_to_fp16(features_path, browser_path)
        # Random input checks that the FP16 model loads and keeps its outputs.
        # It does not measure accuracy; release evaluation is a separate step.
        size = json.loads((checkpoint / "config.json").read_text())["image_size"]
        pixels = np.random.default_rng(0).random((1, 3, size, size), dtype=np.float32)
        expected = run(features_path, pixels)
        actual = run(browser_path, pixels)

    for name, value in actual.items():
        difference = np.abs(value - expected[name]).max()
        print(f"{name}: shape {value.shape}, max FP16 difference {difference:.3g}")
    same_top1 = expected["logits"].argmax() == actual["logits"].argmax()
    print(f"FP32 and FP16 top-1 agree: {same_top1}")
    return browser_path, head_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True, type=Path, help="onnx-fp32/model.onnx from export_model.py")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the browser files")
    args = parser.parse_args()
    browser_path, head_path = prepare_browser_model(args.onnx, args.checkpoint, args.output)
    print(f"Wrote {browser_path} and {head_path}")


if __name__ == "__main__":
    main()
