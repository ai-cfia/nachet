"""Register draft COCO and its source metadata in a new persistent FiftyOne dataset."""

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from uuid import uuid4

from progress_logging import log_progress

logger = logging.getLogger(__name__)


def register_fiftyone(name: str, labels: Path, server_media_root: str) -> None:
    """Import draft COCO into a new persistent dataset; refuse an existing name."""
    import fiftyone as fo

    if fo.dataset_exists(name):
        raise ValueError(
            f"FiftyOne dataset already exists; refusing to replace review work: {name}"
        )
    server_root = PurePosixPath(server_media_root)
    if not server_root.is_absolute():
        raise ValueError("server_media_root must be an absolute server-visible path")
    coco = json.loads(labels.read_text())
    info = coco.get("info") or {}
    boxes_field = datetime.now(UTC).strftime("boxes_%Y%m%d")
    image_count = len(coco["images"])
    records, paths = {}, {}
    for record in coco["images"]:
        key = PurePosixPath(record["file_name"])
        if key.is_absolute() or ".." in key.parts:
            raise ValueError(
                f"Expected an image key under the server media root: {key}"
            )
        records[record["id"]] = record
        paths[record["file_name"]] = str(server_root / key)

    # A killed import must not reserve the requested review-dataset name.
    dataset = fo.Dataset(name="preparation-import-" + uuid4().hex, persistent=False)
    try:
        logger.info("Importing %d COCO images into FiftyOne for %s", image_count, name)
        dataset.add_dir(
            dataset_type=fo.types.COCODetectionDataset,
            data_path=paths,
            labels_path=str(labels),
            label_field={"detections": boxes_field, "coco_id": "coco_id"},
            tags=["not-verified"],
            include_id=True,
            include_annotation_id=True,
        )
        if len(dataset) != image_count:
            raise ValueError("FiftyOne did not import every COCO image")
        dataset.tag_labels("not-verified")
        if coco.get("annotations"):
            prelabel_info = info.get("prelabel") or {}
            model_source = prelabel_info.get("model_source")
            model_path = (
                urlsplit(model_source).path
                if model_source
                else prelabel_info.get("model_path")
            )
            model_name = PurePosixPath(model_path or "").name
            model_revision = prelabel_info.get("model_revision")
            if model_name and model_revision:
                dataset.tag_labels(
                    f"{model_name}-{model_revision}", label_fields=boxes_field
                )
        dataset.add_sample_field("image_sha256", fo.StringField)
        # Declare nullable fields even when the first sample has no value.
        dataset.add_sample_field("source_species", fo.StringField)
        dataset.add_sample_field("split", fo.StringField)
        dataset.add_sample_field("prelabel_status", fo.StringField)
        dataset.add_sample_field("prelabel_reason", fo.StringField)
        dataset.add_sample_field("prelabel_prompt", fo.StringField)
        dataset.add_sample_field("prelabel_project_version", fo.StringField)
        dataset.add_sample_field("prelabel_code_revision", fo.StringField)
        for sample in log_progress(
            dataset.iter_samples(autosave=True),
            logger,
            stage="FiftyOne sample metadata",
            total=image_count,
        ):
            record = records[sample.coco_id]
            sources = record["sources"]
            sample["sources"] = sources
            sample["source_species"] = sources[0].get("species") if sources else None
            sample["split"] = record["split"]
            sample["object_key"] = record["file_name"]
            sample["image_sha256"] = record["image_sha256"]
            sample["prelabel_status"] = record.get("prelabel_status", "unannotated")
            sample["prelabel_reason"] = record.get("prelabel_reason")
            sample["prelabel_prompt"] = record.get("prelabel_prompt")
            sample["prelabel_project_version"] = record.get("prelabel_project_version")
            sample["prelabel_code_revision"] = record.get("prelabel_code_revision")
        dataset.info.update(info)
        dataset.save()
        dataset.persistent = True
        dataset.name = name
    except BaseException:
        # Only this invocation's new dataset is removed. Image objects stay untouched.
        dataset.delete()
        raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("labels", type=Path)
    parser.add_argument("--server-media-root", required=True)
    args = parser.parse_args(argv)
    if not os.environ.get("FIFTYONE_DATABASE_URI"):
        raise ValueError(
            "FIFTYONE_DATABASE_URI is required; refusing an implicit local database"
        )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    register_fiftyone(args.name, args.labels, args.server_media_root)
    print(f"Registered new persistent FiftyOne dataset: {args.name}")


if __name__ == "__main__":
    main()
