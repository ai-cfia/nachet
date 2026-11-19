import asyncio
import copy
import hashlib
import json
import logging

import pytest
from blob.exceptions import BlobStorageError

import audit_s3


@pytest.fixture
def indexed_objects(s3_provider):
    png = b"prepared png bytes"
    raw = [b"first original", b"second original"]
    digest = hashlib.sha256(png).hexdigest()
    key = f"png/detection/{digest}.png"
    sources = [
        {
            "raw_key": f"raw/collection/species/{number}.png",
            "raw_sha256": hashlib.sha256(data).hexdigest(),
        }
        for number, data in enumerate(raw)
    ]
    s3_provider.objects["datasets", key] = png
    for source, data in zip(sources, raw, strict=True):
        s3_provider.objects["datasets", source["raw_key"]] = data
    return {"images": [{"file_name": key, "image_sha256": digest, "sources": sources}]}


def test_audit_checks_png_and_all_duplicate_sources(
    indexed_objects, s3_provider, caplog
):
    caplog.set_level(logging.INFO)
    report = asyncio.run(
        audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects)
    )
    assert report["status"] == "passed"
    assert report["issues"] == []
    assert report["checked_pngs"] == 1
    assert report["checked_sources"] == 2
    assert {
        call.kwargs["Key"] for call in s3_provider.client.get_object.call_args_list
    } == {
        indexed_objects["images"][0]["file_name"],
        *(source["raw_key"] for source in indexed_objects["images"][0]["sources"]),
    }
    assert "Checksum audit passed: pngs=1 sources=2" in caplog.text


@pytest.mark.parametrize("kind", ["png", "first_original", "second_original"])
def test_changed_object_fails_with_key(indexed_objects, s3_provider, kind):
    image = indexed_objects["images"][0]
    key = (
        image["file_name"]
        if kind == "png"
        else image["sources"][0 if kind == "first_original" else 1]["raw_key"]
    )
    s3_provider.objects["datasets", key] = b"changed"
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects))
    assert error.value.report["issues"][0]["code"] == "checksum_mismatch"
    assert error.value.report["issues"][0]["key"] == key


def test_missing_object_is_reported(indexed_objects, s3_provider):
    key = indexed_objects["images"][0]["sources"][1]["raw_key"]
    del s3_provider.objects["datasets", key]
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects))
    assert error.value.report["issues"][0]["code"] == "missing_object"
    assert error.value.report["issues"][0]["key"] == key


@pytest.mark.parametrize(
    "mutation",
    ["empty", "wrong_png_key", "missing_sources", "missing_raw_key", "invalid_hash"],
)
def test_malformed_index_is_reported(indexed_objects, s3_provider, mutation):
    index = copy.deepcopy(indexed_objects)
    image = index["images"][0]
    if mutation == "empty":
        index["images"] = []
    elif mutation == "wrong_png_key":
        image["file_name"] = "png/detection/incorrect.png"
    elif mutation == "missing_sources":
        image["sources"] = []
    elif mutation == "missing_raw_key":
        del image["sources"][0]["raw_key"]
    else:
        image["sources"][0]["raw_sha256"] = "bad"
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", index))
    assert error.value.report["status"] == "failed"
    assert error.value.report["issues"]
    if mutation != "empty":
        assert s3_provider.client.get_object.called


def test_non_object_index_is_reported(s3_provider):
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", []))
    assert error.value.report["issues"][0]["location"] == "$"
    assert "JSON object" in error.value.report["issues"][0]["message"]
    s3_provider.client.get_object.assert_not_called()


