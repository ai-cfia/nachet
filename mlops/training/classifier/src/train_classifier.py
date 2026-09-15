#!/usr/bin/env python
# Adapted from HFTrainer_classifier_2026061801_js.py.
# Transforms are in classifier_transforms.py; metrics use local scikit-learn.
# Local changes also cover bounded sample counts, split seeding, and run logging.
# Copyright 2021 The HuggingFace Inc. team. All rights reserved.
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
#
# =============================================================================
# Modifications by NACHET team (2025-12):
#
# 1. Imbalanced Data Handling:
#    - Added BalancedTrainer class with WeightedRandomSampler to oversample
#      minority classes during training
#    - Added compute_sample_weights() to calculate inverse class frequency weights
#
# 2. Extended Evaluation Metrics:
#    - Added macro-averaged precision, recall, and F1 score alongside accuracy
#    - Better suited for evaluating performance on imbalanced datasets
#
# 3. Heavy Data Augmentation:
#    - RandomHorizontalFlip, RandomVerticalFlip, RandomRotation (0-360 degrees)
#    - RandomAffine (scale 0.5-1.5), GaussianBlur, ColorJitter
#
# 4. Auto Checkpoint Detection:
#    - Automatically resumes training from last checkpoint if found
#
# 5. File + Console Logging:
#    - Logs to both console.log file and stdout
# =============================================================================


#  https://github.com/huggingface/transformers/blob/main/examples/pytorch/image-classification/README.md
#  python run_image_classification.py \
#     --dataset_name beans \
#     --output_dir ./beans_outputs/ \
#     --remove_unused_columns False \
#     --label_column_name labels \
#     --do_train \
#     --do_eval \
#     --push_to_hub \
#     --push_to_hub_model_id vit-base-beans \
#     --learning_rate 2e-5 \
#     --num_train_epochs 5 \
#     --per_device_train_batch_size 8 \
#     --per_device_eval_batch_size 8 \
#     --logging_strategy steps \
#     --logging_steps 10 \
#     --eval_strategy epoch \
#     --save_strategy epoch \
#     --load_best_model_at_end True \
#     --save_total_limit 3 \
#     --seed 1337


import logging
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import numpy as np
import torch
from datasets import load_dataset
from torch.utils.data import WeightedRandomSampler


import transformers
from transformers import (
    MODEL_FOR_IMAGE_CLASSIFICATION_MAPPING,
    AutoConfig,
    AutoImageProcessor,
    AutoModelForImageClassification,
    HfArgumentParser,
    Trainer,
    TrainingArguments,
    set_seed,
)
from transformers.trainer_utils import get_last_checkpoint
from transformers.utils import check_min_version
from transformers.utils.versions import require_version
import mlflow

""" Fine-tuning a 🤗 Transformers model for image classification"""

logger = logging.getLogger(__name__)

# Will error if the minimal version of Transformers is not installed. Remove at your own risks.
check_min_version("4.57.0.dev0")

require_version(
    "datasets>=2.14.0",
    "To fix: pip install -r examples/pytorch/image-classification/requirements.txt",
)

MODEL_CONFIG_CLASSES = list(MODEL_FOR_IMAGE_CLASSIFICATION_MAPPING.keys())
MODEL_TYPES = tuple(conf.model_type for conf in MODEL_CONFIG_CLASSES)


def detect_last_checkpoint(training_args):
    """Detect if there is a checkpoint to resume training from."""
    last_checkpoint = None
    if os.path.isdir(training_args.output_dir) and training_args.do_train:
        last_checkpoint = get_last_checkpoint(training_args.output_dir)
        if last_checkpoint is not None and training_args.resume_from_checkpoint is None:
            logger.info(
                f"Checkpoint detected, resuming training at {last_checkpoint}. To avoid this behavior, change "
                "the `--output_dir` or delete the existing output directory to train from scratch."
            )
    return last_checkpoint


def compute_sample_weights_from_labels(labels):
    """Compute sample weights for WeightedRandomSampler based on class frequencies."""
    class_counts = Counter(labels)
    num_samples = len(labels)

    # Weight for each class = total_samples / (num_classes * class_count)
    num_classes = len(class_counts)
    class_weights = {
        cls: num_samples / (num_classes * count) for cls, count in class_counts.items()
    }

    # Assign weight to each sample based on its class
    sample_weights = torch.tensor([class_weights[label] for label in labels])
    return sample_weights


