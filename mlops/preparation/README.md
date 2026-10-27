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

Install the `sam3` group and provide local model weights.

```bash
uv sync --project mlops/preparation --locked --group sam3
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prelabel.py /work/prepared/index.coco.json \
  /work/prepared /work/draft.coco.json \
  --model-path /models/sam3 --model-revision <weights-revision> --device cuda
```

CUDA follows the notebook's BF16 autocast and TF32 settings; CPU uses FP32.
The revision is an operator-provided label for those weights. The source
species supplies the class. Prompts propose object locations, and every box
needs review. Prompt failures and nested boxes retain a reason field.
Invalid boxes are omitted and flagged for review. High-bit images skip
inference and remain marked for review until a normalization policy is chosen.

## Checks

```bash
uv run --project mlops/preparation --no-sync python -m pytest mlops/preparation/tests
```

## Research origins

Adapted from `ai-cfia/nachet-model-ccds`:

- Image conversion: `nachetmodel/tiff_jpg_to_png.py` at `b7ba50b`.
- COCO indexing: `notebooks/1.01_js_init_coco_dataset.ipynb` at `52988ae`.
- SAM3 drafts: `notebooks/1.02_js_pre_annotate_sam3_hf.ipynb` at `b7ba50b`.

Copyright (c) 2025 AI @ Canadian Food Inspection Agency (CFIA).
See the [MIT licence](../../LICENSE).
