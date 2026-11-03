"""Export reviewed COCO and prepare a release without copying image media."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from collections.abc import Iterable, Sequence
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .contract import (
    ImageMembership,
    ReleaseSpec,
    ReviewedCoco,
    Source,
)


def path_identity(path: str) -> str:
    """Normalize path separators while retaining the complete exported image path."""
    # Normalize separators only; this cannot recover paths rewritten by an export.
    # Membership must use the actual COCO file_name, including any directories.
    return path.replace("\\", "/")


def remap_coco(
    coco: dict[str, Any], memberships: Iterable[ImageMembership]
) -> ReviewedCoco:
    """Join COCO images to memberships by complete paths and assign blob keys.

    Preserve IDs and labels in a copy of the input. Reject duplicate or unmatched
    paths and conflicting hashes, splits, or provenance before validating COCO.
    """
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
            raise ValueError(
                f"Missing membership for COCO image: {image['file_name']}. "
                "Membership file_name must match the exported COCO file_name. "
                "To match original FiftyOne filepaths, export labels only with "
                "Absolute paths enabled (abs_paths=True)."
            )
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
    """Read an optional FiftyOne field, returning None when it is unavailable."""
    try:
        return sample.get_field(field)
    except (AttributeError, KeyError):
        return None


def image_digest(filepath: str, stored_digest: Any) -> str:
    """Use the stored digest, a hash filename, or the exact local file bytes.

    Reject a stored digest that conflicts with a hash filename. Hash file bytes
    only when neither stored identity is available, without decoding the image.
    """
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
) -> tuple[ReviewedCoco, list[ImageMembership]]:
    """Export reviewed labels and memberships from a FiftyOne dataset or view.

    Use absolute paths and labels-only COCO, leaving media and documents unchanged.
    Every sample needs Detections, empty for reviewed negatives; reject exports
    that lose reviewed annotations.
    """
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
    return remap_coco(coco, memberships), memberships


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse dataset/view or offline COCO input for preparing an existing draft."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True, help="Dataset bucket/container")
    parser.add_argument("--name", required=True, help="Existing draft release name")
    parser.add_argument(
        "--version", required=True, help="Existing draft release version"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--dataset", help="FiftyOne dataset containing reviewed labels")
    source.add_argument("--coco", type=Path, help="Existing labels-only COCO JSON")
    parser.add_argument("--view", help="Saved reviewed FiftyOne view to export")
    parser.add_argument("--label-field", help="Field containing corrected detections")
    parser.add_argument("--sha256-field", default="sha256")
    parser.add_argument("--split-field", default="split")
    parser.add_argument("--sources-field", default="sources")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optionally generate JSON exports in a new folder",
    )
    args = parser.parse_args(argv)
    if args.dataset and not args.label_field:
        parser.error("--dataset requires --label-field")
    if args.coco and (args.view or args.label_field):
        parser.error(
            "--coco cannot use --view/--label-field; membership comes from the database"
        )
    return args


async def prepare(args: argparse.Namespace, controller) -> ReleaseSpec:
    """Save reviewed labels and membership to an existing release draft.

    Export a FiftyOne collection or remap offline COCO using database membership.
    Optionally write generated JSON documents to a new output directory.
    """
    if args.output_dir and args.output_dir.exists():
        raise ValueError("Output folder already exists; choose a new folder")
    # Fail before connecting to FiftyOne when the draft has not been registered.
    await controller.catalog.metadata(args.name, args.version)
    if args.dataset:
        import fiftyone as fo

        collection = fo.load_dataset(args.dataset)
        if args.view:
            collection = collection.load_saved_view(args.view)
        coco, members = await asyncio.to_thread(
            export_collection,
            collection,
            args.label_field,
            sha256_field=args.sha256_field,
            split_field=args.split_field,
            sources_field=args.sources_field,
        )
        await controller.catalog.prepare(args.name, args.version, coco, members)
    else:
        await controller.prepare_coco(
            args.name, args.version, json.loads(args.coco.read_text(encoding="utf-8"))
        )
    spec = await controller.catalog.spec(args.name, args.version)
    if args.output_dir:
        args.output_dir.mkdir(parents=True)
        for document, filename in (
            ("coco", "coco.json"),
            ("spec", "dataset-release.json"),
        ):
            (args.output_dir / filename).write_bytes(
                await controller.export_json(args.name, args.version, document)
            )
    return spec


async def execute(args):
    """Run draft preparation with a registry connection and dispose of its engine."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from .registry import registry_engine
    from .release import DatasetController
    from .settings import Settings

    settings = Settings.from_environment()
    engine = registry_engine(settings.database_url, settings.registry_schema)
    try:
        controller = DatasetController(None, async_sessionmaker(engine), args.container)
        return await prepare(args, controller)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Load environment settings, prepare the draft, and print its summary as JSON."""
    args = parse_args(argv)
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("DATASET_ENV_FILE", ".env"))
    try:
        spec = asyncio.run(execute(args))
    except ImportError as error:
        raise SystemExit(
            "COCO preparation failed: run --dataset in an environment with FiftyOne "
            "installed, or use --coco with database membership"
        ) from error
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"COCO preparation failed: {error}") from None
    except Exception as error:
        raise SystemExit(f"COCO preparation failed: {type(error).__name__}") from None
    print(
        json.dumps(
            {
                "name": spec.name,
                "version": spec.version,
                "status": "draft",
                "images": len(spec.coco.images),
                "annotations": len(spec.coco.annotations),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
