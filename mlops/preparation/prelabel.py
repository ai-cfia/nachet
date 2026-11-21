"""Generate draft COCO boxes with the SAM3 notebook's prompt and padding policy."""

import argparse
import asyncio
import copy
import hashlib
import io
import json
import logging
import math
import os
import re
import tempfile
from contextlib import ExitStack
from itertools import combinations
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from PIL import Image
from semver import Version

from checkpoint_version import (
    compatible_checkpoint,
    compatible_directories,
    parse_version,
    project_version,
)
from prepare_images import save_coco
from progress_logging import log_progress

logger = logging.getLogger(__name__)
PROMPTS = ("foreground object", "thick long seed", "insect")
SCORE_THRESHOLD = 0.5
MASK_THRESHOLD = 0.5
MASK_OVERLAP_THRESHOLD = 0.5
SEED_CHECK_PROMPT = "seed"
SEED_CHECK_SCORE_THRESHOLD = 0.45
SEED_CHECK_IOU_THRESHOLD = 0.4
# Notebook 1.02 accepts a prompt's result when it has 1 to 9 boxes.
MAX_BOXES = 9
HIGH_BIT_MODES = {"I", "F", "I;16", "I;16B", "I;16L"}


class Prediction(NamedTuple):
    boxes: list[list[float]]
    prompt: str | None = None
    scores: list[float] | None = None
    has_overlapping_masks: bool | None = None
    has_low_seed_confidence: bool | None = None


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

    def _encode_image(self, image: Image.Image):
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with (
            self.torch.inference_mode(),
            self.torch.autocast(
                self.device, dtype=self.torch.bfloat16, enabled=self.device == "cuda"
            ),
        ):
            vision_embeds = self.model.get_vision_features(
                pixel_values=inputs["pixel_values"]
            )
        height, width = inputs["original_sizes"][0].tolist()
        return vision_embeds, (height, width)

    def __call__(self, image: Image.Image) -> Prediction:
        """Use the first prompt with 1 to 9 boxes, or the last result for review."""
        if not hasattr(self, "model"):
            for prompt in PROMPTS[:-1]:
                prediction = self._predict_prompt(image, prompt)
                if 0 < len(prediction.boxes) <= MAX_BOXES:
                    return prediction
            return self._predict_prompt(image, PROMPTS[-1])

        vision_embeds, original_size = self._encode_image(image)
        for prompt in PROMPTS[:-1]:
            prediction = self._predict_prompt(
                image,
                prompt,
                vision_embeds=vision_embeds,
                original_size=original_size,
            )
            if 0 < len(prediction.boxes) <= MAX_BOXES:
                if prompt == PROMPTS[0]:
                    seed_prediction = self._predict_prompt(
                        image,
                        SEED_CHECK_PROMPT,
                        vision_embeds=vision_embeds,
                        original_size=original_size,
                        score_threshold=SEED_CHECK_SCORE_THRESHOLD,
                    )
                    low_seed = _has_low_seed_confidence(
                        prediction.boxes,
                        seed_prediction.boxes,
                        seed_prediction.scores or [],
                    )
                    return prediction._replace(has_low_seed_confidence=low_seed)
                return prediction
        return self._predict_prompt(
            image,
            PROMPTS[-1],
            vision_embeds=vision_embeds,
            original_size=original_size,
        )

    def _predict_prompt(
        self,
        image: Image.Image,
        prompt: str,
        *,
        vision_embeds=None,
        original_size: tuple[int, int] | None = None,
        score_threshold: float = SCORE_THRESHOLD,
    ) -> Prediction:
        if vision_embeds is None:
            inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(
                self.device
            )
            height, width = inputs["original_sizes"][0].tolist()
            model_kwargs = inputs
        else:
            text_inputs = self.processor(text=prompt, return_tensors="pt").to(
                self.device
            )
            height, width = original_size
            model_kwargs = {
                "vision_embeds": vision_embeds,
                "input_ids": text_inputs["input_ids"],
                "attention_mask": text_inputs.get("attention_mask"),
            }
        with (
            self.torch.inference_mode(),
            self.torch.autocast(
                self.device, dtype=self.torch.bfloat16, enabled=self.device == "cuda"
            ),
        ):
            outputs = self.model(**model_kwargs)
        result = self.processor.post_process_instance_segmentation(
            outputs,
            threshold=score_threshold,
            mask_threshold=MASK_THRESHOLD,
            target_sizes=None,
        )[0]
        scale = result["boxes"].new_tensor([width, height, width, height])
        boxes = (result["boxes"] * scale).detach().cpu().tolist()
        scores = result["scores"].detach().cpu().tolist()
        has_overlapping_masks = _has_overlapping_masks(result["masks"])
        return Prediction(
            boxes=boxes,
            prompt=prompt,
            scores=scores,
            has_overlapping_masks=has_overlapping_masks,
        )


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


