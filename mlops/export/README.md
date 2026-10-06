# Checkpoint export runtime

This directory builds the image that exports trained checkpoints to ONNX and
prepares the Swin classifier for Class Activation Maps (CAM) in Nachet Mini. It
is a standalone uv project. It is separate from the trainer images because
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
they do not check production accuracy or browser behavior.

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

## Update dependencies or the version

Use Python 3.12 and the uv version pinned in the Dockerfile:

```bash
uv lock
uv lock --check
```

The image tag uses `[project].version` from `pyproject.toml`. Review and commit
both files together, then rebuild the image to rerun the tests.
