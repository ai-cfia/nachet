"""Verify prepared PNGs and their indexed original S3 objects."""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Literal, TypedDict

from blob.exceptions import BlobNotFoundError, BlobStorageError

from s3_storage import create_storage

logger = logging.getLogger(__name__)
SHA256 = re.compile(r"[0-9a-f]{64}")
PNG_KEY = re.compile(r"png/detection/[0-9a-f]{64}\.png")


class AuditIssue(TypedDict):
    code: str
    location: str
    key: str | None
    message: str


class AuditReport(TypedDict):
    status: Literal["incomplete", "failed", "passed"]
    bucket: str
    checked_pngs: int
    checked_sources: int
    issues: list[AuditIssue]


class AuditFailure(ValueError):
    def __init__(self, report: AuditReport):
        self.report = report
        super().__init__(f"Checksum audit found {len(report['issues'])} issue(s)")


def new_report(bucket: str) -> AuditReport:
    return {
        "status": "incomplete",
        "bucket": bucket,
        "checked_pngs": 0,
        "checked_sources": 0,
        "issues": [],
    }


def add_issue(
    report: AuditReport, code: str, location: str, message: str, key: str | None = None
) -> None:
    report["issues"].append(
        {"code": code, "location": location, "key": key, "message": message}
    )
    logger.warning("Checksum audit issue at %s: %s", location, message)


def write_report(path: Path, report: AuditReport) -> None:
    """Atomically replace the report so each attempt reflects its latest result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def audit_s3(storage, bucket: str, index: object) -> AuditReport:
    """Check all valid records and raise with a report if any issue is found."""
    report = new_report(bucket)
    if not isinstance(index, dict):
        add_issue(report, "invalid_index", "$", "Audit index must be a JSON object")
        images = []
    elif not isinstance(index.get("images"), list) or not index["images"]:
        add_issue(
            report,
            "invalid_index",
            "images",
            "Audit index must contain at least one image",
        )
        images = []
    else:
        images = index["images"]
    checks: list[tuple[Literal["png", "source"], str, str, str]] = []
    for image_number, image in enumerate(images):
        image_location = f"images[{image_number}]"
        if not isinstance(image, dict):
            add_issue(report, "invalid_image", image_location, "Invalid image record")
            continue
        key, digest = image.get("file_name"), image.get("image_sha256")
        image_key = key if isinstance(key, str) else None
        valid_png_digest = isinstance(digest, str) and bool(SHA256.fullmatch(digest))
        valid_png_key = isinstance(key, str) and bool(PNG_KEY.fullmatch(key))
        if not valid_png_digest:
            add_issue(
                report,
                "invalid_png_sha256",
                f"{image_location}.image_sha256",
                f"Invalid PNG SHA-256 for {key!r}",
                image_key,
            )
        if not valid_png_key:
            add_issue(
                report,
                "invalid_png_key",
                f"{image_location}.file_name",
                f"Invalid PNG key: {key!r}",
                image_key,
            )
        elif valid_png_digest and key != f"png/detection/{digest}.png":
            add_issue(
                report,
                "invalid_png_key",
                f"{image_location}.file_name",
                f"PNG key does not match image_sha256: {key!r}",
                image_key,
            )
        elif valid_png_digest and isinstance(key, str) and isinstance(digest, str):
            checks.append(("png", image_location, key, digest))
        sources = image.get("sources")
        if not isinstance(sources, list) or not sources:
            add_issue(
                report,
                "invalid_sources",
                f"{image_location}.sources",
                f"PNG has no source records: {key!r}",
                image_key,
            )
            continue
        for source_number, source in enumerate(sources):
            source_location = f"{image_location}.sources[{source_number}]"
            if not isinstance(source, dict):
                add_issue(
                    report,
                    "invalid_source",
                    source_location,
                    f"Invalid source record for {key!r}",
                    image_key,
                )
                continue
            raw_key, raw_digest = source.get("raw_key"), source.get("raw_sha256")
            valid_key = isinstance(raw_key, str) and raw_key.startswith("raw/")
            valid_digest = isinstance(raw_digest, str) and bool(
                SHA256.fullmatch(raw_digest)
            )
            if not valid_key:
                add_issue(
                    report,
                    "invalid_raw_key",
                    f"{source_location}.raw_key",
                    f"Invalid raw_key for {key!r}: {raw_key!r}",
                    raw_key if isinstance(raw_key, str) else None,
                )
            if not valid_digest:
                add_issue(
                    report,
                    "invalid_raw_sha256",
                    f"{source_location}.raw_sha256",
                    f"Invalid raw SHA-256 for {raw_key!r}",
                    raw_key if isinstance(raw_key, str) else None,
                )
            if (
                valid_key
                and valid_digest
                and isinstance(raw_key, str)
                and isinstance(raw_digest, str)
            ):
                checks.append(("source", source_location, raw_key, raw_digest))
    for kind, location, key, expected in checks:
        try:
            data = await storage.read_image(bucket, key)
        except BlobStorageError as error:
            add_issue(
                report,
                "missing_object"
                if isinstance(error, BlobNotFoundError)
                else "read_error",
                location,
                f"Cannot read s3://{bucket}/{key}: {error}",
                key,
            )
            continue
        actual = hashlib.sha256(data).hexdigest()
        if kind == "png":
            report["checked_pngs"] += 1
        else:
            report["checked_sources"] += 1
        if actual != expected:
            add_issue(
                report,
                "checksum_mismatch",
                location,
                f"SHA-256 mismatch for s3://{bucket}/{key}: expected {expected}, got {actual}",
                key,
            )
        else:
            logger.debug("Verified s3://%s/%s", bucket, key)
    if report["issues"]:
        report["status"] = "failed"
        raise AuditFailure(report)
    report["status"] = "passed"
    logger.info(
        "Checksum audit passed: pngs=%d sources=%d",
        report["checked_pngs"],
        report["checked_sources"],
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path, help="Prepared index.coco.json")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Audit report location (defaults to checksum-audit.json beside the index)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    report_path = args.report_path or args.index.with_name("checksum-audit.json")
    if report_path.resolve() == args.index.resolve():
        parser.error("Index and checksum audit report must be different files")
    report = new_report(args.bucket)
    write_report(report_path, report)
    logger.info("Checksum audit report: %s", report_path)
    storage = None
    try:
        try:
            index = json.loads(args.index.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            add_issue(report, "invalid_index", "$", f"Cannot read audit index: {error}")
            report["status"] = "failed"
            raise AuditFailure(report) from error
        storage = create_storage(
            args.endpoint_url, args.region, allow_http=args.allow_http
        )
        report = asyncio.run(audit_s3(storage, args.bucket, index))
    except AuditFailure as error:
        write_report(report_path, error.report)
        logger.error(
            "Checksum audit found %d issue(s); report: %s",
            len(error.report["issues"]),
            report_path,
        )
        raise
    else:
        write_report(report_path, report)
    finally:
        if storage is not None:
            storage.close()


if __name__ == "__main__":
    main()
