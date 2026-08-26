#!/usr/bin/env python
# Copied from ai-cfia/nachet-model-ccds at commit 601219b7.
# Original path: nachetmodel/HFTrainer_detector_2026061501_js.py
# The training behavior below is unchanged from that reviewed source.
# Local additions: runtime COCO-to-HF conversion (no duplicate images) via --coco_json_path/--coco_images_dir,
# optional single-class collapse (--coco_single_category/--coco_single_category_name), and label/test-split
# fallbacks for datasets without explicit validation/test splits.
# FIXED: Properly merges categories when using two COCO datasets with exclusive classes
# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# https://github.com/huggingface/transformers/tree/main/examples/pytorch/object-detection/README.md
# python run_object_detection.py \
#     --model_name_or_path facebook/detr-resnet-50 \
#     --dataset_name cppe-5 \
#     --do_train true \
#     --do_eval true \
#     --output_dir detr-finetuned-cppe-5-10k-steps \
#     --num_train_epochs 100 \
#     --image_square_size 600 \
#     --fp16 true \
#     --learning_rate 5e-5 \
#     --weight_decay 1e-4 \
#     --dataloader_num_workers 4 \
#     --dataloader_prefetch_factor 2 \
#     --per_device_train_batch_size 8 \
#     --gradient_accumulation_steps 1 \
#     --remove_unused_columns false \
#     --eval_do_concat_batches false \
#     --ignore_mismatched_sizes true \
#     --metric_for_best_model eval_map \
#     --greater_is_better true \
#     --load_best_model_at_end true \
#     --logging_strategy epoch \
#     --eval_strategy epoch \
#     --save_strategy epoch \
#     --save_total_limit 2 \
#     --push_to_hub true \
#     --push_to_hub_model_id detr-finetuned-cppe-5-10k-steps \
#     --hub_strategy end \
#     --seed 1337


"""Finetuning any 🤗 Transformers model supported by AutoModelForObjectDetection for object detection leveraging the Trainer API."""

import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Optional, Union

import albumentations as A
import numpy as np
import torch
from datasets import concatenate_datasets, load_dataset
from torchmetrics.detection.mean_ap import MeanAveragePrecision

from coco_to_hf_dataset import load_coco_as_hf_dataset

import transformers
from transformers import (
    AutoConfig,
    AutoImageProcessor,
    AutoModelForObjectDetection,
    HfArgumentParser,
    Trainer,
    TrainingArguments,
)
from transformers.image_processing_utils import BatchFeature
from transformers.image_transforms import center_to_corners_format
from transformers.trainer import EvalPrediction
from transformers.utils import check_min_version
from transformers.utils.versions import require_version

import mlflow



logger = logging.getLogger(__name__)

# Will error if the minimal version of Transformers is not installed. Remove at your own risks.
check_min_version("4.57.0.dev0")

require_version(
    "datasets>=2.0.0",
    "To fix: pip install -r examples/pytorch/object-detection/requirements.txt",
)


@dataclass
class ModelOutput:
    logits: torch.Tensor
    pred_boxes: torch.Tensor


def format_image_annotations_as_coco(
    image_id: str, categories: list[int], areas: list[float], bboxes: list[tuple[float]]
) -> dict:
    """Format one set of image annotations to the COCO format

    Args:
        image_id (str): image id. e.g. "0001"
        categories (list[int]): list of categories/class labels corresponding to provided bounding boxes
        areas (list[float]): list of corresponding areas to provided bounding boxes
        bboxes (list[tuple[float]]): list of bounding boxes provided in COCO format
            ([center_x, center_y, width, height] in absolute coordinates)

    Returns:
        dict: {
            "image_id": image id,
            "annotations": list of formatted annotations
        }
    """
    annotations = []
    for category, area, bbox in zip(categories, areas, bboxes):
        formatted_annotation = {
            "image_id": image_id,
            "category_id": category,
            "iscrowd": 0,
            "area": area,
            "bbox": list(bbox),
        }
        annotations.append(formatted_annotation)

    return {
        "image_id": image_id,
        "annotations": annotations,
    }


