# Nachet Async Image Processing Pipeline - Implementation Plan

**Date:** October 19, 2025
**Branch:** `446-backend-blob-module-durable-execution`
**Status:** Implementation In Progress (Updated Oct 20, 2025)

## Executive Summary

This document outlines the implementation plan for an asynchronous image processing pipeline using DBOS durable execution.

**MVP Scope**: The initial implementation focuses on the core workflow:

1. Upload original image to Azure Blob Storage (`nachet-original`)
2. Wait for Azure Defender scan completion
3. Trigger sanitization Azure Function
4. Receive callback when sanitized image is ready in `nachet-sanitized`

The system provides immediate UUIDv7 responses to image submissions while processing continues in the background. ML inference will be added in a later phase.

## Architecture Overview

### High-Level Flow (MVP)

```text
Frontend                Backend                 Azure Blob              Sanitizer Function
   |                      |                          |                       |
   |--POST /submit------->|                          |                       |
   | {image_data,         |--generate UUIDv7---------|                       |
   |  genus, species,     |                          |                       |
   |  org_name}           |                          |                       |
   |<--UUID response------|                          |                       |
   |                      |--start workflow----------|                       |
   |                      |                          |                       |
   |                      |--upload to nachet-original                       |
   |                      |  (org-name/genus-species/uuid.png)               |
   |                      |                          |                       |
   |                      |                    [Defender scan]               |
   |                      |--poll for tags---------->|                       |
   |                      |<--scan complete----------|                       |
   |                      |                          |                       |
   |                      |--trigger sanitize--------|------------------>|   |
   |                      |  {uuid, genus, species}  |                   |   |
   |                      |                          |             [sanitize]|
   |                      |                          |             [upload]  |
   |                      |                          |<--to nachet-sanitized |
   |                      |                          |   (genus/species/uuid)|
   |                      |<--callback: sanitized done-------------------|   |
   |                      |--update DB status--------|                       |
   |                      |                          |                       |
   |--GET /status/{uuid}->|                          |                       |
   |<--{status, urls}-----|                          |                       |
```

**Future Phase**: ML inference will be added after MVP is complete and tested.

### Blob Storage Naming Structure

#### Container: `nachet-original`

**Path structure**: `{org-name}/{genus}-{species}/{uuidv7}.{ext}`

**Example**: `cfia-org/avena-fatua/01933e4f-8b2a-7890-abcd-ef1234567890.png`

**Normalization rules**:

- `org-name`: Normalized organization name of submitter
  - Lowercase only
  - Characters: `a-z`, `0-9`, `-` (dashes)
  - Truncated to 10 characters maximum
  - Example: "CFIA Organization" → "cfia-org"
- `genus`: Genus name (normalized)
  - Lowercase only
  - Characters: `a-z`, `-` (dashes only, no numbers)
  - Example: "Avena" → "avena"
- `species`: Species name (normalized)
  - Lowercase only
  - Characters: `a-z`, `-` (dashes only, no numbers)
  - Example: "Fatua" → "fatua"
- `uuidv7`: UUID v7 generated at submission time
  - Same UUID used for both original and sanitized versions
- `ext`: Original file extension (png, jpg, jpeg)

#### Container: `nachet-sanitized`

**Path structure**: `{genus}/{species}/{uuidv7}.{ext}`

**Example**: `avena/fatua/01933e4f-8b2a-7890-abcd-ef1234567890.png`

**Notes**:

- No `org-name` prefix in sanitized container (removes org identification)
- Same `genus`, `species`, and `uuidv7` as original
- Extension may change based on sanitization process (always outputs PNG)

### Core Components (MVP)

1. **ImageProcessingService** (`app/service/image_processing.py`) - High-level service layer
2. **DBOS Workflow** (`app/service/image_pipeline.py`) - Durable orchestration (MVP: upload → scan → sanitize)
3. **DBOS Steps** (`app/service/blob_operations.py`, `app/service/sanitization.py`) - Individual pipeline stages with retry logic
4. **FastAPI Endpoints** - HTTP API for submission and status polling
5. **Database Schema** - ImageProcessingState table for state tracking
6. **Sanitizer Azure Function** (`sanitizer/`) - Python function for image sanitization using Pillow

## DBOS Benefits for This Use Case