def test_collects_all_object_and_record_issues_and_checks_later_objects(
    indexed_objects, s3_provider, caplog
):
    image = indexed_objects["images"][0]
    png_key = image["file_name"]
    missing_key = image["sources"][0]["raw_key"]
    changed_key = image["sources"][1]["raw_key"]
    s3_provider.objects["datasets", png_key] = b"changed PNG"
    del s3_provider.objects["datasets", missing_key]
    s3_provider.objects["datasets", changed_key] = b"changed original"
    valid_raw = b"last valid original"
    valid_key = "raw/collection/species/later.png"
    s3_provider.objects["datasets", valid_key] = valid_raw
    image["sources"].extend(
        [
            {"raw_key": "raw/collection/species/invalid.png", "raw_sha256": "bad"},
            {"raw_key": valid_key, "raw_sha256": hashlib.sha256(valid_raw).hexdigest()},
        ]
    )
    later_png = b"later valid PNG"
    later_png_digest = hashlib.sha256(later_png).hexdigest()
    later_png_key = f"png/detection/{later_png_digest}.png"
    s3_provider.objects["datasets", later_png_key] = later_png
    indexed_objects["images"].append(
        {
            "file_name": later_png_key,
            "image_sha256": later_png_digest,
            "sources": [
                {
                    "raw_key": valid_key,
                    "raw_sha256": hashlib.sha256(valid_raw).hexdigest(),
                }
            ],
        }
    )

    caplog.set_level(logging.WARNING)
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects))
    report = error.value.report
    assert report["status"] == "failed"
    assert {(item["code"], item["key"]) for item in report["issues"]} == {
        ("invalid_raw_sha256", "raw/collection/species/invalid.png"),
        ("checksum_mismatch", png_key),
        ("missing_object", missing_key),
        ("checksum_mismatch", changed_key),
    }
    assert report["checked_pngs"] == 2
    assert report["checked_sources"] == 3
    assert valid_key in [
        call.kwargs["Key"] for call in s3_provider.client.get_object.call_args_list
    ]
    assert later_png_key in [
        call.kwargs["Key"] for call in s3_provider.client.get_object.call_args_list
    ]
    assert (
        sum("Checksum audit issue" in record.message for record in caplog.records) == 4
    )


def test_invalid_records_do_not_prevent_other_sources_from_being_checked(
    indexed_objects, s3_provider
):
    image = indexed_objects["images"][0]
    invalid = {
        "file_name": "wrong.png",
        "image_sha256": image["image_sha256"],
        "sources": [None, {"raw_key": 42, "raw_sha256": "bad"}, image["sources"][0]],
    }
    indexed_objects["images"].insert(0, invalid)
    indexed_objects["images"].insert(0, None)
    indexed_objects["images"].insert(
        0,
        {
            "file_name": "also-wrong.png",
            "image_sha256": "bad",
            "sources": [image["sources"][0]],
        },
    )
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects))
    report = error.value.report
    assert {issue["code"] for issue in report["issues"]} == {
        "invalid_image",
        "invalid_png_sha256",
        "invalid_png_key",
        "invalid_source",
        "invalid_raw_key",
        "invalid_raw_sha256",
    }
    assert sum(issue["code"] == "invalid_png_key" for issue in report["issues"]) == 2
    assert report["checked_pngs"] == 1
    assert report["checked_sources"] == 4


def test_storage_read_errors_are_reported_without_hiding_other_issues(
    indexed_objects, s3_provider, monkeypatch
):
    read = s3_provider.storage.read_image
    first, second = indexed_objects["images"][0]["sources"]
    s3_provider.objects["datasets", second["raw_key"]] = b"changed"

    async def failing_read(bucket, key):
        if key == first["raw_key"]:
            raise BlobStorageError("read failed")
        return await read(bucket, key)

    monkeypatch.setattr(s3_provider.storage, "read_image", failing_read)
    with pytest.raises(audit_s3.AuditFailure) as error:
        asyncio.run(audit_s3.audit_s3(s3_provider.storage, "datasets", indexed_objects))
    assert {
        (issue["code"], issue["key"]) for issue in error.value.report["issues"]
    } == {
        ("read_error", first["raw_key"]),
        ("checksum_mismatch", second["raw_key"]),
    }
    assert "read failed" in error.value.report["issues"][0]["message"]


