import asyncio
from contextlib import closing
from io import BytesIO
from unittest.mock import Mock
from urllib.parse import quote, urlsplit

import boto3
import pytest
from blob.exceptions import BlobNotFoundError, BlobStorageError
from botocore.awsrequest import AWSResponse
from botocore.stub import Stubber

from s3_storage import PreparationStorage, create_storage

BUCKET = "datasets"
PREFIX = "raw/collection/"
SPACED_KEY = PREFIX + "Amaranthus albus/Tray_A/seed.tiff"


@pytest.fixture
def s3_client():
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    with closing(client):
        yield client


def test_collection_listing_requests_the_next_page(s3_client):
    second_key = PREFIX + "Avena fatua/seed.tiff"
    with Stubber(s3_client) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": SPACED_KEY}],
                "IsTruncated": True,
                "NextContinuationToken": "page-2",
            },
            {"Bucket": BUCKET, "Prefix": PREFIX},
        )
        stubber.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": second_key}], "IsTruncated": False},
            {"Bucket": BUCKET, "Prefix": PREFIX, "ContinuationToken": "page-2"},
        )
        storage = PreparationStorage(s3_client)
        assert asyncio.run(storage.list_collection_keys(BUCKET, PREFIX)) == [
            SPACED_KEY,
            second_key,
        ]
        stubber.assert_no_pending_responses()


def test_repeated_continuation_token_fails_the_listing(s3_client):
    page = {"IsTruncated": True, "NextContinuationToken": "page-2"}
    with Stubber(s3_client) as stubber:
        stubber.add_response(
            "list_objects_v2", page, {"Bucket": BUCKET, "Prefix": PREFIX}
        )
        stubber.add_response(
            "list_objects_v2",
            page,
            {"Bucket": BUCKET, "Prefix": PREFIX, "ContinuationToken": "page-2"},
        )
        with pytest.raises(BlobStorageError, match="same next token"):
            asyncio.run(
                PreparationStorage(s3_client).list_collection_keys(BUCKET, PREFIX)
            )


@pytest.mark.parametrize(
    "key",
    [
        SPACED_KEY,
        PREFIX + "Amaranthus albus/seed;photo.tiff",
        PREFIX + "Amaranthus albus/seed (1), #2+50%&résumé.tiff",
        PREFIX + "Amaranthus albus/literal%20name.tiff",
    ],
)
def test_reads_the_exact_original_key_and_closes_the_stream(s3_client, key):
    body = BytesIO(b"original")
    with Stubber(s3_client) as stubber:
        stubber.add_response(
            "get_object", {"Body": body}, {"Bucket": BUCKET, "Key": key}
        )
        assert (
            asyncio.run(PreparationStorage(s3_client).read_image(BUCKET, key))
            == b"original"
        )
    assert body.closed


def test_sdk_encodes_the_original_key_once(s3_client):
    key = PREFIX + "Amaranthus albus/seed; (1)#50%+&résumé%2F.tiff"
    body = BytesIO(b"original")
    requested_urls = []

    def respond(request, **kwargs):
        requested_urls.append(request.url)
        return AWSResponse(request.url, 200, {"content-length": "8"}, body)

    # Stop at the HTTP boundary: exercise SDK serialization without contacting S3.
    s3_client.meta.events.register("before-send.s3.GetObject", respond)
    assert (
        asyncio.run(PreparationStorage(s3_client).read_image(BUCKET, key))
        == b"original"
    )
    assert len(requested_urls) == 1
    assert urlsplit(requested_urls[0]).path == "/" + quote(key, safe="/")
    assert body.closed


@pytest.mark.parametrize(
    "key",
    [
        PREFIX + "A/../seed.tiff",
        SPACED_KEY + " ",
        PREFIX + "A/seed\n.tiff",
        "/" + SPACED_KEY,
        PREFIX + "A\\seed.tiff",
        PREFIX + "A//seed.tiff",
        PREFIX + "é" * 512 + ".png",
    ],
)
def test_unsafe_image_keys_are_rejected_before_requesting_s3(key):
    client = Mock()
    with pytest.raises(BlobStorageError):
        asyncio.run(PreparationStorage(client).read_image(BUCKET, key))
    client.get_object.assert_not_called()


@pytest.mark.parametrize("code", ["NoSuchKey", "404"])
def test_missing_original_names_the_key(s3_client, code):
    with Stubber(s3_client) as stubber:
        stubber.add_client_error(
            "get_object", service_error_code=code, http_status_code=404
        )
        with pytest.raises(BlobNotFoundError, match="Amaranthus albus"):
            asyncio.run(PreparationStorage(s3_client).read_image(BUCKET, SPACED_KEY))


@pytest.mark.parametrize(
    "endpoint", ["http://storage.example.test", "ftp://storage.example.test"]
)
def test_storage_rejects_insecure_endpoints(monkeypatch, endpoint):
    factory = Mock()
    monkeypatch.setattr("s3_storage.boto3.client", factory)
    with pytest.raises(ValueError, match="HTTPS"):
        create_storage(endpoint, "garage")
    factory.assert_not_called()


@pytest.mark.parametrize("ca_bundle", [None, "/test/ca.pem"])
@pytest.mark.parametrize(
    "endpoint,allow_http",
    [("https://storage.example.test", False), ("http://storage.example.test", True)],
)
def test_storage_preserves_endpoint_and_ca_settings(
    monkeypatch, ca_bundle, endpoint, allow_http
):
    factory = Mock()
    monkeypatch.setattr("s3_storage.boto3.client", factory)
    if ca_bundle:
        monkeypatch.setenv("AWS_CA_BUNDLE", ca_bundle)
    else:
        monkeypatch.delenv("AWS_CA_BUNDLE", raising=False)
    storage = create_storage(endpoint, "garage", allow_http=allow_http)
    factory.assert_called_once()
    assert factory.call_args.args == ("s3",)
    assert factory.call_args.kwargs["endpoint_url"] == endpoint
    assert factory.call_args.kwargs["region_name"] == "garage"
    assert factory.call_args.kwargs["verify"] == (ca_bundle or True)
    assert "aws_access_key_id" not in factory.call_args.kwargs
    assert not factory.return_value.mock_calls
    storage.close()
    factory.return_value.close.assert_called_once()
