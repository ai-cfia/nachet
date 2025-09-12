# Nachet AI-Powered Seed Identification System

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

Nachet is a Canadian government (CFIA) AI-powered seed identification system consisting of a React TypeScript frontend, Python FastAPI backend, PostgreSQL database with Azure Blob Storage for images, and ML model endpoints.

## Working Effectively

### Prerequisites and Dependencies
**CRITICAL: Install these exact versions to avoid build failures:**

- **Node.js 24.5.0 and npm 11.5.2** (required for frontend):
  ```bash
  # Download and install Node.js 24.5.0 manually
  cd /tmp
  wget https://nodejs.org/dist/v24.5.0/node-v24.5.0-linux-x64.tar.gz
  tar -xzf node-v24.5.0-linux-x64.tar.gz
  sudo cp -r node-v24.5.0-linux-x64/* /usr/local/
  node --version  # Should show v24.5.0
  npm --version   # Should show 11.5.2
  ```

- **uv Python package manager** (required for backend/datastore):
  ```bash
  python3 -m pip install uv
  uv --version
  ```

- **Docker and Docker Compose** (for full stack):
  ```bash
  docker --version     # Should be 20.10+
  docker compose version  # Should be v2.0+
  ```

### Frontend Development (React + TypeScript + Vite)

**Bootstrap and build the frontend:**
```bash
cd frontend/
npm install  # Takes 40 seconds. NEVER CANCEL. Set timeout to 120+ seconds.
```

**Essential development commands:**
```bash
# Lint code (takes 13 seconds, NEVER CANCEL, timeout 60 seconds)
npm run lint

# Run tests (takes 7 seconds, 241 tests, NEVER CANCEL, timeout 30 seconds)  
npm run test

# Build for production (takes 25 seconds, NEVER CANCEL, timeout 90 seconds)
npm run build

# Start development server (starts in 200ms on port 5173)
npm run dev

# Format code
npm run format
npm run format:check
```

### Backend Development (Python + FastAPI + uv)

**Bootstrap and build the backend:**
```bash
cd backend/
uv sync  # Takes 4 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
```

**Essential development commands:**
```bash
# Run basic tests (takes 2 seconds, NEVER CANCEL, timeout 30 seconds)
uv run python -m pytest tests/ -v

# Start development server (requires environment setup, see below)
source .venv/bin/activate
hypercorn -b :12435 app.main:app
```

**Note:** Backend requires proper environment configuration in `.env.local` file before starting.

### Datastore Package (Python)

**Bootstrap the datastore:**
```bash
cd datastore/
uv sync  # Takes 1 second. NEVER CANCEL. Set timeout to 30+ seconds.
```

**Run tests (requires environment setup):**
```bash
# Set up test environment first
cp .env.test.template .env.test.local
# Edit .env.test.local with proper database credentials
./run_tests.sh  # Full test cycle with setup/cleanup
```

### Full Stack with Docker Compose

**CRITICAL: Set up environment files first (required for Docker Compose):**

1. **Database configuration:**
   ```bash
   cd db/
   cp .env.config.template .env.config.local
   # Edit with: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD
   ```

2. **Backend configuration:**
   ```bash
   cd backend/
   cp .env.template .env.local
   # Edit with database URL, Azure storage connection, and ML endpoint configurations
   ```

3. **Frontend configuration:**
   ```bash
   cd frontend/
   cp .env.template .env.config.local
   # Edit with backend URL (typically http://localhost:12435)
   ```

**Start the full stack (NEVER CANCEL these commands):**
```bash
# Start core services (takes 16 seconds, timeout 300 seconds)
docker compose -f docker-compose.yaml up -d nachet-db nachet-pgadmin nachet-blob

# Set up database schema (takes 0.5 seconds, timeout 60 seconds)
chmod +x db/dev_setup.sh
./db/dev_setup.sh 0.0.12 <db_name> <db_user> <db_password>

# Start ML mock services (takes 6 seconds, timeout 180 seconds)  
docker compose -f docker-compose.yaml up -d nachet-detector nachet-15spp-classifier nachet-27spp-classifier

# Start backend service (or run locally with hypercorn)
docker compose -f docker-compose.yaml up -d nachet-backend

# Check all services are running
docker ps --format "table {{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Service URLs when running:**
- Frontend: http://localhost:5173 (dev) or http://localhost:12436 (Docker)
- Backend: http://localhost:12435
- Database: localhost:12432
- PgAdmin: http://localhost:12433
- Blob Storage: http://localhost:12434

### End-to-End Testing

**Install and run E2E tests:**
```bash
# Install root dependencies (takes 1 second, timeout 60 seconds)
npm install

# Install Playwright browsers (may fail due to network issues - document this)
npx playwright install --with-deps  # Takes 5+ minutes, may fail, timeout 600 seconds