def convert_bbox_yolo_to_pascal(
    boxes: torch.Tensor, image_size: tuple[int, int]
) -> torch.Tensor:
    """
    Convert bounding boxes from YOLO format (x_center, y_center, width, height) in range [0, 1]
    to Pascal VOC format (x_min, y_min, x_max, y_max) in absolute coordinates.

    Args:
        boxes (torch.Tensor): Bounding boxes in YOLO format
        image_size (tuple[int, int]): Image size in format (height, width)

    Returns:
        torch.Tensor: Bounding boxes in Pascal VOC format (x_min, y_min, x_max, y_max)
    """
    # convert center to corners format
    boxes = center_to_corners_format(boxes)

    # convert to absolute coordinates
    height, width = image_size
    boxes = boxes * torch.tensor([[width, height, width, height]])

    return boxes


def augment_and_transform_batch(
    examples: Mapping[str, Any],
    transform: A.Compose,
    image_processor: AutoImageProcessor,
    return_pixel_mask: bool = False,
) -> BatchFeature:
    """Apply augmentations and format annotations in COCO format for object detection task"""

    images = []
    annotations = []
    for image_id, image, objects in zip(
        examples["image_id"], examples["image"], examples["objects"]
    ):
        image = np.array(image.convert("RGB"))

        # apply augmentations
        output = transform(
            image=image, bboxes=objects["bbox"], category=objects["category"]
        )
        images.append(output["image"])

        # format annotations in COCO format
        formatted_annotations = format_image_annotations_as_coco(
            image_id, output["category"], objects["area"], output["bboxes"]
        )
        annotations.append(formatted_annotations)

    # Apply the image processor transformations: resizing, rescaling, normalization
    result = image_processor(
        images=images, annotations=annotations, return_tensors="pt"
    )

    if not return_pixel_mask:
        result.pop("pixel_mask", None)

    return result


def collate_fn(
    batch: list[BatchFeature],
) -> Mapping[str, Union[torch.Tensor, list[Any]]]:
    data = {}
    data["pixel_values"] = torch.stack([x["pixel_values"] for x in batch])
    data["labels"] = [x["labels"] for x in batch]
    if "pixel_mask" in batch[0]:
        data["pixel_mask"] = torch.stack([x["pixel_mask"] for x in batch])
    return data


