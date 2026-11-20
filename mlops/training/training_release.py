"""Verify a pinned dataset release and stream its media into training batches."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

    from dataset_release.contract import Split
    from dataset_release.reader import ReleasedDataset
    from datasets import DatasetDict


TrainingKind = Literal["detector", "classifier"]
TRAINING_SPLITS = ("train", "validation")


@dataclass(frozen=True)
class ReleaseInput:
    name: str
    version: str
    manifest_sha256: str
    container: str

    @classmethod
    def from_args(cls, args: Namespace) -> ReleaseInput | None:
        identity = (
            args.dataset_name,
            args.dataset_version,
            args.expected_manifest_sha256,
        )
        if not any((*identity, args.dataset_container)):
            if args.preflight_only:
                raise ValueError("--preflight-only requires a dataset release")
            return None
        if not all(identity):
            raise ValueError(
                "Supply --dataset-name, --dataset-version and --expected-manifest-sha256 together"
            )
        return cls(
            *identity, args.dataset_container or os.environ.get("DATASET_CONTAINER", "")
        )

    def __post_init__(self) -> None:
        from dataset_release.contract import SHA256, ReleaseName
        from pydantic import TypeAdapter

        for value in (self.name, self.version):
            TypeAdapter(ReleaseName).validate_python(value)
        TypeAdapter(SHA256).validate_python(self.manifest_sha256)
        if not self.container.strip():
            raise ValueError(
                "Set --dataset-container or DATASET_CONTAINER for release input"
            )

    def trainer_args(self) -> list[str]:
        return ["--dataset_release", json.dumps(asdict(self))]


def add_release_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--dataset-name", default="", help="reviewed dataset release name"
    )
    parser.add_argument(
        "--dataset-version", default="", help="reviewed dataset release version"
    )
    parser.add_argument(
        "--expected-manifest-sha256", default="", help="required release manifest pin"
    )
    parser.add_argument(
        "--dataset-container",
        default="",
        help="S3 bucket; defaults to DATASET_CONTAINER",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="verify the release and its media on CPU, then exit",
    )


async def _open_release(release: ReleaseInput, verify_media: bool) -> ReleasedDataset:
    from dataset_release.reader import ReleasedDataset
    from dataset_release.registry import registry_engine
    from dataset_release.release import DatasetController
    from dataset_release.settings import Settings
    from dataset_release.storage import BlobStorageAdapter
    from sqlalchemy.ext.asyncio import async_sessionmaker

    if os.environ.get("DATASET_BLOB_PROVIDER", "s3").strip().lower() != "s3":
        raise ValueError("Training releases require the S3 storage provider")
    settings = Settings.from_environment()
    engine = registry_engine(settings.database_url, settings.registry_schema)
    try:
        storage = BlobStorageAdapter.from_environment()
        try:
            controller = DatasetController(
                storage, async_sessionmaker(engine), release.container
            )
            return await ReleasedDataset.open(
                controller,
                release.name,
                release.version,
                release.manifest_sha256,
                verify_media=verify_media,
            )
        except BaseException:
            storage.close()
            raise
    finally:
        await engine.dispose()


def _split_rows(reader: ReleasedDataset, kind: TrainingKind, split: Split):
    index = reader.detector_index if kind == "detector" else reader.classifier_index
    return index(split)


def check_training_release(
    release: ReleaseInput, kind: TrainingKind, *, verify_media: bool
) -> dict[str, str]:
    """Check train/validation availability and return the verified MLflow identity."""
    reader = asyncio.run(_open_release(release, verify_media))
    try:
        for split in TRAINING_SPLITS:
            rows = _split_rows(reader, kind, split)
            if next(rows, None) is None:
                raise ValueError(f"Release has no {kind} samples in the {split} split")
        if kind == "detector" and not any(
            row["objects"]["bbox"] for row in reader.detector_index("train")
        ):
            raise ValueError(
                "Release has no reviewed bounding boxes in the train split"
            )
        return reader.registration.training_reference()
    finally:
        reader.controller.storage.close()


def load_training_release(
    value: str, kind: TrainingKind
) -> tuple[DatasetDict, ReleasedDataset]:
    """Build in-memory split indexes; fetch PNGs only when a batch needs them."""
    from datasets import ClassLabel, Dataset, DatasetDict

    release = ReleaseInput(**json.loads(value))
    reader = asyncio.run(_open_release(release, verify_media=False))
    dataset = DatasetDict()
    for split in TRAINING_SPLITS:
        rows = list(_split_rows(reader, kind, split))
        dataset[split] = Dataset.from_list(rows)
        if kind == "classifier":
            dataset[split] = dataset[split].cast_column(
                "label", ClassLabel(names=list(reader.categories.values()))
            )
    return dataset, reader


def stream_media(reader: ReleasedDataset, transform):
    """Decode one batch of verified PNGs before applying the existing transform."""
    from PIL import Image

    async def decode(keys):
        images = []
        for key in keys:
            data = await reader.read_media(key)
            with Image.open(BytesIO(data)) as image:
                images.append(image.copy())
        return images

    def transform_batch(batch):
        batch["image"] = asyncio.run(decode(batch["image"]))
        return transform(batch)

    return transform_batch
