# Dataset preparation

Convert a seed-image collection into SHA-256-named PNGs and a COCO image index
for pre-labeling and review. Use `prepare_s3.py` for originals in S3, or
`prepare_images.py` for a local collection. Run these Python 3.12 commands from
the repository root.

```bash
uv sync --project mlops/preparation --locked
```

## Convert originals from S3

`prepare_s3.py` reads originals under `raw/` through the shared blob package,
converts each image in memory and uploads it to `png/detection/<sha256>.png` in
the same bucket. It uses the local converter's settings and source records.
Neither originals nor generated PNGs are saved locally.

```bash
CODE_REVISION=$(git rev-parse HEAD)
uv sync --project mlops/preparation --locked --group storage
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_s3.py /work/prepared \
  --bucket training-datasets --endpoint-url https://s3.example.test \
  --region us-east-1 --raw-prefix raw/collection-01 \
  --code-revision "$CODE_REVISION"
```

The S3 keys below the collection prefix must follow the species/split layout
described below. Source paths stay relative to that prefix. Empty species
folders are retained when the listing includes directory markers for them.
The index records hashes of the original bytes read; it does not require
ingestion-specific hash metadata. Originals must already be in S3 and remain
unchanged during a run.

Only `index.coco.json` is saved in the output directory, after every upload
succeeds. On failure, already uploaded PNGs remain in S3; a retry uses the same
hash keys. It rereads and converts the originals, so this is restartable rather
than a resumable conversion. Use a new output directory for a changed collection.

All writers to `png/detection/` must use the PNG byte hash as the filename. The
uploader requests create-only writes, but some S3-compatible stores ignore that
condition and upload the same bytes again on retries. It does not read back
existing PNGs or protect against a writer that puts other bytes under a hash key.

The COCO source records do not create database mappings.

Credentials come from the AWS credential chain. For a private CA, set
`AWS_CA_BUNDLE`. Use `--allow-http` only with a trusted test endpoint.

## Collection layout

Species folders sit directly under the collection or inside a split folder.
Each species folder's name becomes a COCO category. Split folders named
`Training`/`Train`, `Validation`/`Val` or `Test`/`Testing` are recognized in any
case. Species folders directly under the collection stay unassigned.

```text
Collection/
  Training/
    Avena fatua/batch-01/tray-a/a.tiff
  Validation/
    Avena fatua/b.tiff
  Zea mays/
    new-image.jpg
```

Images are found recursively under each species folder, so batch and tray
folders stay in the recorded path. Hidden files and folders are skipped, as are
files that are not TIFF, JPEG or PNG. An image directly under the collection or
a split folder is an error.

Split folders directly inside a species folder are rejected; check that you
passed the collection itself, not its parent. Species names that differ only
in case are also rejected.

## Convert and index

Set `CODE_REVISION` to the source revision used for conversion.

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py \
  /work/raw/Collection /work/prepared \
  --raw-prefix raw/Collection --code-revision "$CODE_REVISION"
```

The output directory must be outside the collection. It receives
`index.coco.json` and `png/detection/<sha256>.png`.

In the example, the two Avena images keep their train and validation splits and
the Zea image gets `split: null`. The command never creates a random split. If
a collection has no split folders but belongs to one split, pass
`--split train`, `validation` or `test`. `--split` is refused when split folders
are present.

All images go into one index with one category list, so category IDs are the
same across splits. IDs are only meaningful within one index; match separately
generated indexes by category name.

## Conversion

Raw files are never modified. PNG inputs are copied byte for byte. TIFF and JPEG
conversion uses the research script's OpenCV `IMREAD_UNCHANGED` flag and default
PNG encoding. Both 16-bit grayscale and 16-bit RGB TIFFs keep their depth.
Converted files follow OpenCV's colour handling and do not copy ICC profiles.
Grayscale TIFFs with alpha, signed pixel values, multi-frame images and TIFF
samples above 16 bits fail with the filename.

PNG names are the SHA-256 of the PNG bytes, so an encoder change can
rename the PNG for an unchanged raw image.

## Index contents

Each image records `image_sha256`, the SHA-256 of its PNG bytes. This is the
same hash used in `file_name`; it identifies the PNG rather than the raw file.

Each image's `sources` list records the species, the path relative to the
collection, the raw file's SHA-256 and its legacy MD5. Batch, tray and specimen
meaning is not inferred from folder names. With `--raw-prefix`, each source
also gets `raw_key`, the expected S3 key under `raw/`. The command does not
upload files or check whether those keys exist in S3.

Identical PNGs share one image record and keep every source path. Identical
PNGs with different species or different splits fail, which stops an exact
duplicate from appearing in both training and validation. Different
photographs of the same specimen are not detected.

Outputs can be regenerated: a rerun that produces the same bytes succeeds, and a
run that would change an existing file fails. Use a new output directory when
the collection or settings change.

## Pre-label with SAM3

`prelabel.py` adds draft boxes to the COCO index for review in FiftyOne.
Install the `sam3` group and provide a local directory containing the SAM3
weights. Set `MODEL_REVISION` to their revision label; it is recorded in the
COCO file. The command does not download weights.

```bash
uv sync --project mlops/preparation --locked --group sam3
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  /work/prepared /work/draft.coco.json \
  --model-path /models/sam3 --model-revision "$MODEL_REVISION" --device cuda
