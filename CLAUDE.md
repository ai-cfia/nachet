# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Nachet is a Canadian government (CFIA) AI-powered seed identification system:

- **Nachet**: Weed seed identification using machine learning models

The project consists of a React TypeScript frontend and Python FastAPI backend, with PostgreSQL database and Azure Blob Storage for images.

## Common Development Commands

### Frontend (React + TypeScript + Vite)

```bash
cd frontend/
npm install                    # Install dependencies
npm run dev                    # Start development server (localhost:5173)
npm run build                  # Build for production
npm run lint                   # Run ESLint
npm run test                   # Run tests with Vitest
npm run test:coverage          # Run tests with coverage
npm run format                 # Format code with Prettier
npm run format:check           # Check formatting
```

### Backend (Python + FastApi + SQLAlchemy + Alembic + Azure SDK)

```bash
cd backend/
uv sync                           # Install dependencies (recommended)
uv run hypercorn -b :8080 app/main:app # Start development server
uv run pytest                    # Run tests

# Alternative (legacy pip method)
pip install -r requirements.txt    # Install dependencies
hypercorn -b :8080 app/main:app         # Start development server
pytest                            # Run tests
```

### Docker Commands

```bash
# Frontend only
docker build -t nachet-frontend frontend/
docker run -p 3000:3000 nachet-frontend

# Backend only  
docker build -t nachet-backend backend/
docker run -p 8080:8080 -e PORT=8080 nachet-backend

# Full stack with docker-compose
docker-compose up --build          # Run frontend + backend together
```

## Architecture Overview

### Technology Stack

- **Frontend**: React 18 + TypeScript + Vite + Material-UI + Axios + Zustand (state management)
- **Backend**: Python + FastAPI + SQLAlchemy + Alembic + Azure SDK + DBOS (workflow orchestration)
- **Database**: PostgreSQL (with async SQLAlchemy)
- **Storage**: Azure Blob Storage for images (with Defender scanning)
- **ML**: Remote HTTP endpoints (no local model processing)
- **Workflow Engine**: DBOS for durable, recoverable workflows
- **Observability**: OpenTelemetry + Loguru structured logging
- **Database Management**: Alembic for migrations and version control

### Key Directories Structure

```text
nachet/
├── frontend/          # React TypeScript application
│   ├── src/
│   │   ├── components/    # React components organized by feature
│   │   ├── pages/         # Page-level components
│   │   ├── common/        # Utilities, API client, types, Zod schemas
│   │   ├── hooks/         # Custom React hooks (useWorkflowPolling, etc.)
│   │   ├── stores/        # Zustand stores (useWorkflowStore, useDeviceStore)
│   │   └── logging/       # Error logging with correlation IDs
├── backend/           # Python FastAPI server
│   ├── app/
│   │   ├── main.py        # Main application entry point
│   │   ├── api/           # FastAPI routes
│   │   ├── service/       # Business logic layer
│   │   │   ├── inference/ # Async inference workflows (DBOS)
│   │   │   ├── inference_api/ # ML model API clients
│   │   │   └── auth/      # Authentication services
│   │   ├── blob/          # Blob storage abstraction (Azure)
│   │   ├── db/            # Database models, migrations, utils
│   │   ├── middleware/    # Logging, security headers
│   │   └── model/         # Pydantic models for API
│   └── tests/             # Backend test suite
│       ├── integration/   # Slow tests (DBOS, Azure, E2E)
│       └── *.py           # Fast unit tests
└── datastore/         # Standalone datastore package
```

### Database Architecture

- **PostgreSQL** with schema:
  - `nachet`: Seed detection system (users, pictures, inferences, models)
  - `ImageProcessingState`: Workflow state tracking (upload → scan → sanitization)
  - `InferenceRequestState`: ML inference workflow state tracking
- **Hybrid storage**: Metadata in PostgreSQL, images in Azure Blob Storage
- **UUID-based**: All entities use UUIDs for secure multi-tenant isolation
- **Workflow tracking**: Primary key `workflow_id` for state management tables
- **Schema versioning**: Managed with Alembic migration system

### ML Pipeline Architecture

