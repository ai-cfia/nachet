#!/usr/bin/env python
"""Evaluate classifier checkpoints with the June 2026 notebook's reports.

Adapted from 4.10_js_classifier_validation_v2_6seed_101spp_20260625.ipynb.
"""

import argparse
import json
import math
import random
import re
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from datasets import load_dataset
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from torch.utils.data import Subset
from transformers import AutoImageProcessor, AutoModelForImageClassification


matplotlib.use("Agg")
TOP_K_LIST = [1, 3, 5]
plt.rcParams["figure.figsize"] = [12, 6]
sns.set_style("whitegrid")


def strip_class_prefix(name):
    """Strip leading numbers and whitespace from a folder class name."""
    return re.sub(r"^\d+\s*", "", name.strip())


def normalize_class_name(name):
    """Normalize case, separators and surrounding whitespace for label matching."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Class name must be a nonempty string: {name!r}")
    return name.strip().lower().replace("_", " ").replace("-", " ")


def find_processor_path(model_path, processor_path=None):
    """Find the processor in the checkpoint or its two parent directories."""
    # A bad override must not silently select another processor.
    if processor_path is not None:
        path = Path(processor_path)
        if (path / "preprocessor_config.json").exists():
            return path
        raise FileNotFoundError(f"No preprocessor_config.json found in {path}")
    model_path = Path(model_path)
    candidates = [model_path, model_path.parent, model_path.parent.parent]
    for path in candidates:
        if (path / "preprocessor_config.json").exists():
            return path
    raise FileNotFoundError(f"No preprocessor_config.json found in {candidates}")


def load_model(model_path, processor_path=None):
    """Load the saved processor and model, then put the model in evaluation mode."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    processor_dir = find_processor_path(model_path, processor_path)
    print(f"Loading processor from: {processor_dir}")
    processor = AutoImageProcessor.from_pretrained(processor_dir)
    model = AutoModelForImageClassification.from_pretrained(model_path).to(device)
    model.eval()
    return processor, model, device


def load_test_data(test_data_path):
    """Load an imagefolder's single train split and preserve folder label order."""
    # ImageFolder otherwise omits labels when the input has only one species.
    ds = load_dataset("imagefolder", data_dir=str(test_data_path), drop_labels=False)
    val_ds = ds["train"]
    raw_class_names = val_ds.features["label"].names
    dataset_class_names = [strip_class_prefix(name) for name in raw_class_names]
    counts = val_ds.to_pandas()["label"].value_counts().sort_index()
    print(f"Images: {len(val_ds):,}")
    print(f"Dataset Classes ({len(dataset_class_names)}): {dataset_class_names}")
    print(pd.DataFrame({"class": dataset_class_names, "count": counts.values}))
    return val_ds, dataset_class_names


