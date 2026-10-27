"""Convert an explicitly described intake into hash-named PNGs and a COCO index."""

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path

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
    intake: Path,
    output_root: Path,
    *,
    code_revision: str,
) -> dict:
    """Keep provenance before flattening; folder names are not a label API."""
    source_root = source_root.resolve(strict=True)
    with intake.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"path", "species"}.issubset(reader.fieldnames or []):
            raise ValueError("Intake CSV needs path and species columns")
        records = list(reader)
    if not records:
        raise ValueError("Intake CSV has no images")

    images = {}
    group_splits = {}
    for record in sorted(records, key=lambda item: item["path"]):
        relative = Path(record["path"])
        path = (source_root / relative).resolve(strict=True)
        if relative.is_absolute() or not path.is_relative_to(source_root):
            raise ValueError(f"Source escapes the input root: {relative}")
        species = record["species"].strip()
        if not species:
            raise ValueError(f"Missing species for {relative}")
        split = record.get("split", "").strip() or None
        if split not in {None, "train", "validation", "test"}:
            raise ValueError(f"Invalid split for {relative}: {split!r}")
        group = record.get("specimen_group", "").strip()
        if group and split:
            if group in group_splits and group_splits[group] != split:
                raise ValueError(f"Specimen group appears in different splits: {group}")
            group_splits[group] = split

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
                image.save(buffer, format="PNG", compress_level=6)
                png_bytes = buffer.getvalue()

        digest = hashlib.sha256(png_bytes).hexdigest()
        key = f"png/detection/{digest}.png"
        source = {
            field: value
            for field, value in record.items()
            if field != "split" and value not in (None, "")
        }
        source.update(
            original_path=record.get("original_path") or str(relative),
            path=str(relative),
            species=species,
            raw_sha256=raw_digest,
            legacy_md5=hashlib.md5(raw_bytes, usedforsecurity=False).hexdigest(),
        )
        if key in images:
            prior = images[key]
            if prior["split"] != split or prior["sources"][0]["species"] != species:
                raise ValueError(
                    f"Identical PNG has conflicting species or splits: {relative}"
                )
            prior["sources"].append(source)
        else:
            images[key] = {
                "file_name": key,
                "width": width,
                "height": height,
                "split": split,
                "sources": [source],
            }
        write_new(output_root / key, png_bytes)

    categories = [
        {"id": index, "name": name, "supercategory": "seed"}
        for index, name in enumerate(
            sorted({row["species"].strip() for row in records}), start=1
        )
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
    parser.add_argument("source_root", type=Path)
    parser.add_argument(
        "intake",
        type=Path,
        help="CSV with path, species and optional split/source fields",
    )
    parser.add_argument(
        "output_root", type=Path, help="Working directory for PNGs and COCO"
    )
    parser.add_argument("--code-revision", required=True)
    args = parser.parse_args(argv)
    result = prepare_images(
        args.source_root,
        args.intake,
        args.output_root,
        code_revision=args.code_revision,
    )
    save_coco(args.output_root / "index.coco.json", result)
    print(
        f"Prepared {len(result['images'])} images from {sum(len(i['sources']) for i in result['images'])} sources"
    )


if __name__ == "__main__":
    main()
