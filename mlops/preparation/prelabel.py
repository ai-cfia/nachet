"""Generate draft COCO boxes with the SAM3 notebook's prompt and padding policy."""

import argparse
import asyncio
import copy
import hashlib
import io
import json
import math
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from PIL import Image

from prepare_images import save_coco

PROMPTS = ("foreground object", "thick long seed", "insect")
SCORE_THRESHOLD = 0.5
MASK_THRESHOLD = 0.5
# Notebook 1.02 accepts a prompt's result when it has 1 to 9 boxes.
MAX_BOXES = 9
HIGH_BIT_MODES = {"I", "F", "I;16", "I;16B", "I;16L"}


class Prediction(NamedTuple):
    boxes: list[list[float]]
    prompt: str | None = None


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

    def __call__(self, image: Image.Image) -> Prediction:
        """Use the first prompt with 1 to 9 boxes, or the last result for review."""
        for prompt in PROMPTS[:-1]:
            boxes = self._predict_prompt(image, prompt)
            if 0 < len(boxes) <= MAX_BOXES:
                return Prediction(boxes, prompt)
        prompt = PROMPTS[-1]
        return Prediction(self._predict_prompt(image, prompt), prompt)

    def _predict_prompt(self, image: Image.Image, prompt: str) -> list[list[float]]:
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
    """Clip a pixel XYXY box to the image and pad it; None if nothing is left."""
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
    """Add draft boxes using an image-only callable returning a Prediction.

    Prediction boxes use pixel XYXY coordinates; the prompt is optional.
    """
    media_root = media_root.resolve(strict=True)
    return _prelabel(
        coco,
        lambda record: (media_root / record["file_name"]).open("rb"),
        predictor,
        padding=padding,
    )


def prelabel_s3(
    coco: dict, storage, bucket: str, predictor, *, padding: int = 3
) -> dict:
    """Check each prepared PNG's hash before giving its pixels to the predictor."""
    with asyncio.Runner() as runner:

        def open_image(record):
            key, digest = record["file_name"], record["image_sha256"]
            if key != f"png/detection/{digest}.png":
                raise ValueError(f"PNG key does not match image_sha256: {key}")
            data = runner.run(storage.read_image(bucket, key))
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"PNG does not match image_sha256: {key}")
            return io.BytesIO(data)

        return _prelabel(coco, open_image, predictor, padding=padding)


def _prelabel(coco: dict, open_image, predictor, *, padding: int) -> dict:
    """Use the same decoding and annotation policy for local and S3 streams."""
    if coco["annotations"]:
        raise ValueError(
            "Pre-labeling requires an unannotated index; refusing to replace labels"
        )
    result = copy.deepcopy(coco)
    categories = {category["name"]: category["id"] for category in result["categories"]}
    for record in result["images"]:
        category_id = categories[record["sources"][0]["species"]]
        with open_image(record) as stream:
            # PNG's IHDR bit depth is byte 24; Pillow's RGB/RGBA modes hide it.
            header = stream.read(25)
            stream.seek(0)
            with Image.open(stream) as image:
                if image.size != (record["width"], record["height"]):
                    raise ValueError(
                        f"COCO dimensions do not match {record['file_name']}"
                    )
                if image.mode in HIGH_BIT_MODES or (
                    image.format == "PNG" and header[24] == 16
                ):
                    record.update(
                        prelabel_status="needs_review",
                        prelabel_reason="high_bit_depth",
                        prelabel_prompt=None,
                    )
                    continue
                prediction = predictor(image.convert("RGB"))
        boxes = prediction.boxes
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
            prelabel_status=status,
            prelabel_prompt=prediction.prompt,
            prelabel_reason=reason,
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
    parser.add_argument("media_root", help="Local media directory or s3://<bucket>")
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument(
        "--model-revision",
        required=True,
        help="Operator-provided revision label for the local weights",
    )
    parser.add_argument("--device", required=True, choices=["cpu", "cuda"])
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument("--endpoint-url", help="S3 endpoint; HTTPS unless --allow-http")
    parser.add_argument("--region", help="Region for S3 input")
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow a trusted HTTP endpoint"
    )
    args = parser.parse_args(argv)
    if args.padding < 0:
        parser.error("padding must be non-negative")
    source = urlsplit(args.media_root)
    storage = None
    if source.scheme == "s3":
        if (
            not source.netloc
            or source.path not in ("", "/")
            or source.query
            or source.fragment
        ):
            parser.error("S3 media root must be s3://<bucket> without a key prefix")
        if not args.endpoint_url or not args.region:
            parser.error("S3 input requires --endpoint-url and --region")
        from s3_storage import create_storage

        try:
            storage = create_storage(
                args.endpoint_url, args.region, allow_http=args.allow_http
            )
        except ValueError as error:
            parser.error(str(error))
    elif args.endpoint_url or args.region or args.allow_http:
        parser.error("S3 options require an s3://<bucket> media root")
    try:
        predictor = Sam3Predictor(args.model_path, args.device)
        coco = json.loads(args.index.read_text())
        if storage is not None:
            result = prelabel_s3(
                coco, storage, source.netloc, predictor, padding=args.padding
            )
        else:
            result = prelabel(
                coco, Path(args.media_root), predictor, padding=args.padding
            )
    finally:
        if storage is not None:
            storage.close()
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