def match_classes(val_ds, dataset_class_names, model):
    """Map folder labels to model IDs and report skipped dataset classes."""
    model_id2label = {int(index): name for index, name in model.config.id2label.items()}
    num_model_classes = model.config.num_labels
    if sorted(model_id2label) != list(range(num_model_classes)):
        raise ValueError("Model id2label must cover every output ID from 0 to num_labels - 1")
    model_class_names = [model_id2label[i] for i in range(num_model_classes)]
    num_dataset_classes = len(dataset_class_names)
    print(f"\nModel Classes ({len(model_class_names)}): {model_class_names}")
    print(f"Dataset Classes ({num_dataset_classes}): {dataset_class_names}")

    # Report original folder names when normalization makes two labels identical.
    raw_names = dataset_class_names
    if hasattr(val_ds, "features"):
        raw_names = val_ds.features["label"].names
    dataset_normalized = {}
    for index, name in enumerate(dataset_class_names):
        key = normalize_class_name(name)
        if key in dataset_normalized:
            other = dataset_normalized[key]
            raise ValueError(
                "Dataset class names collide after prefix stripping and normalization: "
                f"{raw_names[other]!r} ({dataset_class_names[other]!r}) and "
                f"{raw_names[index]!r} ({name!r})"
            )
        dataset_normalized[key] = index
    model_normalized = {}
    for index, name in enumerate(model_class_names):
        key = normalize_class_name(name)
        if key in model_normalized:
            other = model_normalized[key]
            raise ValueError(
                "Model class names collide after normalization: "
                f"{model_class_names[other]!r} and {name!r}"
            )
        model_normalized[key] = index
    dataset_to_model_idx = {}
    matched_classes = []
    dataset_only_classes = []
    model_only_classes = []
    for ds_name, ds_idx in dataset_normalized.items():
        if ds_name in model_normalized:
            model_idx = model_normalized[ds_name]
            dataset_to_model_idx[ds_idx] = model_idx
            matched_classes.append(dataset_class_names[ds_idx])
        else:
            dataset_only_classes.append(dataset_class_names[ds_idx])
    for model_name, model_idx in model_normalized.items():
        if model_name not in dataset_normalized:
            model_only_classes.append(model_class_names[model_idx])

    print("\n--- Class Matching Summary ---")
    print(f"Matched classes: {len(matched_classes)}")
    print(f"Dataset-only classes (will be skipped): {len(dataset_only_classes)} - {dataset_only_classes}")
    print(f"Model-only classes (not in validation set): {len(model_only_classes)} - {model_only_classes}")
    if len(matched_classes) == 0:
        raise ValueError("No matching classes between dataset and model!")

    # Keep source indices for the misprediction image grid.
    matched_dataset_indices = list(dataset_to_model_idx.keys())
    print(f"\nFiltering dataset to {len(matched_classes)} matched classes...")
    valid_sample_indices = []
    for idx in range(len(val_ds)):
        if val_ds[idx]["label"] in matched_dataset_indices:
            valid_sample_indices.append(idx)
    print(f"Samples after filtering: {len(valid_sample_indices):,} / {len(val_ds):,}")
    if not valid_sample_indices:
        raise ValueError("No validation samples remain after matching dataset classes")
    matching = {
        "matched_classes": matched_classes,
        "dataset_only_classes": dataset_only_classes,
        "model_only_classes": model_only_classes,
        "evaluated_samples": len(valid_sample_indices),
        "skipped_samples": len(val_ds) - len(valid_sample_indices),
    }
    return dataset_to_model_idx, valid_sample_indices, matching


def make_eval_loader(val_ds, valid_sample_indices, processor, batch_size, num_workers):
    """Apply the saved processor to RGB images in a filtered DataLoader."""
    if num_workers and torch.multiprocessing.get_start_method() != "fork":
        raise ValueError("num_workers > 0 requires fork; use --num_workers 0 with spawn")

    def transform_batch(examples):
        images = examples["image"]
        if not isinstance(images, list):
            images = [images]
        images = [image.convert("RGB") for image in images]
        pixel_values = processor(images=images, return_tensors="pt")["pixel_values"]
        return {"pixel_values": pixel_values, "labels": examples["label"]}

    def collate_fn(batch):
        pixel_values = torch.stack([item["pixel_values"].squeeze(0) for item in batch], dim=0)
        labels = torch.tensor([item["labels"] for item in batch])
        return {"pixel_values": pixel_values, "labels": labels}

    eval_ds = val_ds.with_transform(transform_batch)
    eval_subset = Subset(eval_ds, valid_sample_indices)
    eval_loader = torch.utils.data.DataLoader(
        eval_subset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=collate_fn,
    )
    print(f"Batches: {len(eval_loader)}")
    return eval_loader


