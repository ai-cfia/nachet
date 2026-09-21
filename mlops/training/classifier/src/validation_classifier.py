import torch
import os
import numpy as np
from transformers import Swinv2ForImageClassification, AutoImageProcessor
from torchvision.transforms import (
    Normalize,
    Lambda,
    Resize,
    CenterCrop,
    ToTensor,
    Compose,
)
from torchvision import datasets
from sklearn.metrics import (
    confusion_matrix,
    ConfusionMatrixDisplay,
    classification_report,
)
from tqdm import tqdm
import json
import matplotlib.pyplot as plt
import argparse
import re
from datetime import datetime


def load_model(checkpoint_path):
    model = Swinv2ForImageClassification.from_pretrained(checkpoint_path)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, device


def load_image_processor(checkpoint_path):
    image_processor = AutoImageProcessor.from_pretrained(checkpoint_path)
    if "shortest_edge" in image_processor.size:
        size = image_processor.size["shortest_edge"]
    else:
        size = (image_processor.size["height"], image_processor.size["width"])
    normalize = (
        Normalize(mean=image_processor.image_mean, std=image_processor.image_std)
        if hasattr(image_processor, "image_mean")
        and hasattr(image_processor, "image_std")
        else Lambda(lambda x: x)
    )
    transform = Compose(
        [
            Resize(size),
            CenterCrop(size),
            ToTensor(),
            normalize,
        ]
    )
    return transform


def load_test_data(test_dir, transform, batch_size):
    test_dataset = datasets.ImageFolder(root=test_dir, transform=transform)
    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False
    )
    class_to_idx = test_dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    return test_loader, idx_to_class


def evaluate_model(model, device, test_loader):
    total_samples = len(test_loader.dataset)
    progress_bar = tqdm(total=total_samples, desc="Test set inference", unit="samples")
    predictions = []
    y_test = []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images)
            _, preds = torch.max(outputs.logits, 1)
            predictions.extend(preds.cpu().numpy())
            y_test.extend(labels.cpu().numpy())
            progress_bar.update(len(images))
    return np.array(predictions), np.array(y_test)


def save_confusion_matrix(y_test, predictions, idx_to_class, output_path, figsize):
    cm_normalized = confusion_matrix(y_test, predictions, normalize="true")
    disp_normalized = ConfusionMatrixDisplay(
        cm_normalized,
        display_labels=[idx_to_class[i] for i in range(len(idx_to_class))],
    )
    fig, ax = plt.subplots(figsize=(figsize, figsize))
    disp_normalized.plot(ax=ax)
    disp_normalized.ax_.set_title("Normalized Confusion Matrix")
    plt.xticks(rotation=80)
    plt.tight_layout()  # Ensure the whole plot is saved without cropping
    plt.savefig(output_path)


def save_classification_report(y_test, predictions, idx_to_class, output_path):
    report = classification_report(
        y_test,
        predictions,
        target_names=[idx_to_class[i] for i in range(len(idx_to_class))],
        output_dict=True,
    )
    # Calculate accuracy for each class without reusing confusion_matrix
    correct_predictions = y_test == predictions
    for i, class_name in idx_to_class.items():
        class_indices = y_test == i
        class_accuracy = correct_predictions[class_indices].sum() / class_indices.sum()
        report[class_name]["accuracy"] = class_accuracy
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)


def is_valid_checkpoint_dir(dirname, chkstart, chkend):
    match = re.match(r"checkpoint-(\d+)", dirname)
    if match:
        checkpoint_num = int(match.group(1))
        return chkstart <= checkpoint_num <= chkend
    return False


def process_model(model_path, test_data_path, output_path, batch_size, figsize, test_name):
    model, device = load_model(model_path)
    transform = load_image_processor(model_path)
    test_loader, idx_to_class = load_test_data(test_data_path, transform, batch_size)
    predictions, y_test = evaluate_model(model, device, test_loader)
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


def main():
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
    args = parser.parse_args()

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
