#!/usr/bin/env python
"""Export a local checkpoint to ONNX without publishing or modifying it."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
from shutil import copy2, which
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4


TASKS = {"swin": "image-classification", "rt_detr_v2": "object-detection"}


@contextmanager
def staged_output(output):
    """Finish a new export directory, or retain a uniquely named partial run.

    The destination must have a single writer. Existing paths, including
    dangling symlinks, are rejected before work and checked again before rename.
    """
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Export output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(f".{output.name}.{uuid4().hex}.partial")
    staging.mkdir()
    try:
        yield staging
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Export output already exists: {output}")
        # A sibling directory keeps the final rename on the same filesystem.
        staging.rename(output)
    except BaseException as error:
        error.add_note(f"Incomplete export; diagnostic files retained at {staging}")
        raise


def checkpoint_files(checkpoint):
    """Return the model config and weight files needed for export."""
    config_file = checkpoint / "config.json"
    weights_file = checkpoint / "model.safetensors"
    if weights_file.is_file():
        return [config_file, weights_file]

    # Large checkpoints split their weights across files called shards.
    # The index maps each model parameter to the shard that contains it.
    index_file = checkpoint / "model.safetensors.index.json"
    if not index_file.is_file():
        raise FileNotFoundError(f"No safetensors weights found in {checkpoint}")
    weight_index = json.loads(index_file.read_text())
    if not isinstance(weight_index, dict) or not isinstance(weight_index.get("weight_map"), dict):
        raise ValueError(f"Weight index must contain a weight_map object: {index_file}")
    parameter_to_shard = weight_index["weight_map"]
    if not all(isinstance(name, str) for name in parameter_to_shard.values()):
        raise ValueError(f"Weight index must map parameters to shard filenames: {index_file}")
    shard_names = sorted(set(parameter_to_shard.values()))
    if not shard_names:
        raise ValueError("The checkpoint weight index is empty")

    model_files = [config_file, index_file]
    for shard_name in shard_names:
        # Index entries must be filenames, not paths into other directories.
        if Path(shard_name).name != shard_name:
            raise ValueError(f"Invalid weight shard name: {shard_name!r}")
        if not shard_name.endswith(".safetensors"):
            raise ValueError(f"Invalid weight shard name: {shard_name!r}")
        shard_file = checkpoint / shard_name
        if not shard_file.is_file():
            raise FileNotFoundError(shard_file)
        model_files.append(shard_file)
    return model_files


def export_model(checkpoint, output, processor=None, quantize=False):
    """Export saved model files to a new directory, optionally adding INT8."""
    checkpoint = Path(checkpoint).resolve(strict=True)
    output = Path(output).absolute()
    config = json.loads((checkpoint / "config.json").read_text())
    model_type = config.get("model_type")
    if model_type not in TASKS:
        raise ValueError(f"Unsupported model type: {model_type!r}; expected {list(TASKS)}")
    model_files = checkpoint_files(checkpoint)

    # Some training runs save the image processor outside the checkpoint.
    processor_dir = checkpoint
    if processor:
        processor_dir = Path(processor).resolve(strict=True)
    processor_file = processor_dir / "preprocessor_config.json"
    if not processor_file.is_file():
        raise FileNotFoundError(f"Missing {processor_file}; pass --processor if saved elsewhere")
    # Reject malformed processor JSON before starting the export command.
    json.loads(processor_file.read_text())

    if output.resolve().is_relative_to(checkpoint):
        raise ValueError("Export output must be outside the source checkpoint")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Export output already exists: {output}")
    optimum_cli = which("optimum-cli")
    if optimum_cli is None:
        raise RuntimeError("optimum-cli is required; install the export dependencies")

    # Use the supplied local files without downloading missing Hub files.
    export_env = os.environ.copy()
    export_env["HF_HUB_OFFLINE"] = "1"
    export_env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    with staged_output(output) as staging:
        fp32_dir = staging / "onnx-fp32"
        # Optimum needs the model and processor in one folder. Link the weights
        # to avoid copying them, and leave the original checkpoint untouched.
        with TemporaryDirectory(prefix="nachet-export-") as temporary_dir:
            export_input_dir = Path(temporary_dir)
            for model_file in model_files:
                (export_input_dir / model_file.name).symlink_to(model_file)
            copy2(processor_file, export_input_dir / processor_file.name)
            subprocess.run(
                [
                    optimum_cli, "export", "onnx",
                    "--model", str(export_input_dir),
                    "--task", TASKS[model_type],
                    "--library-name", "transformers",
                    str(fp32_dir),
                ],
                check=True,
                env=export_env,
            )
        if not (fp32_dir / "model.onnx").is_file():
            raise FileNotFoundError("Export command did not produce onnx-fp32/model.onnx")

        # Quantization reads the FP32 export and writes a separate INT8 model.
        if quantize:
            quantized_dir = staging / "onnx-quant"
            subprocess.run(
                [
                    optimum_cli, "onnxruntime", "quantize",
                    "--onnx_model", str(fp32_dir),
                    "--avx512",
                    "-o", str(quantized_dir),
                ],
                check=True,
                env=export_env,
            )
            if not (quantized_dir / "model_quantized.onnx").is_file():
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
