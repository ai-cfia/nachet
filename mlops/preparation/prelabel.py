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


class Sam3Predictor:
    def __init__(self, model_path: Path, device: str):
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


def prelabel(coco: dict, media_root: Path, predictor, *, padding: int = 3) -> dict:
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
            if image.mode in {"I", "F", "I;16", "I;16B", "I;16L"}:
                record.update(
                    prelabel_status="needs_review",
                    prelabel_reason="high_bit_depth",
                    prelabel_prompt=None,
                )
                continue
            image = image.convert("RGB")
            for prompt in PROMPTS:
                boxes = predictor(image, prompt)
                if 0 < len(boxes) < 10:
                    break
        record["prelabel_status"] = "draft" if 0 < len(boxes) < 10 else "needs_review"
        record["prelabel_prompt"] = prompt
        record["prelabel_reason"] = None
        if record["prelabel_status"] == "needs_review":
            record["prelabel_reason"] = (
                "no_detections" if not boxes else "too_many_detections"
            )
        candidates = [
            coco_box(box, record["width"], record["height"], padding) for box in boxes
        ]
        padded = [box for box in candidates if box is not None]
        if len(padded) != len(candidates):
            record.update(
                prelabel_status="needs_review", prelabel_reason="invalid_boxes"
            )
        if record["prelabel_status"] == "draft":
            for outer in padded:
                for inner in padded:
                    if outer is inner:
                        continue
                    if (
                        outer[0] <= inner[0]
                        and outer[1] <= inner[1]
                        and outer[0] + outer[2] >= inner[0] + inner[2]
                        and outer[1] + outer[3] >= inner[1] + inner[3]
                    ):
                        record["prelabel_reason"] = "nested_boxes"
        for box in padded:
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
    print(
        f"Wrote {len(result['annotations'])} draft boxes for {len(result['images'])} images"
    )


if __name__ == "__main__":
    main()
