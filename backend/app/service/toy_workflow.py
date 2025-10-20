"""
Toy DBOS workflow for testing deployment.

This is a minimal example to verify DBOS durable execution is working.
It demonstrates:
- A simple workflow with 2 steps
- Durable sleep between steps
- Event publishing for progress tracking
"""

from typing import Dict, Any
from dbos import DBOS


@DBOS.step(retries_allowed=True, max_attempts=3)
async def step_one(name: str) -> str:
    """
    First step: Process input and return a greeting.

    This step has retry logic - if it fails, DBOS will retry up to 3 times.
    """
    DBOS.logger.info(f"Step 1: Processing name '{name}'")

    # Simulate some processing
    greeting = f"Hello, {name}!"

    DBOS.logger.info(f"Step 1 complete: {greeting}")
    return greeting


@DBOS.step(retries_allowed=True, max_attempts=3)
async def step_two(greeting: str) -> str:
    """
    Second step: Transform the greeting to uppercase.

    This step also has retry logic.
    """
    DBOS.logger.info(f"Step 2: Transforming greeting '{greeting}'")

    # Simulate some processing
    result = greeting.upper()

    DBOS.logger.info(f"Step 2 complete: {result}")
    return result


@DBOS.workflow(max_recovery_attempts=5)
async def toy_workflow(name: str) -> Dict[str, Any]:
    """
    Simple toy workflow to test DBOS deployment.

    This workflow:
    1. Runs step_one to create a greeting
    2. Sleeps for 2 seconds (durable - survives crashes!)
    3. Runs step_two to transform the greeting
    4. Returns the result

    Args:
        name: Name to greet

    Returns:
        Dict with workflow results and metadata
    """
    try:
        DBOS.logger.info(f"Starting toy workflow for name: {name}")

        # Publish start event
        await DBOS.set_event_async("status", "started")
        await DBOS.set_event_async("input", name)

        # Step 1: Create greeting
        greeting = await step_one(name)
        await DBOS.set_event_async("step1_complete", True)
        await DBOS.set_event_async("greeting", greeting)

        # Durable sleep - if the server crashes during this sleep,
        # the workflow will resume from this point when it restarts
        DBOS.logger.info("Sleeping for 2 seconds (durable sleep)...")
        await DBOS.sleep_async(2)

        # Step 2: Transform greeting
        result = await step_two(greeting)
        await DBOS.set_event_async("step2_complete", True)
        await DBOS.set_event_async("result", result)

        # Mark as completed
        await DBOS.set_event_async("status", "completed")

        DBOS.logger.info(f"Toy workflow completed: {result}")

        return {
            "status": "success",
            "input": name,
            "greeting": greeting,
            "result": result,
            "workflow_id": DBOS.workflow_id,
        }

    except Exception as e:
        DBOS.logger.error(f"Toy workflow failed: {str(e)}")
        await DBOS.set_event_async("status", "failed")
        await DBOS.set_event_async("error", str(e))
        raise