```

For PNGs already in S3, install the `storage` group as well and pass the bucket
root instead of a local media directory:

```bash
uv sync --project mlops/preparation --locked --group sam3 --group storage
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  s3://training-datasets /work/draft.coco.json \
  --endpoint-url https://s3.example.test --region us-east-1 \
  --model-path /models/sam3 --model-revision "$MODEL_REVISION" --device cuda
```

S3 input reads one PNG into memory and checks its key and SHA-256 before
decoding. A missing object, hash mismatch or dimension mismatch stops the run.
PNGs are not saved locally. The bucket root contains the `png/detection/` keys
from COCO; a key prefix in the S3 media-root argument is refused. Credentials
and private-CA settings are described under "Convert originals from S3".

For each image, the command tries the notebook's prompts in order:
"foreground object", "thick long seed", then "insect". It stops at the first
prompt returning 1 to 9 boxes. Boxes keep the species recorded in the index.
Padding follows the notebook: `p` pixels on the left and top, `2p` on the
right and bottom, clipped to the image. `--padding` sets `p` (default: 3).

The Python `prelabel()` function accepts a `predictor(image)` callable returning
`Prediction(boxes, prompt=None)`. Boxes use pixel XYXY coordinates. SAM3 handles
its prompts internally; other predictors can leave `prompt` unset. The CLI
currently loads SAM3.

CUDA uses BF16 autocast and TF32; CPU uses FP32. `--model-revision` is a label
you choose for the local weights, recorded in `info.prelabel`.

Each image records its `prelabel_status`, `prelabel_prompt` and
`prelabel_reason`. The prompt is the last one attempted, or `null` if
the predictor does not use prompts or inference was skipped.

| Status | Reason | Meaning |
| --- | --- | --- |
| `draft` | `null` | A prompt returned 1 to 9 valid boxes. |
| `draft` | `nested_boxes` | One padded box lies inside another. |
| `needs_review` | `no_detections` | All prompts failed the count check; the last returned no boxes. |
| `needs_review` | `too_many_detections` | All prompts failed the count check; the last returned at least 10 boxes. |
| `needs_review` | `invalid_boxes` | A prompt returned 1 to 9 boxes, but invalid geometry was dropped. |
| `needs_review` | `high_bit_depth` | High-bit image; inference skipped pending a normalization policy. |

Both statuses require human review. The command refuses an index that already
has annotations. Output is written after the full batch; an interrupted run
currently starts again from the beginning.

## Register for review

`register_fiftyone.py` imports the draft COCO into a new persistent FiftyOne
dataset. It reads only the COCO file. Set `--server-media-root` to the path
where the FiftyOne server can read the `png/detection/...` files; the import
worker does not need access to that path. The command does not copy or upload
images.

```bash
uv sync --project mlops/preparation --locked --group fiftyone
export FIFTYONE_DATABASE_URI='<mongo-uri>'
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/register_fiftyone.py collection-01-review \
  /work/draft.coco.json --server-media-root /srv/datasets
```

Use the server's MongoDB URI and, if customized, `FIFTYONE_DATABASE_NAME`.
The command requires `FIFTYONE_DATABASE_URI` and refuses an implicit local
database. Draft boxes go in `draft_boxes`. Source records, split assignments
and the pre-label fields described above stay on each sample. `source_species`
copies the first source's species for filtering, or stays `null` when it is
unknown. It records the original species separately from reviewed box labels.
`object_key` keeps the PNG key, and `image_sha256` copies its hash from the
COCO image record. Each input image must include this field; the import does
not read image bytes to recalculate it. Raw-file hashes stay in `sources`.
`dataset.info` keeps the COCO `info` block.
Images imported before pre-labeling get `prelabel_status: "unannotated"`.

Existing dataset names are refused so a rerun cannot overwrite review work.
An import uses a temporary `preparation-import-*` name and renames the dataset
only after success. A caught failure deletes that temporary dataset. A killed
process can leave it behind, but a retry uses a new temporary name. Remove a
leftover only after confirming its job has stopped; keep review datasets.

## Runtime images

The Dockerfile uses `mlops/` as its build context. The `cpu` target contains
conversion and upload commands, `sam3` adds CUDA-enabled PyTorch and
pre-labeling, and `registration` adds the FiftyOne SDK. Tests run during the
build without network access. Weights and credentials are supplied at runtime.

```bash
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target cpu -t nachet-preparation-cpu:local mlops
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target sam3 -t nachet-preparation-sam3:local mlops
docker build --platform linux/amd64 -f mlops/preparation/Dockerfile \
  --target registration -t nachet-preparation-registration:local mlops