def test_cli_closes_storage_on_checksum_failure(
    tmp_path, monkeypatch, indexed_objects, s3_provider
):
    index = tmp_path / "index.coco.json"
    index.write_text(json.dumps(indexed_objects))
    image = indexed_objects["images"][0]
    s3_provider.objects["datasets", image["file_name"]] = b"changed"
    monkeypatch.setattr(audit_s3, "create_storage", lambda *a, **k: s3_provider.storage)
    args = [
        str(index),
        "--bucket",
        "datasets",
        "--endpoint-url",
        "https://storage.example.test",
        "--region",
        "test",
    ]
    with pytest.raises(audit_s3.AuditFailure):
        audit_s3.main(args)
    report_path = tmp_path / "checksum-audit.json"
    report = json.loads(report_path.read_text())
    assert report["status"] == "failed"
    assert report["issues"][0]["key"] == image["file_name"]
    s3_provider.client.close.assert_called_once()

    # A subsequent successful audit replaces the previous failure report.
    s3_provider.objects["datasets", image["file_name"]] = b"prepared png bytes"
    audit_s3.main(args)
    report = json.loads(report_path.read_text())
    assert report["status"] == "passed"
    assert report["issues"] == []


def test_invalid_json_saves_failure_report_without_opening_storage(
    tmp_path, monkeypatch
):
    index = tmp_path / "index.coco.json"
    index.write_text("{invalid json")
    monkeypatch.setattr(
        audit_s3,
        "create_storage",
        lambda *args, **kwargs: pytest.fail("Storage should not be opened"),
    )
    with pytest.raises(audit_s3.AuditFailure):
        audit_s3.main(
            [
                str(index),
                "--bucket",
                "datasets",
                "--endpoint-url",
                "https://storage.example.test",
                "--region",
                "test",
            ]
        )
    report = json.loads((tmp_path / "checksum-audit.json").read_text())
    assert report["status"] == "failed"
    assert report["issues"][0]["code"] == "invalid_index"


def test_unexpected_setup_failure_does_not_leave_a_stale_success_report(
    tmp_path, monkeypatch, indexed_objects
):
    index = tmp_path / "index.coco.json"
    index.write_text(json.dumps(indexed_objects))
    report_path = tmp_path / "checksum-audit.json"
    report_path.write_text('{"status": "passed"}')

    def fail_setup(*args, **kwargs):
        raise ValueError("Invalid endpoint")

    monkeypatch.setattr(audit_s3, "create_storage", fail_setup)
    with pytest.raises(ValueError, match="Invalid endpoint"):
        audit_s3.main(
            [
                str(index),
                "--bucket",
                "datasets",
                "--endpoint-url",
                "invalid",
                "--region",
                "test",
            ]
        )
    report = json.loads(report_path.read_text())
    assert report["status"] == "incomplete"
    assert report["issues"] == []


def test_report_cannot_overwrite_input_index(tmp_path):
    index = tmp_path / "checksum-audit.json"
    index.write_text('{"images": []}')
    with pytest.raises(SystemExit):
        audit_s3.main(
            [
                str(index),
                "--bucket",
                "datasets",
                "--endpoint-url",
                "https://storage.example.test",
                "--region",
                "test",
            ]
        )
    assert index.read_text() == '{"images": []}'


def test_explicit_report_cannot_overwrite_input_index(tmp_path):
    index = tmp_path / "index.coco.json"
    index.write_text('{"images": []}')
    with pytest.raises(SystemExit):
        audit_s3.main(
            [
                str(index),
                "--report-path",
                str(index),
                "--bucket",
                "datasets",
                "--endpoint-url",
                "https://storage.example.test",
                "--region",
                "test",
            ]
        )
    assert index.read_text() == '{"images": []}'