def _has_overlapping_boxes(boxes: list[list[float]]) -> bool:
    """Whether two COCO boxes share positive area."""
    for first, second in combinations(boxes, 2):
        left, top, width, height = first
        other_left, other_top, other_width, other_height = second
        overlap_width = min(left + width, other_left + other_width) - max(
            left, other_left
        )
        overlap_height = min(top + height, other_top + other_height) - max(
            top, other_top
        )
        if overlap_width > 0 and overlap_height > 0:
            return True
    return False


def _has_overlapping_masks(masks) -> bool:
    """Whether two native-grid binary masks share >= MASK_OVERLAP_THRESHOLD of the smaller mask."""
    if len(masks) < 2:
        return False
    flat = masks.flatten(1).float()
    areas = flat.sum(dim=1)
    min_areas = areas.unsqueeze(0).minimum(areas.unsqueeze(1))
    overlap = flat @ flat.T
    overlap.fill_diagonal_(0)
    return bool(
        ((overlap >= MASK_OVERLAP_THRESHOLD * min_areas) & (min_areas > 0)).any().item()
    )


def _box_iou_xyxy(first: list[float], second: list[float]) -> float:
    """Intersection over union for two pixel XYXY boxes."""
    inter_w = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    inter_h = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    area_b = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = area_a + area_b - inter
    return inter / union if union > 0.0 else 0.0


def _has_low_seed_confidence(
    boxes: list[list[float]],
    seed_boxes: list[list[float]],
    seed_scores: list[float],
) -> bool:
    """Whether any accepted box lacks a matching 'seed' detection above threshold."""
    for box in boxes:
        best_score = max(
            (
                score
                for seed_box, score in zip(seed_boxes, seed_scores, strict=True)
                if _box_iou_xyxy(box, seed_box) >= SEED_CHECK_IOU_THRESHOLD
            ),
            default=0.0,
        )
        if best_score < SEED_CHECK_SCORE_THRESHOLD:
            return True
    return False


def review_outcome(
    boxes: list,
    padded: list,
    *,
    has_overlapping_masks: bool | None = None,
    has_low_seed_confidence: bool | None = None,
) -> tuple[str | None, str | None]:
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
        return "needs_review", "nested_boxes"
    if has_overlapping_masks is True:
        return "needs_review", "overlapping_masks"
    if has_overlapping_masks is None and _has_overlapping_boxes(padded):
        return "needs_review", "overlapping_boxes"
    if has_low_seed_confidence is True:
        return "needs_review", "low_seed_confidence"
    return None, None


def prelabel(
    coco: dict,
    media_root: Path,
    predictor,
    *,
    padding: int = 3,
    checkpoint_dir: Path | None = None,
    predictor_identity: str | None = None,
    code_revision: str | None = None,
    initial_index_path: Path | None = None,
) -> dict:
    """Add draft boxes using an image-only callable returning a Prediction.

    Prediction boxes use pixel XYXY coordinates and may have one score per box.
    Set initial_index_path to save the unannotated index before a fresh run.
    """
    media_root = media_root.resolve(strict=True)
    return _prelabel(
        coco,
        lambda record: (media_root / record["file_name"]).open("rb"),
        predictor,
        padding=padding,
        checkpoint_dir=checkpoint_dir,
        predictor_identity=predictor_identity,
        code_revision=code_revision,
        media_identity=str(media_root),
        initial_index_path=initial_index_path,
    )


