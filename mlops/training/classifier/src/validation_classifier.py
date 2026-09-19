#!/usr/bin/env python
# Migrated from nachet-model-ccds/nachetmodel/ModelEvaluator.py at
# 228af71adde722d7a484fe6738f5189c9ad48922.
"""Evaluate image-classification checkpoints on ImageFolder data."""

import argparse
from datetime import datetime
import json
import os
import re

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
)
import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.transforms import (
    CenterCrop,
    Compose,
    Lambda,
    Normalize,
    Resize,
    ToTensor,
)
from tqdm import tqdm
from transformers import AutoImageProcessor, AutoModelForImageClassification


def load_model(checkpoint_path):
    """Load whichever image-classification architecture the checkpoint declares."""
    model = AutoModelForImageClassification.from_pretrained(checkpoint_path)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, device


def load_image_processor(checkpoint_path):
    """Build the historical evaluator's checkpoint-driven preprocessing."""
    image_processor = AutoImageProcessor.from_pretrained(checkpoint_path)
    if "shortest_edge" in image_processor.size:
        size = image_processor.size["shortest_edge"]
    else:
        size = (image_processor.size["height"], image_processor.size["width"])
    normalize = (
        Normalize(mean=image_processor.image_mean, std=image_processor.image_std)
        if hasattr(image_processor, "image_mean")
        and hasattr(image_processor, "image_std")
        else Lambda(lambda tensor: tensor)
    )
    return Compose([Resize(size), CenterCrop(size), ToTensor(), normalize])


def load_test_data(test_dir, transform, batch_size):
    test_dataset = datasets.ImageFolder(root=test_dir, transform=transform)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    class_to_idx = test_dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    return test_loader, idx_to_class


def normalize_class_name(class_name):
    """Normalize class names without discarding meaningful words."""
    return " ".join(class_name.replace("_", " ").split()).casefold()


def model_idx_to_class(model):
    """Return every output label in logit order, rejecting incomplete configs."""
    try:
        labels = {int(index): name for index, name in model.config.id2label.items()}
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("model id2label keys must be integer-like") from error

    expected_ids = list(range(model.config.num_labels))
    if sorted(labels) != expected_ids:
        raise ValueError(
            "model id2label IDs must cover every logit from 0 through "
            f"{model.config.num_labels - 1}; found {sorted(labels)}"
        )
    if any(not isinstance(name, str) or not name.strip() for name in labels.values()):
        raise ValueError("model id2label values must be non-empty strings")
    return labels


def map_dataset_class_ids(dataset_idx_to_class, model_labels):
    """Map ImageFolder IDs into model-logit IDs using normalized class names.

    The model label space remains complete. Only ground-truth IDs are translated;
    prediction argmax still sees every output logit.
    """
    model_ids_by_name = {}
    for model_id, class_name in model_labels.items():
        normalized = normalize_class_name(class_name)
        if normalized in model_ids_by_name:
            other_id = model_ids_by_name[normalized]
            raise ValueError(
                "ambiguous model class names after normalization: "
                f"{model_labels[other_id]!r} and {class_name!r}"
            )
        model_ids_by_name[normalized] = model_id

    # Distinct folders that normalize to one name cannot be assigned safely.
    dataset_ids_by_name = {}
    for dataset_id, class_name in dataset_idx_to_class.items():
        normalized = normalize_class_name(class_name)
        if normalized in dataset_ids_by_name:
            other_id = dataset_ids_by_name[normalized]
            raise ValueError(
                "ambiguous external-validation class names after normalization: "
                f"{dataset_idx_to_class[other_id]!r} and {class_name!r}"
            )
        dataset_ids_by_name[normalized] = dataset_id

    unknown = sorted(
        class_name
        for class_name in dataset_idx_to_class.values()
        if normalize_class_name(class_name) not in model_ids_by_name
    )
    if unknown:
        raise ValueError(
            "external-validation classes are missing from model id2label: "
            + ", ".join(repr(name) for name in unknown)
        )

    return {
        dataset_id: model_ids_by_name[normalize_class_name(class_name)]
        for dataset_id, class_name in dataset_idx_to_class.items()
    }


def evaluate_model(model, device, test_loader, dataset_id_to_model_id=None):
    total_samples = len(test_loader.dataset)
    progress_bar = tqdm(total=total_samples, desc="Test set inference", unit="samples")
    predictions = []
    y_test = []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            _, preds = torch.max(outputs.logits, 1)
            predictions.extend(preds.cpu().numpy())

            # ImageFolder assigns alphabetical local IDs. Translate only the
            # references so predictions remain in the model's full label space.
            if dataset_id_to_model_id is None:
                y_test.extend(labels.numpy())
            else:
                y_test.extend(
                    dataset_id_to_model_id[int(label)] for label in labels
                )
            progress_bar.update(len(images))
    progress_bar.close()
    return np.array(predictions), np.array(y_test)


