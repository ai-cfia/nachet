# Dataset preparation

Convert intake images to PNGs and build a COCO image index.
Use Python 3.12 and run commands from the repository root.

```bash
uv sync --project mlops/preparation --locked
```

## Convert and index

Provide a CSV with `path,species` columns. Paths are relative to the source
root. Optional source fields such as batch, tray and specimen group are kept
in `images[].sources`. A known specimen group cannot cross splits; use IDs
that are unique across the intake. Leave unknown splits empty until review.

```csv
path,species,split,batch,tray,specimen_group
batch-01/tray-a/a.tiff,Avena fatua,train,batch-01,tray-a,seed-a
```

```bash
uv run --project mlops/preparation --no-sync python \
  mlops/preparation/prepare_images.py \
  /work/raw intake.csv /work/prepared --code-revision <commit>
```

Outputs are `index.coco.json` and `png/detection/<sha256>.png`. Raw files stay
unchanged. Existing PNGs keep their bytes. TIFF/JPEG inputs become PNGs;
unsupported high-bit colour TIFFs and multi-frame inputs fail with the
filename. Compatible 16-bit grayscale is preserved. An encoder update can
change PNG keys for the same raw image.

Source records keep the raw SHA-256, the legacy raw-byte MD5 and available
CSV fields. Identical PNGs share one image record while retaining their
sources. Named working outputs allow identical retries; use a fresh output
path when the intake or settings change.

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
