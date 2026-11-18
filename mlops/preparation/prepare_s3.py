"""Read originals from S3, convert them and upload hash-named PNGs directly."""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path, PurePosixPath

from checkpoint_version import (
    compatible_checkpoint,
    compatible_directories,
    parse_version,
    project_version,
)
from prepare_images import (
    IMAGE_SUFFIXES,
    SPLIT_FOLDERS,
    SPLITS,
    ImageConversionError,
    add_image,
    coco_index,
    register_image,
    save_coco,
    skip_image,
)
from s3_storage import create_storage

logger = logging.getLogger(__name__)
CHECKPOINT_DIRECTORY = "preparation-checkpoints"


def checkpoint_metadata(
    checkpoint: sqlite3.Connection, name: str, value: object
) -> None:
    encoded = json.dumps(value, sort_keys=True)
    row = checkpoint.execute(
        "SELECT value FROM metadata WHERE name = ?", (name,)
    ).fetchone()
    if row is not None and row[0] != encoded:
        raise ValueError(
            f"Checkpoint settings differ ({name}); use a new checkpoint directory"
        )
    with checkpoint:
        checkpoint.execute(
            "INSERT OR IGNORE INTO metadata VALUES (?, ?)", (name, encoded)
        )


def checkpoint_settings(checkpoint: sqlite3.Connection, settings: dict) -> None:
    row = checkpoint.execute(
        "SELECT value FROM metadata WHERE name = 'settings'"
    ).fetchone()
    if row is not None:
        stored = json.loads(row[0])
        if not isinstance(stored, dict):
            raise ValueError("Invalid preparation checkpoint settings")
        previous = parse_version(stored.get("version"), context="checkpoint version")
        current = parse_version(settings.get("version"), context="project version")
        if not compatible_checkpoint(previous, current):
            raise ValueError(
                f"Incompatible preparation checkpoint version {previous} for {current}"
            )
        ignored = {"version", "code_revision"}
        if {k: v for k, v in stored.items() if k not in ignored} != {
            k: v for k, v in settings.items() if k not in ignored
        }:
            raise ValueError(
                "Checkpoint settings differ (settings); use a new checkpoint directory"
            )
        if stored.get("code_revision") != settings.get("code_revision"):
            logger.info(
                "Resuming with a different code revision; source provenance is retained"
            )
    with checkpoint:
        checkpoint.execute(
            "INSERT OR REPLACE INTO metadata VALUES ('settings', ?)",
            (json.dumps(settings, sort_keys=True),),
        )


