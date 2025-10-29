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

**Status:** All Phase 2 tasks have been completed and files created.

Integration tests are critical for verifying that the DBOS workflow behaves correctly in the context of the full system. These tests should validate:

- Workflow execution across all steps
- State persistence and recovery after simulated crashes
- Callback/messaging between steps
- Error handling and retry logic
- Database state consistency

#### Test Structure

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
async def image_processing_workflow():
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
