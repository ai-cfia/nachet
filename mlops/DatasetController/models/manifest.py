"""Immutable manifest, file inventory and crop lineage models."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, StrictInt, model_validator

from .dataset import (
    SHA256,
    ContractModel,
    ConversionRecipe,
    Identifier,
    ReleaseName,
    Split,
)


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
