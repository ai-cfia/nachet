# Nachet Observability Stack

Simple Grafana observability stack for testing OTEL logging locally.

## Stack Components

- **Grafana Alloy** - Receives OTLP logs (gRPC/HTTP) and forwards to Loki
- **Loki** - Stores logs
- **Grafana** - Visualizes logs

## Quick Start

### 1. Start the stack

```bash
docker-compose -f docker-compose.yaml.local up -d loki alloy grafana
```

### 2. Start your backend

```bash
docker-compose -f docker-compose.yaml.local up -d nachet-backend
```

The backend is configured to send logs to Alloy via OTLP gRPC at `http://alloy:4317`

### 3. Access Grafana

Open http://localhost:12300 in your browser

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
# All logs
{service="nachet-backend"}

# Only errors
{service="nachet-backend"} |= "ERROR"

# Frontend errors
{service="nachet-backend", source="frontend"}

# Filter by correlation_id
{service="nachet-backend"} | json | correlation_id="abc-123"

# Filter by user
{service="nachet-backend"} | json | user_id="user@example.com"
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
OTEL_EXPORTER_ENDPOINT="http://alloy:4317"
LOG_LEVEL="INFO"                  # DEBUG, INFO, WARNING, ERROR
```

### Alloy Configuration

Edit `observability/alloy-config.yaml` to customize log processing.

## Troubleshooting

### Logs not appearing in Grafana

1. Check Alloy is receiving logs:
   - Visit <http://localhost:12345> (Alloy UI)
   - Check for incoming OTLP traffic

2. Check Loki is receiving logs:

   ```bash
   curl http://localhost:12310/ready
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

- `service`: Always "nachet-backend"
- `correlation_id`: Request tracking ID
- `session_id`: User session ID
- `user_id`: Authenticated user ID
- `source`: "frontend" for frontend logs, null for backend
- `level`: Log level (INFO, ERROR, WARNING)
- `method`: HTTP method
- `path`: Request path
- `status_code`: HTTP status
- `duration_ms`: Request duration

## Example Grafana Dashboards

### Request Duration

```logql
avg(rate({service="nachet-backend"} | json | duration_ms > 0 [5m]))
```

### Error Rate

```logql
sum(rate({service="nachet-backend"} |= "ERROR" [5m]))
```

### Requests by Path

```logql
sum by (path) (rate({service="nachet-backend"} | json [5m]))
```
