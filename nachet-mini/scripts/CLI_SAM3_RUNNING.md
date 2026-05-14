# Run SAM 3 Locally in CLI (HuggingFace transformers)

This guide shows how to test Meta's **SAM 3** text-promptable detector against a single image, as a precursor to deciding whether to swap it in for the current RT-DETR detector in nachet-mini's Web Worker pipeline.

The CLI mirrors `run_onnx_cli.py`: same `--image`, `--threshold`, `--display-scale` flags, same OpenCV visualization. The new piece is `--prompt`, which is the concept text fed into SAM 3 (e.g. `"seed"`).

## Prerequisites

- Python 3.10+
- A test image (example: `test-image.png`)
- A Hugging Face account with access to `facebook/sam3` if it is gated (`huggingface-cli login`)

## Setup

From `nachet-mini/`:

```bash
cd nachet-mini
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch transformers pillow opencv-python numpy
```

If your installed `transformers` doesn't yet include SAM 3 support, install from source:

```bash
pip install --upgrade "git+https://github.com/huggingface/transformers"
```

## Run

```bash
cd nachet-mini
source .venv/bin/activate
python scripts/run_sam3_cli.py --image test-image.png --prompt "seed" --threshold 0.5
```

Useful flags:

- `--prompt "weed seed"` — try alternate concept text
- `--threshold 0.3` — lower to surface more candidates
- `--device cpu` — force CPU (default: cuda if available, else cpu)
- `--no-display` — skip the OpenCV window (headless / CI)

## Expected output

- Prints the chosen device and prompt
- Lists each detection as `xyxy + score`
- Opens an OpenCV window named `sam3 detections` with magenta boxes

## Comparing against the current detector

Run the same image through both scripts and eyeball the difference:

```bash
python scripts/run_onnx_cli.py --image test-image.png --threshold 0.3
python scripts/run_sam3_cli.py  --image test-image.png --prompt "seed" --threshold 0.3
```

Things to look for:

- Per-seed recall (does SAM 3 miss seeds RT-DETR catches?)
- False positives (does it pick up debris/shadows?)
- Box tightness (SAM 3 boxes are derived from masks, so they should be tight)
- Runtime — SAM 3 is much heavier than RT-DETR

## Troubleshooting

### Gated model / 401 from Hugging Face

`huggingface-cli login` and accept the model terms on the model page.

### `Sam3*` classes not found / unknown model type

Your `transformers` is too old. Reinstall from source (see Setup).

### No detections

- Lower `--threshold` (try `0.2`).
- Try a more specific or more generic prompt (`"seed"`, `"grain"`, `"small round object"`).
- Confirm the image is what you expect — `--no-display` prints all detections to stdout.

### CUDA OOM

Use `--device cpu`. SAM 3 needs significant VRAM for high-resolution inputs.

## Out of scope

This script is a validation tool only. Wiring SAM 3 into `src/inference/worker.ts` and `models.ts` `DETECTOR_MODELS` will be a follow-up once we know it produces usable boxes on real seed images and once ONNX / transformers.js support is confirmed.