- **Cloud-native**: All models hosted on external endpoints (Azure ML)
- **Asynchronous processing**: DBOS workflow orchestration with durable execution
- **Pipeline-based**: Sequential chains of models (detection → classification)
- **Model types**: Object detection (seed-detector), Classification (Swin transformers), Ensemble models
- **No local inference**: All processing via HTTP API calls
- **Dynamic loading**: Pipeline configurations loaded from encrypted JSON files in Azure Blob
- **Workflow hierarchy**: Parent workflow orchestrates processing + inference child workflows

### DBOS Workflow Architecture

- **Durable workflows**: Survive crashes and restarts with automatic recovery
- **Workflow decorators**: `@DBOS.workflow()` for orchestration, `@DBOS.step()` for non-deterministic operations
- **Event tracking**: `DBOS.set_event_async()` / `DBOS.get_all_events_async()` for status updates
- **Three main workflows**:
  1. `image_processing_and_inference_workflow` - Parent orchestrator
  2. `image_processing_workflow` - Upload → Defender scan → Sanitization
  3. `image_inference_workflow` - Download → ML pipeline → Save results
- **Queue configuration**: DBOS queues for concurrency and rate limiting
- **Recovery**: Max 5 recovery attempts with exponential backoff

## Development Workflow

### Running the Application Locally

1. **Backend**: Set up environment variables in `.env` (copy from `.env.template`)
2. **Start backend**: `cd backend && uv run hypercorn -b :8080 app/main:app`
3. **Start frontend**: `cd frontend && npm run dev`
4. **Access**: Frontend at <http://localhost:5173>, Backend at <http://localhost:8080>

### Testing

- **Frontend tests**: Use `npm run test` (Vitest + React Testing Library)
- **Backend unit tests (fast)**: `uv run pytest tests/ -v --tb=short -m "not integration"` in `backend/`
- **Backend integration tests (slow)**: `uv run pytest tests/ -v --tb=short -m "integration"` in `backend/`
- **All backend tests**: Use `uv run pytest tests/ -v` in directory `backend/`
- **Blob storage tests**: Use `uv run pytest tests/ -v` in `backend/app/blob`
- **Database tests**: Use `uv run pytest tests/ -v` in `backend/app/db`
- **Pre-commit validation**: `uv run ruff format && uv run ruff check --fix && uv run pyright --threads 12`
- **Manual testing**: See comprehensive test documentation in `frontend/TESTING.md` and `backend/TESTING.md`

**Test organization**:

- Unit tests: Fast tests without external dependencies (marked with no marker)
- Integration tests: Slow tests with DBOS, Azure, E2E workflows (marked with `@pytest.mark.integration`)
- Run fast tests first for quick feedback, then run integration tests before commits

### Environment Configuration

- **Frontend**: Uses environment files (`environment.ts`, `environment.staging.ts`, `environment.prod.ts`)
- **Backend**: Requires Azure Storage connection strings, database URLs, and ML endpoint configurations
- **Required variables**: `NACHET_AZURE_STORAGE_CONNECTION_STRING`, `NACHET_DATA`, various pipeline and model credentials

## Key Implementation Notes

### Data Flow (Async Workflow Model)

1. **Image capture/upload** → Frontend (React)
2. **Base64 encoding** → HTTP POST `/inf` to backend
3. **Backend returns** → `{ workflow_id, image_id, status: "processing" }`
4. **Frontend polls** → GET `/workflow/{workflow_id}/status` every 10 seconds
5. **Backend processing** (DBOS workflows):
   - **Processing workflow**: Upload → Defender scan → Sanitization
   - **Inference workflow**: Download sanitized image → ML pipeline → Save results
6. **When complete** → Frontend calls GET `/workflow/{workflow_id}/results`
7. **Results display** → Frontend updates UI with inference results

**Key endpoints**:

- `POST /inf` - Submit async inference (returns workflow_id)
- `GET /workflow/{workflow_id}/status` - Poll for status
- `GET /workflow/{workflow_id}/results` - Fetch results when complete
- `POST /inf-direct` - Synchronous inference (legacy, for testing only)

**Blob storage flow**:

- Original image → `nachet-original` container (EXTERNAL account for Defender)
- Defender scan → Polls blob tags for "clean" status
- Sanitization function → Stores in `nachet-sanitized` container (INTERNAL account)
- Path structure: `{org-prefix}/{image_id}.png`

### Authentication & Security

