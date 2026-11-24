"""Flag pre-labeled COCO images with one-way RT-DETR detector disagreement."""

import argparse
import copy
import json
import logging
from collections import defaultdict
from pathlib import Path

from PIL import Image

from prelabel import _box_iou_xyxy
from prepare_images import save_coco
from progress_logging import log_progress

logger = logging.getLogger(__name__)
RT_SCORE_THRESHOLD = 0.5
MATCH_IOU_THRESHOLD = 0.5
SAM_HIGH_CONF_THRESHOLD = 0.90


class RtDetrPredictor:
    def __init__(self, model_path: Path, device: str):
        # Imported here so the module and tests work without torch/transformers.
        import torch
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.torch = torch
        self.device = device
        self.processor = AutoImageProcessor.from_pretrained(
            model_path, local_files_only=True
        )
        self.model = (
            AutoModelForObjectDetection.from_pretrained(
                model_path, local_files_only=True
            )
            .to(device)
            .eval()
        )

    def __call__(self, image: Image.Image) -> list[list[float]]:
        """Return pixel XYXY boxes above RT_SCORE_THRESHOLD."""
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        result = self.processor.post_process_object_detection(
            outputs,
            threshold=RT_SCORE_THRESHOLD,
            target_sizes=[(image.height, image.width)],
        )[0]
        return result["boxes"].detach().cpu().tolist()


def _coco_to_xyxy(bbox: list[float]) -> list[float]:
    left, top, width, height = bbox
    return [left, top, left + width, top + height]


def _match_boxes(
    sam_boxes: list[list[float]], rt_boxes: list[list[float]]
) -> tuple[set[int], set[int]]:
    """Greedy 1-to-1 IoU matching; return matched index sets (sam_matched, rt_matched)."""
    pairs = [
        (_box_iou_xyxy(sam_box, rt_box), sam_idx, rt_idx)
        for sam_idx, sam_box in enumerate(sam_boxes)
        for rt_idx, rt_box in enumerate(rt_boxes)
    ]
    pairs.sort(key=lambda item: item[0], reverse=True)
    sam_matched: set[int] = set()
    rt_matched: set[int] = set()
    for overlap, sam_idx, rt_idx in pairs:
        if overlap < MATCH_IOU_THRESHOLD:
            break
        if sam_idx in sam_matched or rt_idx in rt_matched:
            continue
        sam_matched.add(sam_idx)
        rt_matched.add(rt_idx)
    return sam_matched, rt_matched


def has_one_way_disagreement(
    annotations: list[dict], rt_boxes: list[list[float]]
) -> bool:
    """Flag unmatched RT-DETR detections or unmatched low-confidence SAM3 boxes."""
    sam_boxes = [_coco_to_xyxy(annotation["bbox"]) for annotation in annotations]
    sam_matched, rt_matched = _match_boxes(sam_boxes, rt_boxes)
    if len(rt_matched) < len(rt_boxes):
        return True
    for idx, annotation in enumerate(annotations):
        if idx in sam_matched:
            continue
        score = annotation.get("score")
        if score is not None and score < SAM_HIGH_CONF_THRESHOLD:
            return True
    return False


def cross_check(coco: dict, media_root: Path, predictor) -> dict:
    """Flag unflagged pre-labeled images that disagree one-way with RT-DETR."""
    result = copy.deepcopy(coco)
    media_root = media_root.resolve(strict=True)
    by_image: dict[int, list[dict]] = defaultdict(list)
    for annotation in result["annotations"]:
        by_image[annotation["image_id"]].append(annotation)

    flagged = 0
    checked = 0
    images = log_progress(
        result["images"],
        logger,
        stage="RT-DETR cross-check",
        total=len(result["images"]),
    )
    for record in images:
        if record.get("prelabel_status") is not None:
            continue
        path = media_root / record["file_name"]
        with Image.open(path) as image:
            rt_boxes = predictor(image.convert("RGB"))
        checked += 1
        if has_one_way_disagreement(by_image[record["id"]], rt_boxes):
            record.update(
                prelabel_status="needs_review",
                prelabel_reason="detector_disagreement",
            )
            flagged += 1
    logger.info("RT-DETR cross-check complete: checked=%d flagged=%d", checked, flagged)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("media_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--device", required=True, choices=["cpu", "cuda"])
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    predictor = RtDetrPredictor(args.model_path, args.device)
    result = cross_check(json.loads(args.index.read_text()), args.media_root, predictor)
    result.setdefault("info", {})["cross_check"] = {
        "model_path": str(args.model_path),
        "device": args.device,
        "rt_score_threshold": RT_SCORE_THRESHOLD,
        "match_iou_threshold": MATCH_IOU_THRESHOLD,
        "sam_high_conf_threshold": SAM_HIGH_CONF_THRESHOLD,
    }
    save_coco(args.output, result)


if __name__ == "__main__":
    main()
