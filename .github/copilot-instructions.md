# Nachet AI Seed Identification System

Canadian government (CFIA) AI-powered seed identification system with React TypeScript frontend and Python Quart backend.

**ALWAYS follow these instructions first and fallback to additional search and context gathering only if the information here is incomplete or found to be in error.**

## Working Effectively

### Bootstrap and Build Repository
Run these commands in sequence to set up a working development environment:

**Install Node.js and npm (if needed):**
```bash
# Check current versions
node --version && npm --version

# Download and install Node.js 24.5.0 if needed (preferred version)
wget https://nodejs.org/dist/v24.5.0/node-v24.5.0-linux-x64.tar.xz
tar -xf node-v24.5.0-linux-x64.tar.xz
sudo cp -r node-v24.5.0-linux-x64/* /usr/local/
```

**Install uv (Python package manager):**
```bash
pip install uv
```

**Build Frontend:**
```bash
cd frontend/
npm config set strict-ssl false  # Only if SSL certificate issues occur
npm install                     # Takes ~60 seconds. NEVER CANCEL. Set timeout to 120+ seconds.
npm run lint                    # Takes ~15 seconds  
npm run build                   # Takes ~40 seconds. NEVER CANCEL. Set timeout to 90+ seconds.
npm run test                    # Takes ~15 seconds. All 241 tests should pass.
```

**Build Backend:**
```bash
cd backend/
uv sync                         # Takes ~10 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
uv run python -c "import app.main; print('Backend ready')"  # Validate import
```

**Build Datastore:**
```bash
cd datastore/
uv sync                         # Takes ~5 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
uv run python -c "import datastore; print('Datastore ready')"  # Validate import
```

### Run Applications

**Frontend Development Server:**
```bash
cd frontend/
npm run dev                     # Starts on http://localhost:5173
```

**Backend Development Server:**
```bash
cd backend/
# Requires environment setup - see Environment Configuration section
uv run hypercorn -b :8080 app.main:app  # Starts on http://localhost:8080
```

**Full Stack with Docker:**
```bash
# Start database and storage services
docker compose up -d nachet-db nachet-pgadmin nachet-blob

# Start all services (requires environment configuration)
docker compose up -d
```

## Validation

**ALWAYS manually validate code changes by running these scenarios:**

1. **Build Validation:**
   ```bash
   cd frontend/ && npm run build && npm run test
   cd ../backend/ && uv run python -c "import app.main"
   cd ../datastore/ && uv run python -c "import datastore"
   ```

2. **Lint and Format Before Committing:**
   ```bash
   cd frontend/ && npm run lint && npm run format:check
   # Backend uses pytest for validation when environment is configured
   ```

3. **End-to-End Testing (when backend is running):**
   ```bash
   npm run test:e2e  # Takes ~10 minutes. NEVER CANCEL. Set timeout to 20+ minutes.
   ```

**Critical Build Timings - NEVER CANCEL:**
- Frontend npm install: 60 seconds (timeout: 120+ seconds)
- Frontend build: 40 seconds (timeout: 90+ seconds)  
- Backend tests: 15 minutes (timeout: 30+ minutes)
- E2E tests: 10 minutes (timeout: 20+ minutes)

## Environment Configuration

**Required for Runtime (not basic builds):**

Create `.env` files from templates:
```bash
# Backend environment
cd backend/
cp .env.template .env.local
# Edit .env.local with Azure Storage, Database, and ML endpoint credentials

# Frontend environment  
cd frontend/
cp .env.template .env.config.local
# Edit with backend URL and environment settings

# Database setup
cd db/
cp .env.config.template .env.config.local
# Edit with PostgreSQL credentials
```

**Minimal environment for basic functionality:**
```bash
export NACHET_ENV=local
export NACHET_FRONTEND_DEV_URL=http://localhost:5173
export BACKEND_DEV_PORT=5174
export FRONTEND_DEV_PORT=5173
```

## Common Issues and Workarounds

**Node.js Version Mismatch:**
- Package requires Node.js ^24.5.0 and npm ^11.5.2
- Current system may have older versions
- **Workaround:** Builds work with warnings on Node.js 20.x and npm 10.x

**npm SSL Certificate Issues:**
```bash
npm config set strict-ssl false
npm config set registry http://registry.npmjs.org/
```

**uv Installation Issues:**
```bash
# If curl fails to reach astral.sh, use pip instead
pip install uv
```

**Docker Permission Issues:**
```bash
sudo usermod -a -G docker $USER
# Logout and login again
```

## Key Projects and Navigation

**Frontend (`frontend/`):**
- `src/components/` - React components by feature
- `src/pages/` - Page-level components  
- `src/common/` - Utilities, API client, types
- `src/hooks/` - Custom React hooks
- Main entry: `src/main.tsx`

**Backend (`backend/`):**
- `app/main.py` - FastAPI application entry point
- `model/` - ML inference request functions
- `storage/` - Data storage integration
- `tests/` - Backend test suite
- `auth/` - Authentication and authorization

**Datastore (`datastore/`):**
- `datastore/` - Core data management package
- `nachet/db/` - Database schemas and migrations
- `tests/` - Datastore test suite

**Database Management:**
- Schema versions managed in `datastore/nachet/db/bytebase/`
- Current schema: `nachet_0.0.12`
- Setup script: `db/dev_setup.sh`

## Architecture Notes

- **No local ML processing** - All inference via HTTP endpoints
- **UUID-based entities** for multi-tenant isolation  
- **Azure Blob Storage** for images, PostgreSQL for metadata
- **Cookie-based authentication** with JWT tokens
- **No global state management** - React state and context only

## Frequent Commands Reference

```bash
# Quick status check
cd frontend/ && npm run build && npm run test
cd ../backend/ && uv run python -c "import app.main"

# Full rebuild
cd frontend/ && rm -rf node_modules && npm install && npm run build
cd ../backend/ && uv sync
cd ../datastore/ && uv sync

# Development servers
cd frontend/ && npm run dev &
cd ../backend/ && uv run hypercorn -b :8080 app.main:app &

# Docker services only
docker compose up -d nachet-db nachet-pgadmin nachet-blob

# Check running services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Always build and exercise your changes before committing. The CI will fail if linting, building, or tests fail.**