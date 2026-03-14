# Run ONNX Model Locally in CLI (onnxruntime)

This guide shows how to run an ONNX object-detection model locally from the command line using `onnxruntime`.

It includes:

- Local Python environment setup
- Required dependencies
- A ready-to-run CLI script
- Common troubleshooting steps

## Prerequisites

- Linux shell (examples use bash)
- Python 3.10+
- An ONNX model file (example: `model.onnx`)
- A test image (example: `test-image.png`)

## Quick Setup

From the `nachet-mini/` folder:

```bash
cd nachet-mini
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install onnxruntime numpy pillow opencv-python
```

## File Layout

Use this minimal layout:

```text
nachet-mini/
|-- model.onnx
|-- test-image.png
`-- run_onnx_cli.py
```

## Create the CLI Runner

The runner script is a standalone file:

- `nachet-mini/run_onnx_cli.py`

You can inspect the CLI options with:

```bash
cd nachet-mini
source .venv/bin/activate
python run_onnx_cli.py --help
```

## Run the Script

```bash
cd nachet-mini
source .venv/bin/activate
python run_onnx_cli.py
```

Run with optional crop classification:

Expected behavior:

- Prints input and output tensor metadata
- Prints each output tensor shape
- Prints decoded boxes and confidence scores
- Opens an OpenCV window named `detections` with drawn bounding boxes

## Optional: Headless Environment Notes

If you run in a headless shell (no GUI), OpenCV display calls will fail. In that case, replace the display section with image write output:

```python
cv2.imwrite("detections-output.png", img_big)
print("Saved detections-output.png")
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'onnxruntime'`

```bash
source .venv/bin/activate
pip install onnxruntime
```

### `Could not read image: test-image.png`

- Verify file path and file name.
- Confirm the image is in `nachet-mini/` or pass `--image <path>`.

### ONNX input shape mismatch

- Check the printed model input metadata from the script.
- Ensure preprocessing matches the model contract:
  - input size (`MODEL_W`, `MODEL_H` for detector)
  - channel order (`CHW` vs `HWC`)
  - normalization range (`0-1` or other)

### No detections returned

- Lower `THRESHOLD` (example: `0.25`).
- Confirm output order assumptions (`outputs[0]` logits, `outputs[1]` boxes) match your model.

## Notes for Developers

- Start with `CPUExecutionProvider` for reproducibility.
- Add GPU providers only after CPU path is stable.
- Keep this script as a local validation tool for quick model sanity checks before backend integration.