@torch.no_grad()
def compute_metrics(
    evaluation_results: EvalPrediction,
    image_processor: AutoImageProcessor,
    threshold: float = 0.0,
    id2label: Optional[Mapping[int, str]] = None,
) -> Mapping[str, float]:
    """
    Compute mean average mAP, mAR and their variants for the object detection task.

    Args:
        evaluation_results (EvalPrediction): Predictions and targets from evaluation.
        threshold (float, optional): Threshold to filter predicted boxes by confidence. Defaults to 0.0.
        id2label (Optional[dict], optional): Mapping from class id to class name. Defaults to None.

    Returns:
        Mapping[str, float]: Metrics in a form of dictionary {<metric_name>: <metric_value>}
    """

    predictions, targets = evaluation_results.predictions, evaluation_results.label_ids

    # For metric computation we need to provide:
    #  - targets in a form of list of dictionaries with keys "boxes", "labels"
    #  - predictions in a form of list of dictionaries with keys "boxes", "scores", "labels"

    image_sizes = []
    post_processed_targets = []
    post_processed_predictions = []

    # Collect targets in the required format for metric computation
    for batch in targets:
        # collect image sizes, we will need them for predictions post processing
        batch_image_sizes = torch.tensor([x["orig_size"] for x in batch])
        image_sizes.append(batch_image_sizes)
        # collect targets in the required format for metric computation
        # boxes were converted to YOLO format needed for model training
        # here we will convert them to Pascal VOC format (x_min, y_min, x_max, y_max)
        for image_target in batch:
            boxes = torch.tensor(image_target["boxes"])
            boxes = convert_bbox_yolo_to_pascal(boxes, image_target["orig_size"])
            labels = torch.tensor(image_target["class_labels"])
            post_processed_targets.append({"boxes": boxes, "labels": labels})

    # Collect predictions in the required format for metric computation,
    # model produce boxes in YOLO format, then image_processor convert them to Pascal VOC format
    for batch, target_sizes in zip(predictions, image_sizes):
        batch_logits, batch_boxes = batch[1], batch[2]
        output = ModelOutput(
            logits=torch.tensor(batch_logits), pred_boxes=torch.tensor(batch_boxes)
        )
        post_processed_output = image_processor.post_process_object_detection(
            output, threshold=threshold, target_sizes=target_sizes
        )
        post_processed_predictions.extend(post_processed_output)

    # Compute metrics
    metric = MeanAveragePrecision(box_format="xyxy", class_metrics=True)
    metric.update(post_processed_predictions, post_processed_targets)
    metrics = metric.compute()

    # Replace list of per class metrics with separate metric for each class
    classes = metrics.pop("classes")
    map_per_class = metrics.pop("map_per_class")
    mar_100_per_class = metrics.pop("mar_100_per_class")

    # Handle single-class case where tensors are 0-d (scalars)
    if classes.dim() == 0:
        classes = classes.unsqueeze(0)
        map_per_class = map_per_class.unsqueeze(0)
        mar_100_per_class = mar_100_per_class.unsqueeze(0)

    for class_id, class_map, class_mar in zip(
        classes, map_per_class, mar_100_per_class
    ):
        class_name = (
            id2label[class_id.item()] if id2label is not None else class_id.item()
        )
        metrics[f"map_{class_name}"] = class_map
        metrics[f"mar_100_{class_name}"] = class_mar

    metrics = {k: round(v.item(), 4) for k, v in metrics.items()}

    return metrics


def remap_dataset_categories(dataset, old_categories, new_category_mapping):
    """
    Remap category IDs in a dataset to match a new unified category mapping.

    Args:
        dataset: HuggingFace dataset with objects.category field
        old_categories: Dict mapping old category IDs to category names
        new_category_mapping: Dict mapping category names to new IDs

    Returns:
        Dataset with remapped category IDs
    """
    def remap_example(example):
        # Create mapping from old ID to new ID via category name
        old_to_new = {
            old_id: new_category_mapping[cat_name]
            for old_id, cat_name in old_categories.items()
        }

        # Remap all category IDs in this example
        example["objects"]["category"] = [
            old_to_new[cat_id] for cat_id in example["objects"]["category"]
        ]
        return example

    return dataset.map(remap_example)


def parse_include_classes(
    include_classes_str: str | None = None,
    include_classes_file: str | None = None,
) -> set[str] | None:
    """
    Parse include_classes from file or comma-separated string.

    Args:
        include_classes_str: Comma-separated list of class names
        include_classes_file: Path to text file with class names (one per line)

    Returns:
        Set of class names to include, or None if neither provided.
        File takes precedence over string if both provided.
    """
    if include_classes_file:
        with open(include_classes_file) as f:
            classes = {line.strip() for line in f if line.strip()}
        if classes:
            logger.info(f"Loaded {len(classes)} classes to include from file: {include_classes_file}")
            return classes
    elif include_classes_str:
        classes = {c.strip() for c in include_classes_str.split(",") if c.strip()}
        if classes:
            logger.info(f"Filtering to {len(classes)} classes: {classes}")
            return classes
    return None


def load_dataset_config(config_path: str) -> dict:
    """
    Load dataset configuration from YAML or JSON file.

    Args:
        config_path: Path to YAML or JSON config file

    Returns:
        Dictionary with config values
    """
    import json

    with open(config_path) as f:
        if config_path.endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "PyYAML is required to load YAML config files. Install with: pip install pyyaml"
                )
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    logger.info(f"Loaded dataset config from: {config_path}")
    return config