def snapshot_checkpoint(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=".snapshot-", suffix=".sqlite3", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        with (
            closing(
                sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
            ) as source_db,
            closing(sqlite3.connect(temporary)) as target_db,
        ):
            source_db.backup(target_db)
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            raise RuntimeError(
                f"Checkpoint was created concurrently: {target}; use one writer"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def open_checkpoint(
    directory: Path | None, settings: dict
) -> Iterator[sqlite3.Connection | None]:
    if directory is None:
        yield None
        return
    directory.mkdir(parents=True, exist_ok=True)
    version = parse_version(settings.get("version"), context="project version")
    root = directory / CHECKPOINT_DIRECTORY
    target = root / str(version) / "preparation.sqlite3"
    if root.is_symlink() or target.parent.is_symlink() or target.is_symlink():
        raise ValueError(f"Checkpoint cannot be a symlink: {target}")
    if (directory / "preparation.sqlite3").exists():
        logger.warning(
            "Ignoring legacy integer-version checkpoint %s",
            directory / "preparation.sqlite3",
        )
    if not target.exists():
        for previous, candidate_dir in compatible_directories(root, version):
            candidate = candidate_dir / "preparation.sqlite3"
            if candidate.is_symlink():
                raise ValueError(f"Checkpoint cannot be a symlink: {candidate}")
            if candidate.exists() and not candidate.is_file():
                raise ValueError(f"Invalid preparation checkpoint: {candidate}")
            if candidate.is_file():
                snapshot_checkpoint(candidate, target)
                logger.info(
                    "Copied compatible preparation checkpoint %s into %s",
                    previous,
                    target,
                )
                break
    target.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(target)) as checkpoint:
        with checkpoint:
            checkpoint.execute(
                "CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            checkpoint.execute(
                "CREATE TABLE IF NOT EXISTS completed (path TEXT PRIMARY KEY, image TEXT NOT NULL)"
            )
        checkpoint_settings(checkpoint, settings)
        logger.info(
            "Using preparation checkpoint %s: completed_sources=%d",
            target,
            checkpoint.execute("SELECT COUNT(*) FROM completed").fetchone()[0],
        )
        yield checkpoint


def collection_prefix(value: str) -> str:
    prefix = PurePosixPath(value)
    if (
        prefix.is_absolute()
        or ".." in prefix.parts
        or "\\" in value
        or prefix.parts[:1] != ("raw",)
        or len(prefix.parts) < 2
    ):
        raise ValueError(
            "Choose a collection prefix below raw/, such as raw/collection-01"
        )
    return str(prefix) + "/"


def find_s3_images(
    keys: list[str], prefix: str, split: str | None
) -> tuple[list[tuple[Path, str, str | None]], list[str]]:
    """Apply the species/split folder layout to keys relative to one collection."""
    entries = []
    for key in sorted(keys):
        if not key.startswith(prefix):
            raise ValueError(f"Object is outside the collection prefix: {key}")
        relative = key[len(prefix) :]
        if not relative:
            continue
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in relative
            or str(path) != relative.rstrip("/")
        ):
            raise ValueError(f"Object has an invalid collection path: {key}")
        directories = path.parts if key.endswith("/") else path.parts[:-1]
        entries.append((path, directories, key.endswith("/")))

    if split is not None and any(
        directories and directories[0].casefold() in SPLIT_FOLDERS
        for _, directories, _ in entries
    ):
        raise ValueError("Cannot set a split for a collection with split folders")

    found, species_names = [], {}
    for path, directories, marker in entries:
        image_split = split
        if directories and directories[0].casefold() in SPLIT_FOLDERS:
            image_split = SPLIT_FOLDERS[directories[0].casefold()]
            directories = directories[1:]
        if path.parts[0].startswith(".") or (
            directories and directories[0].startswith(".")
        ):
            continue
        if not directories:
            if not marker and path.suffix.lower() in IMAGE_SUFFIXES:
                raise ValueError(f"Image must be inside a species folder: {path}")
            continue
        species = directories[0]
        if len(directories) > 1 and directories[1].casefold() in SPLIT_FOLDERS:
            raise ValueError(f"Pass the collection folder, not its parent: {path}")
        known = species_names.setdefault(species.casefold(), species)
        if known != species:
            raise ValueError(
                f"Species folders differ only in case: {known!r}, {species!r}"
            )
        if (
            not marker
            and path.suffix.lower() in IMAGE_SUFFIXES
            and not any(part.startswith(".") for part in path.parts)
        ):
            found.append((Path(path), species, image_split))
    return found, sorted(species_names.values())


