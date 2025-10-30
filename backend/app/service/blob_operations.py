"""Blob storage operations as DBOS steps.

IMPORTANT: DBOS decorators wrap async functions in a way that conflicts with
beartype's automatic type checking. Use @no_type_check to exclude these functions
from automatic beartype decoration applied by beartype_this_package().
"""

from beartype.typing import Dict, Any
from typing import no_type_check
from uuid import UUID
from datetime import datetime, timezone

from dbos import DBOS
from app.service.constants import Bucket, BlobAccount
from app.exceptions import (
    BlobUploadError,
    BlobDownloadError,
    DefenderScanTimeoutError,
    DefenderScanFailedError,
    DefenderScanNotScannedError,
)


# @no_type_check prevents beartype_this_package() from auto-decorating this function
# DBOS.step wraps the async function and returns a coroutine, which would fail beartype's
# type hint validation for the declared return type
@no_type_check
@DBOS.step(
    retries_allowed=True, max_attempts=10, interval_seconds=5.0, backoff_rate=2.0
)
async def upload_to_azure_blob(
    image_id: UUID,
    file_bytes: bytes,
    org_prefix: str,
    user_id: UUID,
    blob_account: BlobAccount = BlobAccount.ONPREM,
) -> str:
    """
    Upload image to Azure Blob Storage with retry logic.

    Naming structure: {org-prefix}/{uuidv7}.{ext}
    Example: cfia-org/01933e4f-8b2a-7890-abcd-ef1234567890.png
    """
    from app.api.config import get_settings
    from app.blob.manager import blob_storage_manager

    storage = blob_storage_manager.get_client(blob_account.value)
    settings = get_settings()
    bucket_prefix = settings.blob_container_prefix

    # Determine container based on environment
    container = bucket_prefix + Bucket.get_original_container(
        is_test=settings.is_test_environment
    )

    # Generate blob path: {org-name}/{uuidv7}.png
    blob_name = f"{org_prefix}/{image_id}.png"

    try:
        _result = await storage.upload_blob(
            container=container,
            name=blob_name,
            data=file_bytes,
            metadata={
                "user_id": str(user_id),
                "date_uploaded": datetime.now(timezone.utc).isoformat(),
            },
        )
        DBOS.logger.info(f"Blob uploaded: {_result['url']}")

        DBOS.logger.info(f"Uploaded to {container}/{blob_name}")
        return f"{blob_name}"

    except Exception as e:
        raise BlobUploadError(f"Failed to upload blob: {str(e)}") from e