def prelabel_s3(
    coco: dict,
    storage,
    bucket: str,
    predictor,
    *,
    padding: int = 3,
    checkpoint_dir: Path | None = None,
    predictor_identity: str | None = None,
    code_revision: str | None = None,
    storage_identity: str | None = None,
    initial_index_path: Path | None = None,
) -> dict:
    """Pre-label S3 images with the same options as prelabel, verifying each PNG hash."""
    with asyncio.Runner() as runner:

        def open_image(record):
            key, digest = record["file_name"], record["image_sha256"]
            if key != f"png/detection/{digest}.png":
                raise ValueError(f"PNG key does not match image_sha256: {key}")
            data = runner.run(storage.read_image(bucket, key))
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"PNG does not match image_sha256: {key}")
            return io.BytesIO(data)

        return _prelabel(
            coco,
            open_image,
            predictor,
            padding=padding,
            checkpoint_dir=checkpoint_dir,
            predictor_identity=predictor_identity,
            code_revision=code_revision,
            media_identity=f"s3://{bucket}|{storage_identity}"
            if storage_identity
            else None,
            initial_index_path=initial_index_path,
        )


def _load_checkpoint(
    path: Path, record: dict, category_id: int, current: Version
) -> dict:
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read pre-label checkpoint {path}: {error}") from error
    if isinstance(checkpoint, dict) and checkpoint.get("prelabel_status") == "draft":
        raise ValueError(
            f"Legacy draft checkpoint at {path}. Restart with a fresh checkpoint directory."
        )
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("image_id") != record["id"]
        or checkpoint.get("file_name") != record["file_name"]
        or checkpoint.get("image_sha256") != record["image_sha256"]
        or "prelabel_status" not in checkpoint
        or checkpoint["prelabel_status"] not in (None, "needs_review")
        or not isinstance(checkpoint.get("annotations"), list)
        or "prelabel_prompt" not in checkpoint
        or "prelabel_reason" not in checkpoint
        or checkpoint["prelabel_prompt"] is not None
        and not isinstance(checkpoint["prelabel_prompt"], str)
        or checkpoint["prelabel_reason"] is not None
        and not isinstance(checkpoint["prelabel_reason"], str)
    ):
        raise ValueError(
            f"Invalid pre-label checkpoint for {record['file_name']}: {path}"
        )
    version = parse_version(checkpoint.get("version"), context=f"checkpoint {path}")
    if str(version) != path.parent.name or not compatible_checkpoint(version, current):
        raise ValueError(f"Incompatible pre-label checkpoint version at {path}")
    producer = checkpoint.get("producer")
    if (
        not isinstance(producer, dict)
        or not isinstance(producer.get("code_revision"), str)
        or not producer["code_revision"]
    ):
        raise ValueError(f"Invalid pre-label checkpoint producer: {path}")
    producer_version = parse_version(
        producer.get("project_version"), context=f"producer in {path}"
    )
    if not compatible_checkpoint(producer_version, version):
        raise ValueError(f"Incompatible pre-label producer version at {path}")
    if any(
        not isinstance(annotation, dict)
        or annotation.get("image_id") != record["id"]
        or annotation.get("category_id") != category_id
        or annotation.get("iscrowd") != 0
        or not isinstance(annotation.get("bbox"), list)
        or len(annotation["bbox"]) != 4
        or any(
            not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in annotation["bbox"]
        )
        or "score" in annotation
        and (
            not isinstance(annotation["score"], (int, float))
            or not math.isfinite(annotation["score"])
        )
        for annotation in checkpoint["annotations"]
    ):
        raise ValueError(f"Invalid annotations in pre-label checkpoint: {path}")
    if (
        "has_overlapping_masks" in checkpoint
        and checkpoint["has_overlapping_masks"] is not None
        and not isinstance(checkpoint["has_overlapping_masks"], bool)
    ):
        raise ValueError(f"Invalid mask overlap flag in pre-label checkpoint: {path}")
    if (
        checkpoint["prelabel_status"] is None
        and checkpoint.get("has_overlapping_masks") is None
        and _has_overlapping_boxes(
            [annotation["bbox"] for annotation in checkpoint["annotations"]]
        )
    ):
        checkpoint.update(
            prelabel_status="needs_review", prelabel_reason="overlapping_boxes"
        )
    return checkpoint


