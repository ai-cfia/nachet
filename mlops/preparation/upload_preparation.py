"""Upload indexed PNGs under their content hashes."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from mlops_blob import BlobStorageInterface, create_blob_storage_client
from mlops_blob.exceptions import BlobAlreadyExistsError


def create_storage(endpoint_url: str, region: str, *, allow_http: bool = False):
    """Use the shared credential chain and require TLS outside explicit tests."""
    scheme = urlsplit(endpoint_url).scheme
    if scheme != "https" and not (scheme == "http" and allow_http):
        raise ValueError(
            "Use an HTTPS endpoint, or --allow-http for a trusted test endpoint"
        )
    return create_blob_storage_client(
        "s3",
        {
            "s3_endpoint_url": endpoint_url,
            "s3_region_name": region,
            "s3_verify": os.environ.get("AWS_CA_BUNDLE") or True,
        },
    )


async def upload_preparation(
    coco: dict, media_root: Path, storage: BlobStorageInterface, bucket: str
) -> int:
    """Verify and upload each PNG; leave source records, labels and splits intact."""
    images = coco["images"]
    root = media_root.resolve(strict=True)
    for image in images:
        key = image["file_name"]
        digest = image["image_sha256"]
        if key != f"png/detection/{digest}.png":
            raise ValueError(f"PNG key does not match image_sha256: {key}")
        path = (root / key).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError(f"PNG escapes the media root: {key}")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"PNG changed since preparation: {key}")
        await upload_png(storage, bucket, key, data)
    return len(images)


async def upload_png(
    storage: BlobStorageInterface, bucket: str, key: str, data: bytes
) -> None:
    """Upload PNG bytes under their verified hash key; allow identical retries."""
    try:
        await storage.upload_blob(
            bucket, key, data, overwrite=False, content_type="image/png"
        )
    except BlobAlreadyExistsError:
        # Callers derive the key from these bytes; all writers must do the same.
        pass


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coco", type=Path)
    parser.add_argument("media_root", type=Path)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--allow-http", action="store_true", help="Allow a trusted HTTP test endpoint"
    )
    args = parser.parse_args(argv)
    try:
        storage = create_storage(
            args.endpoint_url, args.region, allow_http=args.allow_http
        )
    except ValueError as error:
        parser.error(str(error))
    try:
        coco = json.loads(args.coco.read_text())
        count = asyncio.run(
            upload_preparation(coco, args.media_root, storage, args.bucket)
        )
    finally:
        storage.close()
    print(f"Processed {count} prepared PNGs in s3://{args.bucket}/png/detection/")


if __name__ == "__main__":
    main()
