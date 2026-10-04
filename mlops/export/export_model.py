"""Export a local checkpoint to ONNX, optionally adding an INT8 model."""

import argparse
import json
import os
from pathlib import Path
import subprocess


TASKS = {"swin": "image-classification", "rt_detr_v2": "object-detection"}
# The published Nachet models use opset 16. From opset 17, PyTorch exports
# LayerNorm as one LayerNormalization node, which renames the Swin feature
# tensor that browser_cam.py exposes.
OPSET = "16"


def export_model(checkpoint, output, quantize=False):
    """Write output/onnx-fp32 and, with quantize, output/onnx-quant."""
    checkpoint = Path(checkpoint)
    output = Path(output)
    model_type = json.loads((checkpoint / "config.json").read_text()).get("model_type")
    if model_type not in TASKS:
        raise ValueError(f"Unsupported model type: {model_type!r}; expected {list(TASKS)}")
    # A new directory keeps files from an earlier export out of this one.
    output.mkdir(parents=True)
    # Use only the local checkpoint files; never download missing ones.
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}

    subprocess.run(
        [
            "optimum-cli", "export", "onnx",
            "--model", str(checkpoint),
            "--task", TASKS[model_type],
            "--opset", OPSET,
            "--library-name", "transformers",
            str(output / "onnx-fp32"),
        ],
        check=True,
        env=env,
    )
    if quantize:
        subprocess.run(
            [
                "optimum-cli", "onnxruntime", "quantize",
                "--onnx_model", str(output / "onnx-fp32"),
                "--avx512",
                "-o", str(output / "onnx-quant"),
            ],
            check=True,
            env=env,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory for the ONNX files")
    parser.add_argument("--quantize", action="store_true", help="Also create the AVX512 INT8 model")
    args = parser.parse_args()
    export_model(args.checkpoint, args.output, args.quantize)
    print(f"ONNX files written to {args.output}")


if __name__ == "__main__":
    main()