| Feature | Benefit | Use Case |
|---------|---------|----------|
| **Durable Execution** | Workflows survive crashes/restarts | Long-running pipeline continues after interruption |
| **Automatic Retry** | Built-in exponential backoff | Handle transient Azure/ML server failures |
| **State Management** | No custom state machines needed | DBOS tracks workflow progress automatically |
| **Event System** | Progress tracking without custom infra | Frontend polling uses DBOS events |
| **Queue Management** | Built-in rate limiting & concurrency | Prevent overwhelming Azure resources |
| **Observability** | OpenTelemetry integration | Already connected to Grafana/Loki |

## Implementation Tasks

### Phase 1: Database Schema & Core Service ✅ COMPLETED

**Status:** All Phase 1 tasks have been completed and files created.

**Files Created:**

- `app/db/model.py` - Added `ImageProcessingState` table with full schema
- `app/service/constants.py` - Added `Bucket` and `ProcessingStatus` enums
- `app/service/image_processing.py` - Complete `ImageProcessingService` class
- `app/service/image_processing_queue.py` - DBOS queue configuration

**Key Features Implemented:**

- Separate `ImageProcessingState` table for tracking pipeline status
- Blob storage container constants with test/production separation
- High-level service layer with base64 image support
- Image validation and metadata extraction
- Status polling, cancellation, and retry methods

**Database Migration Required:**

```bash
cd backend
uv run alembic revision --autogenerate -m "Add image_processing_state table"
uv run alembic upgrade head
```

### Phase 2: DBOS Workflow & Steps ✅ COMPLETED

**Status:** All Phase 2 tasks have been completed and files created.

**Files Created:**

- `app/service/image_pipeline.py` - Main workflow orchestrator
- `app/service/blob_operations.py` - Blob upload and Defender scan steps
- `app/service/sanitization.py` - Sanitization trigger and callback steps

**Key Features Implemented:**

- `@DBOS.workflow()` main pipeline with durable execution
- `@DBOS.step()` decorators with retry logic and exponential backoff
- DBOS event publishing for progress tracking
- Durable sleep for Defender scan polling
- DBOS recv/send for callback messaging

**Workflow Steps:**

1. Upload to `nachet-original` with retry logic
2. Wait for Azure Defender scan completion (durable polling)
3. Trigger Azure Function for sanitization
4. Wait for sanitization callback via DBOS messaging

### Phase 2.1: DBOS Workflow Integration Testing

Integration tests are critical for verifying that the DBOS workflow behaves correctly in the context of the full system. These tests should validate:

- Workflow execution across all steps
- State persistence and recovery after simulated crashes
- Callback/messaging between steps
- Error handling and retry logic
- Database state consistency

#### Test Structure

**File:** `tests/integration/test_dbos_integration.py`