def _process_defender_scan_result(
    scan_result: str, scan_timestamp: str, tags: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Process Defender scan result and return status or raise appropriate exception.

    This is a pure function for easy unit testing.

    Args:
        scan_result: The scan result from Defender tags
        scan_timestamp: The scan timestamp from Defender tags
        tags: Full tags dictionary

    Returns:
        Dict with status, tags, and scan_timestamp for success cases,
        or None to indicate should continue polling (transient/unknown errors)

    Raises:
        DefenderScanFailedError: Malware detected or permanent scan error
        DefenderScanNotScannedError: Blob couldn't be scanned
    """
    # Success states
    if scan_result == "No threats found":
        return {
            "status": "clean",
            "tags": tags,
            "scan_timestamp": scan_timestamp,
        }
    elif scan_result == "Malicious":
        raise DefenderScanFailedError(
            f"Malware detected in image. Scan time: {scan_timestamp}"
        )
    # Not scanned - blob couldn't be scanned (no charge)
    elif scan_result == "Not scanned":
        raise DefenderScanNotScannedError(
            "Blob could not be scanned due to unsupported type or encryption. "
            f"Scan time: {scan_timestamp}"
        )
    # Error states - check for SAM error codes
    elif scan_result.startswith("SAM"):
        # Parse error code
        error_code = scan_result.split(":")[0] if ":" in scan_result else scan_result

        # Transient errors that should retry (no charge)
        if error_code in [
            "SAM259201",
            "SAM259207",
            "SAM259213",
            "SAM259215",
            "SAM259221",
        ]:
            # Return None to indicate should continue polling
            return None
        # Permanent errors that should fail immediately
        else:
            raise DefenderScanFailedError(
                f"Defender scan failed with error: {scan_result}. Scan time: {scan_timestamp}"
            )
    # Unknown scan result - return None to continue polling
    else:
        return None


@no_type_check
@DBOS.step()
async def check_defender_scan_tags(
    storage,
    container: str,
    blob_name: str,
) -> Dict[str, Any]:
    """
    Step to check Defender scan tags on a blob.

    This is a step so it can be called from the wait_for_defender_scan workflow.
    """
    return await storage.get_blob_tags(container, blob_name)


@no_type_check
@DBOS.workflow()
async def wait_for_defender_scan(
    image_id: UUID,
    org_prefix: str,
    timeout_sec: int = 300,
) -> Dict[str, Any]:
    """
    Poll for Azure Defender scan completion using durable sleep.

    Handles all Azure Defender scan result states:
    - Success: "No threats found" - returns clean status
    - Malicious: "Malicious" - raises DefenderScanFailedError
    - Not scanned: "Not scanned" - raises DefenderScanNotScannedError
    - Transient errors (SAM259201, SAM259207, SAM259213, SAM259215, SAM259221) - retries
    - Permanent errors (other SAM codes) - raises DefenderScanFailedError

    Args:
        image_id: UUID of the image being scanned
        blob_url: Full Azure blob URL
        timeout_sec: Maximum time to wait for scan (default 300s)

    Returns:
        Dict with status, tags, and scan_timestamp

    Raises:
        DefenderScanFailedError: Malware detected or permanent scan error
        DefenderScanNotScannedError: Blob couldn't be scanned (unsupported type/encryption)
        DefenderScanTimeoutError: Scan didn't complete within timeout
    """
    from app.api.config import get_settings
    from app.blob.manager import blob_storage_manager

    storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
    settings = get_settings()
    bucket_prefix = settings.blob_container_prefix

    # Determine container based on environment
    container = bucket_prefix + Bucket.get_original_container(
        is_test=settings.is_test_environment
    )

    blob_name = f"{org_prefix}/{image_id}.png"

    max_attempts = timeout_sec // 5  # Poll every 5 seconds

    for attempt in range(max_attempts):
        try:
            tags = await check_defender_scan_tags(storage, container, blob_name)

            # Log all tags for debugging
            DBOS.logger.debug(
                f"[{image_id}] Defender scan tags retrieved (attempt {attempt}): {tags}"
            )

            # Check if scan has completed using Azure Defender standard tag
            # Note: Azure uses "Scanning" with capital S
            scan_result = tags.get("Malware Scanning scan result")

            if scan_result is not None:
                scan_timestamp = tags.get("Malware Scanning scan time UTC")

                DBOS.logger.debug(
                    f"[{image_id}] Defender scan result: {scan_result}, timestamp: {scan_timestamp}"
                )

                # Process the scan result using the helper function
                result = _process_defender_scan_result(
                    scan_result, scan_timestamp, tags
                )

                if result is not None:
                    # Success case - return the result
                    DBOS.logger.debug(
                        f"[{image_id}] Defender scan completed successfully: {result['status']}"
                    )
                    return result
                else:
                    # Transient error or unknown result - log and continue polling
                    if scan_result.startswith("SAM"):
                        DBOS.logger.warning(
                            f"[{image_id}] Transient Defender scan error (attempt {attempt}): {scan_result}"
                        )
                    else:
                        DBOS.logger.warning(
                            f"[{image_id}] Unexpected Defender scan result: {scan_result}"
                        )
            else:
                DBOS.logger.debug(
                    f"[{image_id}] Defender scan not yet complete (attempt {attempt}), tags: {tags}"
                )

        except (DefenderScanFailedError, DefenderScanNotScannedError):
            # Re-raise defender-specific errors immediately
            raise
        except Exception as e:
            DBOS.logger.error(
                f"[{image_id}] Defender scan check attempt {attempt} failed: {str(e)}",
                exc_info=True,
            )

        # Durable sleep - survives crashes! (now valid since this is a workflow)
        await DBOS.sleep_async(5)

    raise DefenderScanTimeoutError(f"Defender scan timed out after {timeout_sec}s")


@no_type_check
@DBOS.step(
    retries_allowed=True, max_attempts=10, interval_seconds=5.0, backoff_rate=2.0
)
async def download_sanitized_blob(
    image_id: UUID,
    org_prefix: str,
) -> bytes:
    """Download sanitized image from blob storage."""
    from app.api.config import get_settings
    from app.blob.manager import blob_storage_manager

    storage = blob_storage_manager.get_client(BlobAccount.ONPREM.value)
    settings = get_settings()
    bucket_prefix = settings.blob_container_prefix

    # Determine container based on environment
    container = bucket_prefix + Bucket.get_sanitized_container(
        is_test=settings.is_test_environment
    )

    blob_name = f"{org_prefix}/{image_id}.png"

    try:
        blob_bytes = await storage.download_blob(container, blob_name)
        return blob_bytes
    except Exception as e:
        raise BlobDownloadError(f"Failed to download sanitized blob: {str(e)}") from e
