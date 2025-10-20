"""
Image Processing Pipeline Workflow (MVP)

DBOS workflow that orchestrates the MVP image processing pipeline:
1. Upload to Azure Blob Storage (nachet-original)
2. Wait for Azure Defender scan completion
3. Trigger sanitization Azure Function
4. Wait for sanitization callback (image in nachet-sanitized)

Each step is automatically checkpointed by DBOS for crash recovery.

Future: ML inference will be added in a later phase.
"""

from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from dbos import DBOS
from app.service.blob_operations import (
    upload_to_azure_blob,
    wait_for_defender_scan,
)
from app.service.sanitization import (
    trigger_sanitization_function,
    wait_for_sanitization_callback,
)


@DBOS.workflow(max_recovery_attempts=5)
async def process_image_pipeline(
    image_id: UUID,
    file_bytes: bytes,
    filename: str,
    genus: str,
    species: str,
    org_name: str,
    user_id: UUID,
) -> Dict[str, Any]:
    """
    Main image processing workflow (MVP).

    This workflow is durable - it will resume from the last completed step
    if interrupted by a crash or restart.

    Args:
        image_id: UUID v7 of the image
        file_bytes: Raw image bytes
        filename: Original filename
        genus: Genus name (normalized)
        species: Species name (normalized)
        org_name: Organization name (normalized, max 10 chars)
        user_id: Submitting user UUID

    Returns:
        Dict containing processing results and blob URLs

    Raises:
        Various exceptions for different failure modes (defender, sanitization)
    """
    try:
        DBOS.logger.info(f"Starting image processing pipeline for {image_id}")

        # Publish initial progress event
        await DBOS.set_event_async("processing_status", "started")
        await DBOS.set_event_async("timestamps", {
            "started": datetime.utcnow().isoformat()
        })

        # Step 1: Upload to Azure Blob Storage (nachet-original)
        DBOS.logger.info(f"[{image_id}] Step 1: Uploading to nachet-original")
        blob_url_original = await upload_to_azure_blob(
            image_id=image_id,
            file_bytes=file_bytes,
            filename=filename,
            genus=genus,
            species=species,
            org_name=org_name,
        )
        await DBOS.set_event_async("upload_complete", True)
        await DBOS.set_event_async("processing_status", "uploaded")
        await DBOS.set_event_async("blob_url_original", blob_url_original)

        # Step 2: Wait for Azure Defender scan
        DBOS.logger.info(f"[{image_id}] Step 2: Waiting for Defender scan")
        await DBOS.set_event_async("processing_status", "defender_scanning")
        defender_result = await wait_for_defender_scan(
            image_id=image_id,
            blob_url=blob_url_original,
            timeout_sec=300,
        )
        await DBOS.set_event_async("defender_scan_complete", True)
        await DBOS.set_event_async("processing_status", "defender_scanned")
        await DBOS.set_event_async("defender_result", defender_result)

        # Step 3: Trigger sanitization Azure Function
        DBOS.logger.info(f"[{image_id}] Step 3: Triggering sanitization function")
        await DBOS.set_event_async("processing_status", "sanitizing")
        await trigger_sanitization_function(
            image_id=image_id,
            genus=genus,
            species=species,
            blob_url_original=blob_url_original,
        )

        # Step 4: Wait for sanitization callback
        DBOS.logger.info(f"[{image_id}] Step 4: Waiting for sanitization callback")
        sanitized_blob_url = await wait_for_sanitization_callback(
            image_id=image_id,
            timeout_sec=600,
        )
        await DBOS.set_event_async("sanitization_complete", True)
        await DBOS.set_event_async("processing_status", "sanitized")
        await DBOS.set_event_async("blob_url_sanitized", sanitized_blob_url)

        # Publish completion
        await DBOS.set_event_async("processing_status", "completed")
        all_events = await DBOS.get_all_events_async(DBOS.workflow_id)
        await DBOS.set_event_async("timestamps", {
            **all_events.get("timestamps", {}),
            "completed": datetime.utcnow().isoformat()
        })

        DBOS.logger.info(f"[{image_id}] Pipeline completed successfully")

        return {
            "image_id": str(image_id),
            "status": "completed",
            "blob_url_original": blob_url_original,
            "blob_url_sanitized": sanitized_blob_url,
        }

    except Exception as e:
        DBOS.logger.error(f"[{image_id}] Pipeline failed: {str(e)}")

        # Publish error event
        await DBOS.set_event_async("processing_status", "failed")
        await DBOS.set_event_async("error_details", {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat(),
        })

        raise
