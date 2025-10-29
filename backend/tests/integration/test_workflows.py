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


# ============================================================================
# Inference Workflow Wrappers
# ============================================================================


@no_type_check
@DBOS.workflow()
async def download_image_workflow(
    org_prefix: str,
    image_id: UUID,
) -> str:
    """Workflow wrapper for testing download_image_from_blob_step."""
    from app.service.inference import download_image_from_blob_step

    return await download_image_from_blob_step(
        org_prefix=org_prefix,
        image_id=image_id,
    )


@no_type_check
@DBOS.workflow()
async def get_pipeline_configuration_workflow(
    pipeline_id: UUID,
) -> list[Dict[str, Any]]:
    """Workflow wrapper for testing get_pipeline_configuration_step."""
    from app.service.inference import get_pipeline_configuration_step

    return await get_pipeline_configuration_step(
        pipeline_id=pipeline_id,
    )


@no_type_check
@DBOS.workflow()
async def execute_inference_step_workflow(
    step_config: Dict[str, Any],
    previous_result: str | Dict[str, Any],
) -> Dict[str, Any]:
    """Workflow wrapper for testing execute_inference_step."""
    from app.service.inference import execute_inference_step

    return await execute_inference_step(
        step_config=step_config,
        previous_result=previous_result,
    )


@no_type_check
@DBOS.workflow()
async def save_inference_results_workflow(
    user_id: UUID,
    image_id: UUID,
    pipeline_id: UUID,
    org_user_role_id: UUID,
    org_admin_role_id: UUID,
    api_response: Any,  # ApiInferenceResponse
    parent_workflow_id: str,
) -> Dict[str, Any]:
    """Workflow wrapper for testing save_inference_results_step."""
    from app.service.inference import save_inference_results_step

    return await save_inference_results_step(
        user_id=user_id,
        image_id=image_id,
        pipeline_id=pipeline_id,
        org_user_role_id=org_user_role_id,
        org_admin_role_id=org_admin_role_id,
        api_response=api_response,
        parent_workflow_id=parent_workflow_id,
    )
