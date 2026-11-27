"""Stage an S3 base model on the shared training workspace."""

import argparse
from contextlib import closing
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from blob.validation import CONTROL_CHARS, validate_container_name
from dataset_release.providers.s3 import create_s3_client
from dataset_release.storage import s3_configuration

MODEL_SOURCE_RECEIPT = ".nachet-model-source"


def stage_model(source: str, destination: Path) -> None:
    """Download one complete model snapshot, or reuse it on workflow retry."""
    uri = urlsplit(source)
    prefix = uri.path.strip("/") + "/"
    if (
        uri.scheme != "s3"
        or not uri.netloc
        or prefix == "/"
        or uri.query
        or uri.fragment
    ):
        raise ValueError("model-source must be an s3://bucket/prefix URI")
    bucket = validate_container_name(uri.netloc)
    identity = f"s3://{bucket}/{prefix}"
    receipt = destination / MODEL_SOURCE_RECEIPT
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading base model from {identity}", flush=True)
        with TemporaryDirectory(prefix=".model-", dir=destination.parent) as temp:
            snapshot = Path(temp) / "snapshot"
            download_snapshot(bucket, prefix, snapshot)
            (snapshot / MODEL_SOURCE_RECEIPT).write_text(identity, encoding="utf-8")
            try:
                snapshot.rename(destination)
            except OSError:
                if not receipt.is_file():
                    raise
    if not receipt.is_file() or receipt.read_text(encoding="utf-8") != identity:
        raise FileExistsError(
            f"Model directory has a different snapshot: {destination}"
        )


def download_snapshot(bucket: str, prefix: str, directory: Path) -> None:
    """Copy the files under a model prefix while preserving relative paths."""
    with closing(create_s3_client(s3_configuration())) as client:
        pages = client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=prefix
        )
        for page in pages:
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                name = key.removeprefix(prefix)
                parts = name.split("/")
                if (
                    not key.startswith(prefix)
                    or CONTROL_CHARS.intersection(name)
                    or "\\" in name
                    or parts[0] == MODEL_SOURCE_RECEIPT
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise ValueError(f"Invalid S3 model key: {key!r}")
                target = directory.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                response = client.get_object(Bucket=bucket, Key=key)
                with closing(response["Body"]) as body, target.open("wb") as output:
                    copyfileobj(body, output)
    if not directory.is_dir():
        raise FileNotFoundError(f"No model files found under s3://{bucket}/{prefix}")


def main() -> None:
    """Read the model source and staging path from workflow arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    stage_model(args.model_source, args.destination)


if __name__ == "__main__":
    main()