def _write_checkpoint(path: Path, record: dict, outcome: dict, producer: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "version": producer["project_version"],
        "producer": producer,
        "image_id": record["id"],
        "file_name": record["file_name"],
        "image_sha256": record["image_sha256"],
        **outcome,
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".checkpoint-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(checkpoint, stream, allow_nan=False)
            stream.write("\n")
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise RuntimeError(
                f"Checkpoint was created concurrently: {path}; use one writer"
            ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _label_image(
    record: dict, open_image, predictor, category_id: int, padding: int
) -> dict:
    with open_image(record) as stream:
        # PNG's IHDR bit depth is byte 24; Pillow's RGB/RGBA modes hide it.
        header = stream.read(25)
        stream.seek(0)
        with Image.open(stream) as image:
            if image.size != (record["width"], record["height"]):
                raise ValueError(f"COCO dimensions do not match {record['file_name']}")
            if image.mode in HIGH_BIT_MODES or (
                image.format == "PNG" and header[24] == 16
            ):
                return {
                    "prelabel_status": "needs_review",
                    "prelabel_reason": "high_bit_depth",
                    "prelabel_prompt": None,
                    "annotations": [],
                }
            prediction = predictor(image.convert("RGB"))
    boxes = prediction.boxes
    scores = [None] * len(boxes) if prediction.scores is None else prediction.scores
    padded, annotations = [], []
    for box, score in zip(boxes, scores, strict=True):
        padded_box = coco_box(box, record["width"], record["height"], padding)
        if padded_box is None:
            continue
        padded.append(padded_box)
        annotation = {
            "image_id": record["id"],
            "category_id": category_id,
            "bbox": padded_box,
            "iscrowd": 0,
        }
        if score is not None:
            annotation["score"] = score
        annotations.append(annotation)
    status, reason = review_outcome(
        boxes,
        padded,
        has_overlapping_masks=prediction.has_overlapping_masks,
        has_low_seed_confidence=prediction.has_low_seed_confidence,
    )
    outcome = {
        "prelabel_status": status,
        "prelabel_prompt": prediction.prompt,
        "prelabel_reason": reason,
        "annotations": annotations,
    }
    if prediction.has_overlapping_masks is not None:
        outcome["has_overlapping_masks"] = prediction.has_overlapping_masks
    return outcome


def _checkpoint_namespace(
    coco: dict, *, predictor_identity: str, media_identity: str, padding: int
) -> str:
    index = copy.deepcopy(coco)
    preparation = index.get("info", {}).get("preparation", {})
    if isinstance(preparation, dict):
        preparation.pop("code_revision", None)
    for image in index["images"]:
        for source in image["sources"]:
            source.pop("preparation", None)
    identity = {
        "index": index,
        "predictor": predictor_identity,
        "media": media_identity,
        "padding": padding,
        "prompts": PROMPTS,
        "score_threshold": SCORE_THRESHOLD,
        "mask_threshold": MASK_THRESHOLD,
        "mask_overlap_threshold": MASK_OVERLAP_THRESHOLD,
        "seed_check_prompt": SEED_CHECK_PROMPT,
        "seed_check_score_threshold": SEED_CHECK_SCORE_THRESHOLD,
        "seed_check_iou_threshold": SEED_CHECK_IOU_THRESHOLD,
        "max_boxes": MAX_BOXES,
    }
    serialized = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


def _write_unannotated_index(path: Path, coco: dict) -> None:
    snapshot = {**coco, "images": []}
    for record in coco["images"]:
        image = {**record, "prelabel_status": "unannotated"}
        for field in (
            "prelabel_prompt",
            "prelabel_reason",
            "prelabel_project_version",
            "prelabel_code_revision",
        ):
            image.pop(field, None)
        snapshot["images"].append(image)
    if "info" in snapshot:
        snapshot["info"] = coco["info"].copy()
        snapshot["info"].pop("prelabel", None)
    save_coco(path, snapshot)
    logger.info("Wrote initial unannotated COCO index %s", path)


def _prelabel(
    coco: dict,
    open_image,
    predictor,
    *,
    padding: int,
    checkpoint_dir: Path | None,
    predictor_identity: str | None,
    code_revision: str | None,
    media_identity: str | None,
    initial_index_path: Path | None,
) -> dict:
    """Use the same decoding and annotation policy for local and S3 streams."""
    if coco["annotations"]:
        raise ValueError(
            "Pre-labeling requires an unannotated index; refusing to replace labels"
        )
    result = copy.deepcopy(coco)
    categories = {category["name"]: category["id"] for category in result["categories"]}
    result["annotations"] = []
    candidates = []
    target_dir = None
    version = None
    if checkpoint_dir is not None:
        if not predictor_identity or not code_revision or not media_identity:
            raise ValueError(
                "Checkpointing requires predictor, media, and code revision identities"
            )
        for path in (checkpoint_dir, checkpoint_dir / "releases"):
            if path.is_symlink():
                raise ValueError(f"Checkpoint cannot be a symlink: {path}")
        if checkpoint_dir.is_dir() and any(
            path.is_dir() and re.fullmatch(r"[0-9a-f]{64}", path.name)
            for path in checkpoint_dir.iterdir()
        ):
            logger.warning(
                "Ignoring legacy integer-version pre-label checkpoints in %s",
                checkpoint_dir,
            )
        version = project_version()
        identity = _checkpoint_namespace(
            coco,
            predictor_identity=predictor_identity,
            media_identity=media_identity,
            padding=padding,
        )
        root = checkpoint_dir / "releases" / identity
        candidates = compatible_directories(root, version)
        target_dir = root / str(version)
        logger.info("Using pre-label checkpoint %s", target_dir)
    if initial_index_path is not None and not any(
        (candidate_dir / f"{image_number:08d}.json").exists()
        for _, candidate_dir in candidates
        for image_number in range(len(result["images"]))
    ):
        _write_unannotated_index(initial_index_path, result)
    resumed = 0
    images = log_progress(
        result["images"], logger, stage="SAM3 pre-labeling", total=len(result["images"])
    )
    for image_number, record in enumerate(images):
        category_id = categories[record["sources"][0]["species"]]
        outcome = None
        filename = f"{image_number:08d}.json"
        for _, candidate_dir in candidates:
            path = candidate_dir / filename
            if path.is_symlink():
                raise ValueError(f"Checkpoint cannot be a symlink: {path}")
            if path.exists():
                if version is None:
                    raise RuntimeError("Missing pre-label checkpoint version")
                outcome = _load_checkpoint(path, record, category_id, version)
                logger.debug(
                    "Resuming pre-label for %s from %s", record["file_name"], path
                )
                resumed += 1
                break
        if outcome is None:
            outcome = _label_image(record, open_image, predictor, category_id, padding)
            if target_dir is not None:
                producer = {
                    "project_version": str(version),
                    "code_revision": code_revision,
                }
                _write_checkpoint(target_dir / filename, record, outcome, producer)
                outcome["producer"] = producer
        record.update(
            prelabel_status=outcome["prelabel_status"],
            prelabel_prompt=outcome["prelabel_prompt"],
            prelabel_reason=outcome["prelabel_reason"],
        )
        if target_dir is not None:
            record.update(
                prelabel_project_version=outcome["producer"]["project_version"],
                prelabel_code_revision=outcome["producer"]["code_revision"],
            )
        else:
            record.pop("prelabel_project_version", None)
            record.pop("prelabel_code_revision", None)
        for annotation in outcome["annotations"]:
            result["annotations"].append(
                {**annotation, "id": len(result["annotations"])}
            )
    if checkpoint_dir is not None:
        logger.info(
            "Pre-label checkpoint progress: reused=%d processed=%d",
            resumed,
            len(result["images"]) - resumed,
        )
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("media_root", help="Local media directory or s3://<bucket>")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--model-path", required=True, type=Path, help="Local model directory"
    )
    parser.add_argument(
        "--model-source",
        help="S3 snapshot URI (s3://<bucket>/<prefix>) to download into --model-path",
    )
    parser.add_argument(
        "--model-revision",
        required=True,
        help="Operator-provided revision label for the model weights",
    )
    parser.add_argument(
        "--model-identity",
        help="Stable model identity when the same model path can refer to different weights",
    )
    parser.add_argument(
        "--code-revision",
        help="Source revision label; required when checkpointing",
    )
    parser.add_argument("--device", required=True, choices=["cpu", "cuda"])
    parser.add_argument("--padding", type=int, default=3)
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        help="Directory for resumable per-image checkpoints",
    )
    parser.add_argument("--endpoint-url", help="S3 endpoint; HTTPS unless --allow-http")
    parser.add_argument("--region", help="Region for S3 input")
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow a trusted HTTP endpoint"
    )
    args = parser.parse_args(argv)
    if args.padding < 0:
        parser.error("padding must be non-negative")
    if args.checkpoint_dir is not None and not args.code_revision:
        parser.error("--code-revision is required with --checkpoint-dir")
    if args.model_identity is not None and not args.model_identity.strip():
        parser.error("--model-identity cannot be empty")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    source = urlsplit(args.media_root)
    model_source = (
        urlsplit(args.model_source) if args.model_source is not None else None
    )
    if model_source is not None and (
        model_source.scheme != "s3"
        or not model_source.netloc
        or not model_source.path.strip("/")
        or model_source.query
        or model_source.fragment
    ):
        parser.error("--model-source must be s3://<bucket>/<prefix>")
    if source.scheme == "s3" and (
        not source.netloc
        or source.path not in ("", "/")
        or source.query
        or source.fragment
    ):
        parser.error("S3 media root must be s3://<bucket> without a key prefix")
    uses_s3 = source.scheme == "s3" or model_source is not None
    if uses_s3:
        if not args.endpoint_url or not args.region:
            parser.error("S3 input requires --endpoint-url and --region")
    elif args.endpoint_url or args.region or args.allow_http:
        parser.error("S3 options require an S3 media root or --model-source")

    with ExitStack() as resources:
        storage = None
        if uses_s3:
            from s3_storage import create_storage

            try:
                storage = create_storage(
                    args.endpoint_url, args.region, allow_http=args.allow_http
                )
            except ValueError as error:
                parser.error(str(error))
            resources.callback(storage.close)

        coco = json.loads(args.index.read_text())
        model_identity = args.model_source or str(args.model_path)
        identity = {
            "model_path": model_identity,
            "model_identity": args.model_identity or model_identity,
            "model_revision": args.model_revision,
            "device": args.device,
        }
        storage_config = {"endpoint": args.endpoint_url, "region": args.region}
        if model_source is not None:
            prefix = model_source.path.strip("/") + "/"
            snapshot_identity = json.dumps(
                {
                    **storage_config,
                    "source": args.model_source,
                    "revision": args.model_revision,
                },
                sort_keys=True,
            )
            storage.stage_model(
                model_source.netloc, prefix, args.model_path, snapshot_identity
            )
            identity["model_storage"] = storage_config
        predictor = Sam3Predictor(args.model_path, args.device)
        predictor_identity = json.dumps(identity, sort_keys=True)
        initial_index_path = args.output.with_name(
            f"{args.output.stem}.unannotated{args.output.suffix}"
        )
        if source.scheme == "s3":
            result = prelabel_s3(
                coco,
                storage,
                source.netloc,
                predictor,
                padding=args.padding,
                checkpoint_dir=args.checkpoint_dir,
                predictor_identity=predictor_identity,
                code_revision=args.code_revision,
                storage_identity=json.dumps(storage_config, sort_keys=True),
                initial_index_path=initial_index_path,
            )
        else:
            result = prelabel(
                coco,
                Path(args.media_root),
                predictor,
                padding=args.padding,
                checkpoint_dir=args.checkpoint_dir,
                predictor_identity=predictor_identity,
                code_revision=args.code_revision,
                initial_index_path=initial_index_path,
            )
    result["info"]["prelabel"] = {
        "model_path": str(args.model_path),
        "model_revision": args.model_revision,
        "padding": args.padding,
        "device": args.device,
        "precision": "bf16" if args.device == "cuda" else "fp32",
    }
    if args.model_source is not None:
        result["info"]["prelabel"]["model_source"] = args.model_source
    if args.model_identity is not None:
        result["info"]["prelabel"]["model_identity"] = args.model_identity
    save_coco(args.output, result)
    boxes, images = len(result["annotations"]), len(result["images"])
    print(f"Wrote {boxes} draft boxes for {images} images")


if __name__ == "__main__":
    main()