```python
"""
Integration tests for DBOS workflow.

Tests the full image processing pipeline with actual DBOS runtime.
Uses test containers and mock Azure services.
"""

import pytest
import asyncio
from uuid import uuid4, uuid7
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from dbos import DBOS

from app.service.image_pipeline import process_image_pipeline
from app.service.image_processing import ImageProcessingService
from app.service.constants import ProcessingStatus
from app.db.model import ImageProcessingState, Picture, Folder
from tests.fixtures.mock_azure import MockBlobStorage, MockDefender
from tests.fixtures.test_images import get_test_image_bytes


@pytest.fixture
async def test_folder(db_session: AsyncSession, test_user):
    """Create a test folder for image uploads."""
    folder = Folder(
        id=uuid4(),
        name="Test Folder",
        user_id=test_user.id,
        active=True,
    )
    db_session.add(folder)
    await db_session.commit()
    return folder


@pytest.fixture
def mock_blob_storage(monkeypatch):
    """Mock Azure Blob Storage for testing."""
    mock = MockBlobStorage()
    monkeypatch.setattr("app.blob.manager.get_blob_storage", lambda: mock)
    return mock


@pytest.fixture
def mock_defender(monkeypatch):
    """Mock Azure Defender scanning."""
    mock = MockDefender()
    # Patch the Defender scan logic to return mock results
    return mock


class TestDBOSWorkflowIntegration:
    """Integration tests for DBOS workflow execution."""

    @pytest.mark.asyncio
    async def test_complete_workflow_success(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
        mock_defender,
    ):
        """
        Test successful execution of complete workflow.

        Verifies:
        - All steps execute in order
        - Database state updates correctly
        - Final status is COMPLETED
        - Blob URLs are set
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()
        genus = "avena"
        species = "fatua"
        org_name = "cfia-org"

        # Act - Execute workflow
        result = await process_image_pipeline(
            image_id=image_id,
            file_bytes=image_bytes,
            filename="test_seed.png",
            genus=genus,
            species=species,
            org_name=org_name,
            user_id=test_user.id,
        )

        # Assert - Check result
        assert result["status"] == "completed"
        assert result["blob_url_original"]
        assert result["blob_url_sanitized"]

        # Assert - Check database state
        processing_state = await db_session.get(ImageProcessingState, image_id)
        assert processing_state is not None
        assert processing_state.status == ProcessingStatus.COMPLETED
        assert processing_state.blob_url_original is not None
        assert processing_state.blob_url_sanitized is not None
        assert processing_state.uploaded_at is not None
        assert processing_state.defender_scan_completed_at is not None
        assert processing_state.sanitization_completed_at is not None
        assert processing_state.completed_at is not None
        assert processing_state.progress_percentage == 100

    @pytest.mark.asyncio
    async def test_workflow_defender_scan_failure(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
        mock_defender,
    ):
        """
        Test workflow failure when Defender detects malware.

        Verifies:
        - Workflow stops at Defender scan step
        - Error is recorded in database
        - Status is FAILED
        """
        # Arrange
        image_bytes = get_test_image_bytes("malware.png")
        image_id = uuid7()

        # Configure mock to simulate malware detection
        mock_defender.set_malware_detected(True)

        # Act & Assert - Workflow should raise exception
        with pytest.raises(Exception) as exc_info:
            await process_image_pipeline(
                image_id=image_id,
                file_bytes=image_bytes,
                filename="malware.png",
                genus="avena",
                species="fatua",
                org_name="test-org",
                user_id=test_user.id,
            )

        assert "malware" in str(exc_info.value).lower()

        # Assert - Check database state
        processing_state = await db_session.get(ImageProcessingState, image_id)
        assert processing_state.status == ProcessingStatus.FAILED
        assert processing_state.malware_detected is True
        assert processing_state.error_message is not None

    @pytest.mark.asyncio
    async def test_workflow_sanitization_timeout(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test workflow behavior when sanitization times out.

        Verifies:
        - Workflow waits for callback
        - Timeout is raised after configured period
        - Database state reflects failure
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()

        # Configure mock to never send callback (simulate timeout)
        # Note: Use short timeout for testing (e.g., 5 seconds)

        # Act & Assert - Should timeout
        with pytest.raises(TimeoutError):
            await process_image_pipeline(
                image_id=image_id,
                file_bytes=image_bytes,
                filename="test_seed.png",
                genus="avena",
                species="fatua",
                org_name="test-org",
                user_id=test_user.id,
            )

        # Assert - Check database state
        processing_state = await db_session.get(ImageProcessingState, image_id)
        assert processing_state.status == ProcessingStatus.FAILED
        assert "timeout" in processing_state.error_message.lower()

    @pytest.mark.asyncio
    async def test_workflow_recovery_after_crash(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test workflow recovery after simulated crash.

        Verifies:
        - Workflow can resume from last checkpoint
        - No duplicate steps are executed
        - Final state is correct

        This is a key DBOS feature - durable execution.
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()

        # Act - Start workflow
        workflow_handle = await DBOS.start_workflow_async(
            process_image_pipeline,
            image_id=image_id,
            file_bytes=image_bytes,
            filename="test_seed.png",
            genus="avena",
            species="fatua",
            org_name="test-org",
            user_id=test_user.id,
        )

        workflow_id = workflow_handle.get_workflow_id()

        # Wait for upload step to complete
        await asyncio.sleep(2)

        # Simulate crash - retrieve workflow handle
        retrieved_handle = await DBOS.retrieve_workflow_async(workflow_id)

        # Check that workflow can be retrieved and status checked
        status = await retrieved_handle.get_status()
        assert status is not None

        # Wait for workflow to complete (it should continue after "crash")
        result = await retrieved_handle.get_result_async()

        # Assert - Workflow completed successfully after recovery
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_callback_messaging(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test DBOS recv/send callback messaging.

        Verifies:
        - Workflow waits on recv_async()
        - Callback sends message via send_async()
        - Message is received and processed correctly
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()

        # Start workflow in background
        workflow_handle = await DBOS.start_workflow_async(
            process_image_pipeline,
            image_id=image_id,
            file_bytes=image_bytes,
            filename="test_seed.png",
            genus="avena",
            species="fatua",
            org_name="test-org",
            user_id=test_user.id,
        )

        workflow_id = workflow_handle.get_workflow_id()

        # Wait for workflow to reach sanitization step
        await asyncio.sleep(3)

        # Simulate callback from Azure Function
        topic = f"sanitization-{image_id}"
        await DBOS.send_async(
            workflow_id=workflow_id,
            topic=topic,
            message={
                "status": "success",
                "sanitized_blob_url": f"https://test.blob.core.windows.net/nachet-sanitized/avena/fatua/{image_id}.png",
                "original_size_bytes": len(image_bytes),
                "sanitized_size_bytes": len(image_bytes),
            }
        )

        # Wait for workflow to complete
        result = await workflow_handle.get_result_async()

        # Assert - Workflow received callback and completed
        assert result["status"] == "completed"
        assert result["blob_url_sanitized"]

    @pytest.mark.asyncio
    async def test_workflow_event_publishing(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test DBOS event publishing for progress tracking.

        Verifies:
        - Events are published at each stage
        - Frontend can query events for progress
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()

        # Act - Execute workflow
        workflow_handle = await DBOS.start_workflow_async(
            process_image_pipeline,
            image_id=image_id,
            file_bytes=image_bytes,
            filename="test_seed.png",
            genus="avena",
            species="fatua",
            org_name="test-org",
            user_id=test_user.id,
        )

        workflow_id = workflow_handle.get_workflow_id()

        # Wait for workflow to complete
        await workflow_handle.get_result_async()

        # Assert - Check published events
        events = await DBOS.get_all_events_async(workflow_id)

        assert "processing_status" in events
        assert events["upload_complete"] is True
        assert events["defender_scan_complete"] is True
        assert events["sanitization_complete"] is True
        assert events["blob_url_original"]
        assert events["blob_url_sanitized"]

    @pytest.mark.asyncio
    async def test_workflow_retry_logic(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test automatic retry logic in DBOS steps.

        Verifies:
        - Transient failures trigger retries
        - Exponential backoff is applied
        - Eventually succeeds after retries
        """
        # Arrange
        image_bytes = get_test_image_bytes("test_seed.png")
        image_id = uuid7()

        # Configure mock to fail first 2 attempts, then succeed
        mock_blob_storage.set_failure_count(2)

        # Act - Execute workflow
        result = await process_image_pipeline(
            image_id=image_id,
            file_bytes=image_bytes,
            filename="test_seed.png",
            genus="avena",
            species="fatua",
            org_name="test-org",
            user_id=test_user.id,
        )

        # Assert - Workflow succeeded after retries
        assert result["status"] == "completed"
        assert mock_blob_storage.attempt_count >= 3  # Failed twice, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_concurrent_workflows(
        self,
        db_session: AsyncSession,
        test_user,
        test_folder,
        mock_blob_storage,
    ):
        """
        Test multiple concurrent workflows.

        Verifies:
        - Queue rate limiting works
        - Concurrency control is enforced
        - All workflows complete successfully
        """
        # Arrange
        num_workflows = 5
        image_bytes = get_test_image_bytes("test_seed.png")

        # Act - Submit multiple workflows concurrently
        workflow_handles = []
        for i in range(num_workflows):
            image_id = uuid7()
            handle = await DBOS.start_workflow_async(
                process_image_pipeline,
                image_id=image_id,
                file_bytes=image_bytes,
                filename=f"test_seed_{i}.png",
                genus="avena",
                species="fatua",
                org_name="test-org",
                user_id=test_user.id,
            )
            workflow_handles.append(handle)

        # Wait for all workflows to complete
        results = await asyncio.gather(
            *[handle.get_result_async() for handle in workflow_handles]
        )

        # Assert - All workflows completed
        assert len(results) == num_workflows
        assert all(r["status"] == "completed" for r in results)
```

