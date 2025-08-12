# End-to-End Testing Strategy for Nachet

## Overview

This document outlines the design considerations for implementing end-to-end (E2E) testing in the Nachet project using GitHub Actions. The E2E tests will validate the complete user workflow from frontend interactions through backend processing to data persistence.

## Key Requirements & Constraints

### Trigger Conditions

- **Path-based triggering**: Only run E2E tests when changes are made to:
  - `frontend/**`
  - `backend/**`
  - `.github/workflows/end-to-end.yml`
- **PR events**: `opened`, `synchronize`
- **Push to main**: For integration validation

### Version Compatibility Strategy

#### Frontend Changes (PR modifying `frontend/**`)

- **Backend version**: Use compatible backend version specified in `frontend/package.json`

  ```json
  "acia-cfia": {
    "backend-version": "1.0.2"
  }
  ```

- **Backend image**: `ghcr.io/ai-cfia/nachet-backend:<backend-version-from-package.json>`
- **Frontend code**: Use current PR branch code (build from source)

#### Backend Changes (PR modifying `backend/**`)

- **Frontend version**: Use latest stable frontend image
- **Frontend image**: `ghcr.io/ai-cfia/nachet-frontend:latest`
- **Backend code**: Use current PR branch code (build from source)

#### Mixed Changes (both `frontend/**` and `backend/**`)

- **Strategy**: Build both from current PR branch source
- **Rationale**: Ensures compatibility of simultaneous changes

## Infrastructure Architecture

### Service Orchestration

```yaml
Services:
  - postgresql:15        # Database with health checks
  - azurite:3.34.0      # Azure blob storage emulator
  - backend-service     # API server (conditional: image vs build)
  - frontend-service    # React app server (conditional: image vs build)

Network: Docker bridge network for inter-service communication
Ports: 
  - PostgreSQL: 5432
  - Azurite: 10000 
  - Backend: 8080
  - Frontend: 5173
```

### Database Setup (Reuse from backend-tests.yml)

- **PostgreSQL 13** with health checks
- **Schema creation**: Dynamic versioning from `pyproject.toml`
- **Test data**: Load from existing SQL files in datastore
- **Environment**: Isolated test database per workflow run

### Blob Storage (Reuse from backend-tests.yml)

- **Azurite emulator**: Local Azure blob storage compatible service
- **Configuration**: Match production blob storage structure
- **Test data**: Sample images for upload/processing tests

## Test Execution Strategy

### Playwright Configuration

- **Browser**: Chromium (fast, consistent)
- **Base URL**: `http://localhost:5173` (frontend service)
- **Timeout**: 30s per test, 10min total workflow
- **Retry**: 2 retries for flaky network/timing issues
- **Screenshots**: On failure for debugging

### Test Architecture: Playwright UI + SQL Verification

**Testing Strategy**: Use Playwright for user interactions and direct SQL queries for state verification. This hybrid approach provides comprehensive validation of the complete data flow from UI through API to database persistence.

**Advantages:**

- **True E2E validation**: Tests real user workflows with actual database persistence
- **Robust verification**: SQL queries catch data corruption, caching issues, and constraint violations
- **Debugging power**: Direct database inspection provides precise failure analysis
- **Perfect for Nachet**: UUID-based entities and async ML pipeline require database state verification

### Critical Test Scenarios

1. **Authentication Flow**
   - **UI**: Playwright login/logout actions
   - **Verification**: SQL queries to validate session creation, user state, permissions

   ```sql
   SELECT * FROM "nachet_0.0.12".users WHERE email = 'test-user@example.com';
   ```

2. **Image Upload & Processing**
   - **UI**: Playwright file upload through frontend
   - **Verification**: SQL confirms database metadata creation

   ```sql
   SELECT ps.id, ps.name, ps.upload_date 
   FROM "nachet_0.0.12".picture_set ps
   WHERE ps.owner_id = 'test-user-uuid';
   ```

   - **Blob verification**: Azurite storage API checks

3. **ML Pipeline Integration**
   - **UI**: Playwright triggers inference request
   - **Verification**: SQL tracks async processing state transitions

   ```sql
   SELECT status, created_date, inference_dict 
   FROM "nachet_0.0.12".inference
   WHERE picture_set_id = 'uploaded-image-uuid'
   ORDER BY created_date;
   ```