- **Cookie-based authentication** with JWT tokens
- **Encrypted model credentials** using Fernet encryption
- **Multi-tenant isolation** via UUID-based user containers
- **API key authentication** for external ML services

### Frontend State Management

- **Zustand stores**: Global state management with localStorage persistence
  - `useWorkflowStore`: Tracks workflow IDs, status, and errors
  - `useDeviceStore`: Caches device data
  - `useSpeciesStore`: Caches species data
- **Custom hooks**:
  - `useWorkflowPolling`: Polls workflow status every 10 seconds, fetches results on completion
- **API caching** with custom cache utilities
- **Real-time updates** through workflow status polling

### Backend Service Layer Architecture

- **Service facade pattern**: `InferenceService` provides clean API for controllers
- **Module organization** (`backend/app/service/inference/`):
  - `__init__.py` - InferenceService facade class
  - `workflows.py` - DBOS workflow definitions and steps (1131 lines)
  - `queues.py` - DBOS queue configuration (concurrency, rate limiting)
  - `submission.py` - Request submission and status checking
  - `workflow_management.py` - Status retrieval, cancellation, retry logic
  - `state_management.py` - Database state tracking for workflows
  - `image_validation.py` - Image preprocessing and validation
  - `test_endpoints.py` - Direct inference endpoints (disable in production)
- **Separation of concerns**: Business logic separated from API routes
- **Testability**: Each module has focused responsibilities

### Backend Error Handling

- **Custom exception hierarchy** for different error types
- **HTTP status code mapping** for API responses
- **Comprehensive logging** with Loguru structured logging
- **Correlation IDs** for request tracing across services
- **OpenTelemetry integration** for distributed tracing

## Troubleshooting

### Common Issues

- **CORS errors**: Check backend CORS configuration in `app/main.py`
- **Image upload failures**: Verify Azure Storage connection string (both EXTERNAL and INTERNAL accounts)
- **Defender scan timeout**: Check blob tags and Defender service status (300s timeout)
- **Workflow stuck in processing**: Check DBOS logs and workflow status via API
- **ML inference errors**: Check model endpoint availability and API keys
- **Database connection issues**: Verify PostgreSQL credentials and schema setup
- **Build failures**: Ensure all dependencies are installed and environment variables set
- **State tracking issues**: Verify `ImageProcessingState` and `InferenceRequestState` tables exist

### Debug Commands

```bash
# Check backend health
curl http://localhost:8080/health

# Check workflow status
curl http://localhost:8080/workflow/{workflow_id}/status

# auto format frontend code
cd frontend && npm run format

# Verify frontend build
cd frontend && npm run build

# Test database connection
cd backend/app/db && uv run validate_orm_online.py

# Run blob tests
cd backend/app/blob && uv run pytest tests/ -v

# Run db tests
cd backend/app/db && uv run pytest tests/ -v

# Run fast unit tests (recommended for quick feedback)
cd backend && uv run pytest tests/ -v --tb=short -m "not integration"

# Run slow integration tests (DBOS, Azure, E2E)
cd backend && uv run pytest tests/ -v --tb=short -m "integration"

# Pre-commit validation (format, lint, type check)
cd backend && uv run ruff format && uv run ruff check --fix && uv run pyright --threads 12
```

## Key Architecture Patterns

### DBOS Workflow Pattern

- **Parent workflow**: Orchestrates child workflows, returns workflow_id to client
- **Child workflows**: Processing (upload/scan/sanitize) and Inference (ML pipeline)
- **Steps**: Non-deterministic operations (DB writes, API calls, blob storage)
- **Idempotency**: Steps can be retried without side effects
- **Durability**: Workflows survive crashes and restarts

### Service Facade Pattern

- `InferenceService` class provides clean API for controllers
- Delegates to specialized modules (workflows, state_management, etc.)
- Separation of concerns: business logic vs API routes

### Frontend Polling Pattern

- Submit request → Receive workflow_id
- Poll status every 10 seconds with 20s initial delay
- Fetch results when status is "completed"
- Update Zustand store on each poll
- Clean up on unmount or terminal state

### State Tracking Pattern

- `ImageProcessingState`: Tracks upload → scan → sanitization pipeline
- `InferenceRequestState`: Tracks ML inference workflow
- Primary key: `workflow_id` (DBOS UUID)
- Separate from domain tables (Picture, Inference) for clean separation