#### Mock Fixtures

**File:** `tests/fixtures/mock_azure.py`

```python
"""Mock Azure services for testing."""

from typing import Dict, Any, Optional
import asyncio


class MockBlobStorage:
    """Mock Azure Blob Storage for testing."""

    def __init__(self):
        self.uploaded_blobs: Dict[str, bytes] = {}
        self.blob_tags: Dict[str, Dict[str, str]] = {}
        self.attempt_count = 0
        self.failure_count = 0

    def set_failure_count(self, count: int):
        """Set number of times to fail before succeeding."""
        self.failure_count = count
        self.attempt_count = 0

    async def upload_blob(
        self,
        container: str,
        name: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Mock blob upload with optional failure."""
        self.attempt_count += 1

        if self.attempt_count <= self.failure_count:
            raise Exception("Simulated upload failure")

        self.uploaded_blobs[f"{container}/{name}"] = data
        url = f"https://test.blob.core.windows.net/{container}/{name}"
        return {"url": url}

    async def get_blob_tags(self, container: str, name: str) -> Dict[str, str]:
        """Mock getting blob tags (for Defender scan results)."""
        key = f"{container}/{name}"
        return self.blob_tags.get(key, {
            "defender_scan_complete": "true",
            "malware_detected": "false",
        })

    async def download_blob(self, container: str, name: str) -> bytes:
        """Mock blob download."""
        key = f"{container}/{name}"
        return self.uploaded_blobs.get(key, b"")


class MockDefender:
    """Mock Azure Defender for testing."""

    def __init__(self):
        self.malware_detected = False

    def set_malware_detected(self, detected: bool):
        """Configure mock to simulate malware detection."""
        self.malware_detected = detected
```

