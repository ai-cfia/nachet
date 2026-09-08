#!/usr/bin/env python
# Copied without behavioral changes from ai-cfia/nachet-model-ccds at commit
# 601219b7. Original path: nachetmodel/coco_to_hf_dataset.py
"""Convert COCO format dataset to HuggingFace Datasets format."""

import json
from pathlib import Path
from collections import defaultdict

from datasets import Dataset, DatasetDict, Image


def load_coco_as_hf_dataset(
    images_dir: str,
    coco_json_path: str,
    train_val_split: float = 0.15,
    seed: int = 42,
    single_category: bool = False,
    single_category_name: str = "seed",
    reject_list_path: str | None = None,
    include_classes: set[str] | None = None,
) -> tuple[DatasetDict, dict]:
    """
    Convert COCO annotations to HuggingFace Dataset format.

    Args:
        images_dir: Directory containing the images
        coco_json_path: Path to COCO annotations JSON
        train_val_split: Fraction to use for validation
        seed: Random seed for splitting
        single_category: If True, collapse all categories into one
        single_category_name: Name to use for the single category label
        reject_list_path: Optional path to a text file containing filenames to exclude
        include_classes: Optional set of class names to include (case-insensitive).
            If provided, only annotations for these classes are kept.
            Images with no remaining annotations are dropped.

    Returns:
        Tuple of (DatasetDict with 'train' and 'validation' splits, categories dict)
    """
    images_dir = Path(images_dir)

    # Load reject list if provided
    reject_set = set()
    if reject_list_path:
        with open(reject_list_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    # Extract just the filename from the path
                    reject_set.add(Path(line).name)

    # Load COCO annotations
    with open(coco_json_path) as f:
        coco = json.load(f)

    # Build category mapping (COCO uses 1-indexed, HF expects 0-indexed)
    coco_categories = {cat["id"]: cat["name"] for cat in coco["categories"]}

    # Filter categories if include_classes is specified
    if include_classes:
        include_classes_lower = {c.lower() for c in include_classes}

        # Filter to only included categories
        filtered_coco_categories = {
            cat_id: cat_name
            for cat_id, cat_name in coco_categories.items()
            if cat_name.lower() in include_classes_lower
        }

        if not filtered_coco_categories:
            raise ValueError(
                f"No matching categories found. Requested: {include_classes}. "
                f"Available: {list(coco_categories.values())}"
            )

        excluded = set(coco_categories.values()) - set(filtered_coco_categories.values())
        if excluded:
            print(f"Info: Filtering to {len(filtered_coco_categories)} classes, excluded {len(excluded)}: {excluded}")

        coco_categories = filtered_coco_categories

        # Filter annotations to only valid category IDs
        valid_cat_ids = set(coco_categories.keys())
        coco["annotations"] = [
            ann for ann in coco["annotations"] if ann["category_id"] in valid_cat_ids
        ]

    if single_category:
        categories = {0: single_category_name}
        cat_id_to_idx = {cat_id: 0 for cat_id in coco_categories.keys()}
    else:
        # Map original COCO IDs to 0-indexed IDs
        cat_id_to_idx = {
            cat_id: idx for idx, cat_id in enumerate(sorted(coco_categories.keys()))
        }
        # Return 0-indexed mapping to match what's stored in the dataset
        categories = {idx: coco_categories[cat_id] for cat_id, idx in cat_id_to_idx.items()}

    # Group annotations by image_id
    annotations_by_image = defaultdict(list)
    for ann in coco["annotations"]:
        annotations_by_image[ann["image_id"]].append(ann)

    # Build dataset records
    records = []
    missing_images = []
    rejected_images = []
    empty_images = []
    for img_info in coco["images"]:
        image_id = img_info["id"]
        image_path = images_dir / img_info["file_name"]

        # Check if image is in reject list
        if image_path.name in reject_set:
            rejected_images.append(str(image_path))
            continue

        if not image_path.exists():
            missing_images.append(str(image_path))
            continue

        anns = annotations_by_image[image_id]

        # Skip images with no annotations (can happen after class filtering)
        if not anns:
            empty_images.append(str(image_path))
            continue

        # Build objects dict matching HF format
        objects = {
            "id": [],
            "area": [],
            "bbox": [],
            "category": [],
        }

        for ann in anns:
            bbox = ann["bbox"]  # [x, y, width, height]
            area = ann.get("area") or (bbox[2] * bbox[3])

            objects["id"].append(ann["id"])
            objects["area"].append(float(area))
            objects["bbox"].append(bbox)
            objects["category"].append(cat_id_to_idx[ann["category_id"]])

        records.append(
            {
                "image_id": image_id,
                "image": str(image_path),
                "width": img_info["width"],
                "height": img_info["height"],
                "objects": objects,
            }
        )

    if rejected_images:
        print(f"Info: {len(rejected_images)} images excluded via reject list")

    if empty_images:
        print(f"Info: {len(empty_images)} images dropped (no annotations after filtering)")

    if missing_images:
        print(f"Warning: {len(missing_images)} images not found")
        for path in missing_images[:5]:
            print(f"  - {path}")
        if len(missing_images) > 5:
            print(f"  ... and {len(missing_images) - 5} more")

    # Create dataset
    dataset = Dataset.from_list(records)

    # Cast image column to Image type
    dataset = dataset.cast_column("image", Image())

    # Split into train/validation
    # Handle edge case: train_val_split >= 1.0 means all data goes to validation
    if train_val_split >= 1.0:
        return (
            DatasetDict(
                {
                    "train": dataset.select([]),  # Empty train split
                    "validation": dataset,
                }
            ),
            categories,
        )
    elif train_val_split <= 0.0:
        return (
            DatasetDict(
                {
                    "train": dataset,
                    "validation": dataset.select([]),  # Empty validation split
                }
            ),
            categories,
        )

    split = dataset.train_test_split(test_size=train_val_split, seed=seed)

    return (
        DatasetDict(
            {
                "train": split["train"],
                "validation": split["test"],
            }
        ),
        categories,
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert COCO format dataset to HuggingFace Datasets format"
    )
    parser.add_argument(
        "--images_dir", required=True, help="Directory containing images"
    )
    parser.add_argument("--coco_json", required=True, help="Path to COCO JSON")
    parser.add_argument(
        "--output_dir", required=True, help="Output directory for HF dataset"
    )
    parser.add_argument(
        "--val_split", type=float, default=0.15, help="Validation split fraction"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    parser.add_argument(
        "--single_category",
        action="store_true",
        help="Collapse all categories into a single 'seed' class",
    )
    parser.add_argument(
        "--single_category_name",
        default="seed",
        help="Name to use when collapsing to a single category",
    )
    parser.add_argument(
        "--include_classes",
        default=None,
        help="Comma-separated list of class names to include (case-insensitive)",
    )
    args = parser.parse_args()

    # Parse include_classes into a set
    include_classes = None
    if args.include_classes:
        include_classes = {c.strip() for c in args.include_classes.split(",")}

    dataset, categories = load_coco_as_hf_dataset(
        args.images_dir,
        args.coco_json,
        args.val_split,
        args.seed,
        args.single_category,
        args.single_category_name,
        include_classes=include_classes,
    )

    print(f"Dataset created:")
    print(f"  Train: {len(dataset['train'])} images")
    print(f"  Validation: {len(dataset['validation'])} images")
    print(f"  Categories: {len(categories)}")

    # Save to disk
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(args.output_dir)

    # Also save categories mapping
    with open(output_path / "categories.json", "w") as f:
        json.dump(categories, f, indent=2)

    print(f"Saved to {args.output_dir}")


if __name__ == "__main__":
    main()
