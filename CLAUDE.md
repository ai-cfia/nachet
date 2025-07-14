# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Nachet is a Canadian government (CFIA) AI-powered seed identification system:

- **Nachet**: Weed seed identification using machine learning models

The project consists of a React TypeScript frontend and Python Quart backend, with PostgreSQL database and Azure Blob Storage for images.

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

### Backend (Python + Quart)

```bash
cd backend/
pip install -r requirements.txt    # Install dependencies
hypercorn -b :8080 app:app         # Start development server
python -m unittest discover -s tests  # Run tests
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

- **Frontend**: React 18 + TypeScript + Vite + Material-UI + Axios
- **Backend**: Python + Quart (async Flask) + SQLAlchemy + Azure SDK
- **Database**: PostgreSQL with dual schemas (Nachet + FertiScan)
- **Storage**: Azure Blob Storage for images
- **ML**: Remote HTTP endpoints (no local model processing)
- **Database Management**: Bytebase for schema versioning

### Key Directories Structure

```text
nachet/
├── frontend/          # React TypeScript application
│   ├── src/
│   │   ├── components/    # React components organized by feature
│   │   ├── pages/         # Page-level components
│   │   ├── common/        # Utilities, API client, types
│   │   └── hooks/         # Custom React hooks
├── backend/           # Python Quart API server
│   ├── app.py             # Main application entry point
│   ├── model/             # ML inference request functions
│   ├── storage/           # Data storage integration
│   └── tests/             # Backend test suite
└── datastore/         # Standalone datastore package
```

### Database Architecture

- **PostgreSQL** with two schemas:
  - `nachet_0.0.11`: Seed detection system (users, pictures, inferences, models)
  - `fertiscan_0.0.17`: Fertilizer analysis (inspections, labels, ingredients)
- **Hybrid storage**: Metadata in PostgreSQL, images in Azure Blob Storage
- **UUID-based**: All entities use UUIDs for secure multi-tenant isolation
- **Schema versioning**: Managed with Bytebase migration system

### ML Pipeline Architecture

- **Cloud-native**: All models hosted on external endpoints (Azure ML)
- **Pipeline-based**: Sequential chains of models (detection → classification)
- **Model types**: Object detection (seed-detector), Classification (Swin transformers), Ensemble models
- **No local inference**: All processing via HTTP API calls
- **Dynamic loading**: Pipeline configurations loaded from encrypted JSON files in Azure Blob

## Development Workflow

### Running the Application Locally

1. **Backend**: Set up environment variables in `.env` (copy from `.env.template`)
2. **Start backend**: `cd backend && hypercorn -b :8080 app:app`
3. **Start frontend**: `cd frontend && npm run dev`
4. **Access**: Frontend at <http://localhost:5173>, Backend at <http://localhost:8080>

### Testing

- **Frontend tests**: Use `npm run test` (Vitest + React Testing Library)
- **Backend tests**: Use `python -m unittest discover -s tests`
- **Manual testing**: See comprehensive test documentation in `frontend/TESTING.md` and `backend/TESTING.md`

### Environment Configuration

- **Frontend**: Uses environment files (`environment.ts`, `environment.staging.ts`, `environment.prod.ts`)
- **Backend**: Requires Azure Storage connection strings, database URLs, and ML endpoint configurations
- **Required variables**: `NACHET_AZURE_STORAGE_CONNECTION_STRING`, `NACHET_DATA`, various pipeline and model credentials

## Key Implementation Notes

### Data Flow

1. **Image capture/upload** → Frontend (React)
2. **Base64 encoding** → HTTP POST to backend
3. **Storage in Azure Blob** → Metadata to PostgreSQL
4. **ML pipeline execution** → External model endpoints
5. **Results processing** → Database storage → Frontend display

### Authentication & Security

- **Cookie-based authentication** with JWT tokens
- **Encrypted model credentials** using Fernet encryption
- **Multi-tenant isolation** via UUID-based user containers
- **API key authentication** for external ML services

### Frontend State Management

- **No global state library** (Redux/Zustand) - uses React state and context
- **API caching** with custom cache utilities
- **Real-time updates** through API polling for inference results

### Backend Error Handling

- **Custom exception hierarchy** for different error types
- **HTTP status code mapping** for API responses
- **Comprehensive logging** throughout the request pipeline

## Troubleshooting

### Common Issues

- **CORS errors**: Check backend CORS configuration in `app.py`
- **Image upload failures**: Verify Azure Storage connection string
- **ML inference errors**: Check model endpoint availability and API keys
- **Database connection issues**: Verify PostgreSQL credentials and schema setup
- **Build failures**: Ensure all dependencies are installed and environment variables set

### Debug Commands

```bash
# Check backend health
curl http://localhost:8080/health

# Verify frontend build
cd frontend && npm run build

# Test database connection
cd backend && python -c "from storage.datastore_storage_api import *"
```