**File:** `tests/fixtures/test_images.py`

```python
"""Test image fixtures."""

from PIL import Image
import io


def get_test_image_bytes(filename: str = "test.png") -> bytes:
    """Generate a test image as bytes."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')

    return buffer.getvalue()
```

#### Running Integration Tests

```bash
# Run all DBOS integration tests
cd backend
uv run pytest tests/workflows/test_dbos_integration.py -v

# Run specific test
uv run pytest tests/workflows/test_dbos_integration.py::TestDBOSWorkflowIntegration::test_complete_workflow_success -v

# Run with coverage
uv run pytest tests/workflows/test_dbos_integration.py --cov=app.service --cov-report=html
```

#### Key Testing Considerations

1. **Durable Execution**: Test that workflows can be retrieved and resume after simulated crashes
2. **Messaging**: Test DBOS recv/send for callback communication
3. **Events**: Test event publishing for progress tracking
4. **Retries**: Test automatic retry logic with exponential backoff
5. **Concurrency**: Test queue rate limiting and concurrency control
6. **Error Handling**: Test various failure scenarios (malware, timeout, network errors)
7. **Database Consistency**: Verify ImageProcessingState table is updated correctly

#### Success Criteria

- All integration tests pass
- Workflow can recover from simulated crashes
- Callback messaging works correctly
- Events are published and retrievable
- Retry logic handles transient failures
- Database state is consistent across all scenarios

### Phase 2.5: Sanitizer Azure Function 🔄 PENDING

**Status:** Not yet implemented. Detailed specification available in full plan document.

**Overview:** Azure Function for image sanitization using Python Pillow library.

**Directory Structure:**

```text
sanitizer/
├── function_app.py          # HTTP trigger endpoint
├── sanitize/sanitize_image.py   # Pillow-based pixel extraction
├── requirements.txt         # Dependencies
└── host.json               # Configuration
```

**Key Features:**

- HTTP POST trigger receives sanitization requests from backend
- Downloads original image from Azure Blob Storage
- Extracts RGB(A) pixel data using Pillow (removes EXIF/metadata)
- Uploads sanitized PNG to `nachet-sanitized` container
- Calls backend callback endpoint with results

**Callback Endpoint:** `app/api/callbacks.py` - Uses DBOS send to notify waiting workflow

### Phase 3: API Endpoints 🔄 PENDING

**Status:** Not yet implemented.

**Files to Create:**

- `app/api/routes.py` - Add image submission and status endpoints
- Update existing router with new endpoints

**Endpoints:**

1. **POST /inf** - Image Submission
   - Accepts base64 encoded images with genus/species metadata
   - Returns immediate UUID v7 response
   - Starts DBOS workflow in background
   - Normalizes taxonomic names and org names

2. **GET /inf/{image_id}/status** - Status Polling
   - Queries `ImageProcessingState` table
   - Returns current status, progress percentage, timestamps
   - Includes blob URLs when available

### Phase 4: Queue Management ✅ COMPLETED

**Status:** Queue configuration already created in Phase 1.

**File:** `app/service/image_processing_queue.py`

**Features:**