def evaluate_model(model, device, eval_loader, dataset_to_model_idx):
    """Score full model logits against references mapped to model IDs."""
    num_classes = model.config.num_labels

    all_logits = []
    all_preds = []
    all_labels = []
    topk_correct = {k: 0 for k in TOP_K_LIST}
    total = 0
    with torch.no_grad():
        for batch in eval_loader:
            pixel_values = batch["pixel_values"].to(device)
            dataset_labels = batch["labels"]
            logits = model(pixel_values=pixel_values).logits
            if logits.size(-1) != num_classes:
                raise ValueError("Model logits do not match config.num_labels")
            preds = logits.argmax(dim=-1)
            model_labels = torch.tensor(
                [dataset_to_model_idx[label.item()] for label in dataset_labels],
                device=device,
            )
            all_logits.append(logits.cpu())
            all_preds.append(preds.cpu())
            all_labels.append(model_labels.cpu())
            for k in TOP_K_LIST:
                if k <= num_classes:
                    topk_indices = torch.topk(logits, k=k, dim=-1).indices
                    topk_correct[k] += (
                        (topk_indices == model_labels.unsqueeze(1)).any(dim=1).sum().item()
                    )
            total += model_labels.size(0)
    print(f"Inference complete. Total samples: {total}")
    return (
        torch.cat(all_logits),
        torch.cat(all_preds).numpy(),
        torch.cat(all_labels).numpy(),
        topk_correct,
        total,
    )


