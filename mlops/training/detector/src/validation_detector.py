#!/usr/bin/env python
# Migrated from nachet-model-ccds/nachetmodel/ValidationDetector.py at 228af71.
"""Object detection model validation module.

This module provides tools for validating object detection models against
COCO-format validation data, computing mAP/mAR metrics, precision/recall/F1,
and per-subclass breakdown.

Can be used both programmatically and via CLI.

Example:
    # CLI usage
    python -m validation_detector \
        --config_path validation_config.yaml \
        --model_path models/checkpoint-8060

    # Programmatic usage
    from validation_detector import ValidationConfig, DetectorValidator

    config = ValidationConfig(
        config_path=Path("validation_config.yaml"),
        model_path=Path("models/checkpoint-8060"),
    )
    validator = DetectorValidator(config)
    results = validator.run()
    print(f"mAP: {results.overall.map:.4f}")
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Union

import albumentations as A

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import yaml
from PIL import Image
from datasets import Dataset, concatenate_datasets
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from tqdm.auto import tqdm
from transformers import AutoImageProcessor, AutoModelForObjectDetection

from coco_to_hf_dataset import load_coco_as_hf_dataset


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class DataSourceConfig:
    """Configuration for a single validation data source."""

    json_path: str
    """Path to COCO annotations JSON file."""

    images_dir: str
    """Directory containing the images."""

    reject_list: Optional[str] = None
    """Optional path to reject list file."""


@dataclass
class ValidationConfig:
    """Configuration for detector validation."""

    # Required paths
    config_path: Path
    """Path to YAML config file with validation data sources."""

    model_path: Path
    """Path to the model checkpoint directory."""

    # Optional paths
    processor_path: Optional[Path] = None
    """Path to image processor. Auto-detected from model_path if None."""

    output_dir: Optional[Path] = None
    """Output directory for results. Defaults to model_path/validation_analysis."""

    # Inference settings
    confidence_threshold: float = 0.5
    """Filter predictions below this confidence score."""

    iou_threshold: float = 0.5
    """IoU threshold for matching predictions to ground truth."""

    batch_size: int = 16
    """Batch size for inference (lower for detection due to memory)."""

    # Control flags
    generate_visualizations: bool = True
    """Whether to generate visualization plots."""

    save_results: bool = True
    """Whether to save JSON/CSV results to output_dir."""

    device: Optional[str] = None
    """Device to use ('cuda', 'cpu'). Auto-detected if None."""

    preprocessing: Optional[Union[str, A.Compose]] = None
    """Optional preprocessing: 'imagenet', 'clahe', 'clahe+imagenet', or albumentations Compose."""


# =============================================================================
# Result Dataclasses
# =============================================================================


@dataclass
class OverallMetrics:
    """Overall detection metrics from validation."""

    # MeanAveragePrecision metrics
    map: float
    """mAP at IoU 0.50:0.95."""

    map_50: float
    """mAP at IoU 0.50."""

    map_75: float
    """mAP at IoU 0.75."""

    map_small: float
    """mAP for small objects."""

    map_medium: float
    """mAP for medium objects."""

    map_large: float
    """mAP for large objects."""

    mar_1: float
    """mAR at 1 detection per image."""

    mar_10: float
    """mAR at 10 detections per image."""

    mar_100: float
    """mAR at 100 detections per image."""

    # Precision/Recall/F1
    precision: float
    """Overall precision = TP / (TP + FP)."""

    recall: float
    """Overall recall = TP / (TP + FN)."""

    f1_score: float
    """Overall F1 score."""

    # Counts
    true_positives: int
    false_positives: int
    false_negatives: int
    total_ground_truth: int
    total_predictions: int

    # Config used
    confidence_threshold: float
    iou_threshold: float
    num_images: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SubclassMetrics:
    """Metrics for a single subclass/category."""

    subclass: str
    """Subclass/category name."""

    num_gt: int
    """Number of ground truth annotations."""

    num_matched: int
    """Number of matched (TP) detections."""

    tp: int
    """True positives count."""

    fp: int
    """False positives count (attributed to this subclass by nearest GT)."""

    fn: int
    """False negatives count."""

    precision: float
    """Precision = TP / (TP + FP)."""

    recall: float
    """Recall = TP / (TP + FN)."""

    detection_rate: float
    """Detection rate = TP / num_gt."""

    map: float
    """mAP at IoU 0.50:0.95 for this subclass (COCO-style)."""

    mar: float
    """mAR at 100 detections for this subclass."""


@dataclass
class ValidationResults:
    """Complete validation results container."""

    overall: OverallMetrics
    """Overall detection metrics."""

    per_subclass: list[SubclassMetrics]
    """Per-subclass metrics list."""

    # Raw data for further analysis
    predictions: list[dict]
    """List of prediction dicts per image (boxes, scores, labels)."""

    targets: list[dict]
    """List of target dicts per image (boxes, labels)."""

    image_ids: list[str]
    """List of image IDs in order."""

    categories: dict[int, str]
    """Category ID to name mapping."""

    model_id2label: dict[int, str]
    """Model's ID to label mapping."""

    # False negative details for analysis
    false_negatives_by_image: list[dict]
    """Detailed FN info per image for visualization."""

    def to_dataframe(self) -> pd.DataFrame:
        """Convert per_subclass metrics to pandas DataFrame."""
        return pd.DataFrame([asdict(m) for m in self.per_subclass])

    def plot_metrics_table(
        self,
        output_path: Optional[Path] = None,
        show: bool = True,
        sort_alphabetically: bool = True,
        performance_red_threshold: float = 0.80,
    ) -> plt.Figure:
        """
        Plot per-subclass metrics as a seaborn table.

        Args:
            output_path: Optional path to save the rendered table image.
            show: Whether to display the plot.
            sort_alphabetically: Whether to sort subclasses alphabetically.
            performance_red_threshold: Red color cutoff for precision/recall,
                detection rate, mAP, and mAR.

        Returns:
            Matplotlib figure containing the rendered table.
        """
        return plot_subclass_metrics_table(
            self.to_dataframe(),
            output_path=output_path,
            show=show,
            sort_alphabetically=sort_alphabetically,
            performance_red_threshold=performance_red_threshold,
        )

    def save(self, output_dir: Path) -> None:
        """Save all results to output directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save overall metrics
        with open(output_dir / "detection_metrics.json", "w") as f:
            json.dump(self.overall.to_dict(), f, indent=2)

        # Save per-subclass metrics
        df = self.to_dataframe()
        df.to_csv(output_dir / "per_subclass_metrics.csv", index=False)

        # Save extended metrics
        extended_metrics = {
            "overall": {
                "true_positives": self.overall.true_positives,
                "false_positives": self.overall.false_positives,
                "false_negatives": self.overall.false_negatives,
                "total_ground_truth": self.overall.total_ground_truth,
                "total_predictions": self.overall.total_predictions,
                "precision": self.overall.precision,
                "recall": self.overall.recall,
                "f1_score": self.overall.f1_score,
                "iou_threshold": self.overall.iou_threshold,
                "confidence_threshold": self.overall.confidence_threshold,
            },
            "per_subclass": df.to_dict(orient="records"),
        }
        with open(output_dir / "precision_recall_f1_metrics.json", "w") as f:
            json.dump(extended_metrics, f, indent=2)

        # Save false negatives by subclass
        fn_by_subclass = defaultdict(int)
        for fn_info in self.false_negatives_by_image:
            for cat in fn_info.get("fn_categories", []):
                fn_by_subclass[cat] += 1

        fn_df = pd.DataFrame(
            [
                {"subclass": cat, "false_negatives": count}
                for cat, count in fn_by_subclass.items()
            ],
            columns=["subclass", "false_negatives"],
        ).sort_values("false_negatives", ascending=False)
        fn_df.to_csv(output_dir / "false_negatives_by_subclass.csv", index=False)

        print(f"Results saved to {output_dir}")


# =============================================================================
# Utility Functions
# =============================================================================


def load_validation_config(
    config_path: Path,
) -> tuple[list[DataSourceConfig], set[str] | None, bool, str]:
    """
    Load and parse YAML/JSON validation config file.

    Args:
        config_path: Path to the config file.

    Returns:
        Tuple of (sources, include_classes, single_category, single_category_name)
    """
    with open(config_path) as f:
        if str(config_path).endswith((".yaml", ".yml")):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    sources = []
    for src in config.get("sources", []):
        sources.append(
            DataSourceConfig(
                json_path=src["json_path"],
                images_dir=src["images_dir"],
                reject_list=src.get("reject_list"),
            )
        )

    include_classes = set(config.get("include_classes", [])) or None
    single_category = config.get("single_category", False)
    single_category_name = config.get("single_category_name", "seed")

    return sources, include_classes, single_category, single_category_name


def find_processor_path(
    model_path: Path, processor_path: Optional[Path] = None
) -> Path:
    """
    Find a valid path containing preprocessor_config.json.

    Searches in order:
    1. Provided processor_path
    2. model_path
    3. model_path.parent
    4. model_path.parent.parent

    Args:
        model_path: Path to model checkpoint.
        processor_path: Optional explicit processor path.

    Returns:
        Path containing preprocessor_config.json.

    Raises:
        FileNotFoundError: If no valid processor path found.
    """
    candidates = []
    if processor_path:
        candidates.append(Path(processor_path))
    candidates.append(Path(model_path))
    candidates.append(Path(model_path).parent)
    candidates.append(Path(model_path).parent.parent)

    for p in candidates:
        if (p / "preprocessor_config.json").exists():
            return p

    raise FileNotFoundError(f"No preprocessor_config.json found in {candidates}")


def compute_iou(box1: list[float], box2: list[float]) -> float:
    """
    Compute IoU between two boxes in [x1, y1, x2, y2] format.

    Args:
        box1: First bounding box [x1, y1, x2, y2].
        box2: Second bounding box [x1, y1, x2, y2].

    Returns:
        Intersection over Union value.
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area

    return inter_area / union_area if union_area > 0 else 0


def convert_normalized_to_original(
    boxes_cxcywh_norm: torch.Tensor,
    orig_size: tuple[int, int],
    canvas_size: int,
) -> list[list[float]]:
    """
    Convert normalized cxcywh boxes to xyxy in original image coordinates.

    Handles RT-DETR style bottom/right padding conversion.

    Args:
        boxes_cxcywh_norm: Normalized boxes [N, 4] in cxcywh format.
        orig_size: Original image (width, height).
        canvas_size: Square canvas size (e.g., 640).

    Returns:
        List of boxes in [x1, y1, x2, y2] format.
    """
    orig_w, orig_h = orig_size
    scale = canvas_size / max(orig_w, orig_h)

    boxes_xyxy = []
    for box in boxes_cxcywh_norm:
        cx, cy, w, h = box.tolist()
        # Convert normalized coords to canvas pixel space, then to original
        x1 = (cx - w / 2) * canvas_size / scale
        y1 = (cy - h / 2) * canvas_size / scale
        x2 = (cx + w / 2) * canvas_size / scale
        y2 = (cy + h / 2) * canvas_size / scale
        # Clip to original image bounds
        x1 = max(0, min(x1, orig_w))
        y1 = max(0, min(y1, orig_h))
        x2 = max(0, min(x2, orig_w))
        y2 = max(0, min(y2, orig_h))
        boxes_xyxy.append([x1, y1, x2, y2])

    return boxes_xyxy