# Run E2E tests (requires full stack running, takes 5-15 minutes, timeout 1800 seconds)
npx playwright test --workers=1
```

## Validation

**ALWAYS manually validate functionality after making changes:**

### Frontend Validation Scenarios
1. **Start frontend and verify no console errors:**
   ```bash
   cd frontend/ && npm run dev
   # Visit http://localhost:5173 and check browser console
   ```

2. **Test image upload workflow:**
   - Upload an image file
   - Verify it appears in the interface
   - Check that backend connection warning (if any) is appropriate

3. **Test model selection:**
   - Open model selection popup
   - Verify available models are displayed
   - Test switching between models

### Backend Validation Scenarios  
1. **Test health endpoint:**
   ```bash
   curl http://localhost:12435/health
   # Should return 200 OK
   ```

2. **Verify database connection:**
   - Backend should start without connection errors
   - Check logs for successful database pool creation

### Full Stack Validation
1. **Complete image processing workflow:**
   - Upload image via frontend
   - Verify image is stored in blob storage
   - Check that ML inference is triggered
   - Verify results are returned and displayed

2. **Database operations:**
   - Verify images, inferences, and user data are stored correctly
   - Check that all required tables exist in schema

## Troubleshooting

### Common Issues and Solutions

**Frontend:**
- `Error: Engine mismatch` → Install exact Node.js 24.5.0 and npm 11.5.2
- `Build chunk size warnings` → Normal behavior, build still succeeds
- `npm audit vulnerabilities` → Non-blocking for development

**Backend:**
- `Connection refused errors` → Check database is running and environment variables are correct
- `NoAppError: Cannot load application` → Use `app.main:app` not `app:app`
- `Database connection errors` → Verify NACHET_DB_URL points to correct host:port

**Docker:**
- `pgadmin restarting` → Check PGADMIN_DEFAULT_EMAIL/PASSWORD are valid email format
- `Dockerfile.local not found` → Copy existing Dockerfile to Dockerfile.local for local builds
- `Port conflicts` → Ensure ports 12432, 12433, 12434, 12435, 12436 are available

**Environment Setup:**
- `Environment variables not loading` → Use proper shell source syntax and avoid special characters in values
- `Blob storage connection failed` → Use Azurite connection string for local development
- `.env.local missing` → Always copy from .env.template and fill required values

### Build/Test Timing Expectations
- **Frontend npm install:** 40 seconds (timeout: 120s)
- **Frontend lint:** 13 seconds (timeout: 60s)
- **Frontend test:** 7 seconds (timeout: 30s)  
- **Frontend build:** 25 seconds (timeout: 90s)
- **Backend uv sync:** 4 seconds (timeout: 60s)
- **Backend basic tests:** 2 seconds (timeout: 30s)
- **Docker core services:** 16 seconds (timeout: 300s)
- **Docker ML services:** 6 seconds (timeout: 180s)
- **Database schema setup:** 0.5 seconds (timeout: 60s)
- **E2E tests:** 5-15 minutes (timeout: 1800s)

### Validation Commands (Always Run Before Committing)
```bash
# Frontend validation
cd frontend/
npm run lint     # Must pass with 0 warnings
npm run test     # All 241 tests must pass
npm run build    # Must complete successfully

# Backend validation  
cd backend/
uv run python -m pytest tests/ -v  # Basic tests must pass

# Environment validation
docker ps  # All required services must be running and healthy
curl http://localhost:12435/health  # Backend health check
```

## Key Architecture Notes

### Project Structure
- **frontend/**: React TypeScript app with Vite, Material-UI, port 5173
- **backend/**: Python FastAPI with uv package management, port 12435  
- **datastore/**: Standalone Python package for data operations
- **db/**: PostgreSQL schema and development scripts
- **e2e/**: Playwright end-to-end tests and mock configurations

### Technology Stack
- **Frontend:** React 19 + TypeScript + Vite + Material-UI + Axios
- **Backend:** Python 3.11+ + FastAPI + uv + Hypercorn + SQLAlchemy  
- **Database:** PostgreSQL 15 with schema versioning (Bytebase)
- **Storage:** Azure Blob Storage (Azurite for local development)
- **ML:** External HTTP endpoints, no local model processing
- **Testing:** Vitest (frontend), pytest (backend), Playwright (E2E)

### Development Workflow
1. Always set up environment files before starting services
2. Use uv for Python package management (not pip)
3. Frontend and backend can run independently for development
4. Use Docker Compose for integration testing with full stack
5. Database schema is versioned and managed with migration scripts
6. ML models are mocked locally using Wiremock for testing

**NEVER CANCEL long-running commands.** Wait for completion and use the documented timeout values.