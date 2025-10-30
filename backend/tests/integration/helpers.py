"""
Helper functions for integration tests.

These helpers simplify common test operations for workflow and blob testing.
"""

import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model import Picture
from app.blob.azure.storage import AzureBlobStorage
from dbos import DBOS


async def wait_for_workflow_completion(
    workflow_id: str,
    timeout: int = 60,
    poll_interval: float = 1.0,
) -> Dict[str, Any]:
    """
    Poll DBOS workflow status until completion or timeout.

    Args:
        workflow_id: DBOS workflow ID to monitor
        timeout: Maximum time to wait in seconds (default 60)
        poll_interval: Time between polls in seconds (default 1.0)

    Returns:
        Dict with workflow status and events

    Raises:
        TimeoutError: If workflow doesn't complete within timeout
        Exception: If workflow fails
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise TimeoutError(
                f"Workflow {workflow_id} did not complete within {timeout}s"
            )

        # Retrieve workflow handle
        handle = await DBOS.retrieve_workflow_async(workflow_id)

        # Check if workflow completed
        # get_result() with a short timeout to check if ready
        try:
            result = await asyncio.wait_for(handle.get_result(), timeout=0.1)
            # Workflow completed successfully
            events = await DBOS.get_all_events_async(workflow_id)
            return {
                "status": "completed",
                "result": result,
                "events": events,
            }
        except asyncio.TimeoutError:
            # Workflow still running, continue polling
            pass
        except Exception as e:
            # Workflow completed with an exception
            # Re-raise it so the test can catch it
            from app.exceptions import (
                DefenderScanFailedError,
                DefenderScanNotScannedError,
                DefenderScanTimeoutError,
                SanitizationError,
            )

            # Known workflow exceptions - re-raise directly
            if isinstance(
                e,
                (
                    DefenderScanFailedError,
                    DefenderScanNotScannedError,
                    DefenderScanTimeoutError,
                    SanitizationError,
                ),
            ):
                raise

            # Unknown exception - re-raise it
            raise

        # Wait before next poll
        await asyncio.sleep(poll_interval)


async def assert_blob_exists_in_azurite(
    storage: AzureBlobStorage,
    container: str,
    blob_name: str,
) -> Dict[str, Any]:
    """
    Assert that a blob exists in Azurite and return its properties.

    Args:
        storage: AzureBlobStorage instance
        container: Container name
        blob_name: Blob path

    Returns:
        Dict with blob properties

    Raises:
        AssertionError: If blob doesn't exist
    """
    try:
        # List blobs in container to verify existence
        result = await storage.list_blobs(container)
        blobs = result.get("blobs", [])

        matching_blob = None
        for blob in blobs:
            if blob.get("name") == blob_name:
                matching_blob = blob
                break

        assert matching_blob is not None, (
            f"Blob {blob_name} not found in container {container}. "
            f"Available blobs: {[b.get('name') for b in blobs]}"
        )

        return matching_blob

    except Exception as e:
        raise AssertionError(
            f"Failed to verify blob {blob_name} in {container}: {str(e)}"
        )


async def download_blob_from_azurite(
    storage: AzureBlobStorage,
    container: str,
    blob_name: str,
) -> bytes:
    """
    Download blob from Azurite for verification.

    Args:
        storage: AzureBlobStorage instance
        container: Container name
        blob_name: Blob path

    Returns:
        Blob bytes

    Raises:
        Exception: If download fails
    """
    try:
        blob_bytes = await storage.download_blob(container, blob_name)
        return blob_bytes
    except Exception as e:
        raise Exception(
            f"Failed to download blob {blob_name} from {container}: {str(e)}"
        )


async def mock_defender_tags_in_azurite(
    storage: AzureBlobStorage,
    container: str,
    blob_name: str,
    scan_result: str = "No threats found",
    upload_placeholder: bool = True,
) -> None:
    """
    Set Azure Defender scan result tags on blob in Azurite.

    Note: Azurite supports blob tags, but doesn't run actual Defender scans.
    This helper manually sets the tags that Defender would set.

    Args:
        storage: AzureBlobStorage instance
        container: Container name
        blob_name: Blob path
        scan_result: Scan result value (default "No threats found")
            Valid values: "No threats found", "Malicious", "Not scanned", "SAM*"
        upload_placeholder: If True, uploads a placeholder blob if it doesn't exist (default True)
    """
    from datetime import datetime, timezone

    # Check if blob exists; if not, upload a placeholder
    if upload_placeholder:
        try:
            # Try to check if blob exists by attempting to get its properties
            from app.blob.exceptions import BlobNotFoundError

            try:
                await storage.download_blob(container, blob_name)
            except BlobNotFoundError:
                # Blob doesn't exist, upload a placeholder
                placeholder_data = b"placeholder for defender scan tags"
                await storage.upload_blob(container, blob_name, placeholder_data)
        except Exception:
            # If any other error, try to upload placeholder anyway
            placeholder_data = b"placeholder for defender scan tags"
            await storage.upload_blob(container, blob_name, placeholder_data)

    tags = {
        "Malware Scanning scan result": scan_result,  # Capital 'S' to match Azure Defender format
        "Malware Scanning scan time UTC": datetime.now(
            timezone.utc
        ).isoformat(),  # Capital 'S' to match Azure Defender format
    }

    try:
        await storage.set_blob_tags(container, blob_name, tags)
    except Exception as e:
        raise Exception(f"Failed to set Defender tags on {blob_name}: {str(e)}")


async def create_test_picture_with_hash(
    session: AsyncSession,
    folder_id: UUID,
    user_id: UUID,
    org_admin_role_id: UUID,
    org_user_role_id: UUID,
    sha256: str,
    width: int = 640,
    height: int = 480,
) -> Picture:
    """
    Create a test Picture record with specific SHA256 hash.

    Used for testing duplicate detection logic.

    Args:
        session: Database session
        folder_id: Folder UUID
        user_id: User UUID
        org_admin_role_id: Admin role UUID
        org_user_role_id: User role UUID
        sha256: SHA256 hash to use
        width: Image width (default 640)
        height: Image height (default 480)

    Returns:
        Created Picture instance
    """
    from uuid6 import uuid7

    picture = Picture(
        id=uuid7(),
        folder_id=folder_id,
        user_id=user_id,
        org_admin_role_id=org_admin_role_id,
        org_user_role_id=org_user_role_id,
        name="test_duplicate.png",
        width=width,
        height=height,
        format="PNG",
        sha256=sha256,
    )

    session.add(picture)
    await session.commit()
    await session.refresh(picture)

    return picture


async def assert_picture_fields(
    picture: Picture,
    expected_folder_id: UUID,
    expected_sha256: str,
    expected_width: int,
    expected_height: int,
) -> None:
    """
    Assert Picture record has expected field values.

    Args:
        picture: Picture instance to verify
        expected_folder_id: Expected folder ID
        expected_sha256: Expected SHA256 hash
        expected_width: Expected image width
        expected_height: Expected image height

    Raises:
        AssertionError: If any field doesn't match
    """
    assert picture.folder_id == expected_folder_id, (
        f"Folder ID mismatch: {picture.folder_id} != {expected_folder_id}"
    )
    assert picture.sha256 == expected_sha256, (
        f"SHA256 mismatch: {picture.sha256} != {expected_sha256}"
    )
    assert picture.width == expected_width, (
        f"Width mismatch: {picture.width} != {expected_width}"
    )
    assert picture.height == expected_height, (
        f"Height mismatch: {picture.height} != {expected_height}"
    )
    assert picture.format == "PNG", f"Format should be PNG, got {picture.format}"


async def assert_processing_state_fields(
    state,
    expected_status: str,
    expected_workflow_id: Optional[str] = None,
) -> None:
    """
    Assert ImageProcessingState has expected field values.

    Args:
        state: ImageProcessingState instance
        expected_status: Expected status value
        expected_workflow_id: Expected workflow ID (optional)

    Raises:
        AssertionError: If any field doesn't match
    """
    assert state.status == expected_status, (
        f"Status mismatch: {state.status} != {expected_status}"
    )

    if expected_workflow_id is not None:
        assert state.workflow_id == expected_workflow_id, (
            f"Workflow ID mismatch: {state.workflow_id} != {expected_workflow_id}"
        )

    # Verify created_at timestamp exists
    assert state.created_at is not None, "created_at should be set"


async def cleanup_test_blobs(
    storage: AzureBlobStorage,
    container: str,
    prefix: str,
) -> None:
    """
    Clean up test blobs with specific prefix.

    Args:
        storage: AzureBlobStorage instance
        container: Container name
        prefix: Blob name prefix (e.g., "test-org/")
    """
    try:
        # List all blobs in container
        result = await storage.list_blobs(container)
        blobs = result.get("blobs", [])

        # Delete blobs matching prefix
        for blob in blobs:
            blob_name = blob.get("name", "")
            if blob_name.startswith(prefix):
                try:
                    await storage.delete_blob(container, blob_name)
                except Exception:
                    pass  # Best-effort cleanup

    except Exception:
        pass  # Container might not exist