def build_label_mapping(
    categories: dict[int, str],
    model_label2id: dict[str, int],
    single_category: bool = False,
) -> dict[int, int]:
    """
    Build mapping from dataset category IDs to model label IDs.

    Handles exact matches and numbered prefix stripping
    (e.g., "000 Brassica napus" -> "Brassica napus").

    Args:
        categories: Dataset category_id -> name mapping.
        model_label2id: Model's label -> id mapping.
        single_category: Whether validation explicitly requests a one-class head.

    Returns:
        Mapping from dataset category_id to model label_id.
    """
    # Keep species IDs for reports; a one-class head maps every species to its
    # sole output. A multiclass head must recognize each species explicitly.
    if single_category and len(model_label2id) != 1:
        raise ValueError("single_category requires a model with exactly one label")
    if len(model_label2id) == 1:
        model_id = next(iter(model_label2id.values()))
        return {cat_id: model_id for cat_id in categories}

    coco_to_model = {}
    for cat_id, cat_name in categories.items():
        # Try exact match first
        if cat_name in model_label2id:
            coco_to_model[cat_id] = model_label2id[cat_name]
        else:
            # Try without leading number prefix
            clean_name = (
                " ".join(cat_name.split()[1:])
                if cat_name.split()[0].isdigit()
                else cat_name
            )
            if clean_name in model_label2id:
                coco_to_model[cat_id] = model_label2id[clean_name]
            else:
                raise ValueError(
                    f"Category {cat_name!r} not found in model labels"
                )

    return coco_to_model


def _compute_ap_ar(predictions: list[dict], num_gt: int) -> tuple[float, float]:
    """
    Compute AP and AR for a single class.

    Args:
        predictions: List of prediction dicts with 'matched' and 'score' keys.
        num_gt: Number of ground truth annotations.

    Returns:
        Tuple of (AP, AR) values.
    """
    if num_gt == 0:
        return 0.0, 0.0

    # Sort by score descending
    sorted_preds = sorted(
        [p for p in predictions if p["matched"]], key=lambda x: -x["score"]
    )

    # Compute precision-recall curve
    tp = 0
    precisions = []
    recalls = []

    for i, pred in enumerate(sorted_preds):
        tp += 1
        precision = tp / (i + 1)
        recall = tp / num_gt
        precisions.append(precision)
        recalls.append(recall)

    if len(precisions) == 0:
        return 0.0, 0.0

    # Compute AP (area under PR curve with 11-point interpolation)
    ap = 0
    for t in np.linspace(0, 1, 11):
        prec_at_recall = [p for p, r in zip(precisions, recalls) if r >= t]
        if prec_at_recall:
            ap += max(prec_at_recall)
    ap /= 11

    # AR is the max recall achieved
    ar = max(recalls) if recalls else 0.0

    return ap, ar


# =============================================================================
# Preprocessing Helpers
# =============================================================================


def _build_preprocessing_transform(
    preprocessing: Optional[Union[str, A.Compose]],
) -> Optional[A.Compose]:
    """
    Build albumentations transform from preset string or return as-is.

    Args:
        preprocessing: Preset name ('imagenet', 'clahe', 'clahe+imagenet')
                       or an albumentations Compose object.

    Returns:
        Albumentations Compose transform or None.

    Raises:
        ValueError: If unknown preset string is provided.
    """
    if preprocessing is None:
        return None

    if isinstance(preprocessing, str):
        presets = {
            "imagenet": A.Compose(
                [
                    A.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            ),
            "clahe": A.Compose(
                [
                    A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8)),
                ]
            ),
            "clahe+imagenet": A.Compose(
                [
                    A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8)),
                    A.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            ),
        }
        if preprocessing not in presets:
            raise ValueError(
                f"Unknown preprocessing preset: {preprocessing}. "
                f"Available: {list(presets.keys())}"
            )
        return presets[preprocessing]

    # Assume it's already an albumentations Compose
    return preprocessing


def _has_normalize_transform(
    preprocessing: Optional[Union[str, A.Compose]],
) -> bool:
    """
    Check if preprocessing includes A.Normalize.

    Args:
        preprocessing: Preset name or albumentations Compose object.

    Returns:
        True if preprocessing includes normalization.
    """
    if preprocessing is None:
        return False

    if isinstance(preprocessing, str):
        return preprocessing in ("imagenet", "clahe+imagenet")

    # Check albumentations Compose for Normalize
    if hasattr(preprocessing, "transforms"):
        return any(isinstance(t, A.Normalize) for t in preprocessing.transforms)

    return isinstance(preprocessing, A.Normalize)


# =============================================================================
# DetectorValidator Class
# =============================================================================


