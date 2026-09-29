# Checkpoint export runtime

Export a local Swin classifier or RT-DETR V2 detector checkpoint to ONNX.
The scripts write candidate artifacts for evaluation and do not publish models.

## Build and test

Run from `mlops/export`:

```bash
docker build --platform linux/amd64 --target test -t nachet-export:test .
docker run --rm --platform linux/amd64 --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,exec,size=2g nachet-export:test

docker build --platform linux/amd64 -t nachet-export:local .
docker run --rm --platform linux/amd64 --network none --read-only \
  nachet-export:local --help
```

The image uses Python 3.12, CPU PyTorch wheels for Linux x86-64, and dependencies
locked by uv. Test and runtime targets run as a non-root user. The runtime target
excludes tests, test dependencies, model weights, and the package cache.
Building it directly does not run tests. CI builds both targets and runs the
test suite without networking.

The tests use small random-weight models and saved preprocessing. They exercise
export, inference, quantization, CAM reconstruction, and failure handling;
production checkpoint accuracy and browser compatibility need separate checks.

With a populated BuildKit package cache, add
`--build-arg UV_OFFLINE=true --network=none` to prevent package downloads during
build steps. Docker may still resolve image metadata through its registry.
A first build needs the pinned images and locked dependencies.

## Export a checkpoint

The checkpoint needs `config.json` and `model.safetensors`, or a
`model.safetensors.index.json` referencing its weight shards. Include the saved
`preprocessor_config.json`, or mount a separate processor directory and pass
`--processor /processor`. Missing inputs are never downloaded.

Create a writable host output directory. Replace the absolute paths below:

```bash
docker run --rm --platform linux/amd64 --network none --read-only \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,exec,size=2g \
  --mount type=bind,src=/absolute/checkpoint,dst=/checkpoint,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports \
  nachet-export:local --checkpoint /checkpoint --output /exports/run-1
```

The destination must be new and outside the checkpoint. The export writes the
FP32 graph, config, and processor under `onnx-fp32/`. Add `--quantize` to create
`onnx-quant/model_quantized.onnx` with the AVX512 INT8 preset. Check that variant
on the intended hardware and evaluation dataset. Training-state files such as
optimizer state are not export inputs.

## Prepare classifier CAM files

Apply the checkpoint's saved image processor to representative images and save
the resulting finite `float32` array as `pixels.npy`, shaped
`(batch, 3, height, width)`. The helper compares FP32 and FP16 on those exact
pixels. Raw images are not accepted by `--pixels`.

For example, put a small representative set of JPEG crops in a directory and
run the saved processor in the export image. Mount the checkpoint or separate
processor directory at `/processor`; do not substitute a different processor.
This command creates a new file and refuses to overwrite an existing one:

```bash
docker run --rm -i --platform linux/amd64 --network none --read-only \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,exec,size=2g \
  --mount type=bind,src=/absolute/processor,dst=/processor,readonly \
  --mount type=bind,src=/absolute/sample-crops,dst=/images,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports \
  --entrypoint python nachet-export:local - <<'PY'
from pathlib import Path
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor

images = []
for path in sorted(Path("/images").glob("*.jpg")):
    with Image.open(path) as image:
        images.append(image.convert("RGB"))
if not images:
    raise ValueError("No JPEG crops found in /images")
processor = AutoImageProcessor.from_pretrained("/processor", local_files_only=True)
pixels = processor(images=images, return_tensors="np")["pixel_values"]
with open("/exports/pixels.npy", "xb") as destination:
    np.save(destination, pixels.astype(np.float32), allow_pickle=False)
PY
```

```bash
docker run --rm --platform linux/amd64 --network none --read-only \
  --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,exec,size=2g \
  --mount type=bind,src=/absolute/checkpoint,dst=/checkpoint,readonly \
  --mount type=bind,src=/absolute/pixels.npy,dst=/pixels.npy,readonly \
  --mount type=bind,src=/absolute/exports,dst=/exports \
  --entrypoint python nachet-export:local browser_cam.py \
  --onnx /exports/run-1/onnx-fp32/model.onnx --checkpoint /checkpoint \
  --pixels /pixels.npy --output /exports/run-1/browser
```

Successful preparation writes `model.candidate.onnx`,
`classifier_head_<class-count>spp.f32.bin`, and `validation.json`. The head has
one little-endian float32 weight row per class. The report records the supplied
pixels' hash, output checks, and per-image numerical and ranking comparisons.
Release evaluation remains `not_performed`.

By default, FP16 numerical mismatches are reported with a warning and the
candidate artifacts are retained, including when differences are large. Exit
code zero means candidate creation completed, not that the model is accurate.
Add `--strict` to reject changed top-1
predictions or element-wise disagreement in logits or features beyond
`atol=1e-3`, `rtol=1e-2`. Both modes reject inference errors, non-finite outputs,
and interface mismatches. Neither mode approves deployment.

In report schema 3, `output_checks` covers execution and output names, shapes
and types; `fp16_checks` describes numerical agreement on the supplied pixels.
`fp16_mismatch` explains numerical differences. `error` records a failure that
stopped verification, including numerical rejection when `strict` is true.
The script never writes the browser's deployment filename, `model.onnx`.
Release packaging must require separate evaluation and approval before renaming
or publishing a candidate; it must not infer approval from the exit code or
`fp16_checks`. Include the comparison report with the release evidence.

Failed runs preserve diagnostics in a sibling hidden directory ending in
`.partial`; the requested output directory is not installed. Existing outputs
are never overwritten. Fix the input or failure and retry with a new output.
Successful CAM preparation removes intermediate graphs. Inspect retained
`.partial` directories before removing them manually; the script does not
delete diagnostic runs.

## Limits and downstream work

Compare a checkpoint created by another Transformers version against its
training-runtime predictions on identical preprocessed inputs. Numerical
tolerances still need calibration on representative labeled seed images and
the intended browser backend, including CAM quality.

The detector graph keeps its exported pooling behavior. Browser release
packaging must preserve any ONNX external-data files and supply the filenames
expected by its consumer. The classifier release also needs its config and
processor. Mini's current CAM consumer expects a 101-class, 1536-channel head;
other shapes need a compatible consumer.

Argo integration, checkpoint selection, evaluation, the detector browser patch,
release packaging, model cards, and Hugging Face publication are separate work.

## Update dependencies

Use Python 3.12 and the uv version pinned in the Dockerfile:

```bash
uv lock
uv lock --check
```

Review the dependency declarations and generated lockfile together, rebuild
both targets, and rerun the suite. Regenerate the lockfile with uv rather than
editing it by hand. Runtime upgrades also require checkpoint comparisons and
browser checks.
