# Nachet AI Seed Identification System

Canadian government (CFIA) AI-powered seed identification system with React TypeScript frontend and Python Quart backend.

**ALWAYS follow these instructions first and fallback to additional search and context gathering only if the information here is incomplete or found to be in error.**

## Repository Structure and Focus

**Ignore these folders completely**:

- `datastore/` - Legacy data management code (not actively maintained)
- `backend/old/` - Legacy backend code (replaced by current backend)

**Local Development Container Infrastructure**:

- `db/` - PostgreSQL database container mounting and configuration (local development only)
- `blob/` - Azurite blob storage container mounting and configuration (local development only)

**Primary Work Areas**:
Focus your development work on: `frontend/`, `backend/` (excluding old/ subfolder), and root configuration files.

## Setup and Build Process

### Prerequisites

Install required tools for development:

**Node.js and npm setup:**

```bash
# Verify current versions
node --version && npm --version

# Install Node.js 24.5.0 if needed (recommended version)
wget https://nodejs.org/dist/v24.5.0/node-v24.5.0-linux-x64.tar.xz
tar -xf node-v24.5.0-linux-x64.tar.xz
sudo cp -r node-v24.5.0-linux-x64/* /usr/local/
```

**Python package manager:**

```bash
pip install uv
```

### Frontend Build Process

```bash
cd frontend/
npm config set strict-ssl false  # Only if SSL certificate issues occur
npm install                     # ~60 seconds. NEVER CANCEL. Set timeout to 120+ seconds.
npm run lint                    # ~15 seconds
npm run build                   # ~40 seconds. NEVER CANCEL. Set timeout to 90+ seconds.
npm run test                    # ~15 seconds. All 241 tests should pass.
```

### Backend Build Process

```bash
cd backend/
uv sync                         # ~10 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
uv run python -c "import app.main; print('Backend ready')"  # Validate setup
```

## Development Servers

**Frontend Development:**

```bash
cd frontend/
npm run dev                     # Starts on http://localhost:5173
```

**Backend Development:**

```bash
cd backend/
# Requires environment setup - see Environment Configuration section
uv run hypercorn -b :8080 app.main:app  # Starts on http://localhost:8080
```

**Docker Container Services:**

```bash
# Start PostgreSQL and Azurite containers (uses db/ and blob/ folder configurations)
docker compose up -d nachet-db nachet-pgadmin nachet-blob

# Start all services (requires full environment configuration)
docker compose up -d
```

## Code Validation and Testing

**Essential validation steps before committing:**

1. **Build Verification:**

   ```bash
   cd frontend/ && npm run build && npm run test
   cd ../backend/ && uv run python -c "import app.main"
   ```

2. **Code Quality Checks:**

   ```bash
   cd frontend/ && npm run lint && npm run format:check
   # Backend validation requires environment configuration
   ```

3. **End-to-End Testing:**
   ```bash
   npm run test:e2e  # ~10 minutes. NEVER CANCEL. Set timeout to 20+ minutes.
   ```

**Critical Timing Guidelines - NEVER CANCEL PREMATURELY:**

- Frontend npm install: 60 seconds (set timeout: 120+ seconds)
- Frontend build: 40 seconds (set timeout: 90+ seconds)
- Backend tests: 15 minutes (set timeout: 30+ minutes)
- E2E tests: 10 minutes (set timeout: 20+ minutes)

## Environment Configuration

**Runtime Configuration (required for backend/database operations):**

Environment template setup:

```bash
# Backend environment
cd backend/
cp .env.template .env.local
# Edit .env.local with Azure Storage, Database, and ML endpoint credentials

# Frontend environment
cd frontend/
cp .env.template .env.config.local
# Edit with backend URL and environment settings

# Database configuration (uses db/ folder for container mounting)
cd db/
cp .env.config.template .env.config.local
# Edit with PostgreSQL credentials for container setup
```

**Basic environment variables:**

```bash
export NACHET_ENV=local
export NACHET_FRONTEND_DEV_URL=http://localhost:5173
export BACKEND_DEV_PORT=5174
export FRONTEND_DEV_PORT=5173
```

## Troubleshooting Common Issues

**Node.js Version Compatibility:**

- Requires Node.js ^24.5.0 and npm ^11.5.2
- **Workaround:** Works with warnings on Node.js 20.x and npm 10.x

**Network and SSL Issues:**

```bash
npm config set strict-ssl false
npm config set registry http://registry.npmjs.org/
```

**Python Package Manager Issues:**

```bash
# Alternative if curl fails to reach astral.sh
pip install uv
```

**Docker Access Issues:**

```bash
sudo usermod -a -G docker $USER
# Logout and login to apply changes
```

## Codebase Navigation

**Frontend Structure (`frontend/`):**

- `src/components/` - React components organized by feature
- `src/pages/` - Top-level page components
- `src/common/` - Shared utilities, API client, and type definitions
- `src/hooks/` - Custom React hooks
- `src/main.tsx` - Application entry point

**Backend Structure (`backend/`):**

- `app/main.py` - FastAPI application entry point and configuration
- `model/` - Machine learning inference request handling
- `storage/` - Data storage layer integration (Azure Blob + PostgreSQL)
- `tests/` - Backend test suite
- `auth/` - Authentication and authorization logic
- **Important:** Skip the `old/` subfolder - contains deprecated code

**Container Infrastructure (Local Development):**

- `db/` - PostgreSQL database schema and container configuration for mounting
- `blob/` - Azurite blob storage container configuration for mounting
- These folders support local development via Docker container mounting only

## System Architecture

- **Machine Learning:** Remote inference via HTTP endpoints (no local ML processing)
- **Data Architecture:** Azure Blob Storage for images, PostgreSQL for metadata
- **Multi-tenancy:** UUID-based entity isolation
- **Authentication:** Cookie-based sessions with JWT tokens
- **State Management:** React state and context patterns (no global state store)

## Quick Reference Commands

```bash
# Development workflow validation
cd frontend/ && npm run build && npm run test
cd ../backend/ && uv run python -c "import app.main"

# Complete environment rebuild
cd frontend/ && rm -rf node_modules && npm install && npm run build
cd ../backend/ && uv sync

# Start development servers
cd frontend/ && npm run dev &
cd ../backend/ && uv run hypercorn -b :8080 app.main:app &

# Container services (uses db/ and blob/ configurations)
docker compose up -d nachet-db nachet-pgadmin nachet-blob

# Service status check
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Always validate your changes through build and test cycles before committing. CI pipeline failures indicate unresolved build, lint, or test issues.**