```

The SAM3 build checks for a CUDA-enabled PyTorch and the required SAM3 classes.
Actual GPU execution depends on the cluster's NVIDIA driver and model weights.
Published images are `ghcr.io/ai-cfia/nachet-preparation-{cpu,sam3,registration}`.
Use an immutable image tag or digest for a workflow run.
Copy each published digest from the CPU, SAM3 and registration builds in one
successful Actions run into `CPU_IMAGE`, `SAM3_IMAGE` and `REGISTRATION_IMAGE`.
Set `CODE_REVISION` to that run's checked-out commit. Pull-request builds use
the tested merge commit, which can differ from the PR head.

## Argo workflow

`mlops/workflows/preparation-workflow-template.yaml` runs three steps:

```text
S3 originals -> convert/upload PNGs -> SAM3 reads S3 -> register in FiftyOne
```

Conversion uses the CPU image. Pre-labeling requests one NVIDIA GPU and uses
the existing per-node training mutex. Only conversion and pre-labeling receive
the storage Secret; registration receives the FiftyOne database Secret.

Provide an RWX working PVC in `argo-workflows` for the index and draft COCO
files, and a read-only model PVC with SAM3 weights. Images stay in S3. Each run
writes under `/workspace/<workflow-name>/`; remove that directory after checking
the result. A failed pre-labeling step restarts the batch.

The workflow references existing Secrets in its own namespace. Howard/Vault
owns their values and the cluster's network/storage configuration. The S3
bucket root must match FiftyOne's `server-media-root`; check the deployed media
mount before submitting a run. This template does not create buckets, Secrets,
database tables or model weights.

```bash
argo submit -n argo-workflows --from workflowtemplate/nachet-preparation \
  -p cpu-image="ghcr.io/ai-cfia/nachet-preparation-cpu:$REVISION" \
  -p sam3-image="ghcr.io/ai-cfia/nachet-preparation-sam3:$REVISION" \
  -p registration-image="ghcr.io/ai-cfia/nachet-preparation-registration:$REVISION" \
  -p code-revision="$REVISION" -p dataset-name=collection-01-review \
  -p raw-prefix=raw/collection-01 -p bucket=training-datasets \
  -p endpoint-url=https://s3.example.test -p region=us-east-1 \
  -p storage-secret="$STORAGE_SECRET" -p fiftyone-secret="$FIFTYONE_SECRET" \
  -p workspace-pvc="$WORKSPACE_PVC" -p model-pvc="$MODEL_PVC" \
  -p model-revision="$MODEL_REVISION" -p server-media-root="$SERVER_MEDIA_ROOT"
```

The workflow ends at registration for human review. Reviewed export, release
publication and training use their own components.

## Checks

```bash
uv sync --project mlops/preparation --locked --group storage
uv run --project mlops/preparation --no-sync python -m pytest mlops/preparation/tests
```

The SDK tests use FiftyOne 1.22.1 and a disposable MongoDB. They cover registration,
interrupted imports and the workflow's command arguments, using the shared
storage provider with a fake S3 SDK and supplied predictions. The workflow test
checks source paths, hashes, boxes and splits through all three steps and retries.

```bash
uv sync --project mlops/preparation --locked --group fiftyone --group storage
PREPARATION_TEST_MONGO_URI='<disposable-mongo-uri>' \
  uv run --project mlops/preparation --no-sync python -m pytest \
  mlops/preparation/integration_tests -q
```

The deployed FiftyOne media mount and live S3 still need checking.

## Research origins

Adapted from `ai-cfia/nachet-model-ccds`:

- Image conversion: `nachetmodel/tiff_jpg_to_png.py` at `b7ba50b`.
- COCO indexing: `notebooks/1.01_js_init_coco_dataset.ipynb` at `52988ae`.
- SAM3 drafts: `notebooks/1.02_js_pre_annotate_sam3_hf.ipynb` at `b7ba50b`.

Copyright (c) 2025 AI @ Canadian Food Inspection Agency (CFIA).
See the [MIT licence](../../LICENSE).
