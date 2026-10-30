"""Generate draft COCO boxes with the SAM3 notebook's prompt and padding policy."""

import argparse
import copy
import json
import math
from pathlib import Path

from PIL import Image

from prepare_images import save_coco

PROMPTS = ("foreground object", "thick long seed", "insect")
SCORE_THRESHOLD = 0.5
MASK_THRESHOLD = 0.5
# Notebook 1.02 accepts a prompt's result when it has 1 to 9 boxes.
MAX_BOXES = 9
HIGH_BIT_MODES = {"I", "F", "I;16", "I;16B", "I;16L"}


class Sam3Predictor:
    def __init__(self, model_path: Path, device: str):
        # Imported here so the rest of the module works without the sam3 group.
        import torch
        from transformers import Sam3Model, Sam3Processor

        self.torch = torch
        self.device = device
        if device == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        self.model = (
            Sam3Model.from_pretrained(model_path, local_files_only=True)
            .to(device)
            .eval()
        )
        self.processor = Sam3Processor.from_pretrained(
            model_path, local_files_only=True
        )

    def __call__(self, image: Image.Image, prompt: str) -> list[list[float]]:
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(
            self.device
        )
        with (
            self.torch.inference_mode(),
            self.torch.autocast(
                self.device, dtype=self.torch.bfloat16, enabled=self.device == "cuda"
            ),
        ):
            outputs = self.model(**inputs)
        result = self.processor.post_process_instance_segmentation(
            outputs,
            threshold=SCORE_THRESHOLD,
            mask_threshold=MASK_THRESHOLD,
            target_sizes=inputs.get("original_sizes").tolist(),
        )[0]
        return result["boxes"].detach().cpu().tolist()


def coco_box(
    box: list[float], width: int, height: int, padding: int
) -> list[float] | None:
    """Clip a SAM3 XYXY box to the image and pad it; None if nothing is left."""
    if len(box) != 4 or not all(math.isfinite(value) for value in box):
        return None
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(width, x1), min(height, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    # Preserve the notebook's asymmetric policy: p before, 2p after the box.
    left, top = max(0, x0 - padding), max(0, y0 - padding)
    right, bottom = min(width, x1 + 2 * padding), min(height, y1 + 2 * padding)
    return [left, top, right - left, bottom - top]


def contains(outer: list[float], inner: list[float]) -> bool:
    """Whether COCO box `inner` lies within `outer` (notebook's box_in_box_coco)."""
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[0] + outer[2] >= inner[0] + inner[2]
        and outer[1] + outer[3] >= inner[1] + inner[3]
    )


def first_accepted(predictor, image: Image.Image) -> tuple[str, list[list[float]]]:
    """Try the prompts in order; return the first result with 1 to 9 boxes.

    If no prompt is accepted, the last prompt's result is returned for review.
    """
    for prompt in PROMPTS[:-1]:
        boxes = predictor(image, prompt)
        if 0 < len(boxes) <= MAX_BOXES:
            return prompt, boxes
    prompt = PROMPTS[-1]
    return prompt, predictor(image, prompt)


def review_outcome(boxes: list, padded: list) -> tuple[str, str | None]:
    """Return (prelabel_status, prelabel_reason) for one image's detections."""
    if not boxes:
        return "needs_review", "no_detections"
    if len(boxes) > MAX_BOXES:
        return "needs_review", "too_many_detections"
    if len(padded) != len(boxes):
        return "needs_review", "invalid_boxes"
    if any(
        contains(outer, inner)
        for outer in padded
        for inner in padded
        if outer is not inner
    ):
        return "draft", "nested_boxes"
    return "draft", None


def prelabel(coco: dict, media_root: Path, predictor, *, padding: int = 3) -> dict:
    """Return a copy of an unannotated index with draft boxes and review fields."""
    if coco["annotations"]:
        raise ValueError(
            "Pre-labeling requires an unannotated index; refusing to replace labels"
        )
    result = copy.deepcopy(coco)
    categories = {category["name"]: category["id"] for category in result["categories"]}
    media_root = media_root.resolve(strict=True)
    for record in result["images"]:
        category_id = categories[record["sources"][0]["species"]]
        path = media_root / record["file_name"]
        with Image.open(path) as image:
            if image.size != (record["width"], record["height"]):
                raise ValueError(f"COCO dimensions do not match {path}")
            if image.mode in HIGH_BIT_MODES:
                record.update(
                    prelabel_status="needs_review",
                    prelabel_reason="high_bit_depth",
                    prelabel_prompt=None,
                )
                continue
            prompt, boxes = first_accepted(predictor, image.convert("RGB"))
        padded = [
            box
            for box in (
                coco_box(box, record["width"], record["height"], padding)
                for box in boxes
            )
            if box is not None
        ]
        status, reason = review_outcome(boxes, padded)
        record.update(
            prelabel_status=status, prelabel_prompt=prompt, prelabel_reason=reason
        )
        for box in padded:
            # Annotation IDs run across the whole dataset.
            result["annotations"].append(
                {
                    "id": len(result["annotations"]),
                    "image_id": record["id"],
                    "category_id": category_id,
                    "bbox": box,
                    "iscrowd": 0,
                }
            )
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("media_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument(
        "--model-revision",
        required=True,
        help="Operator-provided revision label for the local weights",
    )
    parser.add_argument("--device", required=True, choices=["cpu", "cuda"])
    parser.add_argument("--padding", type=int, default=3)
    args = parser.parse_args(argv)
    if args.padding < 0:
        parser.error("padding must be non-negative")
    predictor = Sam3Predictor(args.model_path, args.device)
    result = prelabel(
        json.loads(args.index.read_text()),
        args.media_root,
        predictor,
        padding=args.padding,
    )
    result["info"]["prelabel"] = {
        "model_path": str(args.model_path),
        "model_revision": args.model_revision,
        "padding": args.padding,
        "device": args.device,
        "precision": "bf16" if args.device == "cuda" else "fp32",
    }
    save_coco(args.output, result)
    boxes, images = len(result["annotations"]), len(result["images"])
    print(f"Wrote {boxes} draft boxes for {images} images")


if __name__ == "__main__":
    main()