class DetectorValidator:
    """
    Object detection model validator.

    Validates a detection model against COCO-format validation data,
    computing mAP/mAR metrics, precision/recall/F1, and per-subclass
    breakdown.

    Can be used programmatically or via CLI.

    Example:
        config = ValidationConfig(
            config_path=Path("validation_config.yaml"),
            model_path=Path("models/checkpoint-1000"),
            confidence_threshold=0.5,
        )
        validator = DetectorValidator(config)
        results = validator.run()

        print(f"mAP: {results.overall.map:.4f}")
        print(results.to_dataframe())
    """

    def __init__(self, config: ValidationConfig) -> None:
        """
        Initialize the validator.

        Args:
            config: Validation configuration.
        """
        self.config = config
        self._setup_device()
        self._setup_output_dir()

        # Lazy-loaded components
        self._model: Optional[AutoModelForObjectDetection] = None
        self._processor: Optional[AutoImageProcessor] = None
        self._dataset: Optional[Dataset] = None
        self._categories: Optional[dict[int, str]] = None
        self._images: Optional[dict] = None
        self._annotations_by_image: Optional[dict] = None
        self._coco_to_model: Optional[dict[int, int]] = None
        self._single_category = False
        self._image_square_size: int = 640

        # Preprocessing
        self._preprocessing_transform = _build_preprocessing_transform(
            config.preprocessing
        )
        self._preprocessing_includes_normalize = _has_normalize_transform(
            config.preprocessing
        )
        if self._preprocessing_transform is not None:
            print(f"Using preprocessing: {config.preprocessing}")

    def _setup_device(self) -> None:
        """Setup compute device."""
        if self.config.device:
            self.device = self.config.device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

    def _setup_output_dir(self) -> None:
        """Create output directory if needed."""
        if self.config.output_dir is None:
            self.config.output_dir = self.config.model_path / "validation_analysis"
        if self.config.save_results or self.config.generate_visualizations:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def load_model(self) -> None:
        """
        Load the model and image processor.

        Populates self._model and self._processor.
        """
        processor_dir = find_processor_path(
            self.config.model_path, self.config.processor_path
        )
        print(f"Loading processor from: {processor_dir}")

        # Disable processor normalization if we're handling it via preprocessing
        do_normalize = not self._preprocessing_includes_normalize
        if self._preprocessing_includes_normalize:
            print("Processor normalization disabled (handled by preprocessing)")

        self._processor = AutoImageProcessor.from_pretrained(
            processor_dir, do_normalize=do_normalize
        )
        self._model = AutoModelForObjectDetection.from_pretrained(
            self.config.model_path
        ).to(self.device)
        self._model.eval()

        # Get image square size from processor config
        self._image_square_size = self._processor.size.get("max_height", 640)

        print(f"Model classes: {len(self._model.config.id2label)}")

    def load_data(self) -> None:
        """
        Load validation dataset from config.

        Populates self._dataset, self._categories, self._images,
        and self._annotations_by_image.
        """
        sources, include_classes, single_category, single_category_name = (
            load_validation_config(self.config.config_path)
        )
        self._single_category = single_category

        print(f"Loading validation data from {len(sources)} source(s)...")
        print(f"Single category mode: {single_category} ({single_category_name})")
        if include_classes:
            print(f"Filtering to {len(include_classes)} classes")

        # First pass: collect all unique category names across all sources
        # to build a unified category mapping
        # Match the shared loader's case-insensitive filter while keeping the
        # original spelling as the species identity used by reports.
        include_classes_lower = (
            {name.lower() for name in include_classes}
            if include_classes is not None
            else None
        )
        all_category_names = set()
        for source in sources:
            with open(source.json_path) as f:
                if str(source.json_path).endswith((".yaml", ".yml")):
                    coco = yaml.safe_load(f)
                else:
                    coco = json.load(f)
            for cat in coco["categories"]:
                cat_name = cat["name"]
                # Apply include_classes filter if specified
                if (
                    include_classes_lower is None
                    or cat_name.lower() in include_classes_lower
                ):
                    all_category_names.add(cat_name)

        # Build unified category mapping: name -> unified_id
        sorted_names = sorted(all_category_names)
        unified_name_to_id = {name: idx for idx, name in enumerate(sorted_names)}
        unified_categories = {idx: name for idx, name in enumerate(sorted_names)}

        # Load datasets from each source with category remapping
        all_datasets = []

        for idx, source in enumerate(sources):
            print(f"\nSource {idx + 1}: {source.images_dir}")
            ds, source_cats = load_coco_as_hf_dataset(
                images_dir=source.images_dir,
                coco_json_path=source.json_path,
                train_val_split=1.0,  # All data to validation split
                seed=42,
                # Preserve species identities for per-subclass reports. Only
                # the model-label mapping may collapse them to one output.
                single_category=False,
                single_category_name=single_category_name,
                reject_list_path=source.reject_list,
                include_classes=include_classes,
                fail_on_missing_images=True,
            )
            print(f"  Loaded {len(ds['validation'])} images")

            # Build remapping from source category IDs to unified IDs
            source_id_to_unified = {}
            for source_id, cat_name in source_cats.items():
                source_id_to_unified[source_id] = unified_name_to_id[cat_name]

            # Every source ID must have a known meaning in the combined data.
            # Reusing an unmapped number could assign an annotation to another species.
            def remap_categories(example):
                remapped_cats = [
                    source_id_to_unified[cat_id]
                    for cat_id in example["objects"]["category"]
                ]
                example["objects"]["category"] = remapped_cats
                return example

            ds_remapped = ds["validation"].map(remap_categories)
            all_datasets.append(ds_remapped)

        # Concatenate if multiple sources
        if len(all_datasets) > 1:
            self._dataset = concatenate_datasets(all_datasets)
        else:
            self._dataset = all_datasets[0]

        self._categories = unified_categories
        print(f"\nTotal images: {len(self._dataset)}")
        print(
            f"Categories ({len(self._categories)}): {list(self._categories.values())[:5]}..."
        )

        # Build legacy data structures
        self._images = {}
        self._annotations_by_image = {}
        all_annotations = []

        for idx, record in enumerate(
            tqdm(self._dataset, desc="Building data structures")
        ):
            img_id = f"img_{idx}"

            # Get image path from the record
            img_path = (
                record["image"].filename
                if hasattr(record["image"], "filename")
                else None
            )

            self._images[img_id] = {
                "id": img_id,
                "file_name": Path(img_path).name if img_path else str(idx),
                "width": record["width"],
                "height": record["height"],
                "source_dir": Path(img_path).parent if img_path else Path("."),
                "source_name": "validation",
                "_pil_image": record["image"],
            }

            self._annotations_by_image[img_id] = []
            for ann_idx, (ann_id, area, bbox, cat_id) in enumerate(
                zip(
                    record["objects"]["id"],
                    record["objects"]["area"],
                    record["objects"]["bbox"],
                    record["objects"]["category"],
                )
            ):
                ann = {
                    "id": f"{img_id}_{ann_idx}",
                    "image_id": img_id,
                    "category_id": cat_id,
                    "bbox": bbox,
                    "area": area,
                    "iscrowd": 0,
                }
                self._annotations_by_image[img_id].append(ann)
                all_annotations.append(ann)

        print(f"Total annotations: {len(all_annotations)}")

        # Build label mapping
        if self._model is not None:
            self._coco_to_model = build_label_mapping(
                self._categories, self._model.config.label2id, self._single_category
            )

    def run(self) -> ValidationResults:
        """
        Run the full validation pipeline.

        Returns:
            ValidationResults containing all metrics and raw data.
        """
        # Load model and data if not already loaded
        if self._model is None:
            self.load_model()
        if self._dataset is None:
            self.load_data()

        # Build label mapping after both are loaded
        if self._coco_to_model is None:
            self._coco_to_model = build_label_mapping(
                self._categories, self._model.config.label2id, self._single_category
            )

        # Run inference
        predictions, targets, image_ids = self._run_inference()

        # Compute overall metrics (includes per-class mAP)
        overall_map_results = self._compute_overall_metrics(predictions, targets)

        # Compute per-subclass metrics and FN details
        subclass_metrics, fn_by_image = self._compute_subclass_metrics(
            predictions, image_ids, overall_map_results
        )

        # Compute TP/FP/FN counts
        total_tp, total_fp, total_fn = self._compute_precision_recall_f1(
            predictions, image_ids
        )
        total_gt = total_tp + total_fn

        # Compute precision/recall/F1
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / total_gt if total_gt > 0 else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        # Build overall metrics
        overall = OverallMetrics(
            map=float(overall_map_results["map"]),
            map_50=float(overall_map_results["map_50"]),
            map_75=float(overall_map_results["map_75"]),
            map_small=float(overall_map_results["map_small"]),
            map_medium=float(overall_map_results["map_medium"]),
            map_large=float(overall_map_results["map_large"]),
            mar_1=float(overall_map_results["mar_1"]),
            mar_10=float(overall_map_results["mar_10"]),
            mar_100=float(overall_map_results["mar_100"]),
            precision=precision,
            recall=recall,
            f1_score=f1,
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            total_ground_truth=total_gt,
            total_predictions=total_tp + total_fp,
            confidence_threshold=self.config.confidence_threshold,
            iou_threshold=self.config.iou_threshold,
            num_images=len(predictions),
        )

        # Build results
        results = ValidationResults(
            overall=overall,
            per_subclass=subclass_metrics,
            predictions=predictions,
            targets=targets,
            image_ids=image_ids,
            categories=self._categories,
            model_id2label=self._model.config.id2label,
            false_negatives_by_image=fn_by_image,
        )

        # Print summary
        print("\n=== Overall Detection Metrics ===")
        print(f"mAP (IoU 0.50:0.95): {overall.map:.4f}")
        print(f"mAP @ IoU 0.50:      {overall.map_50:.4f}")
        print(f"mAP @ IoU 0.75:      {overall.map_75:.4f}")
        print(f"Precision:           {overall.precision:.4f}")
        print(f"Recall:              {overall.recall:.4f}")
        print(f"F1 Score:            {overall.f1_score:.4f}")

        # Save results if configured
        if self.config.save_results:
            results.save(self.config.output_dir)

        # Generate visualizations if configured
        if self.config.generate_visualizations:
            self.generate_visualizations(results)

        return results

    def _run_inference(self) -> tuple[list[dict], list[dict], list[str]]:
        """
        Run model inference on all validation images.

        Returns:
            Tuple of (predictions, targets, image_ids).
        """
        all_predictions = []
        all_targets = []
        image_ids = list(self._images.keys())

        with torch.no_grad():
            for img_id in tqdm(image_ids, desc="Evaluating"):
                img_info = self._images[img_id]

                # Use stored PIL image or load from path
                if "_pil_image" in img_info:
                    image = img_info["_pil_image"].convert("RGB")
                else:
                    img_path = img_info["source_dir"] / img_info["file_name"]
                    if not img_path.exists():
                        # Skipping this image would leave its ID paired with a
                        # later image's prediction, corrupting downstream metrics.
                        raise FileNotFoundError(f"Validation image not found: {img_path}")
                    image = Image.open(img_path).convert("RGB")

                orig_w, orig_h = image.size

                # Apply custom preprocessing if configured
                if self._preprocessing_transform is not None:
                    image_np = np.array(image)
                    transformed = self._preprocessing_transform(image=image_np)
                    result = transformed["image"]

                    if self._preprocessing_includes_normalize:
                        # Pass pre-normalized array directly (processor has do_normalize=False)
                        inputs = self._processor(images=result, return_tensors="pt").to(
                            self.device
                        )
                    else:
                        # CLAHE or other non-normalizing transforms - convert back to PIL
                        image = Image.fromarray(result)
                        inputs = self._processor(images=image, return_tensors="pt").to(
                            self.device
                        )
                else:
                    inputs = self._processor(images=image, return_tensors="pt").to(
                        self.device
                    )

                # Forward pass
                outputs = self._model(**inputs)

                # Process outputs
                pred_boxes_norm = outputs.pred_boxes[0].cpu()
                logits = outputs.logits[0].cpu()

                # Apply sigmoid to get per-class probabilities
                probs = logits.sigmoid()
                max_scores, pred_labels = probs.max(dim=-1)

                # Filter by confidence threshold
                mask = max_scores > self.config.confidence_threshold
                pred_boxes_norm = pred_boxes_norm[mask]
                pred_scores = max_scores[mask]
                pred_labels_filtered = pred_labels[mask]

                # Convert coordinates
                pred_boxes_xyxy = convert_normalized_to_original(
                    pred_boxes_norm, (orig_w, orig_h), self._image_square_size
                )

                # Format predictions
                pred_dict = {
                    "boxes": (
                        torch.tensor(pred_boxes_xyxy, dtype=torch.float32)
                        if pred_boxes_xyxy
                        else torch.zeros((0, 4))
                    ),
                    "scores": (
                        pred_scores if len(pred_scores) > 0 else torch.zeros((0,))
                    ),
                    "labels": (
                        pred_labels_filtered
                        if len(pred_labels_filtered) > 0
                        else torch.zeros((0,), dtype=torch.int64)
                    ),
                }

                # Format ground truth
                gt_anns = self._annotations_by_image.get(img_id, [])
                gt_boxes = []
                gt_labels = []
                for ann in gt_anns:
                    x, y, w, h = ann["bbox"]
                    gt_boxes.append([x, y, x + w, y + h])
                    # A missing mapping must not silently become a seed label.
                    gt_labels.append(self._coco_to_model[ann["category_id"]])

                target_dict = {
                    "boxes": (
                        torch.tensor(gt_boxes, dtype=torch.float32)
                        if gt_boxes
                        else torch.zeros((0, 4))
                    ),
                    "labels": (
                        torch.tensor(gt_labels, dtype=torch.int64)
                        if gt_labels
                        else torch.zeros((0,), dtype=torch.int64)
                    ),
                }

                all_predictions.append(pred_dict)
                all_targets.append(target_dict)

        print(f"Evaluated {len(all_predictions)} images")
        return all_predictions, all_targets, image_ids

    def _compute_overall_metrics(
        self,
        predictions: list[dict],
        targets: list[dict],
    ) -> dict:
        """
        Compute overall mAP/mAR metrics using torchmetrics.

        Returns:
            Dict of metric name -> value.
        """
        metric = MeanAveragePrecision(
            box_format="xyxy", iou_type="bbox", class_metrics=True
        )

        for pred, target in zip(predictions, targets):
            metric.update([pred], [target])

        return metric.compute()

    def _compute_per_subclass_map(
        self,
        predictions: list[dict],
        image_ids: list[str],
        subclass_name: str,
    ) -> tuple[float, float]:
        """
        Compute mAP and mAR for a single subclass.

        Filters ground truth to only boxes of this subclass, then evaluates
        all predictions against this filtered GT using torchmetrics.

        Args:
            predictions: List of prediction dicts per image.
            image_ids: List of image IDs.
            subclass_name: Name of the subclass to evaluate.

        Returns:
            Tuple of (mAP, mAR) for this subclass.
        """
        # Find category ID for this subclass
        cat_id = None
        for cid, cname in self._categories.items():
            if cname == subclass_name:
                cat_id = cid
                break

        if cat_id is None:
            return 0.0, 0.0

        # Build filtered predictions and targets for this subclass only
        filtered_preds = []
        filtered_targets = []

        for img_idx, img_id in enumerate(image_ids):
            pred = predictions[img_idx]
            gt_anns = self._annotations_by_image.get(img_id, [])

            # Filter GT to only this subclass
            subclass_gt_boxes = []
            for ann in gt_anns:
                if ann["category_id"] == cat_id:
                    x, y, w, h = ann["bbox"]
                    subclass_gt_boxes.append([x, y, x + w, y + h])

            # Only include images that have GT for this subclass
            if len(subclass_gt_boxes) > 0:
                # Use all predictions (single-class detector outputs class 0 for all)
                filtered_preds.append(
                    {
                        "boxes": pred["boxes"],
                        "scores": pred["scores"],
                        "labels": torch.zeros(len(pred["boxes"]), dtype=torch.int64),
                    }
                )
                filtered_targets.append(
                    {
                        "boxes": torch.tensor(subclass_gt_boxes, dtype=torch.float32),
                        "labels": torch.zeros(
                            len(subclass_gt_boxes), dtype=torch.int64
                        ),
                    }
                )

        if len(filtered_preds) == 0:
            return 0.0, 0.0

        # Compute mAP using torchmetrics
        metric = MeanAveragePrecision(box_format="xyxy", iou_type="bbox")
        for pred, target in zip(filtered_preds, filtered_targets):
            metric.update([pred], [target])

        result = metric.compute()
        class_map = float(result["map"])
        class_mar = float(result["mar_100"])

        # Handle NaN
        if np.isnan(class_map):
            class_map = 0.0
        if np.isnan(class_mar):
            class_mar = 0.0

        return class_map, class_mar

    def _compute_subclass_metrics(
        self,
        predictions: list[dict],
        image_ids: list[str],
        overall_map_results: dict,
    ) -> tuple[list[SubclassMetrics], list[dict]]:
        """
        Compute per-subclass metrics and false negative details.

        Args:
            predictions: List of prediction dicts per image.
            image_ids: List of image IDs.
            overall_map_results: Results from torchmetrics MeanAveragePrecision
                                 (used for multi-class models).

        Returns:
            Tuple of (subclass_metrics_list, fn_by_image_list).
        """
        # Check if this is a single-class model
        is_single_class = len(self._model.config.id2label) == 1

        # Extract per-class metrics from torchmetrics results (for multi-class models)
        map_per_class = overall_map_results.get("map_per_class", torch.tensor([]))
        mar_100_per_class = overall_map_results.get(
            "mar_100_per_class", torch.tensor([])
        )
        classes_tensor = overall_map_results.get("classes", torch.tensor([]))

        subclass_preds = defaultdict(list)
        subclass_gts = defaultdict(list)
        subclass_tp = defaultdict(int)
        subclass_fn = defaultdict(int)
        subclass_fp = defaultdict(int)
        fn_by_image = []

        for img_idx, img_id in enumerate(image_ids):
            pred = predictions[img_idx]
            gt_anns = self._annotations_by_image.get(img_id, [])

            pred_boxes = pred["boxes"].numpy()
            pred_scores = pred["scores"].numpy()

            pred_matched = [False] * len(pred_boxes)

            fn_boxes = []
            fn_categories = []
            tp_boxes = []
            tp_categories = []

            # Build list of GT boxes with their categories for FP attribution
            gt_boxes_with_cats = []
            for ann in gt_anns:
                cat_name = self._categories[ann["category_id"]]
                x, y, w, h = ann["bbox"]
                gt_box = [x, y, x + w, y + h]
                gt_boxes_with_cats.append((gt_box, cat_name))
                subclass_gts[cat_name].append(gt_box)

            for ann in gt_anns:
                cat_name = self._categories[ann["category_id"]]
                x, y, w, h = ann["bbox"]
                gt_box = [x, y, x + w, y + h]

                # Find best matching prediction
                best_iou = 0
                best_pred_idx = -1
                for pred_idx, pbox in enumerate(pred_boxes):
                    if pred_matched[pred_idx]:
                        continue
                    iou = compute_iou(gt_box, pbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_pred_idx = pred_idx

                if best_iou >= self.config.iou_threshold and best_pred_idx >= 0:
                    pred_matched[best_pred_idx] = True
                    subclass_preds[cat_name].append(
                        {
                            "score": pred_scores[best_pred_idx],
                            "matched": True,
                            "iou": best_iou,
                        }
                    )
                    subclass_tp[cat_name] += 1
                    tp_boxes.append(gt_box)
                    tp_categories.append(cat_name)
                else:
                    subclass_preds[cat_name].append(
                        {"score": 0, "matched": False, "iou": 0}
                    )
                    subclass_fn[cat_name] += 1
                    fn_boxes.append(gt_box)
                    fn_categories.append(cat_name)

            # Attribute FP to nearest GT subclass
            fp_boxes = []
            fp_scores = []
            fp_categories = []
            for pred_idx, pbox in enumerate(pred_boxes):
                if not pred_matched[pred_idx]:
                    fp_boxes.append(pbox.tolist())
                    fp_scores.append(pred_scores[pred_idx])

                    # Find nearest GT box to attribute this FP
                    if len(gt_boxes_with_cats) > 0:
                        best_iou = -1
                        best_cat = None
                        for gt_box, cat_name in gt_boxes_with_cats:
                            iou = compute_iou(pbox.tolist(), gt_box)
                            if iou > best_iou:
                                best_iou = iou
                                best_cat = cat_name
                        if best_cat is not None:
                            subclass_fp[best_cat] += 1
                            fp_categories.append(best_cat)
                        else:
                            fp_categories.append(None)
                    else:
                        fp_categories.append(None)

            # Track FN details for this image
            if len(fn_boxes) > 0 or len(fp_boxes) > 0:
                fn_by_image.append(
                    {
                        "img_id": img_id,
                        "img_idx": img_idx,
                        "num_fn": len(fn_boxes),
                        "num_tp": len(tp_boxes),
                        "num_fp": len(fp_boxes),
                        "fn_boxes": fn_boxes,
                        "fn_categories": fn_categories,
                        "tp_boxes": tp_boxes,
                        "tp_categories": tp_categories,
                        "fp_boxes": fp_boxes,
                        "fp_scores": fp_scores,
                        "fp_categories": fp_categories,
                    }
                )

        # Build mapping from model label ID to torchmetrics class index
        # torchmetrics returns metrics indexed by the class IDs present in predictions/targets
        class_id_to_idx = {}
        # Handle 0-d tensor (single class) vs 1-d tensor (multiple classes)
        if classes_tensor.dim() == 0:
            # Single class case: classes_tensor is a scalar
            class_id_to_idx[int(classes_tensor.item())] = 0
        elif classes_tensor.numel() > 0:
            for idx, class_id in enumerate(classes_tensor.tolist()):
                class_id_to_idx[int(class_id)] = idx

        # Build metrics for each subclass
        subclass_metrics = []
        for cat_name in sorted(self._categories.values()):
            num_gt = len(subclass_gts[cat_name])
            tp = subclass_tp[cat_name]
            fp = subclass_fp[cat_name]
            fn = subclass_fn[cat_name]

            if num_gt > 0:
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                detection_rate = tp / num_gt if num_gt > 0 else 0

                # Get the model label ID for this category
                # Find cat_id from categories dict
                cat_id = None
                for cid, cname in self._categories.items():
                    if cname == cat_name:
                        cat_id = cid
                        break

                # Category zero is a real species ID, not a missing category.
                model_label_id = (
                    self._coco_to_model.get(cat_id, 0) if cat_id is not None else 0
                )

                # Compute per-class mAP
                if is_single_class:
                    # For single-class models, compute mAP per subclass directly
                    class_map, class_mar = self._compute_per_subclass_map(
                        predictions, image_ids, cat_name
                    )
                else:
                    # For multi-class models, look up from torchmetrics results
                    if model_label_id in class_id_to_idx:
                        idx = class_id_to_idx[model_label_id]
                        # Handle 0-d tensors (single class) vs 1-d tensors
                        if map_per_class.dim() == 0:
                            class_map = float(map_per_class.item()) if idx == 0 else 0.0
                        else:
                            class_map = (
                                float(map_per_class[idx])
                                if idx < map_per_class.numel()
                                else 0.0
                            )

                        if mar_100_per_class.dim() == 0:
                            class_mar = (
                                float(mar_100_per_class.item()) if idx == 0 else 0.0
                            )
                        else:
                            class_mar = (
                                float(mar_100_per_class[idx])
                                if idx < mar_100_per_class.numel()
                                else 0.0
                            )

                        # Handle NaN values (classes with no predictions)
                        if np.isnan(class_map):
                            class_map = 0.0
                        if np.isnan(class_mar):
                            class_mar = 0.0
                    else:
                        # Class not in torchmetrics results (no predictions for this class)
                        class_map = 0.0
                        class_mar = 0.0

                subclass_metrics.append(
                    SubclassMetrics(
                        subclass=cat_name,
                        num_gt=num_gt,
                        num_matched=tp,
                        tp=tp,
                        fp=fp,
                        fn=fn,
                        precision=precision,
                        recall=recall,
                        detection_rate=detection_rate,
                        map=class_map,
                        mar=class_mar,
                    )
                )

        return subclass_metrics, fn_by_image

    def _compute_precision_recall_f1(
        self,
        predictions: list[dict],
        image_ids: list[str],
    ) -> tuple[int, int, int]:
        """
        Compute overall TP, FP, FN counts.

        Returns:
            Tuple of (total_tp, total_fp, total_fn).
        """
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for img_idx, img_id in enumerate(image_ids):
            pred = predictions[img_idx]
            gt_anns = self._annotations_by_image.get(img_id, [])

            pred_boxes = pred["boxes"].numpy()
            pred_matched = [False] * len(pred_boxes)

            for ann in gt_anns:
                x, y, w, h = ann["bbox"]
                gt_box = [x, y, x + w, y + h]

                best_iou = 0
                best_pred_idx = -1
                for pred_idx, pbox in enumerate(pred_boxes):
                    if pred_matched[pred_idx]:
                        continue
                    iou = compute_iou(gt_box, pbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_pred_idx = pred_idx

                if best_iou >= self.config.iou_threshold and best_pred_idx >= 0:
                    pred_matched[best_pred_idx] = True
                    total_tp += 1
                else:
                    total_fn += 1

            total_fp += sum(1 for m in pred_matched if not m)

        return total_tp, total_fp, total_fn

    def generate_visualizations(self, results: ValidationResults) -> None:
        """
        Generate and save all visualization plots.

        Args:
            results: Validation results to visualize.
        """
        output_dir = self.config.output_dir
        df = results.to_dataframe()

        # Annotation distribution
        plot_annotation_distribution(
            self._categories,
            [ann for anns in self._annotations_by_image.values() for ann in anns],
            output_path=output_dir / "annotation_distribution.png",
        )

        # Subclass heatmap
        plot_subclass_heatmap(
            df,
            output_path=output_dir / "per_subclass_heatmap.png",
        )

        # Subclass metrics table
        plot_subclass_metrics_table(
            df,
            output_path=output_dir / "per_subclass_metrics_table.png",
        )

        # Precision/recall bars
        plot_precision_recall_bars(
            df,
            results.overall.recall,
            self.config.iou_threshold,
            output_path=output_dir / "per_subclass_precision_recall.png",
        )

        # Detection issues
        plot_detection_issues(
            df,
            highlight_threshold=0.90,
            iou_threshold=self.config.iou_threshold,
            output_path=output_dir / "detection_issues.png",
        )

        # False negatives by subclass
        fn_by_subclass = defaultdict(list)
        for fn_info in results.false_negatives_by_image:
            for box, cat in zip(fn_info["fn_boxes"], fn_info["fn_categories"]):
                fn_by_subclass[cat].append({"img_id": fn_info["img_id"], "box": box})

        plot_false_negatives_by_subclass(
            fn_by_subclass,
            self.config.iou_threshold,
            output_path=output_dir / "false_negatives_by_subclass.png",
        )

        # False positives by subclass (attributed by nearest GT)
        fp_by_subclass = defaultdict(list)
        for fn_info in results.false_negatives_by_image:
            for box, score, cat in zip(
                fn_info["fp_boxes"], fn_info["fp_scores"], fn_info["fp_categories"]
            ):
                if cat is not None:
                    fp_by_subclass[cat].append(
                        {
                            "img_id": fn_info["img_id"],
                            "box": box,
                            "score": score,
                        }
                    )

        plot_false_positives_by_subclass(
            fp_by_subclass,
            self.config.iou_threshold,
            output_path=output_dir / "false_positives_by_subclass.png",
        )

        # False negative examples
        if len(results.false_negatives_by_image) > 0:
            plot_false_negative_examples(
                results.false_negatives_by_image,
                self._images,
                self._categories,
                self.config.iou_threshold,
                examples_per_class=2,
                output_path=output_dir / "false_negative_by_class.png",
            )

        # mAP summary
        plot_map_summary(
            results.overall,
            output_path=output_dir / "map_summary.png",
        )

        # Sample predictions
        plot_sample_predictions(
            self._images,
            results.predictions,
            results.targets,
            results.image_ids,
            results.model_id2label,
            num_samples=6,
            output_path=output_dir / "sample_predictions.png",
        )

        # Confidence distribution
        plot_confidence_distribution(
            results.predictions,
            self.config.confidence_threshold,
            output_path=output_dir / "confidence_distribution.png",
        )

        # Threshold optimization
        _, optimal_threshold = plot_threshold_optimization(
            results.predictions,
            results.targets,
            self._annotations_by_image,
            results.image_ids,
            iou_threshold=self.config.iou_threshold,
            output_path=output_dir / "threshold_optimization.png",
        )
        if optimal_threshold is not None:
            print(f"Recommended confidence threshold: {optimal_threshold:.2f}")

        print(f"Visualizations saved to {output_dir}")


# =============================================================================
# Visualization Functions
# =============================================================================


def plot_annotation_distribution(
    categories: dict[int, str],
    annotations: list[dict],
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot bar chart of annotations per class."""
    ann_counts = {}
    for ann in annotations:
        cat_name = categories[ann["category_id"]]
        ann_counts[cat_name] = ann_counts.get(cat_name, 0) + 1

    ann_df = pd.DataFrame(
        {"class": list(ann_counts.keys()), "annotations": list(ann_counts.values())}
    ).sort_values("class")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(ann_df["class"], ann_df["annotations"], color="tab:blue", alpha=0.8)
    ax.set_ylabel("Annotations")
    ax.set_title("Validation Annotations per Class")
    ax.set_xticklabels(ann_df["class"], rotation=45, ha="right", fontsize=8)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_heatmap(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot heatmap of mAP (IoU 0.50:0.95) and mAR per subclass."""
    # Transpose: classes on x-axis, metrics on y-axis
    fig, ax = plt.subplots(figsize=(max(14, len(subclass_df) * 0.5), 3))

    heatmap_df = subclass_df[["subclass", "map", "mar"]].set_index("subclass")
    heatmap_df = heatmap_df.sort_index()
    heatmap_df = heatmap_df.T  # Transpose

    sns.heatmap(
        heatmap_df,
        annot=True,
        fmt=".3f",
        cmap="RdYlGn",
        vmin=0.8,
        vmax=1,
        ax=ax,
        cbar=False,
        annot_kws={"fontsize": 8},
    )
    ax.set_title(
        "Per-Subclass Detection Performance (mAP IoU 0.50:0.95 and mAR@100)",
        fontsize=14,
    )
    ax.set_xlabel("Subclass", fontsize=12)
    ax.set_ylabel("Metric", fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_metrics_table(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
    sort_alphabetically: bool = True,
    performance_red_threshold: float = 0.80,
) -> plt.Figure:
    """
    Render per-subclass metrics as a seaborn table and highlight worst values.

    Score columns use threshold-based coloring. Count columns are neutral,
    except FP and FN are flagged when they exceed 10% of the row's ground-truth
    count.

    Args:
        subclass_df: DataFrame with one row per subclass.
        output_path: Optional path to save the rendered table image.
        show: Whether to display the plot.
        sort_alphabetically: Whether to sort subclasses alphabetically.
        performance_red_threshold: Red color cutoff for precision/recall,
            detection rate, mAP, and mAR.
    """
    columns = [
        "num_gt",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "detection_rate",
        "map",
        "mar",
    ]
    missing_columns = [col for col in ["subclass", *columns] if col not in subclass_df]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    table_df = subclass_df[["subclass", *columns]].copy()
    if sort_alphabetically:
        table_df = table_df.sort_values("subclass")
    table_df = table_df.set_index("subclass")

    display_columns = {"num_gt": "num_ground_truth"}
    score_df = pd.DataFrame(0.5, index=table_df.index, columns=columns, dtype=float)
    performance_columns = ["precision", "recall", "detection_rate", "map", "mar"]
    error_columns = ["fp", "fn"]
    highlighted_columns = performance_columns + error_columns

    threshold_range = 1.0 - performance_red_threshold
    if threshold_range <= 0:
        raise ValueError("performance_red_threshold must be less than 1.0")
    for col in performance_columns:
        values = table_df[col].astype(float)
        score_df[col] = ((values - performance_red_threshold) / threshold_range).clip(0, 1)

    gt_values = table_df["num_gt"].astype(float)
    error_ratios = pd.DataFrame(0.0, index=table_df.index, columns=error_columns)
    for col in error_columns:
        values = table_df[col].astype(float)
        error_ratios[col] = (values / gt_values.replace(0, np.nan)).fillna(0)
        flagged = error_ratios[col] > 0.10
        if flagged.any():
            max_ratio = error_ratios.loc[flagged, col].max()
            if max_ratio > 0.10:
                severity = ((error_ratios[col] - 0.10) / (max_ratio - 0.10)).clip(0, 1)
                score_df.loc[flagged, col] = 1 - severity.loc[flagged]
            else:
                score_df.loc[flagged, col] = 0

    annotations = table_df.copy()
    integer_columns = ["num_gt", "tp", "fp", "fn"]
    for col in integer_columns:
        annotations[col] = annotations[col].astype(int).astype(str)
    for col in set(columns) - set(integer_columns):
        annotations[col] = annotations[col].map(lambda value: f"{value:.3f}")

    score_df = score_df.rename(columns=display_columns)
    annotations = annotations.rename(columns=display_columns)

    fig_width = max(12, len(columns) * 1.15)
    fig_height = max(4, len(table_df) * 0.42 + 1.5)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    sns.heatmap(
        score_df,
        annot=annotations,
        fmt="",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        cbar=False,
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        annot_kws={"fontsize": 8},
    )

    neutral_columns = ["num_gt", "tp"]
    for col_name in neutral_columns:
        col_idx = columns.index(col_name)
        display_col_name = display_columns.get(col_name, col_name)
        for row_idx, value in enumerate(annotations[display_col_name]):
            ax.add_patch(
                mpatches.Rectangle(
                    (col_idx, row_idx),
                    1,
                    1,
                    facecolor="white",
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=2,
                )
            )
            ax.text(
                col_idx + 0.5,
                row_idx + 0.5,
                value,
                ha="center",
                va="center",
                fontsize=8,
                color="black",
                zorder=3,
            )

    for col_name in highlighted_columns:
        col_idx = columns.index(col_name)
        if col_name in error_columns:
            flagged_rows = error_ratios[col_name] > 0.10
        else:
            values = table_df[col_name].astype(float)
            flagged_rows = np.isclose(values, values.min())

        for row_idx, flagged in enumerate(flagged_rows):
            if flagged:
                ax.add_patch(
                    mpatches.Rectangle(
                        (col_idx, row_idx),
                        1,
                        1,
                        fill=False,
                        edgecolor="black",
                        linewidth=2,
                    )
                )

    ax.set_title("Per-Subclass Metrics Table (flagged values outlined)", fontsize=14)
    ax.set_xlabel("Metric", fontsize=12)
    ax.set_ylabel("Subclass", fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=8)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_map(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot vertical bar chart of mAP (IoU 0.50:0.95) per subclass."""
    fig, ax = plt.subplots(figsize=(max(12, len(subclass_df) * 0.4), 6))

    plot_df = subclass_df.sort_values("subclass")  # Alphabetical order

    # Color bars using heatmap colormap (RdYlGn) normalized to 0.8-1.0 range
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=0.8, vmax=1.0)
    # Clip values to range and apply colormap
    map_values = plot_df["map"].values
    colors = [cmap(norm(np.clip(m, 0.8, 1.0))) for m in map_values]

    bars = ax.bar(range(len(plot_df)), plot_df["map"], color=colors, alpha=0.9)
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["subclass"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("mAP (IoU 0.50:0.95)", fontsize=12)
    ax.set_xlabel("Subclass", fontsize=12)
    ax.set_title("Per-Subclass mAP (IoU 0.50:0.95)", fontsize=14)
    ax.set_ylim(0.8, 1.05)

    # Add value labels on bars
    for bar, val in zip(bars, plot_df["map"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.02,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    # Add overall mean line
    mean_map = plot_df["map"].mean()
    ax.axhline(
        y=mean_map,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {mean_map:.3f}",
    )
    ax.legend(loc="upper right")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_mar(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot vertical bar chart of mAR@100 per subclass."""
    fig, ax = plt.subplots(figsize=(max(12, len(subclass_df) * 0.4), 6))

    plot_df = subclass_df.sort_values("subclass")  # Alphabetical order

    # Color bars using heatmap colormap (RdYlGn) normalized to 0.8-1.0 range
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=0.8, vmax=1.0)
    mar_values = plot_df["mar"].values
    colors = [cmap(norm(np.clip(m, 0.8, 1.0))) for m in mar_values]

    bars = ax.bar(range(len(plot_df)), plot_df["mar"], color=colors, alpha=0.9)
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["subclass"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("mAR@100", fontsize=12)
    ax.set_xlabel("Subclass", fontsize=12)
    ax.set_title("Per-Subclass mAR@100", fontsize=14)
    ax.set_ylim(0.8, 1.05)

    # Add value labels on bars
    for bar, val in zip(bars, plot_df["mar"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.02,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    # Add overall mean line
    mean_mar = plot_df["mar"].mean()
    ax.axhline(
        y=mean_mar,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {mean_mar:.3f}",
    )
    ax.legend(loc="upper right")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_precision(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot vertical bar chart of precision per subclass."""
    fig, ax = plt.subplots(figsize=(max(12, len(subclass_df) * 0.4), 6))

    plot_df = subclass_df.sort_values("subclass")  # Alphabetical order

    # Color bars using heatmap colormap (RdYlGn) normalized to 0.8-1.0 range
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=0.8, vmax=1.0)
    precision_values = plot_df["precision"].values
    colors = [cmap(norm(np.clip(p, 0.8, 1.0))) for p in precision_values]

    bars = ax.bar(range(len(plot_df)), plot_df["precision"], color=colors, alpha=0.9)
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["subclass"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_xlabel("Subclass", fontsize=12)
    ax.set_title("Per-Subclass Precision", fontsize=14)
    ax.set_ylim(0.8, 1.05)

    # Add value labels on bars
    for bar, val in zip(bars, plot_df["precision"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.02,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    # Add overall mean line
    mean_precision = plot_df["precision"].mean()
    ax.axhline(
        y=mean_precision,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {mean_precision:.3f}",
    )
    ax.legend(loc="upper right")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_subclass_recall(
    subclass_df: pd.DataFrame,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot vertical bar chart of recall per subclass."""
    fig, ax = plt.subplots(figsize=(max(12, len(subclass_df) * 0.4), 6))

    plot_df = subclass_df.sort_values("subclass")  # Alphabetical order

    # Color bars using heatmap colormap (RdYlGn) normalized to 0.8-1.0 range
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=0.8, vmax=1.0)
    recall_values = plot_df["recall"].values
    colors = [cmap(norm(np.clip(r, 0.8, 1.0))) for r in recall_values]

    bars = ax.bar(range(len(plot_df)), plot_df["recall"], color=colors, alpha=0.9)
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["subclass"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Recall", fontsize=12)
    ax.set_xlabel("Subclass", fontsize=12)
    ax.set_title("Per-Subclass Recall", fontsize=14)
    ax.set_ylim(0.8, 1.05)

    # Add value labels on bars
    for bar, val in zip(bars, plot_df["recall"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + 0.02,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    # Add overall mean line
    mean_recall = plot_df["recall"].mean()
    ax.axhline(
        y=mean_recall,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {mean_recall:.3f}",
    )
    ax.legend(loc="upper right")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_precision_recall_bars(
    subclass_df: pd.DataFrame,
    overall_recall: float,
    iou_threshold: float,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot per-subclass recall bars and TP/FN stacked bars."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    plot_prf = subclass_df.sort_values("recall", ascending=True)

    # Per-subclass recall
    ax1 = axes[0]
    colors = [
        "tab:green" if r >= 0.8 else "tab:orange" if r >= 0.5 else "tab:red"
        for r in plot_prf["recall"]
    ]
    bars = ax1.barh(plot_prf["subclass"], plot_prf["recall"], color=colors, alpha=0.8)
    ax1.set_xlabel("Recall (Detection Rate)", fontsize=12)
    ax1.set_ylabel("Subclass", fontsize=12)
    ax1.set_title(f"Per-Subclass Recall @ IoU>={iou_threshold}", fontsize=14)
    ax1.set_xlim(0, 1.1)
    ax1.axvline(
        x=overall_recall,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=f"Overall Recall: {overall_recall:.3f}",
    )
    ax1.legend(loc="lower right")
    ax1.tick_params(axis="y", labelsize=8)

    for bar, val in zip(bars, plot_prf["recall"]):
        ax1.text(
            val + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}",
            va="center",
            fontsize=7,
        )

    # TP vs FN stacked bar
    ax2 = axes[1]
    plot_prf_sorted = subclass_df.sort_values("subclass")
    ax2.barh(
        plot_prf_sorted["subclass"],
        plot_prf_sorted["tp"],
        label="TP (Detected)",
        color="tab:green",
        alpha=0.8,
    )
    ax2.barh(
        plot_prf_sorted["subclass"],
        plot_prf_sorted["fn"],
        left=plot_prf_sorted["tp"],
        label="FN (Missed)",
        color="tab:red",
        alpha=0.8,
    )
    ax2.set_xlabel("Count", fontsize=12)
    ax2.set_ylabel("Subclass", fontsize=12)
    ax2.set_title("True Positives vs False Negatives per Subclass", fontsize=14)
    ax2.legend(loc="lower right")
    ax2.tick_params(axis="y", labelsize=8)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_detection_issues(
    subclass_df: pd.DataFrame,
    highlight_threshold: float = 0.90,
    iou_threshold: float = 0.5,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot subclasses with FN > 0 or detection rate below threshold."""
    conf_df_filtered = subclass_df[
        (subclass_df["fn"] > 0) | (subclass_df["detection_rate"] < highlight_threshold)
    ]

    if len(conf_df_filtered) == 0:
        print("All subclasses have 100% detection rate with no false negatives!")
        return None

    plot_df = conf_df_filtered.sort_values("detection_rate", ascending=True)

    fig, ax = plt.subplots(figsize=(14, max(4, len(plot_df) * 0.4)))

    ax.barh(
        plot_df["subclass"],
        plot_df["tp"],
        label="TP (Detected)",
        color="tab:green",
        alpha=0.8,
    )
    ax.barh(
        plot_df["subclass"],
        plot_df["fn"],
        left=plot_df["tp"],
        label="FN (Missed)",
        color="tab:red",
        alpha=0.8,
    )

    ax.set_xlabel("Count", fontsize=12)
    ax.set_ylabel("Subclass", fontsize=12)
    ax.set_title(
        f"Detection Issues: Subclasses with FN > 0 or Detection Rate < {highlight_threshold * 100:.0f}%",
        fontsize=14,
    )
    ax.legend(loc="lower right")
    ax.tick_params(axis="y", labelsize=9)

    # Add detection rate labels
    subclass_list = plot_df["subclass"].tolist()
    for idx, row in plot_df.iterrows():
        total = row["tp"] + row["fn"]
        y_pos = subclass_list.index(row["subclass"])
        ax.text(
            total + 0.5,
            y_pos,
            f"{row['detection_rate'] * 100:.1f}%",
            va="center",
            fontsize=8,
            color="gray",
        )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_false_negative_examples(
    fn_per_image: list[dict],
    images: dict,
    categories: dict[int, str],
    iou_threshold: float,
    examples_per_class: int = 2,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot FN examples grouped by class."""
    # Group FN images by class
    fn_images_by_class = defaultdict(list)
    for fn_info in fn_per_image:
        for cat in set(fn_info["fn_categories"]):
            fn_images_by_class[cat].append(fn_info)

    classes_with_fn = sorted(fn_images_by_class.keys())

    if len(classes_with_fn) == 0:
        print("No false negatives found!")
        return None

    # Collect examples
    examples_to_show = []
    for cls in classes_with_fn:
        cls_images = fn_images_by_class[cls][:examples_per_class]
        for fn_info in cls_images:
            examples_to_show.append((cls, fn_info))

    num_examples = len(examples_to_show)
    cols = 2
    rows = (num_examples + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 6 * rows))
    axes = np.asarray(axes).reshape(-1)

    for i, (ax, (cls, fn_info)) in enumerate(
        zip(axes[:num_examples], examples_to_show)
    ):
        img_info = images[fn_info["img_id"]]
        _draw_fn_visualization(ax, img_info, fn_info, highlight_class=cls)

        cls_fn_count = sum(1 for c in fn_info["fn_categories"] if c == cls)
        ax.set_title(
            f"{cls}\n[{img_info['source_name']}] {img_info['file_name']}\n({cls_fn_count} missed)",
            fontsize=9,
        )
        ax.axis("off")

    for ax in axes[num_examples:]:
        ax.axis("off")

    plt.suptitle(
        f"False Negative Examples by Class (up to {examples_per_class} per class) @ IoU>={iou_threshold}",
        fontsize=14,
        y=1.01,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def _draw_fn_visualization(ax, img_info, fn_info, highlight_class=None):
    """Draw image with TP, FN, and FP boxes highlighted."""
    if "_pil_image" in img_info:
        image = img_info["_pil_image"].convert("RGB")
    else:
        img_path = img_info["source_dir"] / img_info["file_name"]
        image = Image.open(img_path).convert("RGB")

    ax.imshow(image)

    # Draw true positives (green)
    for box, cat in zip(fn_info["tp_boxes"], fn_info["tp_categories"]):
        x1, y1, x2, y2 = box
        alpha = 0.8 if highlight_class is None or cat == highlight_class else 0.3
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=2,
            edgecolor="green",
            facecolor="none",
            linestyle="-",
            alpha=alpha,
        )
        ax.add_patch(rect)

    # Draw false negatives (orange dashed)
    for box, cat in zip(fn_info["fn_boxes"], fn_info["fn_categories"]):
        x1, y1, x2, y2 = box
        is_highlight = highlight_class is None or cat == highlight_class
        linewidth = 3 if is_highlight else 1
        alpha = 0.8 if is_highlight else 0.3
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=linewidth,
            edgecolor="orange",
            facecolor="none",
            linestyle="--",
            alpha=alpha,
        )
        ax.add_patch(rect)
        if is_highlight:
            ax.text(
                x1,
                y2 + 5,
                f"MISSED: {cat}",
                fontsize=7,
                color="darkorange",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
            )

    # Draw false positives (red dotted)
    for box, score in zip(fn_info["fp_boxes"], fn_info["fp_scores"]):
        x1, y1, x2, y2 = box
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=1,
            edgecolor="red",
            facecolor="none",
            linestyle=":",
            alpha=0.4,
        )
        ax.add_patch(rect)


def plot_false_negatives_by_subclass(
    fn_by_subclass: dict[str, list],
    iou_threshold: float,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot bar chart of FN counts per subclass."""
    fn_subclass_counts = {cat: len(boxes) for cat, boxes in fn_by_subclass.items()}
    fn_subclass_df = pd.DataFrame(
        [
            {"subclass": cat, "false_negatives": count}
            for cat, count in fn_subclass_counts.items()
        ],
        columns=["subclass", "false_negatives"],
    ).sort_values("false_negatives", ascending=False)

    if len(fn_subclass_df) == 0:
        return None

    fig, ax = plt.subplots(figsize=(14, 6))
    fn_subclass_sorted = fn_subclass_df.sort_values("false_negatives", ascending=True)
    bars = ax.barh(
        fn_subclass_sorted["subclass"],
        fn_subclass_sorted["false_negatives"],
        color="tab:orange",
        alpha=0.8,
    )
    ax.set_xlabel("Number of False Negatives (Missed Detections)", fontsize=12)
    ax.set_ylabel("Subclass", fontsize=12)
    ax.set_title(f"False Negatives per Subclass @ IoU>={iou_threshold}", fontsize=14)
    ax.tick_params(axis="y", labelsize=8)

    for bar, val in zip(bars, fn_subclass_sorted["false_negatives"]):
        ax.text(
            val + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val}",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_false_positives_by_subclass(
    fp_by_subclass: dict[str, list],
    iou_threshold: float,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot bar chart of FP counts per subclass (attributed by nearest GT)."""
    fp_subclass_counts = {cat: len(items) for cat, items in fp_by_subclass.items()}
    fp_subclass_df = pd.DataFrame(
        [
            {"subclass": cat, "false_positives": count}
            for cat, count in fp_subclass_counts.items()
        ],
        columns=["subclass", "false_positives"],
    ).sort_values("false_positives", ascending=False)

    if len(fp_subclass_df) == 0:
        print("No false positives found!")
        return None

    fig, ax = plt.subplots(figsize=(14, 6))
    fp_subclass_sorted = fp_subclass_df.sort_values("false_positives", ascending=True)
    bars = ax.barh(
        fp_subclass_sorted["subclass"],
        fp_subclass_sorted["false_positives"],
        color="tab:red",
        alpha=0.8,
    )
    ax.set_xlabel("Number of False Positives (Spurious Detections)", fontsize=12)
    ax.set_ylabel("Subclass (attributed by nearest GT)", fontsize=12)
    ax.set_title(f"False Positives per Subclass @ IoU>={iou_threshold}", fontsize=14)
    ax.tick_params(axis="y", labelsize=8)

    for bar, val in zip(bars, fp_subclass_sorted["false_positives"]):
        ax.text(
            val + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val}",
            va="center",
            fontsize=8,
        )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_class_examples(
    subclass_df: pd.DataFrame,
    images: dict,
    predictions: list[dict],
    targets: list[dict],
    image_ids: list[str],
    annotations_by_image: dict,
    categories: dict[int, str],
    model_id2label: dict[int, str],
    subclass: Optional[str] = None,
    num_examples: int = 6,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """
    Plot example images for a specific class showing GT and predictions.

    If no subclass is specified, uses the class with the worst mAP.

    Args:
        subclass_df: DataFrame with per-subclass metrics (must have 'subclass' and 'map' columns).
        images: Dict mapping image_id to image info.
        predictions: List of prediction dicts per image.
        targets: List of target dicts per image.
        image_ids: List of image IDs in order.
        annotations_by_image: Dict mapping image_id to list of annotation dicts.
        categories: Category ID to name mapping.
        model_id2label: Model's ID to label mapping.
        subclass: Class name to visualize. If None, uses worst mAP class.
        num_examples: Number of example images to show.
        output_path: Optional path to save figure.
        show: Whether to display the figure.

    Returns:
        matplotlib Figure.
    """
    # Find the target class
    if subclass is None:
        # Use class with worst mAP
        worst_row = subclass_df.loc[subclass_df["map"].idxmin()]
        subclass = worst_row["subclass"]
        subclass_map = worst_row["map"]
        print(
            f"Showing examples for worst mAP class: {subclass} (mAP: {subclass_map:.3f})"
        )
    else:
        row = subclass_df[subclass_df["subclass"] == subclass]
        if len(row) == 0:
            print(f"Class '{subclass}' not found in results")
            return None
        subclass_map = row["map"].values[0]
        print(f"Showing examples for: {subclass} (mAP: {subclass_map:.3f})")

    # Find category ID for this subclass
    target_cat_id = None
    for cat_id, cat_name in categories.items():
        if cat_name == subclass:
            target_cat_id = cat_id
            break

    if target_cat_id is None:
        print(f"Category ID not found for '{subclass}'")
        return None

    # Find images that have GT annotations for this class
    class_image_ids = []
    for img_id in image_ids:
        anns = annotations_by_image.get(img_id, [])
        for ann in anns:
            if ann["category_id"] == target_cat_id:
                class_image_ids.append(img_id)
                break

    if len(class_image_ids) == 0:
        print(f"No images found with GT for class '{subclass}'")
        return None

    # Sample images
    sample_ids = class_image_ids[:num_examples]

    cols = 3
    rows = (len(sample_ids) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows))
    axes = np.asarray(axes).reshape(-1)

    for ax, img_id in zip(axes[: len(sample_ids)], sample_ids):
        img_info = images[img_id]
        img_idx = image_ids.index(img_id)
        pred = predictions[img_idx]
        anns = annotations_by_image.get(img_id, [])

        # Load image
        if "_pil_image" in img_info:
            image = img_info["_pil_image"].convert("RGB")
        else:
            img_path = img_info["source_dir"] / img_info["file_name"]
            image = Image.open(img_path).convert("RGB")

        ax.imshow(image)

        # Draw GT boxes for this class (green solid)
        gt_count = 0
        for ann in anns:
            if ann["category_id"] == target_cat_id:
                x, y, w, h = ann["bbox"]
                rect = mpatches.Rectangle(
                    (x, y),
                    w,
                    h,
                    linewidth=2,
                    edgecolor="green",
                    facecolor="none",
                    linestyle="-",
                )
                ax.add_patch(rect)
                ax.text(
                    x,
                    y - 3,
                    "GT",
                    fontsize=7,
                    color="green",
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
                )
                gt_count += 1

        # Draw predictions (red dashed with score)
        pred_count = 0
        for box, score in zip(pred["boxes"].numpy(), pred["scores"].numpy()):
            x1, y1, x2, y2 = box
            rect = mpatches.Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                linewidth=2,
                edgecolor="red",
                facecolor="none",
                linestyle="--",
            )
            ax.add_patch(rect)
            ax.text(
                x1,
                y2 + 12,
                f"Pred: {score:.2f}",
                fontsize=7,
                color="red",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
            )
            pred_count += 1

        ax.set_title(
            f"{img_info['file_name']}\nGT: {gt_count}, Pred: {pred_count}",
            fontsize=9,
        )
        ax.axis("off")

    # Hide unused axes
    for ax in axes[len(sample_ids) :]:
        ax.axis("off")

    plt.suptitle(
        f"Class Examples: {subclass} (mAP: {subclass_map:.3f})\n"
        f"Green=GT, Red=Predictions",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_worst_iou_examples(
    images: dict,
    predictions: list[dict],
    image_ids: list[str],
    annotations_by_image: dict,
    categories: dict[int, str],
    iou_threshold: float = 0.5,
    num_examples: int = 6,
    subclass: Optional[str] = None,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """
    Plot images with the worst IoU (poorest localization) between predictions and GT.

    Shows images where matched predictions have the lowest IoU with their GT boxes.
    Useful for identifying localization issues.

    Args:
        images: Dict mapping image_id to image info.
        predictions: List of prediction dicts per image.
        image_ids: List of image IDs in order.
        annotations_by_image: Dict mapping image_id to list of annotation dicts.
        categories: Category ID to name mapping.
        iou_threshold: IoU threshold used for matching.
        num_examples: Number of example images to show.
        subclass: Optional class name to filter by. If None, considers all classes.
        output_path: Optional path to save figure.
        show: Whether to display the figure.

    Returns:
        matplotlib Figure.
    """
    # Find target category ID if subclass specified
    target_cat_id = None
    if subclass:
        for cat_id, cat_name in categories.items():
            if cat_name == subclass:
                target_cat_id = cat_id
                break
        if target_cat_id is None:
            print(f"Class '{subclass}' not found")
            return None

    # Compute IoU stats per image
    image_iou_stats = []

    for img_idx, img_id in enumerate(image_ids):
        pred = predictions[img_idx]
        anns = annotations_by_image.get(img_id, [])

        # Filter annotations by subclass if specified
        if target_cat_id is not None:
            anns = [a for a in anns if a["category_id"] == target_cat_id]

        if len(anns) == 0:
            continue

        pred_boxes = pred["boxes"].numpy()
        if len(pred_boxes) == 0:
            # No predictions - this is bad localization (0 IoU effectively)
            image_iou_stats.append(
                {
                    "img_id": img_id,
                    "img_idx": img_idx,
                    "avg_iou": 0.0,
                    "min_iou": 0.0,
                    "num_gt": len(anns),
                    "num_matched": 0,
                    "ious": [],
                }
            )
            continue

        # Match predictions to GT and compute IoUs
        matched_ious = []
        pred_matched = [False] * len(pred_boxes)

        for ann in anns:
            x, y, w, h = ann["bbox"]
            gt_box = [x, y, x + w, y + h]

            best_iou = 0
            best_pred_idx = -1
            for pred_idx, pbox in enumerate(pred_boxes):
                if pred_matched[pred_idx]:
                    continue
                iou = compute_iou(gt_box, pbox.tolist())
                if iou > best_iou:
                    best_iou = iou
                    best_pred_idx = pred_idx

            if best_iou >= iou_threshold and best_pred_idx >= 0:
                pred_matched[best_pred_idx] = True
                matched_ious.append(best_iou)
            else:
                # Unmatched GT - count as 0 IoU
                matched_ious.append(0.0)

        avg_iou = np.mean(matched_ious) if matched_ious else 0.0
        min_iou = min(matched_ious) if matched_ious else 0.0

        image_iou_stats.append(
            {
                "img_id": img_id,
                "img_idx": img_idx,
                "avg_iou": avg_iou,
                "min_iou": min_iou,
                "num_gt": len(anns),
                "num_matched": sum(1 for i in matched_ious if i >= iou_threshold),
                "ious": matched_ious,
            }
        )

    if len(image_iou_stats) == 0:
        print("No images found with GT annotations")
        return None

    # Sort by average IoU (ascending = worst first)
    image_iou_stats.sort(key=lambda x: x["avg_iou"])

    # Take worst examples
    worst_examples = image_iou_stats[:num_examples]

    cols = 3
    rows = (len(worst_examples) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows))
    axes = np.asarray(axes).reshape(-1)

    for ax, stats in zip(axes[: len(worst_examples)], worst_examples):
        img_id = stats["img_id"]
        img_idx = stats["img_idx"]
        img_info = images[img_id]
        pred = predictions[img_idx]
        anns = annotations_by_image.get(img_id, [])

        # Filter annotations by subclass if specified
        if target_cat_id is not None:
            anns = [a for a in anns if a["category_id"] == target_cat_id]

        # Load image
        if "_pil_image" in img_info:
            image = img_info["_pil_image"].convert("RGB")
        else:
            img_path = img_info["source_dir"] / img_info["file_name"]
            image = Image.open(img_path).convert("RGB")

        ax.imshow(image)

        # Draw GT boxes (green solid)
        for ann in anns:
            x, y, w, h = ann["bbox"]
            cat_name = categories.get(ann["category_id"], "?")
            rect = mpatches.Rectangle(
                (x, y),
                w,
                h,
                linewidth=2,
                edgecolor="green",
                facecolor="none",
                linestyle="-",
            )
            ax.add_patch(rect)
            ax.text(
                x,
                y - 3,
                f"GT: {cat_name}",
                fontsize=6,
                color="green",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
            )

        # Draw predictions (red dashed with score)
        for box, score in zip(pred["boxes"].numpy(), pred["scores"].numpy()):
            x1, y1, x2, y2 = box
            rect = mpatches.Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                linewidth=2,
                edgecolor="red",
                facecolor="none",
                linestyle="--",
            )
            ax.add_patch(rect)
            ax.text(
                x1,
                y2 + 12,
                f"Pred: {score:.2f}",
                fontsize=6,
                color="red",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
            )

        ax.set_title(
            f"{img_info['file_name']}\n"
            f"Avg IoU: {stats['avg_iou']:.3f}, Matched: {stats['num_matched']}/{stats['num_gt']}",
            fontsize=9,
        )
        ax.axis("off")

    # Hide unused axes
    for ax in axes[len(worst_examples) :]:
        ax.axis("off")

    title = "Worst IoU Examples (Poorest Localization)"
    if subclass:
        title += f" - {subclass}"
    plt.suptitle(
        f"{title}\nGreen=GT, Red=Predictions",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_false_positive_examples(
    fp_per_image: list[dict],
    images: dict,
    iou_threshold: float,
    examples_per_class: int = 2,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot FP examples grouped by attributed class."""
    # Group FP images by attributed class
    fp_images_by_class = defaultdict(list)
    for fn_info in fp_per_image:
        for cat in set(fn_info["fp_categories"]):
            if cat is not None:
                fp_images_by_class[cat].append(fn_info)

    classes_with_fp = sorted(fp_images_by_class.keys())

    if len(classes_with_fp) == 0:
        print("No false positives found!")
        return None

    # Collect examples
    examples_to_show = []
    for cls in classes_with_fp:
        cls_images = fp_images_by_class[cls][:examples_per_class]
        for fn_info in cls_images:
            examples_to_show.append((cls, fn_info))

    num_examples = len(examples_to_show)
    cols = 2
    rows = (num_examples + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 6 * rows))
    axes = np.asarray(axes).reshape(-1)

    for i, (ax, (cls, fn_info)) in enumerate(
        zip(axes[:num_examples], examples_to_show)
    ):
        img_info = images[fn_info["img_id"]]
        _draw_fp_visualization(ax, img_info, fn_info, highlight_class=cls)

        cls_fp_count = sum(1 for c in fn_info["fp_categories"] if c == cls)
        ax.set_title(
            f"{cls}\n[{img_info['source_name']}] {img_info['file_name']}\n({cls_fp_count} false positive(s))",
            fontsize=9,
        )
        ax.axis("off")

    for ax in axes[num_examples:]:
        ax.axis("off")

    plt.suptitle(
        f"False Positive Examples by Class (up to {examples_per_class} per class) @ IoU>={iou_threshold}",
        fontsize=14,
        y=1.01,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def _draw_fp_visualization(ax, img_info, fn_info, highlight_class=None):
    """Draw image with FP boxes highlighted."""
    if "_pil_image" in img_info:
        image = img_info["_pil_image"].convert("RGB")
    else:
        img_path = img_info["source_dir"] / img_info["file_name"]
        image = Image.open(img_path).convert("RGB")

    ax.imshow(image)

    # Draw true positives (green, faded)
    for box, cat in zip(fn_info["tp_boxes"], fn_info["tp_categories"]):
        x1, y1, x2, y2 = box
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=1,
            edgecolor="green",
            facecolor="none",
            linestyle="-",
            alpha=0.3,
        )
        ax.add_patch(rect)

    # Draw false negatives (orange, faded)
    for box, cat in zip(fn_info["fn_boxes"], fn_info["fn_categories"]):
        x1, y1, x2, y2 = box
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=1,
            edgecolor="orange",
            facecolor="none",
            linestyle="--",
            alpha=0.3,
        )
        ax.add_patch(rect)

    # Draw false positives (red) - highlight the target class
    for box, score, cat in zip(
        fn_info["fp_boxes"], fn_info["fp_scores"], fn_info["fp_categories"]
    ):
        x1, y1, x2, y2 = box
        is_highlight = highlight_class is None or cat == highlight_class
        linewidth = 3 if is_highlight else 1
        alpha = 0.9 if is_highlight else 0.3
        rect = mpatches.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            linewidth=linewidth,
            edgecolor="red",
            facecolor="none",
            linestyle="-",
            alpha=alpha,
        )
        ax.add_patch(rect)
        if is_highlight:
            ax.text(
                x1,
                y1 - 5,
                f"FP: {score:.2f}",
                fontsize=7,
                color="red",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
            )


def plot_map_summary(
    overall: OverallMetrics,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot mAP by IoU threshold and object size."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # mAP by IoU threshold
    ax1 = axes[0]
    iou_labels = ["mAP (0.5:0.95)", "mAP@50", "mAP@75"]
    iou_values = [overall.map, overall.map_50, overall.map_75]
    ax1.bar(iou_labels, iou_values, color=["tab:blue", "tab:green", "tab:orange"])
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("mAP")
    ax1.set_title("mAP by IoU Threshold")
    for i, v in enumerate(iou_values):
        ax1.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)

    # mAP by object size
    ax2 = axes[1]
    size_labels = ["Small", "Medium", "Large"]
    size_values = [overall.map_small, overall.map_medium, overall.map_large]
    ax2.bar(size_labels, size_values, color=["tab:purple", "tab:cyan", "tab:red"])
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("mAP")
    ax2.set_title("mAP by Object Size")
    for i, v in enumerate(size_values):
        ax2.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=10)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_sample_predictions(
    images: dict,
    predictions: list[dict],
    targets: list[dict],
    image_ids: list[str],
    model_id2label: dict[int, str],
    num_samples: int = 6,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot sample images with GT and predictions overlaid."""
    import random

    sample_ids = random.sample(image_ids, k=min(num_samples, len(image_ids)))

    cols = 3
    rows = (len(sample_ids) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(18, 6 * rows))
    axes = np.asarray(axes).reshape(-1)

    for ax, img_id in zip(axes[: len(sample_ids)], sample_ids):
        img_info = images[img_id]

        if "_pil_image" in img_info:
            image = img_info["_pil_image"].convert("RGB")
        else:
            img_path = img_info["source_dir"] / img_info["file_name"]
            image = Image.open(img_path).convert("RGB")

        idx = image_ids.index(img_id)
        pred = predictions[idx]
        target = targets[idx]

        ax.imshow(image)

        # Draw ground truth (green)
        for box, lbl in zip(target["boxes"].numpy(), target["labels"].numpy()):
            x1, y1, x2, y2 = box
            rect = mpatches.Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                linewidth=2,
                edgecolor="green",
                facecolor="none",
            )
            ax.add_patch(rect)
            label_text = model_id2label.get(int(lbl), f"{lbl}")
            ax.text(
                x1,
                y1 - 5,
                label_text,
                fontsize=7,
                color="green",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
            )

        # Draw predictions (red)
        for box, lbl, score in zip(
            pred["boxes"].numpy(), pred["labels"].numpy(), pred["scores"].numpy()
        ):
            x1, y1, x2, y2 = box
            rect = mpatches.Rectangle(
                (x1, y1),
                x2 - x1,
                y2 - y1,
                linewidth=2,
                edgecolor="red",
                facecolor="none",
            )
            ax.add_patch(rect)
            label_text = f"{model_id2label.get(int(lbl), str(lbl))}: {score:.2f}"
            ax.text(
                x1,
                y1 - 15,
                label_text,
                fontsize=7,
                color="red",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
            )

        ax.set_title(
            f"[{img_info['source_name']}] {img_info['file_name']}\nGT: green, Pred: red",
            fontsize=9,
        )
        ax.axis("off")

    for ax in axes[len(sample_ids) :]:
        ax.axis("off")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_confidence_distribution(
    predictions: list[dict],
    confidence_threshold: float,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> plt.Figure:
    """Plot histogram of prediction confidence scores."""
    scores = [p["scores"] for p in predictions if len(p["scores"]) > 0]
    if not scores:
        return None
    all_scores = torch.cat(scores)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(all_scores.numpy(), bins=50, edgecolor="black", alpha=0.7)
    ax.set_xlabel("Confidence Score")
    ax.set_ylabel("Count")
    ax.set_title(
        f"Prediction Confidence Distribution (threshold={confidence_threshold})"
    )
    ax.axvline(
        x=confidence_threshold,
        color="red",
        linestyle="--",
        label=f"Threshold: {confidence_threshold}",
    )
    ax.legend()
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
    if show:
        plt.show()
    else:
        plt.close()

    return fig


def plot_threshold_optimization(
    predictions: list[dict],
    targets: list[dict],
    annotations_by_image: dict,
    image_ids: list[str],
    iou_threshold: float = 0.5,
    output_path: Optional[Path] = None,
    show: bool = False,
) -> tuple[plt.Figure, float]:
    """
    Plot F1 score vs confidence threshold and recommend optimal threshold.

    Sweeps confidence thresholds and computes precision, recall, F1 at each point.
    Finds the threshold that maximizes F1 score.

    Args:
        predictions: List of prediction dicts per image (boxes, scores, labels).
        targets: List of target dicts per image (boxes, labels).
        annotations_by_image: Dict mapping image_id to list of annotation dicts.
        image_ids: List of image IDs in order.
        iou_threshold: IoU threshold for matching predictions to ground truth.
        output_path: Optional path to save figure.
        show: Whether to display the figure.

    Returns:
        Tuple of (figure, optimal_threshold).
    """
    # Collect all prediction scores (before any threshold filtering)
    all_pred_scores = []
    all_pred_boxes = []
    all_pred_image_indices = []

    for img_idx, pred in enumerate(predictions):
        scores = pred["scores"].numpy()
        boxes = pred["boxes"].numpy()
        for i in range(len(scores)):
            all_pred_scores.append(scores[i])
            all_pred_boxes.append(boxes[i])
            all_pred_image_indices.append(img_idx)

    all_pred_scores = np.array(all_pred_scores)
    all_pred_boxes = (
        np.array(all_pred_boxes)
        if len(all_pred_boxes) > 0
        else np.array([]).reshape(0, 4)
    )
    all_pred_image_indices = np.array(all_pred_image_indices)

    # Get total ground truth count
    total_gt = sum(len(annotations_by_image.get(img_id, [])) for img_id in image_ids)

    if len(all_pred_scores) == 0 or total_gt == 0:
        print("No predictions or ground truth to analyze for threshold optimization")
        return None, 0.5

    # Sweep thresholds
    thresholds = np.arange(0.05, 0.96, 0.05)
    precisions = []
    recalls = []
    f1_scores = []

    for thresh in thresholds:
        # Apply threshold
        mask = all_pred_scores >= thresh
        thresh_pred_boxes = all_pred_boxes[mask]
        thresh_pred_indices = all_pred_image_indices[mask]

        # Group predictions by image
        preds_by_image = defaultdict(list)
        for i, idx in enumerate(thresh_pred_indices):
            preds_by_image[int(idx)].append(thresh_pred_boxes[i])

        # Compute TP, FP, FN
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for img_idx, img_id in enumerate(image_ids):
            pred_boxes = preds_by_image.get(img_idx, [])
            gt_anns = annotations_by_image.get(img_id, [])

            pred_matched = [False] * len(pred_boxes)

            for ann in gt_anns:
                x, y, w, h = ann["bbox"]
                gt_box = [x, y, x + w, y + h]

                best_iou = 0
                best_pred_idx = -1
                for pred_idx, pbox in enumerate(pred_boxes):
                    if pred_matched[pred_idx]:
                        continue
                    iou = compute_iou(gt_box, pbox.tolist())
                    if iou > best_iou:
                        best_iou = iou
                        best_pred_idx = pred_idx

                if best_iou >= iou_threshold and best_pred_idx >= 0:
                    pred_matched[best_pred_idx] = True
                    total_tp += 1
                else:
                    total_fn += 1

            total_fp += sum(1 for m in pred_matched if not m)

        # Compute metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)

    # Find optimal threshold (max F1)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds[optimal_idx]
    optimal_f1 = f1_scores[optimal_idx]
    optimal_precision = precisions[optimal_idx]
    optimal_recall = recalls[optimal_idx]

    # Create plot with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Precision vs threshold
    ax1 = axes[0]
    ax1.plot(thresholds, precisions, "b-", linewidth=2, marker="o", markersize=4)
    ax1.axvline(x=optimal_threshold, color="red", linestyle="--", alpha=0.7)
    ax1.scatter([optimal_threshold], [optimal_precision], color="red", s=100, zorder=5)
    ax1.set_xlabel("Confidence Threshold", fontsize=11)
    ax1.set_ylabel("Precision", fontsize=11)
    ax1.set_title("Precision vs Threshold", fontsize=12)
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    # Recall vs threshold
    ax2 = axes[1]
    ax2.plot(thresholds, recalls, "g-", linewidth=2, marker="o", markersize=4)
    ax2.axvline(x=optimal_threshold, color="red", linestyle="--", alpha=0.7)
    ax2.scatter([optimal_threshold], [optimal_recall], color="red", s=100, zorder=5)
    ax2.set_xlabel("Confidence Threshold", fontsize=11)
    ax2.set_ylabel("Recall", fontsize=11)
    ax2.set_title("Recall vs Threshold", fontsize=12)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3)

    # F1 vs threshold (with optimal point annotated)
    ax3 = axes[2]
    ax3.plot(thresholds, f1_scores, "purple", linewidth=2, marker="o", markersize=4)
    ax3.axvline(
        x=optimal_threshold,
        color="red",
        linestyle="--",
        alpha=0.7,
        label=f"Optimal: {optimal_threshold:.2f}",
    )
    ax3.scatter(
        [optimal_threshold],
        [optimal_f1],
        color="red",
        s=150,
        zorder=5,
        edgecolors="black",
        linewidths=2,
    )
    ax3.annotate(
        f"Optimal threshold: {optimal_threshold:.2f}\n"
        f"F1: {optimal_f1:.3f}\n"
        f"Precision: {optimal_precision:.3f}\n"
        f"Recall: {optimal_recall:.3f}",
        xy=(optimal_threshold, optimal_f1),
        xytext=(0.65, 0.3),
        textcoords="axes fraction",
        fontsize=10,
        bbox=dict(
            boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="orange"
        ),
        arrowprops=dict(
            arrowstyle="->", connectionstyle="arc3,rad=0.2", color="orange"
        ),
    )
    ax3.set_xlabel("Confidence Threshold", fontsize=11)
    ax3.set_ylabel("F1 Score", fontsize=11)
    ax3.set_title("F1 Score vs Threshold", fontsize=12)
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1.05)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper right")

    plt.suptitle(
        f"Confidence Threshold Optimization (IoU >= {iou_threshold})\n"
        f"Recommended threshold: {optimal_threshold:.2f}",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    else:
        plt.close()

    return fig, optimal_threshold


# =============================================================================
# CLI
# =============================================================================


def get_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Validate object detection model against COCO-format data."
    )

    parser.add_argument(
        "--config_path",
        type=str,
        required=True,
        help="Path to YAML config file with validation data sources.",
    )
    parser.add_argument(
        "--model_path",
        type=str,
        required=True,
        help="Path to model checkpoint directory.",
    )
    parser.add_argument(
        "--processor_path",
        type=str,
        default=None,
        help="Path to image processor. Auto-detected if not provided.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Output directory for results. Defaults to model_path/validation_analysis.",
    )
    parser.add_argument(
        "--confidence_threshold",
        type=float,
        default=0.5,
        help="Confidence threshold for predictions (default: 0.5).",
    )
    parser.add_argument(
        "--iou_threshold",
        type=float,
        default=0.5,
        help="IoU threshold for matching predictions to GT (default: 0.5).",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=16,
        help="Batch size for inference (default: 16).",
    )
    parser.add_argument(
        "--no_visualizations",
        action="store_true",
        help="Disable visualization generation.",
    )
    parser.add_argument(
        "--no_save",
        action="store_true",
        help="Disable saving results to files.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help="Device to use. Auto-detected if not provided.",
    )
    parser.add_argument(
        "--preprocessing",
        type=str,
        default=None,
        choices=["imagenet", "clahe", "clahe+imagenet"],
        help="Preprocessing preset: 'imagenet', 'clahe', or 'clahe+imagenet'.",
    )

    return parser


def main():
    """CLI entry point."""
    parser = get_parser()
    args = parser.parse_args()

    config = ValidationConfig(
        config_path=Path(args.config_path),
        model_path=Path(args.model_path),
        processor_path=Path(args.processor_path) if args.processor_path else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        confidence_threshold=args.confidence_threshold,
        iou_threshold=args.iou_threshold,
        batch_size=args.batch_size,
        generate_visualizations=not args.no_visualizations,
        save_results=not args.no_save,
        device=args.device,
        preprocessing=args.preprocessing,
    )

    validator = DetectorValidator(config)
    results = validator.run()

    # Print final summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Model: {config.model_path.name}")
    print(f"Config: {config.config_path}")
    print(f"\nImages evaluated: {results.overall.num_images}")
    print(f"Confidence threshold: {config.confidence_threshold}")
    print(f"IoU threshold: {config.iou_threshold}")
    print("\nKey Metrics:")
    print(f"  mAP (IoU 0.50:0.95): {results.overall.map:.4f}")
    print(f"  mAP @ IoU 0.50:      {results.overall.map_50:.4f}")
    print(f"  mAR @ 100:           {results.overall.mar_100:.4f}")
    print(f"  Precision:           {results.overall.precision:.4f}")
    print(f"  Recall:              {results.overall.recall:.4f}")
    print(f"  F1 Score:            {results.overall.f1_score:.4f}")

    if config.save_results:
        print(f"\nOutputs saved to: {config.output_dir}")


if __name__ == "__main__":
    main()
