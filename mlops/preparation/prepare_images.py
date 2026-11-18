"""Convert a species-folder collection into hash-named PNGs and a COCO image index."""

import argparse
import hashlib
import io
import json
import logging
import os
import tempfile
from pathlib import Path, PurePosixPath

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

SPLITS = {"train", "validation", "test"}
# Folder names, in any case, that assign a split instead of naming a species.
SPLIT_FOLDERS = {
    "train": "train",
    "training": "train",
    "val": "validation",
    "validation": "validation",
    "test": "test",
    "testing": "test",
}
IMAGE_SUFFIXES = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
TIFF_BITS_PER_SAMPLE = 258


def write_new(path: Path, data: bytes) -> None:
    """Identical reruns are allowed; different content needs a new output path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError(
                    f"Refusing to replace different content: {path}"
                ) from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_coco(path: Path, data: dict) -> None:
    write_new(path, (json.dumps(data, indent=2, allow_nan=False) + "\n").encode())


def find_images(
    collection: Path, split: str | None
) -> tuple[list[tuple[Path, str, str | None]], list[str]]:
    """Return (path, species, split) for each image and the sorted species names.

    Species folders sit directly under the collection or under a split folder.

    Example file structure from the Seed Lab:
        Nachet Images-RGB seed images/
            Amaranthus albus/
                AmAl-02_2026-03-27/
                    Tray_A/
                        AmAl-02-i47.tiff

    Pass the top folder as collection. Images stay unassigned unless a split
    is provided.
    """
    split_folders = [
        (SPLIT_FOLDERS[path.name.casefold()], path)
        for path in sorted(collection.iterdir())
        if path.is_dir() and path.name.casefold() in SPLIT_FOLDERS
    ]
    if split_folders and split is not None:
        raise ValueError("Cannot set a split for a collection with split folders")
    images = []
    species_names = {}
    for folder_split, parent in [*split_folders, (split, collection)]:
        if not parent.resolve().is_relative_to(collection):
            raise ValueError(f"Split folder escapes the collection: {parent}")
        for species_dir in sorted(parent.iterdir()):
            name = species_dir.name
            if name.startswith(".") or (
                parent == collection and name.casefold() in SPLIT_FOLDERS
            ):
                continue
            if species_dir.is_file() and species_dir.suffix.lower() in IMAGE_SUFFIXES:
                raise ValueError(
                    f"Image must be inside a species folder: {species_dir}"
                )
            if not species_dir.is_dir():
                continue
            # Checked before walking, so rglob never leaves the collection.
            if not species_dir.resolve().is_relative_to(collection):
                raise ValueError(
                    f"Species folder escapes the collection: {species_dir}"
                )
            if any(
                child.is_dir() and child.name.casefold() in SPLIT_FOLDERS
                for child in species_dir.iterdir()
            ):
                raise ValueError(
                    f"Pass the collection folder, not its parent: {species_dir}"
                )
            known = species_names.setdefault(name.casefold(), name)
            if known != name:
                raise ValueError(
                    f"Species folders differ only in case: {known!r}, {name!r}"
                )
            images.extend(
                (path, name, folder_split)
                for path in sorted(species_dir.rglob("*"))
                if path.is_file()
                and path.suffix.lower() in IMAGE_SUFFIXES
                and not any(
                    part.startswith(".") for part in path.relative_to(collection).parts
                )
            )
    return images, sorted(species_names.values())


def to_png(raw_bytes: bytes, relative: Path) -> tuple[bytes, int, int]:
    """Apply the conversion policy and return PNG bytes, width and height."""
    try:
        image = Image.open(io.BytesIO(raw_bytes))
    except OSError as error:
        raise OSError(f"{relative}: {error}") from error
    with image:
        if image.format not in {"PNG", "TIFF", "JPEG"}:
            raise ValueError(f"Expected PNG, TIFF or JPEG: {relative}")
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError(
                f"Multi-frame image needs an explicit frame choice: {relative}"
            )
        if image.format == "TIFF":
            if image.mode == "LA":
                raise ValueError(
                    f"{relative}: grayscale TIFF with alpha needs a lossless conversion policy"
                )
            bits = image.tag_v2.get(TIFF_BITS_PER_SAMPLE, (8,))
            bits = (bits,) if isinstance(bits, int) else bits
            if max(bits) > 16:
                raise ValueError(
                    f"{relative}: {bits}-bit TIFF needs a lossless conversion policy"
                )
        try:
            width, height = image.size
            if image.format == "PNG":
                image.load()
                return raw_bytes, width, height
            # Match the research converter, using the bytes already read for hashing.
            pixels = cv2.imdecode(
                np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_UNCHANGED
            )
            if pixels is None:
                raise OSError("cannot decode image")
            if pixels.dtype not in (np.uint8, np.uint16):
                raise ValueError(
                    f"{relative}: {pixels.dtype} image needs a lossless conversion policy"
                )
            ok, encoded = cv2.imencode(".png", pixels)
            if not ok:
                raise OSError("cannot encode PNG")
        except (OSError, cv2.error) as error:
            raise OSError(f"{relative}: {error}") from error
    return encoded.tobytes(), width, height


def add_image(
    images: dict,
    raw_bytes: bytes,
    relative: Path,
    *,
    species: str,
    split: str | None,
    raw_prefix: PurePosixPath | None,
    allow_conflicting_duplicates: bool = False,
) -> tuple[dict, bytes]:
    """Convert one image, retain its source record and return the PNG bytes."""
    png_bytes, width, height = to_png(raw_bytes, relative)
    image_sha256 = hashlib.sha256(png_bytes).hexdigest()
    key = f"png/detection/{image_sha256}.png"
    source = {
        "original_path": relative.as_posix(),
        "species": species,
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "legacy_md5": hashlib.md5(raw_bytes, usedforsecurity=False).hexdigest(),
    }
    if raw_prefix is not None:
        source["raw_key"] = str(raw_prefix / relative.as_posix())
    image = images.setdefault(
        key,
        {
            "file_name": key,
            "image_sha256": image_sha256,
            "width": width,
            "height": height,
            "split": split,
            "sources": [],
        },
    )
    if image["sources"] and (
        image["sources"][0]["species"] != species or image["split"] != split
    ):
        if not allow_conflicting_duplicates:
            raise ValueError(
                f"Identical PNG has conflicting species or splits: {relative}"
            )
        first_source = image["sources"][0]
        logger.warning(
            "Bypassing duplicate conflict: sha256=%s retained_path=%r "
            "retained_species=%r retained_split=%r incoming_path=%r "
            "incoming_species=%r incoming_split=%r; keeping first source species "
            "and split",
            image_sha256,
            first_source.get("raw_key", first_source["original_path"]),
            first_source["species"],
            image["split"],
            source.get("raw_key", source["original_path"]),
            species,
            split,
        )
    image["sources"].append(source)
    return image, png_bytes


def coco_index(images: dict, species_names: list[str], code_revision: str) -> dict:
    """Assign stable image/category IDs after the complete collection is known."""
    return {
        "info": {"preparation": {"code_revision": code_revision}},
        "images": [
            {"id": index, **images[key]}
            for index, key in enumerate(sorted(images), start=1)
        ],
        "categories": [
            {"id": index, "name": name, "supercategory": "seed"}
            for index, name in enumerate(species_names, start=1)
        ],
        "annotations": [],
    }


def prepare_images(
    collection: Path,
    output_root: Path,
    *,
    code_revision: str,
    split: str | None = None,
    raw_prefix: str | None = None,
    allow_conflicting_duplicates: bool = False,
) -> dict:
    """Write each image as png/detection/<sha256>.png and return the COCO index."""
    collection = collection.resolve(strict=True)
    if output_root.resolve().is_relative_to(collection):
        raise ValueError("Output directory must be outside the collection")
    if split is not None and split not in SPLITS:
        raise ValueError(f"Invalid split: {split!r}")
    prefix = PurePosixPath(raw_prefix) if raw_prefix is not None else None
    if prefix is not None and (
        prefix.is_absolute() or ".." in prefix.parts or prefix.parts[:1] != ("raw",)
    ):
        raise ValueError("raw_prefix must start with raw/")

    logger.info("Discovering images in %s", collection)
    found, species_names = find_images(collection, split)
    if not found:
        raise ValueError(f"No images found in species folders: {collection}")
    logger.info(
        "Preparing %s: sources=%d duplicate_conflicts=%s",
        collection,
        len(found),
        "warn" if allow_conflicting_duplicates else "error",
    )
    if allow_conflicting_duplicates:
        logger.warning(
            "Temporary duplicate-conflict bypass enabled; retaining first source "
            "species and split in sorted relative-path order"
        )
        found.sort(key=lambda item: item[0].relative_to(collection).as_posix())

    images = {}
    for number, (path, species, image_split) in enumerate(found, start=1):
        relative = path.relative_to(collection)
        logger.info("Processing image %d/%d: %s", number, len(found), relative)
        path = path.resolve(strict=True)
        if not path.is_relative_to(collection):
            raise ValueError(f"Image escapes the collection: {relative}")
        image, png_bytes = add_image(
            images,
            path.read_bytes(),
            relative,
            species=species,
            split=image_split,
            raw_prefix=prefix,
            allow_conflicting_duplicates=allow_conflicting_duplicates,
        )
        write_new(output_root / image["file_name"], png_bytes)
        logger.info(
            "%s PNG %s for %s",
            "Saved" if len(image["sources"]) == 1 else "Reused",
            image["file_name"],
            relative,
        )
    logger.info(
        "Image processing complete: sources=%d unique_pngs=%d duplicate_sources=%d",
        len(found),
        len(images),
        len(found) - len(images),
    )
    return coco_index(images, species_names, code_revision)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "collection",
        type=Path,
        help="Collection containing species folders and optional split folders",
    )
    parser.add_argument(
        "output_root", type=Path, help="Working directory for PNGs and COCO"
    )
    parser.add_argument("--code-revision", required=True)
    parser.add_argument(
        "--split",
        choices=sorted(SPLITS),
        help="Split for a collection without split folders",
    )
    parser.add_argument(
        "--raw-prefix", help="Matching S3 raw/ prefix to record in source metadata"
    )
    parser.add_argument(
        "--duplicate-conflicts",
        choices=["error", "warn"],
        default="error",
        help="Temporarily warn on conflicting duplicates, retaining first source species and split",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = prepare_images(
        args.collection,
        args.output_root,
        code_revision=args.code_revision,
        split=args.split,
        raw_prefix=args.raw_prefix,
        allow_conflicting_duplicates=args.duplicate_conflicts == "warn",
    )
    save_coco(args.output_root / "index.coco.json", result)
    sources = sum(len(image["sources"]) for image in result["images"])
    print(f"Prepared {len(result['images'])} images from {sources} sources")


if __name__ == "__main__":
    main()
