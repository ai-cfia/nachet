"""Package an approved model release and upload it as a Hugging Face PR."""

import argparse
import json
import os
from pathlib import Path
from shutil import copy2

from huggingface_hub import HfApi


def release_model(checkpoint, exports, model_card, output, repo_id,
                  evaluation=(), browser=False, include_int8=False):
    """Copy selected files into a new folder, then propose their release on the Hub."""
    token = os.environ["HF_TOKEN"]
    checkpoint, exports, output = Path(checkpoint), Path(exports), Path(output)
    reports = [Path(report) for report in evaluation]
    if len({report.name for report in reports}) != len(reports):
        raise ValueError("Give evaluation reports distinct filenames")

    files = {name: checkpoint / name for name in (
        "config.json", "model.safetensors", "preprocessor_config.json",
    )}
    files["README.md"] = Path(model_card)
    files["onnx/model.onnx"] = exports / "onnx-fp32/model.onnx"
    if include_int8:
        files["onnx/model_quantized.onnx"] = exports / "onnx-quant/model_quantized.onnx"
    if browser:
        config = json.loads((checkpoint / "config.json").read_text())
        head_name = f"classifier_head_{len(config['id2label'])}spp.f32.bin"
        files["onnx/model.onnx"] = exports / "browser/model_browser.fp16.onnx"
        files[head_name] = exports / "browser" / head_name
    for report in reports:
        files[f"evaluation/{report.name}"] = report

    output.mkdir(parents=True)
    for name, source in files.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, destination)

    api = HfApi(endpoint="https://huggingface.co", token=token)
    # Existing repositories keep their visibility and any other files.
    api.create_repo(repo_id=repo_id, repo_type="model", private=False, exist_ok=True)
    return api.upload_folder(
        folder_path=str(output),
        repo_id=repo_id,
        repo_type="model",
        create_pr=True,
        commit_message=f"Publish {checkpoint.name}",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--exports", required=True, type=Path, help="Evaluated export directory")
    parser.add_argument("--model-card", required=True, type=Path, help="Reviewed model card")
    parser.add_argument("--output", required=True, type=Path, help="New release directory")
    parser.add_argument("--repo-id", required=True, help="Approved Hugging Face model repository")
    parser.add_argument("--evaluation", nargs="+", default=[], type=Path,
                        help="Optional reviewed reports with distinct filenames")
    parser.add_argument("--browser", action="store_true", help="Use the Swin FP16 CAM model")
    parser.add_argument("--include-int8", action="store_true", help="Also include the INT8 model")
    args = parser.parse_args()
    result = release_model(
        args.checkpoint, args.exports, args.model_card, args.output, args.repo_id,
        args.evaluation, args.browser, args.include_int8,
    )
    print(f"Release proposed for review: {result.pr_url}")


if __name__ == "__main__":
    main()
