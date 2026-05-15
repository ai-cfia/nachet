"""Run Meta SAM 3 text-promptable detection on a single image.

Mirrors the CLI shape of run_onnx_cli.py so the two scripts are interchangeable
on the same test images. Loads facebook/sam3 via HuggingFace transformers
(PyTorch), runs Promptable Concept Segmentation against a text prompt
(default: "seed"), and visualizes the resulting boxes with OpenCV.

Example:
    python run_sam3_cli.py --image test-image.png --prompt "seed" --threshold 0.5
"""

from pathlib import Path
import argparse
import numpy as np
from PIL import Image
import cv2
import torch
from transformers import AutoTokenizer
from transformers.models.sam3.image_processing_sam3 import Sam3ImageProcessor
from transformers.models.sam3.modeling_sam3 import Sam3Model
from transformers.models.sam3.processing_sam3 import Sam3Processor

MODEL_ID = "facebook/sam3"
IMAGE_PATH = "test-image.png"
PROMPT = "seed"
THRESHOLD = 0.5
DISPLAY_SCALE = 2.0


def parse_args():
    parser = argparse.ArgumentParser(description="Run SAM 3 text-promptable detection")
    parser.add_argument("--model", default=MODEL_ID, help="HF model id (default: facebook/sam3)")
    parser.add_argument("--image", default=IMAGE_PATH)
    parser.add_argument("--prompt", default=PROMPT, help="Concept text prompt (default: 'seed')")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--display-scale", type=float, default=DISPLAY_SCALE)
    parser.add_argument("--device", default=None, help="cuda | cpu (auto if omitted)")
    parser.add_argument("--no-display", action="store_true", help="Skip the OpenCV window")
    return parser.parse_args()


def mask_to_box(mask: np.ndarray):
    """Compute xyxy bbox from a 2D boolean/0-1 mask. Returns None for empty masks."""
    ys, xs = np.where(mask > 0)
    if ys.size == 0 or xs.size == 0:
        return None
    return np.array([xs.min(), ys.min(), xs.max(), ys.max()], dtype=np.float32)


def extract_detections(outputs, processor, target_size, threshold):
    """Pull (boxes_xyxy, scores) out of SAM 3 outputs.

    SAM 3's transformers API exposes instance segmentation via the processor's
    post-processing helper. We prefer that path; if it isn't available in the
    installed version, we fall back to thresholding raw mask logits and deriving
    boxes from each connected component.
    """
    target_sizes = [target_size]  # (H, W) per HF convention

    post = getattr(processor, "post_process_instance_segmentation", None)
    if post is not None:
        try:
            results = post(outputs, threshold=threshold, target_sizes=target_sizes)
            r = results[0]
            scores = np.asarray(r.get("scores", []))
            boxes = r.get("boxes", None)
            masks = r.get("masks", None)

            if boxes is not None and len(boxes) > 0:
                boxes_np = np.asarray(boxes)
                return boxes_np, scores

            if masks is not None and len(masks) > 0:
                masks_np = np.asarray(masks)
                derived = []
                kept_scores = []
                for i, m in enumerate(masks_np):
                    b = mask_to_box(np.asarray(m))
                    if b is not None:
                        derived.append(b)
                        kept_scores.append(scores[i] if i < len(scores) else 1.0)
                if derived:
                    return np.stack(derived), np.asarray(kept_scores)
        except Exception as e:
            print(f"[warn] post_process_instance_segmentation failed: {e}; falling back.")

    # Fallback: raw mask logits → threshold → connected components → boxes.
    pred_masks = getattr(outputs, "pred_masks", None)
    if pred_masks is None:
        raise RuntimeError(
            "Could not extract detections: no post_process_instance_segmentation "
            "and outputs has no pred_masks. Inspect outputs:\n"
            f"  fields: {list(outputs.keys()) if hasattr(outputs, 'keys') else dir(outputs)}"
        )

    masks_t = pred_masks
    if masks_t.ndim == 5:
        masks_t = masks_t[0]
    masks_np = masks_t.detach().float().cpu().numpy()

    h, w = target_size
    derived, kept_scores = [], []
    for m in masks_np:
        # Take a 2D mask: collapse extra dims by max.
        while m.ndim > 2:
            m = m.max(axis=0)
        # Resize to target size if needed.
        if m.shape != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
        binary = (m > 0).astype(np.uint8)
        if binary.sum() == 0:
            continue
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for lbl in range(1, n_labels):
            x, y, bw, bh, area = stats[lbl]
            if area < 4:
                continue
            score = float(m[labels == lbl].mean())
            if score < threshold:
                continue
            derived.append([x, y, x + bw, y + bh])
            kept_scores.append(score)

    if not derived:
        return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.float32)
    return np.asarray(derived, dtype=np.float32), np.asarray(kept_scores, dtype=np.float32)


def main():
    args = parse_args()

    if not Path(args.image).exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading {args.model} on {device}...")

    # Build Sam3Processor manually from its parts. AutoProcessor /
    # Sam3Processor.from_pretrained on facebook/sam3 resolves to the *video*
    # processor, which doesn't accept text=. Constructing it explicitly forces
    # the image variant.
    image_processor = Sam3ImageProcessor.from_pretrained(args.model)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    processor = Sam3Processor(image_processor=image_processor, tokenizer=tokenizer)
    model = Sam3Model.from_pretrained(args.model).to(device).eval()

    pil_img = Image.open(args.image).convert("RGB")
    orig_w, orig_h = pil_img.size
    print(f"Image: {args.image} ({orig_w}x{orig_h})")
    print(f"Prompt: {args.prompt!r}  threshold={args.threshold}")

    inputs = processor(images=pil_img, text=args.prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    boxes, scores = extract_detections(
        outputs, processor, target_size=(orig_h, orig_w), threshold=args.threshold
    )

    print(f"\nDetections ({len(boxes)}):")
    for i, (box, score) in enumerate(zip(boxes, scores)):
        x1, y1, x2, y2 = box
        print(f"  [{i}] xyxy=({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})  score={score:.4f}")

    if args.no_display or len(boxes) == 0:
        if len(boxes) == 0:
            print("(no boxes to display)")
        return

    img = cv2.imread(args.image)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    display_w = int(orig_w * args.display_scale)
    display_h = int(orig_h * args.display_scale)
    img_big = cv2.resize(img, (display_w, display_h), interpolation=cv2.INTER_LINEAR)

    for box, score in zip(boxes, scores):
        x1, y1, x2, y2 = (
            int(box[0] * args.display_scale),
            int(box[1] * args.display_scale),
            int(box[2] * args.display_scale),
            int(box[3] * args.display_scale),
        )
        cv2.rectangle(img_big, (x1, y1), (x2, y2), (255, 0, 255), 4)
        text_y = max(y1 - 8, 20)
        cv2.putText(
            img_big,
            f"{args.prompt}:{score:.2f}",
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 255),
            2,
        )

    cv2.namedWindow("sam3 detections", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("sam3 detections", min(display_w, 1600), min(display_h, 1200))
    cv2.imshow("sam3 detections", img_big)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
