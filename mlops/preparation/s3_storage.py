"""S3 connection and content-addressed PNG uploads."""

import os
from urllib.parse import urlsplit

from mlops_blob import BlobStorageInterface, create_blob_storage_client
from mlops_blob.exceptions import BlobAlreadyExistsError


def create_storage(endpoint_url: str, region: str, *, allow_http: bool = False):
    """Use shared credentials; allow HTTP only when explicitly requested."""
    scheme = urlsplit(endpoint_url).scheme
    if scheme != "https" and not (scheme == "http" and allow_http):
        raise ValueError(
            "Use an HTTPS endpoint, or --allow-http for a trusted HTTP endpoint"
        )
    return create_blob_storage_client(
        "s3",
        {
            "s3_endpoint_url": endpoint_url,
            "s3_region_name": region,
            "s3_verify": os.environ.get("AWS_CA_BUNDLE") or True,
        },
    )


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
