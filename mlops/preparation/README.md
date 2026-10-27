# Dataset preparation

`prepare_images.py` converts a folder of seed images into SHA-256-named PNGs
and a COCO image index that later steps use for pre-labeling and review. It is
a standalone uv project on Python 3.12. Run the commands below from the
repository root.

```bash
uv sync --project mlops/preparation --locked
```

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

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py \
  /work/raw/Collection /work/prepared \
  --raw-prefix raw/Collection --code-revision <commit>
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
inputs are re-encoded as PNG, and 16-bit grayscale stays 16-bit. CMYK inputs are
converted to RGB, which can change colour values. High-bit colour TIFFs and
multi-frame images fail with the filename until a conversion policy is agreed.

PNG names are the SHA-256 of the PNG bytes, so a Pillow encoder change can
rename the PNG for an unchanged raw image.

## Index contents

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
weights. The command does not download weights.

```bash
uv sync --project mlops/preparation --locked --group sam3
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  /work/prepared /work/draft.coco.json \
  --model-path /models/sam3 --model-revision <weights-revision> --device cuda
```

For each image, the command tries the notebook's prompts in order:
"foreground object", "thick long seed", then "insect". It stops at the first
prompt returning 1 to 9 boxes. Boxes keep the species recorded in the index.
Padding follows the notebook: `p` pixels on the left and top, `2p` on the
right and bottom, clipped to the image. `--padding` sets `p` (default: 3).

CUDA uses BF16 autocast and TF32; CPU uses FP32. `--model-revision` is a label
you choose for the local weights, recorded in `info.prelabel`.

Each image records its `prelabel_status`, `prelabel_prompt` and
`prelabel_reason`. The prompt is the last one attempted, or `null` if
inference was skipped.

| Status | Reason | Meaning |
| --- | --- | --- |
| `draft` | `null` | A prompt returned 1 to 9 valid boxes. |
| `draft` | `nested_boxes` | One padded box lies inside another. |
| `needs_review` | `no_detections` | All prompts failed the count check; the last returned no boxes. |
| `needs_review` | `too_many_detections` | All prompts failed the count check; the last returned at least 10 boxes. |
| `needs_review` | `invalid_boxes` | A prompt returned 1 to 9 boxes, but invalid geometry was dropped. |
| `needs_review` | `high_bit_depth` | High-bit grayscale image; inference skipped pending a normalization policy. |

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
and the pre-label fields described above stay on each sample. `object_key`
keeps the PNG key, and `dataset.info` keeps the COCO `info` block.

Existing dataset names are refused so a rerun cannot overwrite review work.
An import uses a temporary `preparation-import-*` name and renames the dataset
only after success. A caught failure deletes that temporary dataset. A killed
process can leave it behind, but a retry uses a new temporary name. Remove a
leftover only after confirming its job has stopped; keep review datasets.

## Checks

```bash
uv run --project mlops/preparation --no-sync python -m pytest mlops/preparation/tests
```

The SDK checks need the `fiftyone` group and a disposable MongoDB instance.
CI starts its own test database; cluster deployment settings stay in
`howard-on-prem`.

```bash
PREPARATION_TEST_MONGO_URI='<disposable-mongo-uri>' \
  uv run --project mlops/preparation --no-sync python -m pytest \
  mlops/preparation/integration_tests/test_fiftyone_registration.py -q
```

## Research origins

Adapted from `ai-cfia/nachet-model-ccds`:

- Image conversion: `nachetmodel/tiff_jpg_to_png.py` at `b7ba50b`.
- COCO indexing: `notebooks/1.01_js_init_coco_dataset.ipynb` at `52988ae`.
- SAM3 drafts: `notebooks/1.02_js_pre_annotate_sam3_hf.ipynb` at `b7ba50b`.

Copyright (c) 2025 AI @ Canadian Food Inspection Agency (CFIA).
See the [MIT licence](../../LICENSE).