class BalancedTrainer(Trainer):
    """Trainer with WeightedRandomSampler for imbalanced datasets."""

    def __init__(self, *args, sample_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sample_weights = sample_weights

    # Transformers 5.16.1 saves legacy Swin keys but Trainer resume loads them
    # without conversion. Use the model loader, keeping optimizer references intact.
    def _load_from_checkpoint(self, resume_from_checkpoint, model=None):
        model = self.model if model is None else model
        restored, loading_info = type(model).from_pretrained(
            resume_from_checkpoint,
            local_files_only=True,
            output_loading_info=True,
            dtype="auto",
        )
        if any(loading_info.values()):
            raise ValueError(
                f"checkpoint weights could not be fully restored: {loading_info}"
            )
        model.load_state_dict(restored.state_dict(), strict=True)

    def _load_best_model(self):
        self._load_from_checkpoint(self.state.best_model_checkpoint)

    def _get_train_sampler(self, *args, **kwargs):
        """Return a sampler; accepts optional dataset param for newer Trainer signatures."""
        if self.sample_weights is not None:
            return WeightedRandomSampler(
                weights=self.sample_weights,
                num_samples=len(self.sample_weights),
                replacement=True,
            )
        return super()._get_train_sampler(*args, **kwargs)


@dataclass
class DataTrainingArguments:
    """
    Arguments pertaining to what data we are going to input our model for training and eval.
    Using `HfArgumentParser` we can turn this class into argparse arguments to be able to specify
    them on the command line.
    """

    dataset_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "Name of a dataset from the hub (could be your own, possibly private dataset hosted on the hub)."
        },
    )
    dataset_config_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "The configuration name of the dataset to use (via the datasets library)."
        },
    )
    train_dir: Optional[str] = field(
        default=None, metadata={"help": "A folder containing the training data."}
    )
    validation_dir: Optional[str] = field(
        default=None, metadata={"help": "A folder containing the validation data."}
    )
    train_val_split: Optional[float] = field(
        default=0.15, metadata={"help": "Percent to split off of train for validation."}
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
    image_column_name: str = field(
        default="image",
        metadata={
            "help": "The name of the dataset column containing the image data. Defaults to 'image'."
        },
    )
    label_column_name: str = field(
        default="label",
        metadata={
            "help": "The name of the dataset column containing the labels. Defaults to 'label'."
        },
    )

    def __post_init__(self):
        if self.dataset_name is None and (
            self.train_dir is None and self.validation_dir is None
        ):
            raise ValueError(
                "You must specify either a dataset name from the hub or a train and/or validation directory."
            )


@dataclass
class ModelArguments:
    """
    Arguments pertaining to which model/config/tokenizer we are going to fine-tune from.
    """

    model_name_or_path: str = field(
        default="google/vit-base-patch16-224-in21k",
        metadata={
            "help": "Path to pretrained model or model identifier from huggingface.co/models"
        },
    )
    model_type: Optional[str] = field(
        default=None,
        metadata={
            "help": "If training from scratch, pass a model type from the list: "
            + ", ".join(MODEL_TYPES)
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
    ignore_mismatched_sizes: bool = field(
        default=False,
        metadata={
            "help": "Will enable to load a pretrained model whose head dimensions are different."
        },
    )


def train_classifier(transform_factory):
    # See all possible arguments in src/transformers/training_args.py
    # or by passing the --help flag to this script.
    # We now keep distinct sets of args, for a cleaner separation of concerns.

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

    # Keep the image column available for transforms; Trainer would drop it otherwise.
    training_args.remove_unused_columns = False

    # Inputs are read-only in Argo; keep the trainer log with its writable output.
    os.makedirs(training_args.output_dir, exist_ok=True)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(os.path.join(training_args.output_dir, "console.log")),
            logging.StreamHandler(sys.stdout),
        ],
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

    # Set seed before initializing model.
    set_seed(training_args.seed)

    logger.info("[stage] Checking for last checkpoint...")
    last_checkpoint = detect_last_checkpoint(training_args)
    if last_checkpoint:
        logger.info("[stage] Found checkpoint: %s", last_checkpoint)
    else:
        logger.info("[stage] No checkpoint found; starting fresh")

    # Initialize our dataset and prepare it for the 'image-classification' task.
    logger.info("[stage] Loading dataset...")
    if data_args.dataset_name is not None:
        dataset = load_dataset(
            data_args.dataset_name,
            data_args.dataset_config_name,
            cache_dir=model_args.cache_dir,
            token=model_args.token,
            trust_remote_code=model_args.trust_remote_code,
        )
    else:
        data_files = {}
        if data_args.train_dir is not None:
            data_files["train"] = os.path.join(data_args.train_dir, "**")
        if data_args.validation_dir is not None:
            data_files["validation"] = os.path.join(data_args.validation_dir, "**")
        dataset = load_dataset(
            "imagefolder",
            data_files=data_files,
            cache_dir=model_args.cache_dir,
        )

    logger.info(
        "[stage] Dataset loaded; preparing columns and splits... (splits=%s)",
        list(dataset.keys()),
    )
    dataset_column_names = (
        dataset["train"].column_names
        if "train" in dataset
        else dataset["validation"].column_names
    )
    if data_args.image_column_name not in dataset_column_names:
        raise ValueError(
            f"--image_column_name {data_args.image_column_name} not found in dataset '{data_args.dataset_name}'. "
            "Make sure to set `--image_column_name` to the image column - one of "
            f"{', '.join(dataset_column_names)}."
        )
    if data_args.label_column_name not in dataset_column_names:
        raise ValueError(
            f"--label_column_name {data_args.label_column_name} not found in dataset '{data_args.dataset_name}'. "
            "Make sure to set `--label_column_name` to the label column - one of "
            f"{', '.join(dataset_column_names)}."
        )

    def collate_fn(examples):
        pixel_values = torch.stack([example["pixel_values"] for example in examples])
        labels = torch.tensor(
            [example[data_args.label_column_name] for example in examples]
        )
        return {"pixel_values": pixel_values, "labels": labels}

    logger.info("[stage] Applying transforms and splits...")
    # If we don't have a validation split, split off a percentage of train as validation.
    data_args.train_val_split = (
        None if "validation" in dataset else data_args.train_val_split
    )
    if isinstance(data_args.train_val_split, float) and data_args.train_val_split > 0.0:
        split = dataset["train"].train_test_split(
            data_args.train_val_split,
            seed=training_args.seed,
        )
        dataset["train"] = split["train"]
        dataset["validation"] = split["test"]

    # Prepare label mappings.
    # We'll include these in the model's config to get human readable labels in the Inference API.
    labels = dataset["train"].features[data_args.label_column_name].names
    label2id, id2label = {}, {}
    for i, label in enumerate(labels):
        label2id[label] = str(i)
        id2label[str(i)] = label
    logger.info("[stage] Labels prepared: %d classes", len(labels))

    # Define our compute_metrics function. It takes an `EvalPrediction` object (a namedtuple with a
    # predictions and label_ids field) and has to return a dictionary string to float.
    def compute_metrics(p):
        """Compute accuracy and macro-averaged precision, recall and F1."""
        predictions = np.argmax(p.predictions, axis=1)
        references = p.label_ids

        # Calculate the same metrics locally; training pods need no Hub metric downloads.
        precision, recall, f1, _ = precision_recall_fscore_support(
            references,
            predictions,
            average="macro",
            zero_division=0,
        )
        return {
            "accuracy": accuracy_score(references, predictions),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    config = AutoConfig.from_pretrained(
        model_args.config_name or model_args.model_name_or_path,
        num_labels=len(labels),
        label2id=label2id,
        id2label=id2label,
        finetuning_task="image-classification",
        cache_dir=model_args.cache_dir,
        revision=model_args.model_revision,
        token=model_args.token,
        trust_remote_code=model_args.trust_remote_code,
    )
    model = AutoModelForImageClassification.from_pretrained(
        model_args.model_name_or_path,
        from_tf=bool(".ckpt" in model_args.model_name_or_path),
        config=config,
        cache_dir=model_args.cache_dir,
        revision=model_args.model_revision,
        token=model_args.token,
        trust_remote_code=model_args.trust_remote_code,
        ignore_mismatched_sizes=model_args.ignore_mismatched_sizes,
    )
    image_processor = AutoImageProcessor.from_pretrained(
        model_args.image_processor_name or model_args.model_name_or_path,
        cache_dir=model_args.cache_dir,
        revision=model_args.model_revision,
        token=model_args.token,
        trust_remote_code=model_args.trust_remote_code,
    )

    _train_transforms, _val_transforms = transform_factory(image_processor)

    def train_transforms(example_batch):
        """Apply _train_transforms across a batch."""
        example_batch["pixel_values"] = [
            _train_transforms(pil_img.convert("RGB"))
            for pil_img in example_batch[data_args.image_column_name]
        ]
        return example_batch

    def val_transforms(example_batch):
        """Apply _val_transforms across a batch."""
        example_batch["pixel_values"] = [
            _val_transforms(pil_img.convert("RGB"))
            for pil_img in example_batch[data_args.image_column_name]
        ]
        return example_batch

    # Compute sample weights before attaching image transforms to avoid heavy preprocessing here.
    logger.info(
        "[stage] Computing sample weights for balanced sampler (pre-transform)..."
    )
    sample_weights = None
    if training_args.do_train:
        if "train" not in dataset:
            raise ValueError("--do_train requires a train dataset")
        if data_args.max_train_samples is not None:
            dataset["train"] = (
                dataset["train"]
                .shuffle(seed=training_args.seed)
                .select(range(min(data_args.max_train_samples, len(dataset["train"]))))
            )
        labels_for_weights = dataset["train"][data_args.label_column_name]
        sample_weights = compute_sample_weights_from_labels(labels_for_weights)
        logger.info(
            "[stage] Sample weights computed (min=%.4f max=%.4f)",
            float(sample_weights.min()),
            float(sample_weights.max()),
        )

    # Now attach transforms for training/eval
    if training_args.do_train:
        dataset["train"].set_transform(train_transforms)
        logger.info(
            "[stage] Train split ready: %d samples (max_train_samples=%s)",
            len(dataset["train"]),
            data_args.max_train_samples,
        )

    if training_args.do_eval:
        if "validation" not in dataset:
            raise ValueError("--do_eval requires a validation dataset")
        if data_args.max_eval_samples is not None:
            dataset["validation"] = (
                dataset["validation"]
                .shuffle(seed=training_args.seed)
                .select(
                    range(min(data_args.max_eval_samples, len(dataset["validation"])))
                )
            )
        dataset["validation"].set_transform(val_transforms)
        logger.info(
            "[stage] Validation split ready: %d samples (max_eval_samples=%s)",
            len(dataset["validation"]),
            data_args.max_eval_samples,
        )

    mlflow.autolog()
    # MLflow parameters cannot change within a run; give each attempt a child run.
    with mlflow.start_run(), mlflow.start_run(nested=True):
        # Trainer records model settings; record the image-folder inputs alongside them.
        mlflow.log_params(
            {
                "train_dir": data_args.train_dir,
                "validation_dir": data_args.validation_dir,
                "train_val_split": data_args.train_val_split,
            }
        )
        logger.info("[stage] Initializing trainer...")

        # Initialize our trainer with balanced sampling
        trainer = BalancedTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset["train"] if training_args.do_train else None,
            eval_dataset=dataset["validation"] if training_args.do_eval else None,
            compute_metrics=compute_metrics,
            processing_class=image_processor,
            data_collator=collate_fn,
            sample_weights=sample_weights,
        )

        logger.info("[stage] Starting training...")
        if training_args.do_train:
            checkpoint = training_args.resume_from_checkpoint or last_checkpoint
            logger.info(
                "[stage] trainer.train starting (checkpoint=%s, grad_accum=%s, batch_size=%s)",
                checkpoint,
                training_args.gradient_accumulation_steps,
                training_args.per_device_train_batch_size,
            )
            train_result = trainer.train(resume_from_checkpoint=checkpoint)
            trainer.save_model()
            trainer.log_metrics("train", train_result.metrics)
            trainer.save_metrics("train", train_result.metrics)
            trainer.save_state()

        # Evaluation
        if training_args.do_eval:
            logger.info("[stage] Starting evaluation...")
            metrics = trainer.evaluate()
            trainer.log_metrics("eval", metrics)
            trainer.save_metrics("eval", metrics)

        # Write model card and (optionally) push to hub
        kwargs = {
            "finetuned_from": model_args.model_name_or_path,
            "tasks": "image-classification",
            "dataset": data_args.dataset_name,
            "tags": ["image-classification", "vision"],
        }
        if training_args.push_to_hub:
            trainer.push_to_hub(**kwargs)
        else:
            trainer.create_model_card(**kwargs)


def main():
    from classifier_transforms import build_transforms

    train_classifier(build_transforms)


if __name__ == "__main__":
    main()
