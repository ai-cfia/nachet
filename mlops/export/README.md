# Checkpoint export runtime

This directory builds the image that exports trained checkpoints to ONNX,
prepares the Swin classifier for Class Activation Maps (CAM) in Nachet Mini,
and packages approved model releases. It is a standalone uv project. It is
separate from the trainer images because
`optimum-onnx==0.1.0` requires Transformers below 4.58, while training uses
5.16.1.

## Dependencies

`pyproject.toml` declares the Python dependencies and `uv.lock` records their
resolved versions. Generate the lockfile with uv; do not edit it by hand. The
lock targets Linux x86-64 with CPU PyTorch wheels, because export does not need
a GPU.

## Build and check

Run these commands from this directory:

```bash
docker build --platform linux/amd64 -t nachet-export:local .
docker run --rm --platform linux/amd64 --network none \
  nachet-export:local export_model.py --help
```

The build checks that `uv.lock` is current and runs all tests in `tests/` with
networking disabled. A failed test stops the build. Test files are mounted for
that step, not copied into the image. The tests use small random-weight models;
they do not check production accuracy or browser behavior. Publication tests
check local packaging and mock Hub calls; they do not upload anything.

CI builds, pushes and signs `ghcr.io/ai-cfia/nachet-export` for pull requests
and merges, like the trainer images. New GHCR packages are private by default,
so confirm pull access before the first cluster run.

## Export a checkpoint

The checkpoint needs `config.json` and `model.safetensors`. Replace the
absolute paths below; the output directory must not exist yet.

```bash
docker run --rm --platform linux/amd64 --network none \
  --user "$(id -u):$(id -g)" \
  --mount type=bind,src=/absolute/checkpoint,dst=/checkpoint,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports \
  nachet-export:local export_model.py \
  --checkpoint /checkpoint --output /exports/run-1 --quantize
```

This writes the FP32 model to `onnx-fp32/` using opset 16, like the published
Nachet models. `--quantize` also writes the AVX512 INT8 model to `onnx-quant/`.

## Prepare classifier CAM files

Use the same checkpoint that produced the ONNX model:

```bash
docker run --rm --platform linux/amd64 --network none \
  --user "$(id -u):$(id -g)" \
  --mount type=bind,src=/absolute/checkpoint,dst=/checkpoint,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports \
  nachet-export:local browser_cam.py \
  --onnx /exports/run-1/onnx-fp32/model.onnx --checkpoint /checkpoint \
  --output /exports/run-1/browser
```

This follows `exporter/DFF_EXPORT.md` in nachet-model-ccds. It writes
`model_browser.fp16.onnx`, which adds the `swin_layernorm` output, and
`classifier_head_<class-count>spp.f32.bin`. The printed FP32 and FP16
comparison uses random input on CPU; it checks that the model loads, not that
it is accurate.

A failed run may leave partial files. Retry with a new output directory.

## Evaluate converted classifier models

Run from the repository root in the classifier trainer's Python environment.
Use the checkpoint and saved processor that produced the ONNX file, with the
same dataset and evaluation settings used for checkpoint evaluation:

```bash
PYTHONPATH=mlops/training \
  python mlops/training/classifier/src/validation_classifier.py \
  --model_path /absolute/checkpoint --test_data_path /absolute/images \
  --onnx_path /absolute/exports/run-1/browser/model_browser.fp16.onnx \
  --output_path /absolute/reports/browser-fp16
```

`--onnx_path` switches inference to ONNX Runtime on CPU; preprocessing, label
mapping and metrics stay unchanged. It also works with the INT8 export. Without
the option, the evaluator loads the PyTorch checkpoint as before. The classifier
trainer image already sets `PYTHONPATH` for the shared ONNX adapter.

The metrics JSON includes `onnx_model` with the filename, SHA-256, runtime
version and provider. Use separate report directories for each artifact. These
CPU results do not establish browser compatibility or approve publication.

## Publish an approved release

`ModelRelease.py` adapts the
[original release script](https://github.com/ai-cfia/nachet-model-ccds/blob/229a3d40d384a9db05eb83a6201005818104e202/exporter/ModelRelease.py)
from nachet-model-ccds. It keeps the original upload: create the repository if
needed, then upload the release as a Hugging Face PR. It no longer converts the
model or uploads training state.

Run it only after the checkpoint and its exports have been evaluated and a
person has approved the release. Supply `HF_TOKEN` from the Vault secret
manager. The output directory must not exist yet:

```bash
docker run --rm --platform linux/amd64 \
  --user "$(id -u):$(id -g)" --env HF_TOKEN \
  --mount type=bind,src=/absolute/checkpoint,dst=/checkpoint,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports,readonly \
  --mount type=bind,src=/absolute/review,dst=/review,readonly \
  --mount type=bind,src=/absolute/releases,dst=/releases \
  nachet-export:local ModelRelease.py \
  --checkpoint /checkpoint --exports /exports/run-1 \
  --model-card /review/README.md --output /releases/seed-model \
  --repo-id cfia-ai-lab/approved-model-repository --browser
```

The release contains the checkpoint's `config.json`,
`preprocessor_config.json` and `model.safetensors`, the reviewed model card as
`README.md`, and the FP32 model at `onnx/model.onnx`.

- `--browser` puts the FP16 CAM model at `onnx/model.onnx` instead and adds the
  classifier head at the repository root, as Mini expects.
- `--include-int8` adds `onnx/model_quantized.onnx`. It has no CAM output.
- `--evaluation` copies reports into `evaluation/`. Give them distinct
  filenames.

New repositories are public. The Hub PR keeps the release off `main` until
someone merges it, but anyone can see the PR's files. A failed run may leave
partial files; retry with a new output directory.

Mini's RT-DETR entries currently request `onnx/model_patched.onnx`; this
script packages detector ONNX at `onnx/model.onnx`.

## Update dependencies or the version

Use Python 3.12 and the uv version pinned in the Dockerfile:

```bash
uv lock
uv lock --check
```

The image tag uses `[project].version` from `pyproject.toml`. Review and commit
both files together, then rebuild the image to rerun the tests.
