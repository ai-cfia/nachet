"""
DBOS test routes for deployment verification.

Simple routes with no authentication/authorization decorators to test
that DBOS workflows are working correctly.

  1. Health Check

  curl http://localhost:8080/test/dbos/health

  2. Run Synchronous Workflow (waits for completion)

  curl -X POST http://localhost:8080/test/dbos/sync-workflow \
    -H "Content-Type: application/json" \
    -d '{"name": "Alice"}'

  Expected response (after ~2 seconds):
  {
    "status": "success",
    "input": "Alice",
    "greeting": "Hello, Alice!",
    "result": "HELLO, ALICE!",
    "workflow_id": "..."
  }

  3. Submit Async Workflow (returns immediately)

  curl -X POST http://localhost:8080/test/dbos/toy-workflow \
    -H "Content-Type: application/json" \
    -d '{"name": "Bob"}'

  Expected response (immediate):
  {
    "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890",
    "message": "Workflow submitted. Check status at /test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890"
  }

  4. Check Workflow Status (use the workflow_id from step 3)

  curl http://localhost:8080/test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890

  5. Get Workflow Events

  curl http://localhost:8080/test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890/events

  ---
  Quick One-Liner Test

  curl -X POST http://localhost:8080/test/dbos/sync-workflow -H "Content-Type: application/json" -d '{"name": 
  "Test"}' && echo ""

  This will verify DBOS is working in ~2 seconds!


"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from beartype.typing import Dict, Any

from dbos import DBOS
from app.service.toy_workflow import toy_workflow


# Create router
router = APIRouter(prefix="/test/dbos", tags=["DBOS Testing"])


class ToyWorkflowRequest(BaseModel):
    """Request model for toy workflow."""

    name: str


class ToyWorkflowResponse(BaseModel):
    """Response model for toy workflow submission."""

    workflow_id: str
    message: str


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status check."""

    workflow_id: str
    status: str
    result: Dict[str, Any] | None = None
    error: str | None = None


@router.post("/toy-workflow", response_model=ToyWorkflowResponse)
async def submit_toy_workflow(request: ToyWorkflowRequest):
    """
    Submit a toy workflow for execution.

    This is a simple test endpoint with NO decorators to verify DBOS is working.

    The workflow will:
    1. Create a greeting from the name
    2. Sleep for 2 seconds (durable sleep)
    3. Transform the greeting to uppercase
    4. Return the result

    You can use the workflow_id to check status at GET /test/dbos/workflow/{workflow_id}

    Example:
        POST /test/dbos/toy-workflow
        {
            "name": "Alice"
        }

        Response:
        {
            "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890",
            "message": "Workflow submitted. Check status at /test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890"
        }
    """
    try:
        # Start the workflow asynchronously
        workflow_handle = await DBOS.start_workflow_async(
            toy_workflow,
            name=request.name,
        )

        workflow_id = workflow_handle.get_workflow_id()

        return ToyWorkflowResponse(
            workflow_id=workflow_id,
            message=f"Workflow submitted. Check status at /test/dbos/workflow/{workflow_id}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/workflow/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Get the status of a workflow.

    This endpoint checks the status of a previously submitted workflow.

    Example:
        GET /test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890

        Response (while running):
        {
            "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890",
            "status": "PENDING",
            "result": null,
            "error": null
        }

        Response (completed):
        {
            "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890",
            "status": "SUCCESS",
            "result": {
                "status": "success",
                "input": "Alice",
                "greeting": "Hello, Alice!",
                "result": "HELLO, ALICE!",
                "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890"
            },
            "error": null
        }
    """
    try:
        # Retrieve the workflow handle
        workflow_handle = await DBOS.retrieve_workflow_async(workflow_id)

        if workflow_handle is None:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )

        # Get workflow status
        status = await workflow_handle.get_status()

        # Try to get result if completed
        result: Dict[str, Any] | None = None
        error: str | None = None

        if status.status == "SUCCESS":
            try:
                # Get result using get_result() instead of get_result_async()
                raw_result = workflow_handle.get_result()
                # Ensure result is a dict, not a coroutine
                if isinstance(raw_result, dict):
                    result = raw_result
            except AttributeError:
                # Fallback: try to get events which contain the result
                try:
                    events = await DBOS.get_all_events_async(workflow_id)
                    if events:
                        result = events
                except Exception:
                    pass
            except Exception as e:
                error = f"Failed to get result: {str(e)}"
        elif status.status == "ERROR":
            # Convert error to string if it's an Exception
            error = str(status.error) if status.error else None

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status.status,
            result=result,
            error=error,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get("/workflow/{workflow_id}/events")
async def get_workflow_events(workflow_id: str):
    """
    Get all events published by a workflow.

    This shows the progress tracking events published by the workflow.

    Example:
        GET /test/dbos/workflow/01933e4f-8b2a-7890-abcd-ef1234567890/events

        Response:
        {
            "workflow_id": "01933e4f-8b2a-7890-abcd-ef1234567890",
            "events": {
                "status": "completed",
                "input": "Alice",
                "step1_complete": true,
                "greeting": "Hello, Alice!",
                "step2_complete": true,
                "result": "HELLO, ALICE!"
            }
        }
    """
    try:
        # Retrieve the workflow handle
        workflow_handle = await DBOS.retrieve_workflow_async(workflow_id)

        if workflow_handle is None:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )

        # Get all events
        events = await DBOS.get_all_events_async(workflow_id)

        return {
            "workflow_id": workflow_id,
            "events": events,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get workflow events: {str(e)}"
        )


@router.post("/sync-workflow")
async def run_toy_workflow_sync(request: ToyWorkflowRequest):
    """
    Run toy workflow synchronously (wait for completion).

    This endpoint waits for the workflow to complete before returning.
    Useful for simple testing.

    Example:
        POST /test/dbos/sync-workflow
        {
            "name": "Bob"
        }

        Response (after ~2 seconds):
        {
            "status": "success",
            "input": "Bob",
            "greeting": "Hello, Bob!",
            "result": "HELLO, BOB!",
            "workflow_id": "..."
        }
    """
    try:
        # Run workflow and wait for result
        result = await toy_workflow(request.name)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


@router.get("/health")
async def dbos_health():
    """
    Simple health check for DBOS testing routes.

    Returns:
        {"status": "ok", "message": "DBOS test routes are available"}
    """
    return {
        "status": "ok",
        "message": "DBOS test routes are available",
        "endpoints": [
            "POST /test/dbos/toy-workflow - Submit async workflow",
            "POST /test/dbos/sync-workflow - Run sync workflow",
            "GET /test/dbos/workflow/{workflow_id} - Get workflow status",
            "GET /test/dbos/workflow/{workflow_id}/events - Get workflow events",
        ],
    }
