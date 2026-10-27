# Dataset preparation

Convert intake images to PNGs and build a COCO image index.
Use Python 3.12 and run commands from the repository root.

```bash
uv sync --project mlops/preparation --locked
```

## Convert and index

Pass the collection folder. `Training` and `Validation` subfolders are
recognized automatically, ignoring case. Their immediate subfolders are
species. Ordinary species folders directly under the collection keep their
split unassigned. Images are discovered recursively beneath each species;
hidden files and folders are skipped. The output must be outside the input tree.

```text
Collection/
  Training/
    Avena fatua/batch-01/tray-a/a.tiff
  Validation/
    Avena fatua/b.tiff
  Zea mays/
    new-image.jpg
```

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py \
  /work/raw/Collection /work/prepared \
  --raw-prefix raw/Collection --code-revision <commit>
```

The same command handles split, unsplit and mixed collections. In this
example, the two Avena images retain their train/validation assignments and
the new Zea image keeps `split: null`. No random split is created.

For a nonstandard layout, optional `--input SPLIT DIRECTORY` overrides can
select folders relative to the collection root. A whole collection with one
known assignment can use `--split train`, `validation` or `test`; this cannot
override discovered Training/Validation folders or explicit `--input` options.
Arbitrary wrapper folders are not discovered as additional collection roots.

One output contains all selected images, a shared category list and each
image's assignment. Category IDs belong to that output; match independent
indexes by category name. Identical PNGs assigned to different splits fail instead
of crossing the train/validation boundary. This catches exact duplicates,
not different photographs of the same specimen. Specimen grouping still
needs source information and an agreed splitting policy. Independently
generated indexes cannot detect overlaps with each other.

Outputs are `index.coco.json` and `png/detection/<sha256>.png`. Raw files stay
unchanged. Existing PNGs keep their bytes. TIFF/JPEG inputs become PNGs;
unsupported high-bit colour TIFFs and multi-frame inputs fail with the
filename. Compatible 16-bit grayscale is preserved. An encoder update can
change PNG keys for the same raw image.

CMYK inputs are converted to RGB; this can change colour values.

COCO `images[].sources` records the species, original path relative to the
input root, raw SHA-256 and legacy raw-byte MD5. Nested batch/tray folders stay
in the path; their meaning and physical specimen groups are not inferred.
When supplied, `--raw-prefix` adds the matching S3 `raw_key` for each original.
It records the object-key mapping and does not perform an S3 upload.

Identical PNGs share one image record while retaining their source paths.
Conflicting species or split assignments fail. Named working outputs allow
identical retries; use a fresh output path when the collection or settings change.

## Checks

```bash
uv run --project mlops/preparation --no-sync python -m pytest mlops/preparation/tests
```

## Research origins

Adapted from `ai-cfia/nachet-model-ccds`:

- Image conversion: `nachetmodel/tiff_jpg_to_png.py` at `b7ba50b`.
- COCO indexing: `notebooks/1.01_js_init_coco_dataset.ipynb` at `52988ae`.

## Source notice

The original research-source notice is retained below.

```text
MIT License

Copyright (c) 2025 AI @ Canadian Food Inspection Agency (CFIA)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
