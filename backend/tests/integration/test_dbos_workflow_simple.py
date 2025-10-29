"""
Simple test to verify DBOS workflows work in test environment.
"""

import pytest
import asyncio
from dbos import DBOS


@DBOS.workflow()
async def simple_test_workflow(value: str) -> str:
    """Simple workflow that returns immediately."""
    return f"processed-{value}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_workflow(dbos_runtime):
    """Test that a simple workflow can be started and completed."""
    # Start workflow
    handle = DBOS.start_workflow(simple_test_workflow, value="test")

    # Wait for workflow using polling with short timeouts
    workflow_id = handle.workflow_id
    max_attempts = 30
    for attempt in range(max_attempts):
        # Retrieve workflow status
        retrieved_handle = await DBOS.retrieve_workflow_async(workflow_id)

        # Try to get result with a short timeout
        try:
            result = await asyncio.wait_for(retrieved_handle.get_result(), timeout=0.1)
            # Workflow completed
            assert result == "processed-test"
            return
        except asyncio.TimeoutError:
            # Workflow still running, continue polling
            await asyncio.sleep(0.5)

    pytest.fail(f"Workflow {workflow_id} did not complete within 15 seconds")
