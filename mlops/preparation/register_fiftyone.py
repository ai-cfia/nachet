"""Register draft COCO and its source metadata in a new persistent FiftyOne dataset."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4


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
        dataset.add_dir(
            dataset_type=fo.types.COCODetectionDataset,
            data_path=paths,
            labels_path=str(labels),
            label_field={"detections": "draft_boxes", "coco_id": "coco_id"},
            include_id=True,
            include_annotation_id=True,
        )
        if len(dataset) != len(coco["images"]):
            raise ValueError("FiftyOne did not import every COCO image")
        dataset.add_sample_field("image_sha256", fo.StringField)
        # Declare nullable fields even when the first sample has no value.
        dataset.add_sample_field("source_species", fo.StringField)
        dataset.add_sample_field("split", fo.StringField)
        dataset.add_sample_field("prelabel_reason", fo.StringField)
        dataset.add_sample_field("prelabel_prompt", fo.StringField)
        for sample in dataset.iter_samples(autosave=True):
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
        dataset.info.update(coco.get("info") or {})
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
    register_fiftyone(args.name, args.labels, args.server_media_root)
    print(f"Registered new persistent FiftyOne dataset: {args.name}")


if __name__ == "__main__":
    main()