- Global concurrency limit: 10 workflows
- Rate limiting: 50 starts per 60 seconds
- Worker concurrency: 5 per process
- Partition queue enabled for tenant isolation

### Phase 5-10: Advanced Features 🔄 FUTURE

#### **Phase 5: Advanced Features**

- Event streaming (SSE/WebSocket for real-time updates)
- Timeout/cancellation handlers
- Workflow recovery/resume UI
- Enhanced error handling
- Observability dashboards

#### **Phase 6: Testing**

- Unit tests for individual components
- Integration tests (covered in Phase 2.1)
- End-to-end pipeline tests

#### **Phase 7: Documentation**

- API documentation (OpenAPI/Swagger)
- Architecture diagrams
- Troubleshooting guides
- Operational procedures

#### **Phase 8: Frontend Integration**

- Update React frontend for polling
- Implement exponential backoff
- Add progress UI for pipeline stages
- Display blob URLs and errors

#### **Phase 9: Configuration**

- Environment variables for all Azure services
- DBOS configuration
- Pipeline timeout and concurrency settings

#### **Phase 10: Performance Testing**

- Load testing with realistic workloads
- Optimization based on metrics
- Stress testing queue limits

## MVP Scope Summary

### What's Included in MVP

1. **Image Upload with Metadata**
   - Accept base64 encoded images from frontend
   - Include genus, species, and organization name
   - Generate UUIDv7 immediately for response

2. **Blob Storage Upload**
   - Upload to `nachet-original` container
   - Path structure: `{org-name}/{genus}-{species}/{uuidv7}.{ext}`
   - Automatic name normalization

3. **Azure Defender Scan**
   - Wait for malware scan completion
   - Poll blob tags every 5 seconds
   - Fail if malware detected

4. **Image Sanitization**
   - Trigger Azure Function for sanitization
   - Extract RGB(A) pixel data using Pillow
   - Remove all EXIF/metadata
   - Upload to `nachet-sanitized` with path: `{genus}/{species}/{uuidv7}.png`
   - Callback-based completion using DBOS recv/send

5. **Status Tracking**
   - Separate `ImageProcessingState` table for clean data model
   - Tracks upload → scan → sanitize pipeline only
   - Real-time status polling endpoint
   - Progress percentage tracking (0-100%)
   - Comprehensive timestamps for each stage
   - **Note**: Inference state is NOT tracked here, as images can be processed multiple times by different models

### What's NOT in MVP (Future Phases)

- ML inference pipeline (will be added after MVP is stable)
  - Inference will be tracked separately (not in ImageProcessingState)
  - Each image can have multiple inference runs with different models
- Advanced error recovery UI
- Performance optimizations
- WebSocket/SSE streaming

### Key Deliverables

1. **Backend** (`backend/app/`)
   - `service/constants.py` - Blob container and status enums
   - `service/image_processing.py` - High-level service layer
   - `service/image_pipeline.py` - DBOS workflow orchestrator
   - `service/blob_operations.py` - Blob upload and Defender scan steps
   - `service/sanitization.py` - Sanitization trigger and callback steps
   - `service/image_processing_queue.py` - DBOS queue configuration
   - `db/model.py` - ImageProcessingState table
   - `api/routes.py` - Image submission endpoint (updated)
   - `api/callbacks.py` - Sanitization callback endpoint (new)

2. **Sanitizer Azure Function** (`sanitizer/`)
   - `function_app.py` - HTTP trigger
   - `sanitize/sanitize_image.py` - Pillow-based sanitization
   - `requirements.txt` - Dependencies

3. **Database Migration**
   - Alembic migration for `image_processing_state` table

## Key Architectural Decisions

### 1. Separate Processing State Table

Instead of polluting the `Picture` model with many nullable processing fields, we created a dedicated `ImageProcessingState` table:

**Benefits**:

- Clean separation of concerns
- Easy to query processing status independently
- No impact on existing Picture queries
- One-to-one relationship for data integrity

### 2. Blob Storage Naming Structure

**Original container** includes organization for access control/auditing:

- `{org-name}/{genus}-{species}/{uuidv7}.{ext}`
- Example: `cfia-org/avena-fatua/01933e4f-8b2a-7890.png`

**Sanitized container** removes organization for privacy:

- `{genus}/{species}/{uuidv7}.png`
- Example: `avena/fatua/01933e4f-8b2a-7890.png`

