# Nachet Observability Stack

Simple Grafana observability stack for testing OTEL logging locally.

## Stack Components

- **Grafana Alloy** - Receives OTLP logs (gRPC/HTTP) and forwards to Loki
- **Loki** - Stores logs
- **Grafana** - Visualizes logs

## Logging Modes

The Nachet backend supports two logging modes:

### 1. Full Observability Mode (Default)

Used by the FastAPI application with OTEL integration for structured logging to Grafana/Loki.

### 2. Console-Only Mode (Scripts)

For standalone scripts, CLI tools, or utilities that don't need OTEL overhead. This mode provides structured logging to console without requiring the full observability stack.

**Example usage in scripts:**

```python
from app.service import LogService

# Initialize console-only logging (no OTEL required)
LogService.setup_console_only_logging("INFO")
logger = LogService.get_logger()

# Use structured logging
logger.info("Processing data", record_count=100)
logger.error("Failed to process", error=str(e))
```

**Configuration:**

- Set `OTEL_ENABLED=false` in environment to disable OTEL for the main application
- The system gracefully degrades to console-only logging if OTEL setup fails

## Quick Start

### 1. Start the stack

```bash
docker-compose -f docker-compose.yaml.local up -d loki alloy grafana
```

### 2. Start your backend

```bash
docker-compose -f docker-compose.yaml.local up -d nachet-backend
```

The backend is configured to send logs to Alloy via OTLP gRPC at `http://alloy:4317` <!-- markdownlint-disable-line MD034 -->

### 3. Access Grafana

Open <http://localhost:12300> in your browser

- **Username**: admin
- **Password**: admin
- Loki datasource is pre-configured
- **"Nachet - Application Monitoring"** dashboard is auto-loaded

### 4. Access the Pre-loaded Dashboard

The **"Nachet - Application Monitoring"** dashboard is automatically available:

1. Click **Dashboards** (four squares icon) in the left sidebar
2. Select **"Nachet - Application Monitoring"**

The dashboard includes:

- 📊 Request Rate & Errors over time
- ⏱️ Response Time Distribution (p50, p95, max)
- 👥 Active Sessions counter
- 🔴 Total Errors (24h)
- 🧠 Total ML Inferences (24h)
- ✅ Success Rate percentage
- 🗺️ API Endpoint Heatmap
- 📋 Error Distribution by Type
- 📝 Error Logs viewer
- 🤖 ML Inference Performance
- 🔀 Frontend vs Backend Events
- 🔍 Trace by Correlation ID
- 👤 Session Activity logs

**Template Variables** (top of dashboard):

- **Correlation ID**: Filter all panels by a specific request
- **Session ID**: Filter by user session
- **User ID**: Filter by authenticated user

### 5. Explore Logs Manually

You can also explore logs directly:

1. Go to **Explore** (compass icon in left sidebar)
2. Select **Loki** datasource
3. Use LogQL queries to filter logs:

```logql
# All backend logs
{service_name="nachet-backend"}

# All frontend logs
{service_name="nachet-frontend"}

# All logs (both frontend and backend)
{service_name=~"nachet-.*"}

# Only errors
{service_name="nachet-backend"} |= "ERROR"

# Frontend errors
{service_name="nachet-frontend"} |= "ERROR"

# Filter by correlation_id
{service_name=~"nachet-.*"} | json | correlation_id="abc-123"

# Filter by user (across both services)
{service_name=~"nachet-.*"} | json | user_id="user@example.com"
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Grafana | 12300 | Web UI |
| Loki | 12310 | Loki API |
| Alloy (gRPC) | 12317 | OTLP gRPC receiver |
| Alloy (HTTP) | 12318 | OTLP HTTP receiver |
| Alloy UI | 12345 | Alloy web UI |

## Configuration

### Backend Environment Variables

Edit `backend/.env.container.local`:

```bash
OTEL_EXPORTER_PROTOCOL="grpc"    # or "http"
OTEL_EXPORTER_ENDPOINT="http://alloy:4317" <!-- markdownlint-disable-line MD034 -->
LOG_LEVEL="INFO"                  # DEBUG, INFO, WARNING, ERROR
```

### Alloy Configuration

Edit `observability/alloy-config.yaml` to customize log processing.

## Troubleshooting

### Logs not appearing in Grafana

1. Check Alloy is receiving logs:
   - Visit <http://localhost:12345> (Alloy UI) <!-- markdownlint-disable-line MD034 -->
   - Check for incoming OTLP traffic

2. Check Loki is receiving logs:

   ```bash
   curl http://localhost:12310/ready <!-- markdownlint-disable-line MD034 -->
   ```

3. Check backend logs:

   ```bash
   docker logs nachet-backend
   ```

### Clear all data

```bash
docker-compose -f docker-compose.yaml.local down
rm -rf observability/loki-data observability/grafana-data
docker-compose -f docker-compose.yaml.local up -d loki alloy grafana
```

## Log Structure

Logs include structured metadata:

- `service_name`: Service identifier (indexed label in Loki)
  - `"nachet-backend"` - Backend API logs
  - `"nachet-frontend"` - Frontend application logs
- `correlation_id`: Request tracking ID (UUIDv7 - time-ordered, sortable)
- `session_id`: User session ID (UUIDv7 - time-ordered, sortable)
- `user_id`: Authenticated user ID
- `source`: "frontend" for frontend logs, null for backend (legacy field)
- `level`: Log level (INFO, ERROR, WARNING)
- `method`: HTTP method (backend logs only)
- `path`: Request path (backend logs only)
- `status_code`: HTTP status (backend logs only)
- `duration_ms`: Request duration (backend logs only)
- `remote_addr`: Client IP address (backend logs only)

**Frontend-specific fields:**

- `url`: Browser URL where log originated
- `user_agent`: Browser user agent
- `error_type`: JavaScript error type
- `stack_trace`: JavaScript stack trace

**Note:** Both `correlation_id` and `session_id` use UUIDv7 format for time-ordered tracing and better database performance.

## Example Grafana Dashboards

### Backend Request Duration

```logql
avg(rate({service_name="nachet-backend"} | json | duration_ms > 0 [5m]))
```

### Backend Error Rate

```logql
sum(rate({service_name="nachet-backend"} |= "ERROR" [5m]))
```

### Frontend Error Rate

```logql
sum(rate({service_name="nachet-frontend"} |= "ERROR" [5m]))
```

### Backend Requests by Path

```logql
sum by (path) (rate({service_name="nachet-backend"} | json [5m]))
```

### Frontend Errors by Type

```logql
sum by (error_type) (count_over_time({service_name="nachet-frontend"} |= "ERROR" | json [1h]))
```