async def prepare_s3(
    storage,
    bucket: str,
    raw_prefix: str,
    *,
    code_revision: str,
    split: str | None = None,
    allow_conflicting_duplicates: bool = False,
    skip_invalid_images: bool = False,
    checkpoint: sqlite3.Connection | None = None,
    checkpoint_version: str | None = None,
) -> dict:
    """Read, convert and upload one image at a time; return an index on success."""
    prefix = collection_prefix(raw_prefix)
    if split is not None and split not in SPLITS:
        raise ValueError(f"Invalid split: {split!r}")
    if checkpoint is not None:
        version = parse_version(checkpoint_version, context="checkpoint version")
        if not code_revision:
            raise ValueError("code_revision is required for checkpoint provenance")
    logger.info("Listing images in s3://%s/%s", bucket, prefix)
    keys = await storage.list_collection_keys(bucket, prefix)
    found, species_names = find_s3_images(keys, prefix, split)
    if not found:
        raise ValueError(f"No images found in species folders: s3://{bucket}/{prefix}")
    if checkpoint is not None:
        checkpoint_metadata(checkpoint, "collection", sorted(keys))
    logger.info(
        "Preparing s3://%s/%s: sources=%d duplicate_conflicts=%s invalid_images=%s",
        bucket,
        prefix,
        len(found),
        "warn" if allow_conflicting_duplicates else "error",
        "skip" if skip_invalid_images else "error",
    )
    if allow_conflicting_duplicates:
        logger.warning(
            "Temporary duplicate-conflict bypass enabled; retaining first source "
            "species and split in sorted relative-path order"
        )
        found.sort(key=lambda item: item[0].as_posix())
    images, skipped = {}, []
    for number, (relative, species, image_split) in enumerate(found, start=1):
        source_key = prefix + relative.as_posix()
        logger.debug(
            "Processing image %d/%d: s3://%s/%s",
            number,
            len(found),
            bucket,
            source_key,
        )
        if checkpoint is not None:
            completed = checkpoint.execute(
                "SELECT image FROM completed WHERE path = ?", (source_key,)
            ).fetchone()
            if completed is not None:
                record = json.loads(completed[0])
                provenance = record["sources"][0]["preparation"]
                producer_version = parse_version(
                    provenance["project_version"], context="source producer version"
                )
                if not compatible_checkpoint(producer_version, version):
                    raise ValueError(
                        f"Incompatible source producer version {producer_version} for {version}"
                    )
                if (
                    not isinstance(provenance.get("code_revision"), str)
                    or not provenance["code_revision"]
                ):
                    raise ValueError(f"Missing source producer revision: {source_key}")
                register_image(
                    images,
                    record,
                    allow_conflicting_duplicates=allow_conflicting_duplicates,
                )
                logger.debug("Resuming completed image: s3://%s/%s", bucket, source_key)
                continue
        data = await storage.read_image(bucket, source_key)
        try:
            image, png_bytes = add_image(
                images,
                data,
                relative,
                species=species,
                split=image_split,
                raw_prefix=PurePosixPath(prefix),
                allow_conflicting_duplicates=allow_conflicting_duplicates,
            )
        except ImageConversionError as error:
            if not skip_invalid_images:
                raise
            skip_image(skipped, relative, error, PurePosixPath(prefix))
            continue
        if len(image["sources"]) == 1:
            await storage.upload_png(bucket, image["file_name"], png_bytes)
        if checkpoint is not None:
            image["sources"][-1]["preparation"] = {
                "project_version": str(version),
                "code_revision": code_revision,
            }
            record = {
                **image,
                "split": image_split,
                "sources": [image["sources"][-1]],
            }
            with checkpoint:
                checkpoint.execute(
                    "INSERT INTO completed VALUES (?, ?)",
                    (source_key, json.dumps(record, allow_nan=False)),
                )
        logger.debug(
            "%s PNG s3://%s/%s for %s",
            "Uploaded" if len(image["sources"]) == 1 else "Reused",
            bucket,
            image["file_name"],
            source_key,
        )
    result = coco_index(images, species_names, code_revision, skipped)
    logger.info(
        "Image processing complete: sources=%d unique_pngs=%d duplicate_sources=%d skipped_sources=%d",
        len(found),
        len(images),
        len(found) - len(skipped) - len(images),
        len(skipped),
    )
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path, help="Directory for index.coco.json")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--raw-prefix", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--split", choices=sorted(SPLITS))
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow a trusted HTTP endpoint"
    )
    parser.add_argument(
        "--duplicate-conflicts",
        choices=["error", "warn"],
        default="error",
        help="Temporarily warn on conflicting duplicates, retaining first source species and split",
    )
    parser.add_argument(
        "--invalid-images",
        choices=["error", "skip"],
        default="error",
        help="Skip undecodable images with warnings and index records; storage errors still fail",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Persist and resume successful sources in output_root/preparation-checkpoints",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        help="Persist/resume checkpoints in this directory instead of output_root",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        collection_prefix(args.raw_prefix)
        storage = create_storage(
            args.endpoint_url, args.region, allow_http=args.allow_http
        )
    except ValueError as error:
        parser.error(str(error))
    try:
        checkpoint_dir = args.checkpoint_dir or (
            args.output_root if args.resume else None
        )
        version = project_version() if checkpoint_dir is not None else None
        settings = {
            "version": str(version) if version is not None else None,
            "endpoint_url": args.endpoint_url,
            "region": args.region,
            "bucket": args.bucket,
            "raw_prefix": collection_prefix(args.raw_prefix),
            "code_revision": args.code_revision,
            "split": args.split,
            "duplicate_conflicts": args.duplicate_conflicts,
        }
        with open_checkpoint(checkpoint_dir, settings) as checkpoint:
            result = asyncio.run(
                prepare_s3(
                    storage,
                    args.bucket,
                    args.raw_prefix,
                    code_revision=args.code_revision,
                    split=args.split,
                    allow_conflicting_duplicates=args.duplicate_conflicts == "warn",
                    skip_invalid_images=args.invalid_images == "skip",
                    checkpoint=checkpoint,
                    checkpoint_version=str(version) if version is not None else None,
                )
            )
            save_coco(args.output_root / "index.coco.json", result)
    finally:
        storage.close()
    print(
        f"Prepared {len(result['images'])} images from s3://{args.bucket}/{args.raw_prefix}"
    )


if __name__ == "__main__":
    main()