4. **Multi-tenant Data Isolation**
   - **UI**: Multiple user sessions via Playwright
   - **Verification**: SQL ensures proper data separation

   ```sql
   SELECT COUNT(*) FROM "nachet_0.0.12".picture_set ps
   JOIN "nachet_0.0.12".users u ON ps.owner_id = u.id
   WHERE u.email != 'current-test-user@example.com'
   AND ps.id IN (SELECT visible_pictures_for_user);
   ```

5. **Error Handling**
   - **UI**: Playwright simulates invalid uploads, network failures
   - **Verification**: SQL confirms no orphaned data, proper rollbacks

## Implementation Details

### Database Integration in Playwright

**PostgreSQL Connection Setup:**

- Use `pg` npm package in Playwright test setup
- Connect directly to test database using same connection string as GitHub Actions services
- Execute SQL queries from test runner for verification

**Test Pattern:**

```javascript
// Setup: Clean database state
await db.query('DELETE FROM "nachet_0.0.12".picture_set WHERE owner_id = $1', [testUserId]);

// Action: Playwright UI interaction
await page.click('input[type="file"]');
await page.setInputFiles('test-image.png');
await page.click('button[data-testid="upload-button"]');

// Verification: SQL confirms database changes
const result = await db.query(`
  SELECT ps.id, ps.name, ps.upload_date 
  FROM "nachet_0.0.12".picture_set ps 
  WHERE ps.owner_id = $1
`, [testUserId]);
expect(result.rows).toHaveLength(1);

// Cleanup: SQL removes test data
await db.query('DELETE FROM "nachet_0.0.12".picture_set WHERE owner_id = $1', [testUserId]);
```

### Environment Variables

Reuse most variables from `backend-tests.yml`:

- Database connection strings for SQL verification
- Azure storage emulator config
- ML pipeline mocks
- Test-specific configurations
- Schema versioning for dynamic table names

### Service Health Checks

```yaml
Backend: GET /health endpoint
Frontend: Static file serving check  
PostgreSQL: pg_isready command
Azurite: HTTP ping to blob service
```

### Build Optimization

- **Conditional builds**: Only build services that changed
- **Image caching**: Leverage GitHub Actions cache
- **Parallel execution**: Build services concurrently where possible

## Workflow Structure

```yaml
name: End-to-End Tests
on:
  pull_request:
    paths: ['frontend/**', 'backend/**', '.github/workflows/end-to-end.yml']
  push:
    branches: [main]
    paths: ['frontend/**', 'backend/**']

jobs:
  e2e-test:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    
    services:
      postgres: # Reuse from backend-tests.yml
      azurite:  # Reuse from backend-tests.yml
    
    steps:
      - setup-services
      - determine-build-strategy  # Frontend PR vs Backend PR vs Mixed
      - build-or-pull-images
      - start-application-stack
      - wait-for-health-checks
      - run-playwright-tests
      - collect-artifacts
      - cleanup
```

## Security Considerations

### Secrets Management

- Reuse existing secrets from `backend-tests.yml`
- Test environment isolation
- No production credentials in test workflows

### Network Security  

- Isolated docker network
- No external network access during tests
- Mock external ML endpoints

## Monitoring & Debugging

### Artifacts Collection

- Playwright test reports
- Screenshots on failure
- Service logs (backend, frontend)
- Database query logs

### Performance Monitoring

- Test execution timing
- Service startup times
- Resource usage metrics

## Future Enhancements

### Scalability

- Parallel test execution across browsers
- Test sharding for large test suites
- Matrix testing across different configurations

### Integration Points

- Visual regression testing
- Accessibility testing integration
- Performance testing with Lighthouse

## Dependencies

### Required GitHub Secrets

- All secrets from `backend-tests.yml`
- Additional secrets for image registry access if needed

### External Dependencies

- GitHub Container Registry (GHCR) for images
- Node.js and Python ecosystems
- PostgreSQL and Azurite services

This strategy ensures robust E2E testing while maintaining compatibility between frontend and backend versions through intelligent build strategies based on the nature of changes in each pull request.