@dataclass
class DataTrainingArguments:
    """
    Arguments pertaining to what data we are going to input our model for training and eval.
    Using `HfArgumentParser` we can turn this class into argparse arguments to be able to specify
    them on the command line.
    """

    dataset_name: str = field(
        default="cppe-5",
        metadata={
            "help": "Name of a dataset from the hub (could be your own, possibly private dataset hosted on the hub)."
        },
    )
    coco_json_path: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to a local COCO annotations json. If provided with coco_images_dir, dataset_name is ignored."
        },
    )
    coco_images_dir: Optional[str] = field(
        default=None,
        metadata={
            "help": "Directory containing images referenced by the COCO annotations json."
        },
    )
    coco_json_path2: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to a second COCO annotations json to combine with the first."
        },
    )
    coco_images_dir2: Optional[str] = field(
        default=None,
        metadata={
            "help": "Directory containing images for the second COCO annotations json."
        },
    )
    coco_single_category: bool = field(
        default=False,
        metadata={
            "help": "Collapse all categories into a single category when loading COCO annotations."
        },
    )
    coco_single_category_name: str = field(
        default="seed",
        metadata={"help": "Category name to use when collapsing to a single category."},
    )
    coco_reject_list: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to a text file containing filenames to exclude from the first dataset."
        },
    )
    coco_reject_list2: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to a text file containing filenames to exclude from the second dataset."
        },
    )
    include_classes: Optional[str] = field(
        default=None,
        metadata={
            "help": "Comma-separated list of class names to include for training (case-insensitive)."
        },
    )
    include_classes_file: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to a text file with class names to include (one per line). Overrides --include_classes."
        },
    )
    dataset_config: Optional[str] = field(
        default=None,
        metadata={
            "help": "Path to YAML/JSON config file specifying dataset sources and filtering options."
        },
    )
    dataset_config_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "The configuration name of the dataset to use (via the datasets library)."
        },
    )
    train_val_split: Optional[float] = field(
        default=0.15, metadata={"help": "Percent to split off of train for validation."}
    )
    image_square_size: Optional[int] = field(
        default=600,
        metadata={
            "help": "Image longest size will be resized to this value, then image will be padded to square."
        },
    )
    max_train_samples: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "For debugging purposes or quicker training, truncate the number of training examples to this "
                "value if set."
            )
        },
    )
    max_eval_samples: Optional[int] = field(
        default=None,
        metadata={
            "help": (
                "For debugging purposes or quicker training, truncate the number of evaluation examples to this "
                "value if set."
            )
        },
    )
    use_fast: Optional[bool] = field(
        default=True,
        metadata={
            "help": "Use a fast torchvision-base image processor if it is supported for a given model."
        },
    )


@dataclass
class ModelArguments:
    """
    Arguments pertaining to which model/config/tokenizer we are going to fine-tune from.
    """

    model_name_or_path: str = field(
        default="facebook/detr-resnet-50",
        metadata={
            "help": "Path to pretrained model or model identifier from huggingface.co/models"
        },
    )
    config_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "Pretrained config name or path if not the same as model_name"
        },
    )
    cache_dir: Optional[str] = field(
        default=None,
        metadata={
            "help": "Where do you want to store the pretrained models downloaded from s3"
        },
    )
    model_revision: str = field(
        default="main",
        metadata={
            "help": "The specific model version to use (can be a branch name, tag name or commit id)."
        },
    )
    image_processor_name: Optional[str] = field(
        default=None, metadata={"help": "Name or path of preprocessor config."}
    )
    ignore_mismatched_sizes: bool = field(
        default=False,
        metadata={
            "help": "Whether or not to raise an error if some of the weights from the checkpoint do not have the same size as the weights of the model (if for instance, you are instantiating a model with 10 labels from a checkpoint with 3 labels)."
        },
    )
    token: Optional[str] = field(
        default=None,
        metadata={
            "help": (
                "The token to use as HTTP bearer authorization for remote files. If not specified, will use the token "
                "generated when running `hf auth login` (stored in `~/.huggingface`)."
            )
        },
    )
    trust_remote_code: bool = field(
        default=False,
        metadata={
            "help": (
                "Whether to trust the execution of code from datasets/models defined on the Hub."
                " This option should only be set to `True` for repositories you trust and in which you have read the"
                " code, as it will execute code present on the Hub on your local machine."
            )
        },
    )