def save_confusion_matrix(y_test, predictions, idx_to_class, output_path, figsize):
    label_ids = list(range(len(idx_to_class)))
    cm_normalized = confusion_matrix(
        y_test, predictions, labels=label_ids, normalize="true"
    )
    disp_normalized = ConfusionMatrixDisplay(
        cm_normalized,
        display_labels=[idx_to_class[i] for i in label_ids],
    )
    fig, ax = plt.subplots(figsize=(figsize, figsize))
    disp_normalized.plot(ax=ax)
    disp_normalized.ax_.set_title("Normalized Confusion Matrix")
    plt.xticks(rotation=80)
    plt.tight_layout()  # Ensure the whole plot is saved without cropping
    plt.savefig(output_path)
    plt.close(fig)


def save_classification_report(y_test, predictions, idx_to_class, output_path):
    label_ids = list(range(len(idx_to_class)))
    report = classification_report(
        y_test,
        predictions,
        labels=label_ids,
        target_names=[idx_to_class[i] for i in label_ids],
        output_dict=True,
        zero_division=0,
    )
    # Preserve the historical per-class accuracy field. An absent model-only
    # class has no correct references, so its accuracy is explicitly zero.
    correct_predictions = y_test == predictions
    for i, class_name in idx_to_class.items():
        class_indices = y_test == i
        support = int(class_indices.sum())
        report[class_name]["accuracy"] = (
            float(correct_predictions[class_indices].sum() / support)
            if support
            else 0.0
        )
    with open(output_path, "w") as file:
        json.dump(report, file, indent=4)


def is_valid_checkpoint_dir(dirname, chkstart, chkend):
    match = re.match(r"checkpoint-(\d+)", dirname)
    if match:
        checkpoint_num = int(match.group(1))
        return chkstart <= checkpoint_num <= chkend
    return False


def process_model(model_path, test_data_path, output_path, batch_size, figsize, test_name):
    model, device = load_model(model_path)
    transform = load_image_processor(model_path)
    test_loader, dataset_idx_to_class = load_test_data(
        test_data_path, transform, batch_size
    )

    # The model owns output IDs; folder ordering only identifies the incoming
    # ground truth and must never redefine or subset the classifier head.
    idx_to_class = model_idx_to_class(model)
    dataset_id_to_model_id = map_dataset_class_ids(
        dataset_idx_to_class, idx_to_class
    )
    predictions, y_test = evaluate_model(
        model, device, test_loader, dataset_id_to_model_id
    )
    os.makedirs(output_path, exist_ok=True)
    print("Saving evaluation results to {}...".format(output_path))
    save_confusion_matrix(
        y_test,
        predictions,
        idx_to_class,
        f"{output_path}/{output_path.split('/')[-1]}_confusion_matrix.png",
        figsize,
    )
    save_classification_report(
        y_test,
        predictions,
        idx_to_class,
        f"{output_path}/{output_path.split('/')[-1]}{test_name}_classification_report.json",
    )
    with torch.no_grad():
        torch.cuda.empty_cache()


def get_parser():
    parser = argparse.ArgumentParser(description="Evaluate model checkpoints.")
    parser.add_argument(
        "--model_path",
        type=str,
        help="Path to the model checkpoint or parent directory.",
    )
    parser.add_argument(
        "--test_data_path", type=str, help="Path to the test data directory."
    )
    parser.add_argument(
        "--batch_size", type=int, default=4, help="Batch size for inference."
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="output",
        help="Path to save evaluation results.",
    )
    parser.add_argument(
        "--parent",
        type=str,
        choices=["true", "false"],
        default="false",
        help="If set to true, process as parent directory containing multiple checkpoint directories.",
    )
    parser.add_argument(
        "--chkstart",
        type=int,
        default=0,
        help="Start range for checkpoint directories (inclusive).",
    )
    parser.add_argument(
        "--chkend",
        type=int,
        default=float("inf"),
        help="End range for checkpoint directories (inclusive).",
    )
    parser.add_argument(
        "--figsize", type=int, default=10, help="Size of the confusion matrix figure."
    )
    parser.add_argument(
        "--test_name", type=str, default="", help="Name of the test dataset."
    )
    return parser


def main():
    args = get_parser().parse_args()

    print("{}: Starting evaluation...".format(datetime.now()))

    if args.chkstart < 0 or args.chkend < 0:
        raise ValueError("chkstart and chkend must be positive integers.")

    if args.parent == "true":
        for subdir in os.listdir(args.model_path):
            subdir_path = os.path.join(args.model_path, subdir)
            if os.path.isdir(subdir_path) and is_valid_checkpoint_dir(
                subdir, args.chkstart, args.chkend
            ):
                process_model(
                    subdir_path,
                    args.test_data_path,
                    os.path.join(args.output_path, subdir),
                    args.batch_size,
                    args.figsize,
                    args.test_name,
                )
    else:
        process_model(
            args.model_path,
            args.test_data_path,
            args.output_path,
            args.batch_size,
            args.figsize,
            args.test_name,
        )

    print("{}: Evaluation complete.".format(datetime.now()))


if __name__ == "__main__":
    main()
