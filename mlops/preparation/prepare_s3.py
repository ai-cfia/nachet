"""Read originals from S3, convert them and upload hash-named PNGs directly."""

import argparse
import asyncio
from pathlib import Path, PurePosixPath

from prepare_images import (
    IMAGE_SUFFIXES,
    SPLIT_FOLDERS,
    SPLITS,
    add_image,
    coco_index,
    save_coco,
)
from s3_storage import create_storage


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
) -> dict:
    """Read, convert and upload one image at a time; return an index on success."""
    prefix = collection_prefix(raw_prefix)
    if split is not None and split not in SPLITS:
        raise ValueError(f"Invalid split: {split!r}")
    keys = await storage.list_collection_keys(bucket, prefix)
    found, species_names = find_s3_images(keys, prefix, split)
    if not found:
        raise ValueError(f"No images found in species folders: s3://{bucket}/{prefix}")
    images = {}
    for relative, species, image_split in found:
        data = await storage.read_image(bucket, prefix + relative.as_posix())
        image, png_bytes = add_image(
            images,
            data,
            relative,
            species=species,
            split=image_split,
            raw_prefix=PurePosixPath(prefix),
        )
        if len(image["sources"]) == 1:
            await storage.upload_png(bucket, image["file_name"], png_bytes)
    return coco_index(images, species_names, code_revision)


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
        "--allow-http", action="store_true", help="Allow a trusted HTTP test endpoint"
    )
    args = parser.parse_args(argv)
    try:
        collection_prefix(args.raw_prefix)
        storage = create_storage(
            args.endpoint_url, args.region, allow_http=args.allow_http
        )
    except ValueError as error:
        parser.error(str(error))
    try:
        result = asyncio.run(
            prepare_s3(
                storage,
                args.bucket,
                args.raw_prefix,
                code_revision=args.code_revision,
                split=args.split,
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
