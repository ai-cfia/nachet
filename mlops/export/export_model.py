#!/usr/bin/env python
"""Export a local checkpoint to ONNX without publishing or modifying it."""

import argparse
import json
import os
from pathlib import Path
from shutil import copy2, which
import subprocess
from tempfile import TemporaryDirectory


TASKS = {"swin": "image-classification", "rt_detr_v2": "object-detection"}


def checkpoint_files(checkpoint):
    """Collect saved weights without including optimizer or training state."""
    weights = checkpoint / "model.safetensors"
    if weights.is_file():
        return [checkpoint / "config.json", weights]
    index = checkpoint / "model.safetensors.index.json"
    if not index.is_file():
        raise FileNotFoundError(f"No safetensors weights found in {checkpoint}")
    names = set(json.loads(index.read_text())["weight_map"].values())
    if not names:
        raise ValueError("The checkpoint weight index is empty")
    files = [checkpoint / "config.json", index]
    for name in sorted(names):
        if Path(name).name != name or not name.endswith(".safetensors"):
            raise ValueError(f"Invalid weight shard name: {name!r}")
        path = checkpoint / name
        if not path.is_file():
            raise FileNotFoundError(path)
        files.append(path)
    return files


def export_model(checkpoint, output, processor=None, quantize=False):
    checkpoint = Path(checkpoint).resolve(strict=True)
    output = Path(output).absolute()
    config = json.loads((checkpoint / "config.json").read_text())
    model_type = config.get("model_type")
    if model_type not in TASKS:
        raise ValueError(f"Unsupported model type: {model_type!r}; expected {list(TASKS)}")
    files = checkpoint_files(checkpoint)
    processor = Path(processor).resolve(strict=True) if processor else checkpoint
    processor_file = processor / "preprocessor_config.json"
    if not processor_file.is_file():
        raise FileNotFoundError(f"Missing {processor_file}; pass --processor if saved elsewhere")
    json.loads(processor_file.read_text())
    if output.resolve().is_relative_to(checkpoint):
        raise ValueError("Export output must be outside the source checkpoint")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Export output already exists: {output}")
    executable = which("optimum-cli")
    if executable is None:
        raise RuntimeError("optimum-cli is required; install the export dependencies")

    # The temporary view supplies the saved processor without changing the checkpoint.
    env = dict(os.environ, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    output.mkdir(parents=True)
    with TemporaryDirectory(prefix="nachet-export-") as staging:
        staging = Path(staging)
        for source in files:
            (staging / source.name).symlink_to(source)
        copy2(processor_file, staging / processor_file.name)
        subprocess.run(
            [executable, "export", "onnx", "--model", str(staging),
             "--task", TASKS[model_type], "--library-name", "transformers",
             str(output / "onnx-fp32")],
            check=True, env=env,
        )
    if not (output / "onnx-fp32" / "model.onnx").is_file():
        raise FileNotFoundError("Export command did not produce onnx-fp32/model.onnx")
    if quantize:
        subprocess.run(
            [executable, "onnxruntime", "quantize", "--onnx_model",
             str(output / "onnx-fp32"), "--avx512", "-o", str(output / "onnx-quant")],
            check=True, env=env,
        )
        if not (output / "onnx-quant" / "model_quantized.onnx").is_file():
            raise FileNotFoundError("Quantization did not produce model_quantized.onnx")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory outside the checkpoint")
    parser.add_argument("--processor", type=Path, help="Directory containing the saved image processor")
    parser.add_argument("--quantize", action="store_true", help="Also create the original AVX512 INT8 variant")
    args = parser.parse_args()
    output = export_model(args.checkpoint, args.output, args.processor, args.quantize)
    print(f"ONNX files written to {output}; publication and browser checks are separate.")


if __name__ == "__main__":
    main()
