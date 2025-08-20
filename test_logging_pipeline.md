# Test Plan for Logging Pipeline

## Backend Tests

### 1. Test Correlation ID Middleware
```bash
# Start the backend server
cd backend
uv run hypercorn -b :8080 app:app

# In another terminal, test with curl
curl -X GET http://localhost:8080/health -H "X-Correlation-ID: test-123" -v
# Should return X-Correlation-ID header in response
```

### 2. Test Frontend Error Logging Endpoint
```bash
# Send a test error log
curl -X POST http://localhost:8080/api/logs \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-456" \
  -H "X-Session-ID: session-789" \
  -d '{
    "level": "ERROR",
    "message": "Test error from frontend",
    "error_type": "TestError",
    "stack_trace": "Error at line 1",
    "url": "http://localhost:5173/test"
  }'
```

### 3. Check Backend Logs
- Verify correlation IDs appear in logs
- Verify request/response logging
- Verify error logging with stack traces

## Frontend Tests

### 1. Test Error Logger Service
```javascript
// In browser console after starting frontend
errorLogger.logError('Test error', new Error('Test'));
// Check Network tab for POST to /api/logs
// Check correlation ID in headers
```

### 2. Test Error Boundary
```javascript
// Trigger an error in a component
// Verify error is caught and logged
// Check error boundary UI appears
```

### 3. Test API Error Handling
```javascript
// Make a failing API call
// Verify error is logged with correlation ID
// Check backend receives the error log
```

## End-to-End Test Flow

1. Start backend: `cd backend && uv run hypercorn -b :8080 app:app`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser to http://localhost:5173
4. Open browser DevTools (Network and Console tabs)
5. Perform actions that trigger API calls
6. Check for:
   - X-Correlation-ID headers in requests/responses
   - X-Session-ID headers in requests
   - Errors logged to backend via /api/logs
   - Correlation IDs matching between frontend and backend logs

## Monitoring Integration

For production with Grafana/Loki:
1. Verify OTEL environment variables are set
2. Check logs are being sent to Alloy/Loki
3. Query Loki for correlation IDs
4. Verify Grafana dashboard shows:
   - Active user sessions
   - Error rates
   - Request/response times
   - Frontend vs backend errors

## Success Criteria

✅ Correlation IDs propagate from frontend to backend
✅ All errors are logged with correlation IDs
✅ Frontend errors are sent to backend /api/logs endpoint
✅ Session IDs track user sessions
✅ Logs include structured data (service, user_id, etc.)
✅ Error boundary catches React errors
✅ API errors are logged with details
✅ Backend middleware logs all requests/responses