def save_sample_images(val_ds, dataset_class_names, output_dir):
    """Save one randomly chosen RGB image per class, alphabetically arranged."""
    num_dataset_classes = len(dataset_class_names)
    indices_by_class = {i: [] for i in range(num_dataset_classes)}
    for idx in range(len(val_ds)):
        label = val_ds[idx]["label"]
        indices_by_class[label].append(idx)
    samples_by_class = {
        cls: random.choice(indices) for cls, indices in indices_by_class.items()
    }
    sorted_classes = sorted(range(num_dataset_classes), key=lambda i: dataset_class_names[i])
    cols = 5
    rows = math.ceil(num_dataset_classes / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 3 * rows))
    axes = axes.flatten()
    for i, class_idx in enumerate(sorted_classes):
        ax = axes[i]
        image = val_ds[samples_by_class[class_idx]]["image"].convert("RGB")
        ax.imshow(image)
        ax.set_title(dataset_class_names[class_idx], fontsize=9)
        ax.axis("off")
    for ax in axes[num_dataset_classes:]:
        ax.axis("off")
    plt.suptitle("Sample Images by Class (Alphabetical)", fontsize=14, y=1.01)
    plt.tight_layout()
    fig.savefig(output_dir / "sample_images_by_class.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_metrics(all_logits, all_preds, all_labels, topk_correct, total, class_names, matching, output_dir):
    """Score all model classes, with null AUC where OvR is undefined."""
    num_classes = len(class_names)
    all_probs = torch.softmax(all_logits, dim=-1).numpy()
    print("--- Top-K Accuracy ---")
    for k in TOP_K_LIST:
        if k <= num_classes:
            print(f"Top-{k} accuracy: {topk_correct[k] / total:.4f}")
    print("\n--- ROC AUC (One-vs-Rest) ---")
    # AUC needs both positive and negative examples for each class.
    roc_auc_per_class = []
    supports = np.bincount(all_labels, minlength=num_classes)
    for index in range(num_classes):
        binary_labels = all_labels == index
        if not binary_labels.any() or binary_labels.all():
            roc_auc_per_class.append(None)
        else:
            roc_auc_per_class.append(float(roc_auc_score(binary_labels, all_probs[:, index])))
    defined_indices = [index for index, auc in enumerate(roc_auc_per_class) if auc is not None]
    if defined_indices:
        defined_aucs = [roc_auc_per_class[index] for index in defined_indices]
        roc_auc_macro = float(np.mean(defined_aucs))
        roc_auc_weighted = float(np.average(defined_aucs, weights=supports[defined_indices]))
        print(f"ROC AUC (macro):    {roc_auc_macro:.4f} ({len(defined_indices)}/{num_classes} classes defined)")
        print(f"ROC AUC (weighted): {roc_auc_weighted:.4f} ({len(defined_indices)}/{num_classes} classes defined)")
    else:
        roc_auc_macro = None
        roc_auc_weighted = None
        print("ROC AUC (macro/weighted): undefined (no class has both positives and negatives)")
    roc_auc_dict = {name: roc_auc_per_class[index] for index, name in enumerate(class_names)}

    report = classification_report(
        all_labels, all_preds, labels=list(range(num_classes)),
        target_names=class_names, output_dict=True, zero_division=0,
    )
    report_df = pd.DataFrame(report).T
    print(report_df.round(4))
    metrics = {
        "top_k_accuracy": {
            f"top_{k}": topk_correct[k] / total for k in TOP_K_LIST if k <= num_classes
        },
        "roc_auc": {
            "macro": roc_auc_macro,
            "weighted": roc_auc_weighted,
            "per_class": roc_auc_dict,
        },
        "classification_report": report,
        "class_matching": matching,
    }
    metrics_path = output_dir / "validation_metrics.json"
    with metrics_path.open("w") as stream:
        json.dump(metrics, stream, indent=2, allow_nan=False)
    print(f"\nMetrics saved to {metrics_path}")
    return report_df, roc_auc_per_class if defined_indices else None


def save_per_class_report(report_df, roc_auc_per_class, all_labels, all_preds, class_names, output_dir, figsize):
    """Save per-class metrics, their heatmap and the normalized confusion matrix."""
    num_classes = len(class_names)
    class_metrics = report_df.loc[class_names].copy()
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(num_classes)))
    # Match classification_report's zero_division=0 for classes with no samples.
    per_class_acc = np.divide(
        cm.diagonal(), cm.sum(axis=1), out=np.zeros(num_classes, dtype=float),
        where=cm.sum(axis=1) != 0,
    )
    class_metrics["accuracy"] = per_class_acc
    if roc_auc_per_class is not None:
        class_metrics["roc_auc"] = pd.to_numeric(pd.Series(roc_auc_per_class, index=class_names))

    # Scale colors above 0.80; annotations show the actual scores.
    fig, ax = plt.subplots(figsize=(12, max(10, len(class_metrics) * 0.4)))
    heatmap_cols = ["precision", "recall", "f1-score", "accuracy"]
    if roc_auc_per_class is not None:
        heatmap_cols.append("roc_auc")
    heatmap_df = class_metrics[heatmap_cols].sort_index()
    red_threshold = 0.80
    threshold_range = 1.0 - red_threshold
    color_df = ((heatmap_df - red_threshold) / threshold_range).clip(0, 1)
    sns.heatmap(color_df, annot=heatmap_df, fmt=".3f", cmap="RdYlGn", vmin=0, vmax=1, ax=ax, cbar=False)
    title_metrics = "Precision, Recall, F1-Score, Accuracy" + (
        " & ROC AUC" if roc_auc_per_class is not None else ""
    )
    ax.set_title(f"Per-Class Classification Performance\n({title_metrics})", fontsize=14)
    ax.set_xlabel("Metric", fontsize=12)
    ax.set_ylabel("Class", fontsize=12)
    plt.tight_layout()
    fig.savefig(output_dir / "classification_report_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("\n=== Per-Class Summary Statistics ===")
    summary_metrics = ["precision", "recall", "f1-score", "accuracy"]
    if roc_auc_per_class is not None:
        summary_metrics.append("roc_auc")
    for metric in summary_metrics:
        metric_title = metric.replace("-", " ").replace("_", " ").title()
        defined = class_metrics[metric].dropna()
        print(f"{metric_title}: {len(defined)}/{num_classes} classes with defined report values")
        print(f"Mean {metric_title}:   {defined.mean():.4f}")
        print(f"Median {metric_title}: {defined.median():.4f}")
        print(f"Std {metric_title}:    {defined.std():.4f}")
        print(f"Min {metric_title}:    {defined.min():.4f} ({defined.idxmin()})")
        print(f"Max {metric_title}:    {defined.max():.4f} ({defined.idxmax()})")
        print()
    export_cols = ["precision", "recall", "f1-score", "support", "accuracy"]
    if roc_auc_per_class is not None:
        export_cols.append("roc_auc")
    class_metrics[export_cols].round(4).to_csv(output_dir / "per_class_metrics.csv")
    print(f"Saved per-class metrics to {output_dir / 'per_class_metrics.csv'}")

    # Keep correct predictions gray so classification errors stand out in red.
    cm_norm = np.divide(
        cm.astype(float), cm.sum(axis=1, keepdims=True),
        out=np.zeros_like(cm, dtype=float), where=cm.sum(axis=1, keepdims=True) != 0,
    )
    fig_size = max(figsize, num_classes * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    colors_array = np.zeros((num_classes, num_classes, 3))
    for i in range(num_classes):
        for j in range(num_classes):
            val = cm_norm[i, j]
            if i == j:
                colors_array[i, j] = [0.95, 0.95, 0.95]
            else:
                intensity = min(val * 5, 1.0)
                colors_array[i, j] = [1, 1 - 0.8 * intensity, 1 - 0.8 * intensity]
    ax.imshow(colors_array, aspect="auto")
    for i in range(num_classes):
        for j in range(num_classes):
            val = cm_norm[i, j]
            if val == 0:
                continue
            fontweight = "bold" if i != j and val > 0.1 else "normal"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color="black", fontweight=fontweight)
    ax.set_xticks(range(num_classes))
    ax.set_yticks(range(num_classes))
    ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(class_names, fontsize=8)
    ax.set_title("Confusion Matrix (Row-Normalized)", fontsize=14)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.grid(False)
    ax.set_frame_on(False)
    plt.tight_layout()
    fig.savefig(output_dir / "confusion_matrix_normalized.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return class_metrics, cm


def save_tp_fn_plot(cm, class_names, output_dir):
    """Plot recall and false-negative percentage from each confusion row."""
    num_classes = len(class_names)
    per_class_tp = cm.diagonal()
    per_class_fn = cm.sum(axis=1) - cm.diagonal()
    row_totals = per_class_tp + per_class_fn
    recall = np.divide(per_class_tp, row_totals, out=np.zeros(num_classes, dtype=float), where=row_totals != 0)
    fn_percent = np.divide(100 * per_class_fn, row_totals, out=np.zeros(num_classes, dtype=float), where=row_totals != 0)
    tp_fn_df = pd.DataFrame({
        "class": class_names,
        "TP": per_class_tp,
        "FN": per_class_fn,
        "Total": row_totals,
        "recall": recall,
        "fn_percent": fn_percent,
    }).sort_values("class")
    fig, axes = plt.subplots(1, 2, figsize=(16, max(8, num_classes * 0.3)))
    ax1, ax2 = axes
    plot_df = tp_fn_df.sort_values("recall", ascending=False)
    colors = [
        "tab:gray" if total == 0 else "tab:green" if r >= 0.8 else "tab:orange" if r >= 0.5 else "tab:red"
        for r, total in zip(plot_df["recall"], plot_df["Total"])
    ]
    bars = ax1.barh(plot_df["class"], plot_df["recall"], color=colors, alpha=0.8)
    ax1.set_xlabel("Recall (Per-Class Accuracy)", fontsize=12)
    ax1.set_ylabel("Class", fontsize=12)
    ax1.set_title("Per-Class Recall (Worst on Top)", fontsize=14)
    ax1.set_xlim(min(plot_df["recall"]) - 0.1, 1)
    ax1.grid(False)
    overall_acc = per_class_tp.sum() / (per_class_tp.sum() + per_class_fn.sum())
    ax1.axvline(x=overall_acc, color="blue", linestyle="--", linewidth=1, label=f"Overall Accuracy: {overall_acc:.3f}")
    ax1.legend(loc="lower right")
    ax1.tick_params(axis="y", labelsize=8)
    for bar, val, support in zip(bars, plot_df["recall"], plot_df["Total"]):
        label = f"{val:.3f}" if support else "N/A"
        ax1.text(val + 0.01, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=7)

    plot_df_fn = tp_fn_df.sort_values("fn_percent", ascending=True)
    colors_fn = [
        "tab:gray" if total == 0 else "tab:red" if fn > 10 else "tab:orange" if fn > 5 else "tab:green"
        for fn, total in zip(plot_df_fn["fn_percent"], plot_df_fn["Total"])
    ]
    bars2 = ax2.barh(plot_df_fn["class"], plot_df_fn["fn_percent"], color=colors_fn, alpha=0.8)
    ax2.set_xlabel("False Negatives (%)", fontsize=12)
    ax2.set_ylabel("Class", fontsize=12)
    ax2.set_title("False Negative Rate per Class (Worst on Top)", fontsize=14)
    ax2.set_xlim(0, max(plot_df_fn["fn_percent"]) + 5)
    ax2.tick_params(axis="y", labelsize=8)
    ax2.grid(False)
    for bar, val, support in zip(bars2, plot_df_fn["fn_percent"], plot_df_fn["Total"]):
        label = f"{val:.1f}%" if support else "N/A"
        ax2.text(val + 0.3, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=7)
    plt.tight_layout()
    fig.savefig(output_dir / "per_class_tp_fn_bar.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved to {output_dir / 'per_class_tp_fn_bar.png'}")


def save_precision_plot(cm, class_metrics, class_names, output_dir):
    """Plot precision and the false-positive share of each predicted class."""
    num_classes = len(class_names)
    per_class_fp = cm.sum(axis=0) - cm.diagonal()
    per_class_total_preds = cm.sum(axis=0)
    fp_percent = np.divide(
        100 * per_class_fp, per_class_total_preds,
        out=np.zeros(num_classes, dtype=float), where=per_class_total_preds != 0,
    )
    precision_df = pd.DataFrame({
        "class": class_names,
        "precision": class_metrics["precision"].values,
        "false_positives": per_class_fp,
        "total_predictions": per_class_total_preds,
        "fp_percent": fp_percent,
    })
    fig, axes = plt.subplots(1, 2, figsize=(16, max(8, num_classes * 0.3)))
    ax1, ax2 = axes
    plot_df = precision_df.sort_values("precision", ascending=False)
    colors = ["tab:green" if p >= 0.8 else "tab:orange" if p >= 0.5 else "tab:red" for p in plot_df["precision"]]
    bars = ax1.barh(plot_df["class"], plot_df["precision"], color=colors, alpha=0.8)
    ax1.set_xlabel("Precision", fontsize=12)
    ax1.set_ylabel("Class", fontsize=12)
    ax1.set_title("Per-Class Precision (Worst on Top)", fontsize=14)
    ax1.set_xlim(min(plot_df["precision"]) - 0.1, 1)
    ax1.grid(False)
    mean_precision = class_metrics["precision"].mean()
    ax1.axvline(x=mean_precision, color="blue", linestyle="--", linewidth=1, label=f"Mean Precision: {mean_precision:.3f}")
    ax1.legend(loc="lower right")
    ax1.tick_params(axis="y", labelsize=8)
    for bar, val in zip(bars, plot_df["precision"]):
        ax1.text(val + 0.01, bar.get_y() + bar.get_height() / 2, f"{val:.2f}", va="center", fontsize=7)

    plot_df_fp = precision_df.sort_values("fp_percent", ascending=True)
    colors_fp = [
        "tab:gray" if total == 0 else "tab:red" if fp > 10 else "tab:orange" if fp > 5 else "tab:green"
        for fp, total in zip(plot_df_fp["fp_percent"], plot_df_fp["total_predictions"])
    ]
    bars2 = ax2.barh(plot_df_fp["class"], plot_df_fp["fp_percent"], color=colors_fp, alpha=0.8)
    ax2.set_xlabel("False Positives (%)", fontsize=12)
    ax2.set_ylabel("Class", fontsize=12)
    ax2.set_xlim(0, max(plot_df_fp["fp_percent"]) + 5)
    ax2.set_title("False Positives Among Predictions (Worst on Top)", fontsize=14)
    ax2.tick_params(axis="y", labelsize=8)
    ax2.grid(False)
    for bar, val, total in zip(bars2, plot_df_fp["fp_percent"], plot_df_fp["total_predictions"]):
        label = f"{val:.1f}%" if total else "N/A"
        ax2.text(val + 0.3, bar.get_y() + bar.get_height() / 2, label, va="center", fontsize=7)
    plt.tight_layout()
    fig.savefig(output_dir / "per_class_precision_bar.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved to {output_dir / 'per_class_precision_bar.png'}")


def save_mispredictions_plot(all_preds, all_labels, class_metrics, class_names, valid_sample_indices, val_ds, processor, model, device, output_dir):
    """Show misclassified images with their three highest-scoring predictions."""
    num_classes = len(class_names)
    misprediction_indices = np.where(all_preds != all_labels)[0]
    print(f"Total mispredictions: {len(misprediction_indices)} / {len(all_labels)} ({100 * len(misprediction_indices) / len(all_labels):.2f}%)")
    # Only classes present in the dataset have example images to display.
    supported_metrics = class_metrics.loc[class_metrics["support"] > 0]
    worst_classes_by_metric = {}
    for metric in ["precision", "recall", "f1-score", "accuracy"]:
        worst_classes_by_metric[metric] = supported_metrics[metric].idxmin()
        print(f"Lowest {metric}: {worst_classes_by_metric[metric]} ({supported_metrics[metric].min():.3f})")
    samples_per_metric = 4
    all_samples = {}
    for metric, cls_name in worst_classes_by_metric.items():
        cls_idx = class_names.index(cls_name)
        cls_mispreds = [i for i in misprediction_indices if all_labels[i] == cls_idx]
        if cls_mispreds:
            all_samples[metric] = random.sample(cls_mispreds, k=min(samples_per_metric, len(cls_mispreds)))
        else:
            all_samples[metric] = []

    fig, axes = plt.subplots(4, 4, figsize=(16, 20))
    for row_idx, metric in enumerate(["precision", "recall", "f1-score", "accuracy"]):
        cls_name = worst_classes_by_metric[metric]
        samples = all_samples[metric]
        metric_val = class_metrics.loc[cls_name, metric]
        for col_idx in range(4):
            ax = axes[row_idx, col_idx]
            if col_idx < len(samples):
                subset_idx = samples[col_idx]
                original_idx = valid_sample_indices[subset_idx]
                image = val_ds[original_idx]["image"].convert("RGB")
                inputs = processor(images=image, return_tensors="pt").to(device)
                with torch.no_grad():
                    logits = model(**inputs).logits
                probs = logits[0].softmax(-1).cpu()
                topk = torch.topk(probs, k=min(3, num_classes))
                true_class = class_names[all_labels[subset_idx]]
                ax.imshow(image)
                top3_str = "\n".join([
                    f"{class_names[topk.indices[j]]}: {topk.values[j]:.2f}"
                    for j in range(min(3, num_classes))
                ])
                caption = f"True: {true_class}\nPred: {top3_str}"
                ax.set_title(caption, color="red", fontsize=8)
            else:
                ax.text(0.5, 0.5, "No sample", ha="center", va="center", fontsize=12, color="gray")
            ax.axis("off")
            if col_idx == 0:
                ax.set_ylabel(f"Lowest {metric}\n{cls_name}\n({metric_val:.3f})", fontsize=10, rotation=0, ha="right", va="center", labelpad=60)
    plt.suptitle("Mispredictions by Lowest Metric Class (4 samples each)", fontsize=14, y=1.01)
    plt.tight_layout()
    fig.savefig(output_dir / "mispredictions_by_metric.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def process_model(model_path, test_data_path, output_path, batch_size, figsize, test_name, processor_path, num_workers):
    """Evaluate one checkpoint and save its reports."""
    model_path = Path(model_path)
    output_dir = Path(output_path) / test_name if test_name else Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Validation dir: {test_data_path}")
    print(f"Model path:     {model_path}")
    print(f"Outputs to:     {output_dir}")
    val_ds, dataset_class_names = load_test_data(test_data_path)
    save_sample_images(val_ds, dataset_class_names, output_dir)
    processor, model, device = load_model(model_path, processor_path)
    dataset_to_model_idx, valid_sample_indices, matching = match_classes(val_ds, dataset_class_names, model)
    eval_loader = make_eval_loader(val_ds, valid_sample_indices, processor, batch_size, num_workers)
    all_logits, all_preds, all_labels, topk_correct, total = evaluate_model(
        model, device, eval_loader, dataset_to_model_idx
    )
    # Include predictions for species absent from the evaluation dataset.
    class_names = [model.config.id2label[index] for index in range(model.config.num_labels)]
    report_df, roc_auc_per_class = save_metrics(
        all_logits, all_preds, all_labels, topk_correct, total, class_names, matching, output_dir
    )
    class_metrics, cm = save_per_class_report(
        report_df, roc_auc_per_class, all_labels, all_preds, class_names, output_dir, figsize
    )
    save_tp_fn_plot(cm, class_names, output_dir)
    save_precision_plot(cm, class_metrics, class_names, output_dir)
    save_mispredictions_plot(
        all_preds, all_labels, class_metrics, class_names, valid_sample_indices,
        val_ds, processor, model, device, output_dir,
    )
    with torch.no_grad():
        torch.cuda.empty_cache()


def is_valid_checkpoint_dir(dirname, chkstart, chkend):
    """Match checkpoint-N directories within the requested range."""
    match = re.fullmatch(r"checkpoint-(\d+)", dirname)
    return bool(match and chkstart <= int(match.group(1)) <= chkend)


def get_parser():
    parser = argparse.ArgumentParser(description="Evaluate classifier checkpoints with the June notebook reports.")
    parser.add_argument("--model_path", type=str, required=True, help="Checkpoint or parent directory.")
    parser.add_argument("--test_data_path", type=str, required=True, help="ImageFolder validation directory.")
    parser.add_argument("--output_path", type=str, default="output", help="Directory for the eight reports.")
    parser.add_argument("--batch_size", type=int, default=16, help="Inference batch size (notebook: 16).")
    parser.add_argument("--parent", choices=["true", "false"], default="false", help="Process checkpoint subdirectories.")
    parser.add_argument("--chkstart", type=int, default=0, help="First checkpoint number (inclusive).")
    parser.add_argument("--chkend", type=int, default=float("inf"), help="Last checkpoint number (inclusive).")
    parser.add_argument("--figsize", type=int, default=12, help="Base size of the confusion matrix (notebook: 12).")
    parser.add_argument("--test_name", type=str, default="", help="Optional report subdirectory name.")
    parser.add_argument("--processor_path", type=str, default=None, help="Optional processor directory.")
    parser.add_argument("--num_workers", type=int, default=0, help="DataLoader workers (notebook: 4; default 0 works with spawn).")
    return parser


def main():
    args = get_parser().parse_args()
    print(f"{datetime.now()}: Starting evaluation...")
    if args.chkstart < 0 or args.chkend < 0:
        raise ValueError("chkstart and chkend must be non-negative.")
    if args.chkstart > args.chkend:
        raise ValueError("chkstart must be no greater than chkend.")
    if args.batch_size <= 0 or args.figsize <= 0 or args.num_workers < 0:
        raise ValueError("batch_size and figsize must be positive; num_workers must be non-negative.")
    if args.parent == "true":
        checkpoints = [
            subdir for subdir in Path(args.model_path).iterdir()
            if subdir.is_dir() and is_valid_checkpoint_dir(subdir.name, args.chkstart, args.chkend)
        ]
        if not checkpoints:
            raise ValueError("No checkpoint directories matched the requested range.")
        for subdir in checkpoints:
            process_model(
                subdir, args.test_data_path, Path(args.output_path) / subdir.name,
                args.batch_size, args.figsize, args.test_name, args.processor_path, args.num_workers,
            )
    else:
        process_model(
            args.model_path, args.test_data_path, args.output_path,
            args.batch_size, args.figsize, args.test_name, args.processor_path, args.num_workers,
        )
    print(f"{datetime.now()}: Evaluation complete.")


if __name__ == "__main__":
    main()