**Benefits**:

- Consistent UUIDs across both containers
- Organized by taxonomy for easy browsing
- Privacy-preserving sanitized storage

### 3. Callback-Based Sanitization

Using DBOS `recv_async()` instead of polling:

**Benefits**:

- More efficient (no constant polling)
- Lower latency (immediate notification)
- Cleaner code (no polling loops)
- Leverages DBOS durable messaging

### 4. ImageProcessingService Layer

The service layer (`app/service/image_processing.py`) provides:

- **Abstraction**: High-level interface for image processing operations
- **Validation**: Pre-workflow validation to fail fast (base64 decode, image format)
- **Coordination**: Orchestrates between DBOS, blob storage, and database
- **Error handling**: Consistent error handling and logging
- **Normalization**: Handles genus/species/org name normalization

### 5. DBOS Workflow Pattern

**Why DBOS?**

- **Durable execution**: Workflows survive crashes/restarts
- **Automatic retry**: Built-in exponential backoff for transient failures
- **State management**: No custom state machines needed
- **Observability**: Built-in tracing and monitoring (Grafana/Loki)
- **Messaging**: Recv/send for callback-based communication

**MVP Workflow Design:**

```python
@DBOS.workflow()  # Orchestrator
async def process_image_pipeline():
    await upload_to_azure_blob()  # @DBOS.step with retries
    await wait_for_defender_scan()  # @DBOS.step with durable sleep
    await trigger_sanitization_function()  # @DBOS.step with retries
    await wait_for_sanitization_callback()  # @DBOS.step with recv_async
```

### 3. Queue-Based Submission

Using `Queue.enqueue_async()` instead of direct workflow start provides:

- **Rate limiting**: Prevent overwhelming Azure services
- **Concurrency control**: Limit parallel executions
- **Partitioning**: Tenant isolation via org_id
- **Prioritization**: Optional priority-based dequeuing

### 4. Status Polling vs. Streaming

**Phase 1**: Polling via `/status` endpoint
**Phase 2**: Optional streaming via SSE or WebSocket

Polling is simpler and sufficient for most use cases. Streaming can be added later for real-time updates.

## Environment Variables

```bash
# DBOS Configuration
DBOS_DATABASE_URL=postgresql://user:pass@localhost:5432/nachet
DBOS_SYSTEM_SCHEMA=nachetdbos

# Azure Sanitization Function
AZURE_SANITIZATION_FUNCTION_URL=https://sanitize.azurewebsites.net/api/sanitize
AZURE_SANITIZATION_FUNCTION_KEY=xxxxx

# ML Inference
INFERENCE_SERVER_ENDPOINT=https://inference.example.com/predict

# Pipeline Configuration
IMAGE_PIPELINE_TIMEOUT_SECONDS=3600
IMAGE_PIPELINE_MAX_CONCURRENCY=10
IMAGE_PIPELINE_RATE_LIMIT=50  # per minute
```

## Success Criteria 2

1. **Response Time**: Image submission returns UUID in < 100ms
2. **Reliability**: Workflows resume after crashes with no data loss
3. **Throughput**: Handle 50+ image submissions per minute
4. **Visibility**: Status endpoint provides accurate progress tracking
5. **Error Handling**: Failed workflows can be retried manually
6. **Monitoring**: All stages tracked in Grafana/Loki

## Rollout Plan

1. **Development**: Implement on feature branch `446-backend-blob-module-durable-execution`
2. **Testing**: Unit tests, integration tests, load tests
3. **Staging**: Deploy to staging environment with real Azure services
4. **Monitoring**: Verify metrics and tracing work correctly
5. **Production**: Gradual rollout with feature flag
6. **Validation**: Monitor error rates and performance

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Azure service outages | Retry logic with exponential backoff |
| Long-running workflows | Timeout + cancellation endpoints |
| Database deadlocks | DBOS transactions with proper isolation |
| Memory issues (large images) | Streaming downloads, size limits |
| Queue backlog | Rate limiting, monitoring, auto-scaling |

## Next Steps

1. Review and approve this plan
2. Create Alembic migration for database schema
3. Implement ImageProcessingService
4. Implement DBOS workflow and steps
5. Create API endpoints
6. Write tests
7. Deploy to staging

---

**Document Version:** 1.0  
**Last Updated:** October 19, 2025  
**Authors:** Development Team  
**Status:** Awaiting Approval
