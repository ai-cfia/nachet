"""The versioned release contract, independent of the backend and trainers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    model_validator,
)

Split = Literal["train", "validation", "test"]
Identifier = Annotated[StrictInt, Field(ge=0)]
PositiveInt = Annotated[StrictInt, Field(gt=0)]
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ReleaseName = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")]
Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False)]


def canonical_json(value: Any) -> bytes:
    """Hash JSON meaning rather than whitespace; reject NaN and Infinity."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(BaseModel):
    """Several source records can refer to the same image bytes."""

    model_config = ConfigDict(extra="allow", frozen=True)
    original_path: str = Field(min_length=1)
    collection_date: str | None = None
    species: str | None = None
    batch: str | None = None
    tray: str | None = None
    specimen_group: str | None = None


class CocoImage(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    id: Identifier
    file_name: str = Field(pattern=r"^png/detection/[a-f0-9]{64}\.png$")
    width: PositiveInt
    height: PositiveInt
    split: Split
    sources: list[Source] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_sha256(self) -> CocoImage:
        # Keep this optional extra absent on older releases so their serialized
        # specification and immutable request hash do not change on retries.
        if "sha256" in self.model_extra:
            digest = self.model_extra["sha256"]
            if (
                not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or self.file_name != f"png/detection/{digest}.png"
            ):
                raise ValueError("COCO image SHA-256 does not match its blob key")
        return self


class CocoCategory(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    id: Identifier
    name: str = Field(min_length=1)


class CocoAnnotation(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)
    id: Identifier
    image_id: Identifier
    category_id: Identifier
    bbox: list[Coordinate] = Field(min_length=4, max_length=4)
    area: Annotated[float, Field(ge=0, strict=True, allow_inf_nan=False)] | None = None
    iscrowd: Annotated[StrictInt, Field(ge=0, le=1)] = 0


class ReviewedCoco(BaseModel):
    """COCO with explicit splits and optional provenance on each image."""

    model_config = ConfigDict(extra="allow", frozen=True)
    images: list[CocoImage] = Field(min_length=1)
    categories: list[CocoCategory] = Field(min_length=1)
    annotations: list[CocoAnnotation]

    @model_validator(mode="after")
    def validate_references(self) -> ReviewedCoco:
        for name in ("images", "categories", "annotations"):
            items = getattr(self, name)
            if len({item.id for item in items}) != len(items):
                raise ValueError(f"Duplicate COCO IDs in {name}")
        category_names = [category.name for category in self.categories]
        if len(set(category_names)) != len(category_names):
            raise ValueError("Category names must be unique")
        images = {image.id: image for image in self.images}
        categories = {category.id for category in self.categories}
        groups: dict[tuple[str, str], str] = {}
        for image in self.images:
            identities = [("file", image.file_name)]
            identities.extend(
                ("specimen", source.specimen_group)
                for source in image.sources
                if source.specimen_group
            )
            for identity in identities:
                if identity in groups and groups[identity] != image.split:
                    raise ValueError(
                        f"Image/specimen appears in different splits: {identity}"
                    )
                groups[identity] = image.split
        for annotation in self.annotations:
            if (
                annotation.image_id not in images
                or annotation.category_id not in categories
            ):
                raise ValueError(f"Invalid reference in annotation {annotation.id}")
            image = images[annotation.image_id]
            x, y, width, height = annotation.bbox
            if (
                not all(math.isfinite(value) for value in annotation.bbox)
                or min(x, y) < 0
                or min(width, height) <= 0
                or x + width > image.width
                or y + height > image.height
            ):
                raise ValueError(f"Invalid bounding box in annotation {annotation.id}")
        # Extra COCO metadata must also be portable, finite JSON.
        canonical_json(self.model_dump(mode="json"))
        return self


class ConversionRecipe(ContractModel):
    code_revision: str = Field(min_length=1)
    settings: dict[str, Any]


class ReleaseSpec(ContractModel):
    schema_version: Literal[1] = 1
    name: ReleaseName
    version: ReleaseName
    author: str = Field(min_length=1)
    conversion: ConversionRecipe
    coco: ReviewedCoco
    generate_crops: StrictBool = False


class FileReference(ContractModel):
    key: str
    sha256: SHA256
    size: Annotated[StrictInt, Field(gt=0)]

    @model_validator(mode="after")
    def validate_key(self) -> FileReference:
        if not re.fullmatch(
            r"(?:png/(?:detection|classification)/[a-f0-9]{64}\.png|"
            r"releases/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/coco\.json)",
            self.key,
        ):
            raise ValueError("Invalid release object key")
        return self


class CropReference(ContractModel):
    image_id: Identifier
    annotation_id: Identifier
    category_id: Identifier
    split: Split
    pixel_box: tuple[int, int, int, int]
    file: FileReference


class ReleaseManifest(ContractModel):
    schema_version: Literal[1] = 1
    release_id: UUID
    name: ReleaseName
    version: ReleaseName
    author: str
    created_at: str
    request_sha256: SHA256
    hash_rule: Literal["sha256-file-bytes"] = "sha256-file-bytes"
    conversion: ConversionRecipe
    crop_recipe: dict[str, Any] | None
    coco: FileReference
    images: list[FileReference]
    crops: list[CropReference]
