"""Collection paths and listing pages must survive the shared provider boundary."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from mlops_blob import create_blob_storage_client
from mlops_blob.exceptions import BlobStorageError
from mlops_blob.models import ListOptions
from mlops_blob.validation import validate_blob_name


@pytest.mark.asyncio
async def test_species_paths_with_spaces_round_trip(blob_provider):
    key = "raw/Collection/Amaranthus albus/batch-01/Tray_A/seed.tiff"
    await blob_provider.storage.upload_blob("datasets", key, b"seed")
    assert await blob_provider.storage.download_blob("datasets", key) == b"seed"
    assert blob_provider.objects["datasets", key] == b"seed"


@pytest.mark.parametrize(
    "key", [" leading", "trailing ", "A/../seed.png", "A\nB/seed.png", "A\\seed.png"]
)
def test_allowing_spaces_keeps_other_path_restrictions(key):
    with pytest.raises(BlobStorageError):
        validate_blob_name(key)


@pytest.mark.asyncio
@pytest.mark.parametrize("as_model", [False, True])
async def test_s3_listing_forwards_the_returned_token(as_model):
    client = Mock()
    now = datetime.now(UTC)
    first_key = "raw/Collection/A/first.tiff"
    second_key = "raw/Collection/A/second.tiff"
    client.list_objects_v2.side_effect = [
        {
            "Contents": [{"Key": first_key, "Size": 1, "LastModified": now}],
            "IsTruncated": True,
            "NextContinuationToken": "opaque-token",
        },
        {
            "Contents": [{"Key": second_key, "Size": 1, "LastModified": now}],
            "IsTruncated": False,
        },
    ]
    with patch("mlops_blob.s3.storage.create_s3_client", return_value=client):
        storage = create_blob_storage_client("s3", {})
    try:
        first = await storage.list_blobs(
            "datasets", options={"prefix": "raw/Collection/"}
        )
        options = {
            "prefix": "raw/Collection/",
            "max_results": 1000,
            "continuation_token": first["continuation_token"],
        }
        second = await storage.list_blobs(
            "datasets", options=ListOptions(**options) if as_model else options
        )
        assert [blob["name"] for blob in first["blobs"] + second["blobs"]] == [
            first_key,
            second_key,
        ]
        assert second["continuation_token"] is None
        assert (
            "ContinuationToken" not in client.list_objects_v2.call_args_list[0].kwargs
        )
        assert client.list_objects_v2.call_args_list[1].kwargs == {
            "Bucket": "datasets",
            "Prefix": "raw/Collection/",
            "MaxKeys": 1000,
            "ContinuationToken": "opaque-token",
        }
    finally:
        storage.close()
