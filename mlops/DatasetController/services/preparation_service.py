"""Join reviewed COCO to explicit image membership without guessing paths."""

import re
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from ..models.dataset import ImageMembership, ReviewedCoco, Source, path_identity


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
