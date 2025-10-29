"""
Test wrapper workflows for integration testing of DBOS steps.

These workflows wrap individual DBOS steps so they can be tested in isolation
while still respecting DBOS workflow requirements (like DBOS.sleep()).
"""

from typing import no_type_check, Dict, Any
from uuid import UUID
from dbos import DBOS

from app.service.blob_operations import (
    upload_to_azure_blob,
    wait_for_defender_scan,
)
from app.service.sanitization import trigger_sanitization_function_local
from app.service.constants import BlobAccount


@no_type_check
@DBOS.workflow()
async def upload_blob_workflow(
    image_id: UUID,
    file_bytes: bytes,
    org_prefix: str,
    user_id: UUID,
    blob_account: BlobAccount = BlobAccount.ONPREM,
) -> str:
    """Workflow wrapper for testing upload_to_azure_blob step."""
    return await upload_to_azure_blob(
        image_id=image_id,
        file_bytes=file_bytes,
        org_prefix=org_prefix,
        user_id=user_id,
        blob_account=blob_account,
    )


@no_type_check
@DBOS.workflow()
async def wait_for_defender_scan_workflow(
    image_id: UUID,
    org_prefix: str,
    timeout_sec: int = 300,
) -> Dict[str, Any]:
    """Workflow wrapper for testing wait_for_defender_scan step."""
    return await wait_for_defender_scan(
        image_id=image_id,
        org_prefix=org_prefix,
        timeout_sec=timeout_sec,
    )


@no_type_check
@DBOS.workflow()
async def trigger_sanitization_workflow(
    image_id: UUID,
    org_prefix: str,
) -> str:
    """Workflow wrapper for testing trigger_sanitization_function_local step."""
    return await trigger_sanitization_function_local(
        image_id=image_id,
        org_prefix=org_prefix,
    )
