"""Blob storage operations as DBOS steps."""

from typing import Dict, Any
from uuid import UUID

from dbos import DBOS
from app.blob.manager import get_blob_storage
from app.service.constants import Bucket
from app.exceptions import BlobUploadError, BlobDownloadError, DefenderScanTimeoutError, DefenderScanFailedError


@DBOS.step(retries_allowed=True, max_attempts=5, interval_seconds=1.0, backoff_rate=2.0)
async def upload_to_azure_blob(
    image_id: UUID,
    file_bytes: bytes,
    filename: str,
    genus: str,
    species: str,
    org_name: str,
) -> str:
    """
    Upload image to Azure Blob Storage with retry logic.

    Naming structure: {org-name}/{genus}-{species}/{uuidv7}.{ext}
    Example: cfia-org/avena-fatua/01933e4f-8b2a-7890-abcd-ef1234567890.png
    """
    from app.api.config import get_settings

    storage = await get_blob_storage()
    settings = get_settings()

    # Determine container based on environment
    container = Bucket.get_original_container(is_test=settings.is_test_environment)

    # Extract file extension
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'

    # Generate blob path: {org-name}/{genus}-{species}/{uuidv7}.{ext}
    blob_name = f"{org_name}/{genus}-{species}/{image_id}.{file_ext}"

    try:
        result = await storage.upload_blob(
            container=container,
            name=blob_name,
            data=file_bytes,
            metadata={
                "original_filename": filename,
                "genus": genus,
                "species": species,
                "org_name": org_name,
                "image_id": str(image_id),
            },
        )

        DBOS.logger.info(f"Uploaded to {container}/{blob_name}")
        return result["url"]

    except Exception as e:
        raise BlobUploadError(f"Failed to upload blob: {str(e)}") from e


@DBOS.step(retries_allowed=True, max_attempts=60)
async def wait_for_defender_scan(
    image_id: UUID,
    blob_url: str,
    timeout_sec: int = 300,
) -> Dict[str, Any]:
    """Poll for Azure Defender scan completion using durable sleep."""
    storage = await get_blob_storage()

    # Extract container and blob name from URL
    # Parse: https://{account}.blob.core.windows.net/{container}/{blob}
    parts = blob_url.split('/')
    container = parts[3]
    blob_name = '/'.join(parts[4:])

    max_attempts = timeout_sec // 5  # Poll every 5 seconds

    for attempt in range(max_attempts):
        try:
            tags = await storage.get_blob_tags(container, blob_name)

            # Check for malware detection
            if tags.get("malware_detected") == "true":
                raise DefenderScanFailedError("Malware detected in image")

            # Check for scan completion
            if tags.get("defender_scan_complete") == "true":
                return {
                    "status": "clean",
                    "tags": tags,
                    "scan_timestamp": tags.get("scan_timestamp"),
                }

        except Exception as e:
            if "malware" in str(e).lower():
                raise
            DBOS.logger.warning(f"Defender scan check attempt {attempt}: {str(e)}")

        # Durable sleep - survives crashes!
        await DBOS.sleep_async(5)

    raise DefenderScanTimeoutError(f"Defender scan timed out after {timeout_sec}s")


@DBOS.step(retries_allowed=True, max_attempts=5)
async def download_sanitized_blob(
    image_id: UUID,
    sanitized_blob_url: str,
) -> bytes:
    """Download sanitized image from blob storage."""
    storage = await get_blob_storage()

    # Parse URL to get container and blob name
    parts = sanitized_blob_url.split('/')
    container = parts[3]
    blob_name = '/'.join(parts[4:])

    try:
        blob_bytes = await storage.download_blob(container, blob_name)
        return blob_bytes
    except Exception as e:
        raise BlobDownloadError(f"Failed to download sanitized blob: {str(e)}") from e
