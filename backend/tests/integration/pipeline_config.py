"""
Pipeline configuration helper for integration tests.

This module provides functions to select the appropriate test pipeline
based on the NACHET_ENV environment variable.

Pipeline Selection Logic:
- NACHET_ENV="local" → Use local pipelines (127.0.0.1:12380/12390/12360 WireMock endpoints)
- NACHET_ENV="ci" or "test" → Use non-local pipelines (Docker service names)
"""

import os
from uuid import UUID


# Local pipelines - use 127.0.0.1 endpoints with WireMock
LOCAL_PIPELINE_15SPP_ID = UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a4b")
LOCAL_PIPELINE_27SPP_ID = UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f4a")

# CI pipelines - use Docker service names with unique ports for GitHub Actions
CI_PIPELINE_15SPP_ID = UUID("e5f6a7b8-c9d0-4e5f-8a7b-9c0d1e2f3a5b")
CI_PIPELINE_27SPP_ID = UUID("d4e5f6a7-b8c9-4d5e-8f7a-9b0c1d2e3f5a")


def get_pipeline_id_for_test(species_count: int = 15) -> UUID:
    """
    Get the appropriate pipeline ID based on NACHET_ENV.

    Args:
        species_count: Number of species (15 or 27)

    Returns:
        UUID: Pipeline ID to use for testing

    Usage in tests:
        from tests.integration.pipeline_config import get_pipeline_id_for_test

        @pytest_asyncio.fixture
        async def test_pipeline_id():
            return get_pipeline_id_for_test(species_count=15)
    """
    nachet_env = os.getenv("NACHET_ENV", "local").lower()

    # Determine which pipeline set to use
    if nachet_env == "local":
        # Local development - use 127.0.0.1 endpoints
        if species_count == 15:
            return LOCAL_PIPELINE_15SPP_ID
        elif species_count == 27:
            return LOCAL_PIPELINE_27SPP_ID
    else:
        # CI environment - use Docker service names with unique ports
        if species_count == 15:
            return CI_PIPELINE_15SPP_ID
        elif species_count == 27:
            return CI_PIPELINE_27SPP_ID

    raise ValueError(f"Unsupported species_count: {species_count}. Use 15 or 27.")


def is_using_local_pipelines() -> bool:
    """
    Check if tests should use local pipelines.

    Returns:
        bool: True if NACHET_ENV="local", False otherwise
    """
    nachet_env = os.getenv("NACHET_ENV", "local").lower()
    return nachet_env == "local"


def get_pipeline_description() -> str:
    """
    Get a description of which pipeline environment is being used.

    Returns:
        str: Description of the current pipeline configuration
    """
    if is_using_local_pipelines():
        return "Using LOCAL pipelines (127.0.0.1 WireMock endpoints)"
    else:
        return "Using CI pipelines (Docker service names with unique ports)"
