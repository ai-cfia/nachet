"""Export reviewed COCO and prepare a release without copying image media."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pydantic import Field

from .contract import (
    SHA256,
    ContractModel,
    ReleaseSpec,
    ReviewedCoco,
    Source,
    Split,
)


class ImageMembership(ContractModel):
    """Join exported image paths to existing blobs and explicit split metadata."""

    file_name: str = Field(min_length=1)
    sha256: SHA256
    split: Split
    sources: list[Source] = Field(default_factory=list)


def path_identity(path: str) -> str:
    # Exported paths can come from a Windows FiftyOne host or a Linux pod.
    # Do not join on basename: different directories may contain the same name.
    return path.replace("\\", "/")


def remap_coco(
    coco: dict[str, Any], memberships: Iterable[ImageMembership]
) -> ReviewedCoco:
    """Preserve COCO IDs/labels, replacing paths and attaching release metadata."""
    by_path = {}
    for member in memberships:
        key = path_identity(member.file_name)
        if key in by_path:
            raise ValueError(f"Duplicate membership path: {member.file_name}")
        by_path[key] = member

    result = deepcopy(coco)
    used = set()
    for image in result["images"]:
        key = path_identity(image["file_name"])
        if key not in by_path:
            raise ValueError(f"Missing membership for COCO image: {image['file_name']}")
        if key in used:
            raise ValueError(f"Duplicate COCO image path: {image['file_name']}")
        used.add(key)
        member = by_path[key]
        if "sha256" in image and image["sha256"] != member.sha256:
            raise ValueError("COCO image SHA-256 differs from membership")
        if "split" in image and image["split"] != member.split:
            raise ValueError("COCO image split differs from membership")
        filename = key.rsplit("/", 1)[-1]
        match = re.fullmatch(r"([a-f0-9]{64})\.png", filename)
        if match and match[1] != member.sha256:
            raise ValueError("COCO image filename hash differs from membership")
        sources = [source.model_dump(mode="json") for source in member.sources]
        if image.get("sources"):
            existing_sources = [
                Source.model_validate(source) for source in image["sources"]
            ]
            if member.sources and existing_sources != member.sources:
                raise ValueError("COCO image sources differ from membership")
            sources = image["sources"]
        image.update(
            file_name=f"png/detection/{member.sha256}.png",
            sha256=member.sha256,
            split=member.split,
            sources=sources,
        )
    if used != by_path.keys():
        raise ValueError("Membership contains images missing from the COCO export")
    return ReviewedCoco.model_validate(result)


def sample_field(sample: Any, field: str) -> Any:
    try:
        return sample.get_field(field)
    except (AttributeError, KeyError):
        return None


def image_digest(filepath: str, stored_digest: Any) -> str:
    filename = path_identity(filepath).rsplit("/", 1)[-1]
    match = re.fullmatch(r"([a-f0-9]{64})\.png", filename)
    if stored_digest is not None:
        if match and match[1] != stored_digest:
            raise ValueError("FiftyOne SHA-256 differs from the image filename")
        return stored_digest
    if match:
        return match[1]
    # Generic local filenames need their exact bytes hashed, without re-encoding.
    with Path(filepath).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def export_collection(
    collection: Any,
    label_field: str,
    *,
    sha256_field: str = "sha256",
    split_field: str = "split",
    sources_field: str = "sources",
) -> ReviewedCoco:
    """Accept a FiftyOne dataset/view; leave its media and documents unchanged."""
    # FiftyOne belongs to the annotation environment, not the publisher's
    # dependency graph. Offline remapping and publishing never import it.
    import fiftyone as fo

    if collection.get_field(label_field, embedded_doc_type=fo.Detections) is None:
        raise ValueError("The reviewed label field must contain FiftyOne Detections")
    memberships = []
    annotation_count = 0
    for sample in collection.iter_samples():
        filepath = sample.filepath
        detections = sample_field(sample, label_field)
        if detections is None:
            raise ValueError(
                "Each sample needs reviewed detections; use empty Detections "
                "for a reviewed negative image"
            )
        annotation_count += len(detections.detections)
        sources = sample_field(sample, sources_field)
        if sources is None:
            sources = [
                {"original_path": filepath, "fiftyone_sample_id": str(sample.id)}
            ]
        memberships.append(
            ImageMembership(
                file_name=filepath,
                sha256=image_digest(filepath, sample_field(sample, sha256_field)),
                split=sample_field(sample, split_field),
                sources=sources,
            )
        )
    with TemporaryDirectory(prefix="nachet-coco-") as temporary:
        labels = Path(temporary) / "coco.json"
        collection.export(
            dataset_type=fo.types.COCODetectionDataset,
            label_field=label_field,
            labels_path=str(labels),
            export_media=False,
            abs_paths=True,
            extra_attrs=True,
        )
        coco = json.loads(labels.read_text(encoding="utf-8"))
    if len(coco.get("annotations", [])) != annotation_count:
        raise ValueError(
            "COCO export did not retain every reviewed detection; check the "
            "FiftyOne class definitions and pause edits during export"
        )
    return remap_coco(coco, memberships)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", help="FiftyOne dataset containing reviewed labels")
    source.add_argument("--coco", type=Path, help="Existing labels-only COCO JSON")
    parser.add_argument("--view", help="Saved reviewed FiftyOne view to export")
    parser.add_argument("--label-field", help="Field containing corrected detections")
    parser.add_argument("--sha256-field", default="sha256")
    parser.add_argument("--split-field", default="split")
    parser.add_argument("--sources-field", default="sources")
    parser.add_argument(
        "--membership", type=Path, help="Image metadata JSON for --coco"
    )
    parser.add_argument("--release-metadata", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="New output folder"
    )
    args = parser.parse_args(argv)
    if args.dataset and (not args.label_field or args.membership):
        parser.error("--dataset requires --label-field and cannot use --membership")
    if args.coco and (not args.membership or args.view or args.label_field):
        parser.error("--coco requires --membership and cannot use --view/--label-field")
    return args


def prepare(args: argparse.Namespace) -> ReleaseSpec:
    if args.output_dir.exists():
        raise ValueError("Output folder already exists; choose a new folder")
    metadata = json.loads(args.release_metadata.read_text(encoding="utf-8"))
    # Reject incompatible metadata before connecting to FiftyOne or exporting.
    if not isinstance(metadata, dict) or "coco" in metadata:
        raise ValueError("Release metadata must be an object without a coco field")
    if metadata.get("generate_crops", False) is not False:
        raise ValueError("Labels-only export requires generate_crops=false")
    if args.dataset:
        import fiftyone as fo

        collection = fo.load_dataset(args.dataset)
        if args.view:
            collection = collection.load_saved_view(args.view)
        coco = export_collection(
            collection,
            args.label_field,
            sha256_field=args.sha256_field,
            split_field=args.split_field,
            sources_field=args.sources_field,
        )
    else:
        members = json.loads(args.membership.read_text(encoding="utf-8"))
        coco = remap_coco(
            json.loads(args.coco.read_text(encoding="utf-8")),
            [ImageMembership.model_validate(member) for member in members],
        )
    spec = ReleaseSpec.model_validate(
        {**metadata, "coco": coco.model_dump(mode="json")}
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "coco.json").write_text(
        coco.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "dataset-release.json").write_text(
        spec.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return spec


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        spec = prepare(args)
    except ImportError as error:
        raise SystemExit(
            "COCO preparation failed: run --dataset in an environment with FiftyOne "
            "installed, or use --coco and --membership"
        ) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"COCO preparation failed: {error}") from None
    print(
        json.dumps(
            {
                "spec": str(args.output_dir / "dataset-release.json"),
                "images": len(spec.coco.images),
                "annotations": len(spec.coco.annotations),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