def main():
    # See all possible arguments in src/transformers/training_args.py
    # or by passing the --help flag to this script.
    # We now keep distinct sets of args, for a cleaner separation of concerns.
    # --- MLflow / S3 env setup ---
    # load_dotenv("notebooks/shell/.env.local")  # tracking URI + S3 creds
    # os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", "rtdetr-seed-detector")
    # mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT_NAME"])
    # Handled in shell

    parser = HfArgumentParser(
        (ModelArguments, DataTrainingArguments, TrainingArguments)
    )
    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        # If we pass only one argument to the script and it's the path to a json file,
        # let's parse it to get our arguments.
        model_args, data_args, training_args = parser.parse_json_file(
            json_file=os.path.abspath(sys.argv[1])
        )
    else:
        model_args, data_args, training_args = parser.parse_args_into_dataclasses()

    # Setup logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    if training_args.should_log:
        # The default of training_args.log_level is passive, so we set log level at info here to have that default.
        transformers.utils.logging.set_verbosity_info()

    log_level = training_args.get_process_log_level()
    logger.setLevel(log_level)
    transformers.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.enable_default_handler()
    transformers.utils.logging.enable_explicit_format()

    # Log on each process the small summary:
    logger.warning(
        f"Process rank: {training_args.local_process_index}, device: {training_args.device}, n_gpu: {training_args.n_gpu}, "
        + f"distributed training: {training_args.parallel_mode.value == 'distributed'}, 16-bits training: {training_args.fp16}"
    )
    logger.info(f"Training/evaluation parameters {training_args}")

    # ------------------------------------------------------------------------------------------------
    # Load dataset, prepare splits
    # ------------------------------------------------------------------------------------------------

    dataset_categories: Optional[list[str]] = None

    # Parse include_classes from file or comma-separated string
    include_classes = parse_include_classes(
        data_args.include_classes,
        data_args.include_classes_file,
    )

    # Check for dataset_config (new unified config file)
    if data_args.dataset_config:
        config = load_dataset_config(data_args.dataset_config)

        # Override include_classes from config if specified there
        if config.get("include_classes") and not include_classes:
            include_classes = set(config["include_classes"])
            logger.info(f"Using include_classes from config: {include_classes}")

        # Get single_category settings from config or fall back to CLI args
        single_category = config.get("single_category", data_args.coco_single_category)
        single_category_name = config.get("single_category_name", data_args.coco_single_category_name)

        # Load each source from config
        sources = config.get("sources", [])
        if not sources:
            raise ValueError("dataset_config must specify at least one source in 'sources' list")

        datasets_list = []
        categories_list = []

        for i, source in enumerate(sources):
            if not source.get("json_path") or not source.get("images_dir"):
                raise ValueError(f"Source {i} must have 'json_path' and 'images_dir'")

            ds, cats = load_coco_as_hf_dataset(
                images_dir=source["images_dir"],
                coco_json_path=source["json_path"],
                train_val_split=data_args.train_val_split,
                seed=training_args.seed,
                single_category=single_category,
                single_category_name=single_category_name,
                reject_list_path=source.get("reject_list"),
                include_classes=include_classes,
            )
            datasets_list.append(ds)
            categories_list.append(cats)
            logger.info(f"Loaded source {i+1}: {len(ds['train'])} train, {len(ds['validation'])} val images")

        # Merge all datasets
        if len(datasets_list) == 1:
            dataset = datasets_list[0]
            categories_mapping = categories_list[0]
        else:
            # Merge category mappings - create unified mapping with all unique categories
            all_category_names = set()
            for cat_map in categories_list:
                all_category_names.update(cat_map.values())

            unified_categories = {name: idx for idx, name in enumerate(sorted(all_category_names))}
            logger.info(f"Unified categories from {len(datasets_list)} sources: {sorted(unified_categories.keys())}")

            # Remap and concatenate all datasets
            for i, (ds, cats) in enumerate(zip(datasets_list, categories_list)):
                for split in ["train", "validation"]:
                    datasets_list[i][split] = remap_dataset_categories(ds[split], cats, unified_categories)

            # Concatenate all
            dataset = datasets_list[0]
            for ds in datasets_list[1:]:
                dataset["train"] = concatenate_datasets([dataset["train"], ds["train"]])
                dataset["validation"] = concatenate_datasets([dataset["validation"], ds["validation"]])

            categories_mapping = {idx: name for name, idx in unified_categories.items()}

        logger.info(f"Final dataset: {len(dataset['train'])} train, {len(dataset['validation'])} val images")
        logger.info(f"Total categories: {len(categories_mapping)}")

        dataset_categories = [categories_mapping[k] for k in sorted(categories_mapping.keys())]

    elif data_args.coco_json_path and data_args.coco_images_dir:
        # Legacy args path (backward compatibility)
        if data_args.coco_json_path2:
            logger.warning(
                "Using legacy --coco_json_path/--coco_json_path2 arguments. "
                "Consider migrating to --dataset_config for easier management of multiple sources."
            )

        dataset, categories_mapping = load_coco_as_hf_dataset(
            images_dir=data_args.coco_images_dir,
            coco_json_path=data_args.coco_json_path,
            train_val_split=data_args.train_val_split,
            seed=training_args.seed,
            single_category=data_args.coco_single_category,
            single_category_name=data_args.coco_single_category_name,
            reject_list_path=data_args.coco_reject_list,
            include_classes=include_classes,
        )

        # Load and merge second COCO source if provided
        if data_args.coco_json_path2 and data_args.coco_images_dir2:
            dataset2, categories_mapping2 = load_coco_as_hf_dataset(
                images_dir=data_args.coco_images_dir2,
                coco_json_path=data_args.coco_json_path2,
                train_val_split=data_args.train_val_split,
                seed=training_args.seed,
                single_category=data_args.coco_single_category,
                single_category_name=data_args.coco_single_category_name,
                reject_list_path=data_args.coco_reject_list2,
                include_classes=include_classes,
            )

            # Merge category mappings - create unified mapping with all unique categories
            all_category_names = set()
            for cat_map in [categories_mapping, categories_mapping2]:
                all_category_names.update(cat_map.values())

            # Create unified mapping: category_name -> new_id (0-indexed, sorted)
            unified_categories = {name: idx for idx, name in enumerate(sorted(all_category_names))}

            logger.info(f"Dataset 1 categories: {sorted(categories_mapping.values())}")
            logger.info(f"Dataset 2 categories: {sorted(categories_mapping2.values())}")
            logger.info(f"Unified categories: {sorted(unified_categories.keys())}")

            # Remap category IDs in both datasets to use unified mapping
            for split in ["train", "validation"]:
                dataset[split] = remap_dataset_categories(
                    dataset[split],
                    categories_mapping,
                    unified_categories
                )
                dataset2[split] = remap_dataset_categories(
                    dataset2[split],
                    categories_mapping2,
                    unified_categories
                )

            # Now concatenate with consistent category IDs
            dataset["train"] = concatenate_datasets([dataset["train"], dataset2["train"]])
            dataset["validation"] = concatenate_datasets([dataset["validation"], dataset2["validation"]])

            # Use unified categories for final mapping
            categories_mapping = {idx: name for name, idx in unified_categories.items()}

            logger.info(
                f"Combined datasets: {len(dataset['train'])} train, {len(dataset['validation'])} validation images"
            )
            logger.info(f"Total unique categories: {len(categories_mapping)}")

        # Keep categories ordered by id for id2label consistency
        dataset_categories = [
            categories_mapping[k] for k in sorted(categories_mapping.keys())
        ]

    else:
        dataset = load_dataset(
            data_args.dataset_name,
            cache_dir=model_args.cache_dir,
            trust_remote_code=model_args.trust_remote_code,
        )

    # If we don't have a validation split, split off a percentage of train as validation
    data_args.train_val_split = (
        None if "validation" in dataset else data_args.train_val_split
    )
    if isinstance(data_args.train_val_split, float) and data_args.train_val_split > 0.0:
        split = dataset["train"].train_test_split(
            data_args.train_val_split, seed=training_args.seed
        )
        dataset["train"] = split["train"]
        dataset["validation"] = split["test"]

    # Get dataset categories and prepare mappings for label_name <-> label_id
    if dataset_categories is None:
        try:
            if isinstance(dataset["train"].features["objects"], dict):
                dataset_categories = (
                    dataset["train"].features["objects"]["category"].feature.names
                )
            else:  # (for old versions of `datasets` that used Sequence({...}) of the objects)
                dataset_categories = (
                    dataset["train"].features["objects"].feature["category"].names
                )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                "Could not infer dataset categories. Provide COCO metadata or ensure ClassLabel features are present."
            ) from exc

    # Ensure we always have a test split (fall back to validation when absent)
    # Ensure we always have a test split (fall back to validation when absent)
    if "test" not in dataset:
        dataset["test"] = dataset["validation"]

    if data_args.max_train_samples is not None:
        max_train = min(len(dataset["train"]), data_args.max_train_samples)
        dataset["train"] = dataset["train"].select(range(max_train))
        logger.info(f"Truncated train split to {max_train} examples for quick testing.")

    if data_args.max_eval_samples is not None:
        max_eval = min(len(dataset["validation"]), data_args.max_eval_samples)
        dataset["validation"] = dataset["validation"].select(range(max_eval))
        dataset["test"] = dataset["test"].select(range(max_eval))
        logger.info(f"Truncated validation/test splits to {max_eval} examples for quick testing.")

    id2label = dict(enumerate(dataset_categories))
    label2id = {v: k for k, v in id2label.items()}

    # ------------------------------------------------------------------------------------------------
    # Load pretrained config, model and image processor
    # ------------------------------------------------------------------------------------------------

    common_pretrained_args = {
        "cache_dir": model_args.cache_dir,
        "revision": model_args.model_revision,
        "token": model_args.token,
        "trust_remote_code": model_args.trust_remote_code,
    }
    config = AutoConfig.from_pretrained(
        model_args.config_name or model_args.model_name_or_path,
        label2id=label2id,
        id2label=id2label,
        **common_pretrained_args,
    )
    model = AutoModelForObjectDetection.from_pretrained(
        model_args.model_name_or_path,
        config=config,
        ignore_mismatched_sizes=model_args.ignore_mismatched_sizes,
        **common_pretrained_args,
    )
    image_processor = AutoImageProcessor.from_pretrained(
        model_args.image_processor_name or model_args.model_name_or_path,
        do_resize=True,
        size={
            "max_height": data_args.image_square_size,
            "max_width": data_args.image_square_size,
        },
        do_pad=True,
        pad_size={
            "height": data_args.image_square_size,
            "width": data_args.image_square_size,
        },
        use_fast=data_args.use_fast,
        **common_pretrained_args,
    )

    # ------------------------------------------------------------------------------------------------
    # Define image augmentations and dataset transforms
    # ------------------------------------------------------------------------------------------------
    max_size = data_args.image_square_size
    train_augment_and_transform = A.Compose(
        [
            # A.Compose(
            #     [
            #         A.SmallestMaxSize(max_size=max_size, p=1.0),
            #         A.RandomSizedBBoxSafeCrop(height=max_size, width=max_size, p=1.0),
            #     ],
            #     p=0.2,
            # ),
            # A.SmallestMaxSize(max_size=max_size, p=1.0),
            A.Perspective(p=0.1),
            A.HorizontalFlip(p=0.3),
            A.VerticalFlip(p=0.3),
            A.Rotate(360),
            A.OneOf(
                [
                    A.RandomBrightnessContrast(
                        brightness_limit=0.2, contrast_limit=0.2, p=1.0
                    ),
                    A.ColorJitter(
                        brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1, p=1.0
                    ),
                    A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=1.0),
                ],
                p=0.5,
            ),
            A.OneOf(
                [
                    A.Blur(blur_limit=7, p=1),
                    A.MotionBlur(blur_limit=7, p=1),
                    A.Defocus(radius=(1, 5), alias_blur=(0.1, 0.25), p=1),
                ],
                p=0.2,
            ),
            # A.Resize(height=max_size, width=max_size),
            # A.CenterCrop(height=max_size, width=max_size),
            A.Normalize(mean=image_processor.image_mean, std=image_processor.image_std),
        ],
        bbox_params=A.BboxParams(
            format="coco", label_fields=["category"], clip=True, min_area=25
        ),
    )
    validation_transform = A.Compose(
        [
            # A.Resize(height=max_size, width=max_size),
            # A.CenterCrop(height=max_size, width=max_size),
            A.Normalize(mean=image_processor.image_mean, std=image_processor.image_std),
        ],
        bbox_params=A.BboxParams(format="coco", label_fields=["category"], clip=True),
    )

    # Make transform functions for batch and apply for dataset splits
    train_transform_batch = partial(
        augment_and_transform_batch,
        transform=train_augment_and_transform,
        image_processor=image_processor,
    )
    validation_transform_batch = partial(
        augment_and_transform_batch,
        transform=validation_transform,
        image_processor=image_processor,
    )

    dataset["train"] = dataset["train"].with_transform(train_transform_batch)
    dataset["validation"] = dataset["validation"].with_transform(
        validation_transform_batch
    )
    dataset["test"] = dataset["test"].with_transform(validation_transform_batch)

    # ------------------------------------------------------------------------------------------------
    # Model training and evaluation with Trainer API
    # ------------------------------------------------------------------------------------------------

    eval_compute_metrics_fn = partial(
        compute_metrics,
        image_processor=image_processor,
        id2label=id2label,
        threshold=0.0,
    )
    mlflow.autolog()
    with mlflow.start_run():

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset["train"] if training_args.do_train else None,
            eval_dataset=dataset["validation"] if training_args.do_eval else None,
            processing_class=image_processor,
            data_collator=collate_fn,
            compute_metrics=eval_compute_metrics_fn,
        )

        # Training
        if training_args.do_train:
            train_result = trainer.train(
                resume_from_checkpoint=training_args.resume_from_checkpoint
            )
            trainer.save_model()
            trainer.log_metrics("train", train_result.metrics)
            trainer.save_metrics("train", train_result.metrics)
            trainer.save_state()

        # Final evaluation
        if training_args.do_eval:
            metrics = trainer.evaluate(
                eval_dataset=dataset["test"], metric_key_prefix="test"
            )
            trainer.log_metrics("test", metrics)
            trainer.save_metrics("test", metrics)

        # --- MLflow: log traceability artifacts + params (added) ---
        if mlflow.active_run() is not None and trainer.is_world_process_zero():
            # the dataset config that defined sources + include_classes
            if getattr(data_args, "dataset_config", None):
                mlflow.log_artifact(data_args.dataset_config, artifact_path="config")
            # a few key params for filtering runs in the UI
            mlflow.log_params({
                "num_classes": len(id2label),
                "base_model": model_args.model_name_or_path,
            })

    # Write model card and (optionally) push to hub
    kwargs = {
        "finetuned_from": model_args.model_name_or_path,
        "dataset": data_args.dataset_name,
        "tags": ["object-detection", "vision"],
    }
    if training_args.push_to_hub:
        trainer.push_to_hub(**kwargs)
    else:
        trainer.create_model_card(**kwargs)


if __name__ == "__main__":
    main()
