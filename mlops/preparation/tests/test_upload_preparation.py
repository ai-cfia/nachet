"""Upload contracts using the real shared provider with an in-memory SDK."""

import asyncio
import copy
import hashlib

import pytest
from botocore.exceptions import ClientError
from mlops_blob.exceptions import BlobStorageError

import upload_preparation as module
from prepare_images import save_coco


def test_upload_and_retry_preserve_all_coco_metadata(prepare, intake, s3_provider):
    coco = prepare()
    before = copy.deepcopy(coco)
    _, prepared = intake
    for _ in range(2):
        assert asyncio.run(
            module.upload_preparation(coco, prepared, s3_provider.storage, "datasets")
        ) == len(coco["images"])
    assert coco == before
    assert len(s3_provider.objects) == len(coco["images"])
    s3_provider.client.get_object.assert_not_called()
    for image in coco["images"]:
        data = s3_provider.objects["datasets", image["file_name"]]
        assert hashlib.sha256(data).hexdigest() == image["image_sha256"]
        assert data == (prepared / image["file_name"]).read_bytes()
        for source in image["sources"]:
            raw = (intake[0] / source["path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["raw_sha256"]
    for call in s3_provider.client.put_object.call_args_list:
        assert call.kwargs["IfNoneMatch"] == "*"
        assert call.kwargs["ContentType"] == "image/png"


def test_one_png_keeps_multiple_original_sources(prepare, intake, s3_provider):
    original = intake[0] / "Avena fatua/batch-01/tray-a/a.tiff"
    duplicate = original.with_name("same-seed.tiff")
    duplicate.write_bytes(original.read_bytes())
    coco = prepare()
    before = copy.deepcopy(coco)
    assert sum(len(image["sources"]) for image in coco["images"]) == 5
    asyncio.run(
        module.upload_preparation(coco, intake[1], s3_provider.storage, "datasets")
    )
    assert coco == before
    assert len(s3_provider.objects) == 4


@pytest.mark.parametrize("problem", ["bytes", "key", "symlink"])
def test_changed_or_escaping_png_fails_before_upload(
    prepare, intake, s3_provider, tmp_path, problem
):
    coco = prepare()
    image = coco["images"][0]
    path = intake[1] / image["file_name"]
    if problem == "bytes":
        path.write_bytes(b"changed")
        message = "PNG changed"
    elif problem == "key":
        image["file_name"] = "png/detection/wrong.png"
        message = "PNG key does not match"
    else:
        outside = tmp_path / "outside.png"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        message = "escapes the media root"
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            module.upload_preparation(coco, intake[1], s3_provider.storage, "datasets")
        )
    s3_provider.client.put_object.assert_not_called()


@pytest.mark.parametrize(
    "code", ["AccessDenied", "NotImplemented", "ConditionalRequestConflict"]
)
def test_service_errors_do_not_fall_back_to_overwrite(
    prepare, intake, s3_provider, code
):
    s3_provider.client.put_object.side_effect = ClientError(
        {"Error": {"Code": code}}, "PutObject"
    )
    with pytest.raises(BlobStorageError):
        asyncio.run(
            module.upload_preparation(
                prepare(), intake[1], s3_provider.storage, "datasets"
            )
        )
    s3_provider.client.put_object.assert_called_once()
    assert s3_provider.client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    s3_provider.client.get_object.assert_not_called()
    assert not s3_provider.objects


def test_retry_completes_a_partially_uploaded_collection(prepare, intake, s3_provider):
    coco = prepare()
    put = s3_provider.client.put_object.side_effect
    attempts = 0

    def interrupted_put(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        return put(**kwargs)

    s3_provider.client.put_object.side_effect = interrupted_put
    with pytest.raises(BlobStorageError):
        asyncio.run(
            module.upload_preparation(coco, intake[1], s3_provider.storage, "datasets")
        )
    assert len(s3_provider.objects) == 1
    asyncio.run(
        module.upload_preparation(coco, intake[1], s3_provider.storage, "datasets")
    )
    assert len(s3_provider.objects) == len(coco["images"])
    s3_provider.client.get_object.assert_not_called()


@pytest.mark.parametrize("changed", [False, True])
def test_cli_closes_the_client_on_success_and_failure(
    prepare, intake, s3_provider, monkeypatch, tmp_path, changed
):
    coco = prepare()
    labels = tmp_path / "draft.coco.json"
    save_coco(labels, coco)
    before = labels.read_bytes()
    if changed:
        (intake[1] / coco["images"][0]["file_name"]).write_bytes(b"changed")
    from unittest.mock import Mock

    factory = Mock(return_value=s3_provider.storage)
    monkeypatch.setattr(module, "create_blob_storage_client", factory)
    monkeypatch.setenv("AWS_CA_BUNDLE", "/test/ca.pem")
    args = [
        str(labels),
        str(intake[1]),
        "--bucket",
        "datasets",
        "--endpoint-url",
        "https://storage.example.test",
        "--region",
        "garage",
    ]
    if changed:
        with pytest.raises(ValueError, match="PNG changed"):
            module.main(args)
    else:
        module.main(args)
    s3_provider.client.close.assert_called_once()
    assert labels.read_bytes() == before
    factory.assert_called_once_with(
        "s3",
        {
            "s3_endpoint_url": "https://storage.example.test",
            "s3_region_name": "garage",
            "s3_verify": "/test/ca.pem",
        },
    )


@pytest.mark.parametrize(
    "endpoint", ["http://storage.example.test", "ftp://storage.example.test"]
)
def test_cli_refuses_unapproved_transport(tmp_path, endpoint):
    with pytest.raises(SystemExit) as error:
        module.main(
            [
                str(tmp_path / "unused.json"),
                str(tmp_path),
                "--bucket",
                "datasets",
                "--endpoint-url",
                endpoint,
                "--region",
                "garage",
            ]
        )
    assert error.value.code == 2


def test_cli_allows_explicit_http_for_testing(
    prepare, intake, s3_provider, monkeypatch
):
    from unittest.mock import Mock

    labels = intake[1] / "index.coco.json"
    save_coco(labels, prepare())
    factory = Mock(return_value=s3_provider.storage)
    monkeypatch.setattr(module, "create_blob_storage_client", factory)
    monkeypatch.delenv("AWS_CA_BUNDLE", raising=False)
    module.main(
        [
            str(labels),
            str(intake[1]),
            "--bucket",
            "datasets",
            "--endpoint-url",
            "http://127.0.0.1:12345",
            "--region",
            "garage",
            "--allow-http",
        ]
    )
    assert factory.call_args.args[1]["s3_verify"] is True
    s3_provider.client.close.assert_called_once()
