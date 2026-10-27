"""Convert species folders into hash-named PNGs and a COCO image index."""

import argparse
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from PIL import Image


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


def prepare_images(
    source_root: Path,
    output_root: Path,
    *,
    code_revision: str,
    split: str | None = None,
    raw_prefix: str | None = None,
    inputs: list[tuple[str, str]] | None = None,
) -> dict:
    """Use immediate subfolders as species and preserve paths before flattening."""
    source_root = source_root.resolve(strict=True)
    if output_root.resolve().is_relative_to(source_root):
        raise ValueError("Output directory must be outside the source root")
    if split not in {None, "train", "validation", "test"}:
        raise ValueError(f"Invalid split: {split!r}")
    if inputs and split is not None:
        raise ValueError("Use --input assignments or --split, not both")
    prefix = PurePosixPath(raw_prefix) if raw_prefix is not None else None
    if prefix is not None and (
        prefix.is_absolute() or ".." in prefix.parts or prefix.parts[:1] != ("raw",)
    ):
        raise ValueError("raw_prefix must start with raw/")

    extensions = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
    split_folders = {"training": "train", "validation": "validation"}
    if not inputs:
        discovered = [
            (split_folders[path.name.casefold()], path.name)
            for path in sorted(source_root.iterdir())
            if path.is_dir() and path.name.casefold() in split_folders
        ]
        if discovered and split is not None:
            raise ValueError("--split cannot override Training/Validation folders")
        inputs = discovered + [(split, ".")]
    records = []
    species_names = set()
    for assignment, directory in inputs:
        assignment = None if assignment == "unassigned" else assignment
        if assignment not in {None, "train", "validation", "test"}:
            raise ValueError(f"Invalid input split: {assignment!r}")
        input_root = source_root / directory
        if Path(directory).is_absolute() or not input_root.resolve().is_relative_to(
            source_root
        ):
            raise ValueError(f"Input directory escapes the source root: {directory}")
        for species_dir in sorted(input_root.iterdir()):
            if species_dir.name.startswith("."):
                continue
            if (
                input_root == source_root
                and species_dir.name.casefold() in split_folders
            ):
                continue
            if species_dir.is_file():
                if species_dir.suffix.lower() in extensions:
                    raise ValueError(
                        f"Image must be inside a species subfolder: {species_dir}"
                    )
                continue
            if not species_dir.is_dir():
                continue
            if not species_dir.resolve().is_relative_to(source_root):
                raise ValueError(
                    f"Species folder escapes the source root: {species_dir}"
                )
            species_names.add(species_dir.name)
            for path in sorted(species_dir.rglob("*")):
                relative = path.relative_to(source_root)
                if (
                    path.is_file()
                    and path.suffix.lower() in extensions
                    and not any(part.startswith(".") for part in relative.parts)
                ):
                    records.append(
                        {
                            "path": relative.as_posix(),
                            "species": species_dir.name,
                            "split": assignment,
                        }
                    )
    if not records:
        raise ValueError(f"No images found in species subfolders: {source_root}")

    images = {}
    for record in records:
        relative = Path(record["path"])
        path = (source_root / relative).resolve(strict=True)
        if not path.is_relative_to(source_root):
            raise ValueError(f"Source escapes the input root: {relative}")
        species = record["species"]

        raw_bytes = path.read_bytes()
        raw_digest = hashlib.sha256(raw_bytes).hexdigest()
        try:
            original = Image.open(io.BytesIO(raw_bytes))
        except OSError as error:
            raise OSError(f"{relative}: {error}") from error
        with original:
            if original.format not in {"PNG", "TIFF", "JPEG"}:
                raise ValueError(f"Expected PNG, TIFF or JPEG: {relative}")
            if getattr(original, "n_frames", 1) != 1:
                raise ValueError(
                    f"Multi-frame image needs an explicit frame choice: {relative}"
                )
            if original.format == "TIFF":
                bits = original.tag_v2.get(258, (8,))
                bits = (bits,) if isinstance(bits, int) else bits
                if max(bits) > 16 or (
                    max(bits) > 8 and original.mode not in {"I;16", "I;16B", "I;16L"}
                ):
                    raise ValueError(
                        f"{relative}: {bits}-bit TIFF needs a lossless conversion policy"
                    )
            try:
                original.load()
            except OSError as error:
                raise OSError(f"{relative}: {error}") from error
            width, height = original.size
            if original.format == "PNG":
                png_bytes = raw_bytes
            else:
                image = original.convert("RGB") if original.mode == "CMYK" else original
                buffer = io.BytesIO()
                try:
                    image.save(buffer, format="PNG", compress_level=6)
                except OSError as error:
                    raise OSError(f"{relative}: {error}") from error
                png_bytes = buffer.getvalue()

        digest = hashlib.sha256(png_bytes).hexdigest()
        key = f"png/detection/{digest}.png"
        source = {
            "path": record["path"],
            "species": species,
            "raw_sha256": raw_digest,
            "legacy_md5": hashlib.md5(raw_bytes, usedforsecurity=False).hexdigest(),
        }
        if prefix is not None:
            source["raw_key"] = str(prefix / relative.as_posix())
        if key in images:
            prior = images[key]
            if (
                prior["sources"][0]["species"] != species
                or prior["split"] != record["split"]
            ):
                raise ValueError(
                    f"Identical PNG has conflicting species or splits: {relative}"
                )
            prior["sources"].append(source)
        else:
            images[key] = {
                "file_name": key,
                "width": width,
                "height": height,
                "split": record["split"],
                "sources": [source],
            }
        write_new(output_root / key, png_bytes)

    categories = [
        {"id": index, "name": name, "supercategory": "seed"}
        for index, name in enumerate(sorted(species_names), start=1)
    ]
    return {
        "info": {
            "preparation": {
                "code_revision": code_revision,
            }
        },
        "images": [
            dict(id=index, **image)
            for index, image in enumerate(
                (images[key] for key in sorted(images)), start=1
            )
        ],
        "categories": categories,
        "annotations": [],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_root",
        type=Path,
        help="Collection with species folders and/or Training/Validation folders",
    )
    parser.add_argument(
        "output_root", type=Path, help="Working directory for PNGs and COCO"
    )
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"])
    parser.add_argument(
        "--input",
        action="append",
        nargs=2,
        metavar=("SPLIT", "DIRECTORY"),
        help="Override automatic discovery for an unusual layout; split is train, validation, test or unassigned",
    )
    parser.add_argument(
        "--raw-prefix", help="Matching S3 raw/ prefix to record in source metadata"
    )
    args = parser.parse_args(argv)
    result = prepare_images(
        args.source_root,
        args.output_root,
        code_revision=args.code_revision,
        split=args.split,
        raw_prefix=args.raw_prefix,
        inputs=args.input,
    )
    save_coco(args.output_root / "index.coco.json", result)
    print(
        f"Prepared {len(result['images'])} images from {sum(len(i['sources']) for i in result['images'])} sources"
    )


if __name__ == "__main__":
    main()
