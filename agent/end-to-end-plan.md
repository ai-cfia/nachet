# End-to-End Testing Workflow Update Plan

## Executive Summary

This document outlines a comprehensive plan to update the GitHub workflow for end-to-end testing with intelligent version selection based on code changes. The approach ensures proper compatibility testing between frontend and backend components while optimizing CI/CD resource usage.

## Current State Analysis

### Existing Workflow Status

- **Current workflow**: `.github/workflows/end-to-end.yml`
- **Scope**: Backend-only testing (despite triggering on frontend changes)
- **Triggers**: Changes to `backend/**` or `frontend/**` paths
- **Environment**: PostgreSQL + Azurite blob storage emulator
- **Test suite**: Backend pytest suite only

### Repository Versioning Structure

- **Frontend tags**: `nachet-frontend-v0.9.29` (latest), pattern: `nachet-frontend-v{semver}`
- **Backend tags**: `nachet-backend-v1.0.2` (latest), pattern: `nachet-backend-v{semver}`
- **Datastore tags**: `v1.1.0-nachet-datastore` (separate versioning)
- **Package.json metadata**: Frontend tracks compatible backend version (`acia-cfia.backend-version: "1.0.2"`)

## Proposed Approach Evaluation

### User's Original Proposal

1. **Backend-only changes** → Use current backend + highest tagged frontend
2. **Frontend-only changes** → Use current frontend + highest tagged backend  
3. **Both changed** → Use current codebase for both

### Critical Issues Identified

#### 1. **API Compatibility Gaps**

- **Risk**: Latest tagged versions may not be compatible with current development
- **Example**: Current backend v1.0.3-dev might use new API endpoints not present in frontend v0.9.29
- **Impact**: False negatives (tests fail due to version mismatch, not code issues)

#### 2. **Database Schema Dependencies**

- **Current schema**: `nachet_0.0.12` (from pyproject.toml)
- **Problem**: Tagged versions may expect different schema versions
- **Risk**: Database migration mismatches causing test failures

#### 3. **Environment Configuration Drift**

- **Issue**: Tagged versions may have different environment variable requirements
- **Example**: New authentication flow in current backend incompatible with older frontend
- **Result**: Configuration-related test failures

#### 4. **Missing Frontend E2E Testing**

- **Gap**: Current workflow only tests backend, doesn't verify UI functionality
- **Problem**: Frontend changes can't be properly validated in end-to-end scenarios

#### 5. **Dependency Version Conflicts**

- **Risk**: Different Node.js/Python version requirements between releases
- **Example**: Frontend v0.9.29 requires Node 22.x, current requires Node 24.x
- **Impact**: Build failures or runtime incompatibilities

## Alternative Approaches

### Option A: Matrix Testing (Recommended)

```yaml
strategy:
  matrix:
    include:
      - name: "Current Development"
        frontend_ref: ${{ github.ref }}
        backend_ref: ${{ github.ref }}
      - name: "Backend changes with stable frontend"
        frontend_ref: refs/tags/nachet-frontend-v0.9.29
        backend_ref: ${{ github.ref }}
        condition: backend_changed && !frontend_changed
      - name: "Frontend changes with stable backend"  
        frontend_ref: ${{ github.ref }}
        backend_ref: refs/tags/nachet-backend-v1.0.2
        condition: frontend_changed && !backend_changed
```

**Advantages:**

- Tests all relevant combinations
- Catches compatibility regressions early
- Validates current development state
- Provides fallback testing scenarios

**Disadvantages:**

- Higher CI resource usage
- Longer workflow execution time
- More complex configuration

### Option B: Compatibility Metadata Approach

Use `package.json` metadata (`acia-cfia.backend-version`) to determine compatible versions.

```yaml
- name: Determine compatible versions
  run: |
    if [[ "$FRONTEND_CHANGED" == "true" && "$BACKEND_CHANGED" == "false" ]]; then
      COMPATIBLE_BACKEND=$(jq -r '.["acia-cfia"]["backend-version"]' frontend/package.json)
      echo "backend_version=nachet-backend-v${COMPATIBLE_BACKEND}" >> $GITHUB_OUTPUT
    fi
```

**Advantages:**

- Uses explicit compatibility declarations
- Reduces guesswork in version selection
- Maintains developer-defined compatibility matrix

**Disadvantages:**

- Requires manual maintenance of compatibility metadata
- Risk of stale metadata
- Additional metadata maintenance overhead

### Option C: Branch-Based Testing

Create dedicated integration branches for cross-version testing.

**Advantages:**

- Clear separation of testing concerns
- Allows manual validation before automation
- Reduces main workflow complexity

**Disadvantages:**

- Additional branch maintenance overhead
- Delays in feedback loop
- More complex developer workflow

### Option D: Incremental Rollback Testing

Test current + previous N versions to find compatibility boundaries.

**Advantages:**

- Discovers compatibility break points
- Provides migration path validation
- Historical compatibility verification

**Disadvantages:**

- Exponential complexity growth
- Resource intensive
- Difficult to configure correctly

## Recommended Implementation Plan

### Phase 1: Enhanced Change Detection

```yaml
- name: Detect changes
  id: changes
  run: |
    echo "frontend_changed=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }} | grep -q '^frontend/' && echo true || echo false)" >> $GITHUB_OUTPUT
    echo "backend_changed=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }} | grep -q '^backend/' && echo true || echo false)" >> $GITHUB_OUTPUT
    echo "datastore_changed=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }} | grep -q '^datastore/' && echo true || echo false)" >> $GITHUB_OUTPUT
```

### Phase 2: Dynamic Version Resolution

```yaml
- name: Resolve test versions
  id: versions
  run: |
    LATEST_FRONTEND=$(git tag --sort=-version:refname | grep "nachet-frontend-v" | head -1)
    LATEST_BACKEND=$(git tag --sort=-version:refname | grep "nachet-backend-v" | head -1)
    
    if [[ "${{ steps.changes.outputs.frontend_changed }}" == "true" && "${{ steps.changes.outputs.backend_changed }}" == "false" ]]; then
      echo "frontend_ref=${{ github.ref }}" >> $GITHUB_OUTPUT  
      echo "backend_ref=refs/tags/${LATEST_BACKEND}" >> $GITHUB_OUTPUT
      echo "test_scenario=frontend-only" >> $GITHUB_OUTPUT
    elif [[ "${{ steps.changes.outputs.backend_changed }}" == "true" && "${{ steps.changes.outputs.frontend_changed }}" == "false" ]]; then
      echo "frontend_ref=refs/tags/${LATEST_FRONTEND}" >> $GITHUB_OUTPUT
      echo "backend_ref=${{ github.ref }}" >> $GITHUB_OUTPUT  
      echo "test_scenario=backend-only" >> $GITHUB_OUTPUT
    else
      echo "frontend_ref=${{ github.ref }}" >> $GITHUB_OUTPUT
      echo "backend_ref=${{ github.ref }}" >> $GITHUB_OUTPUT
      echo "test_scenario=full-development" >> $GITHUB_OUTPUT
    fi
```

### Phase 3: Multi-Component Checkout

```yaml
- name: Checkout frontend code
  uses: actions/checkout@v4
  with:
    ref: ${{ steps.versions.outputs.frontend_ref }}
    path: frontend-code

- name: Checkout backend code  
  uses: actions/checkout@v4
  with:
    ref: ${{ steps.versions.outputs.backend_ref }}
    path: backend-code
```

### Phase 4: True End-to-End Testing

```yaml
- name: Setup frontend
  working-directory: frontend-code
  run: |
    npm ci
    npm run build
    
- name: Start frontend server
  working-directory: frontend-code  
  run: |
    npm run preview &
    sleep 10
  
- name: Setup backend
  working-directory: backend-code
  run: |
    uv sync --dev
    
- name: Start backend server
  working-directory: backend-code
  run: |
    uv run hypercorn -b :8080 app:app &
    sleep 5

- name: Run end-to-end tests
  run: |
    # Frontend tests against live backend
    cd frontend-code && npm run test:e2e
    # Backend integration tests  
    cd backend-code && uv run pytest tests/
    # Cross-component API tests
    cd backend-code && uv run pytest tests/integration/
```

### Phase 5: Compatibility Validation

```yaml
- name: API compatibility check
  run: |
    # Test API endpoint availability
    curl -f http://localhost:8080/health
    curl -f http://localhost:8080/api/v1/inference
    
    # Test frontend can reach backend
    curl -f http://localhost:3000/
    
    # Validate authentication flow
    cd frontend-code && npm run test:auth-flow
```

## Implementation Considerations

### Database Schema Handling

```yaml
- name: Extract schema versions
  id: schema
  run: |
    FRONTEND_SCHEMA="0.0.12"  # Default or extract from compatible backend
    BACKEND_SCHEMA=$(cd backend-code && uv run python -c "import toml; print(toml.load('pyproject.toml')['tool']['nachet-db']['db-schema-version'])")
    
    if [[ "$FRONTEND_SCHEMA" != "$BACKEND_SCHEMA" ]]; then
      echo "::warning::Schema version mismatch: Frontend expects $FRONTEND_SCHEMA, Backend uses $BACKEND_SCHEMA"
      # Use backend schema version for testing
      echo "schema_version=$BACKEND_SCHEMA" >> $GITHUB_OUTPUT
    else
      echo "schema_version=$BACKEND_SCHEMA" >> $GITHUB_OUTPUT
    fi
```

### Environment Configuration Management

```yaml
- name: Setup unified environment
  run: |
    # Merge environment requirements from both components
    # Backend env vars
    cp backend-code/.env.template .env
    
    # Frontend-specific overrides
    echo "NACHET_FRONTEND_DEV_URL=http://localhost:3000" >> .env
    echo "NACHET_BACKEND_DEV_URL=http://localhost:8080" >> .env
    
    # Test-specific settings
    echo "TESTING=true" >> .env
    echo "E2E_TESTING=true" >> .env
```

### Dependency Resolution

```yaml
- name: Check version compatibility
  run: |
    FRONTEND_NODE_VERSION=$(cd frontend-code && node -pe "require('./package.json').engines.node")
    BACKEND_PYTHON_VERSION=$(cd backend-code && python -c "import toml; print(toml.load('pyproject.toml')['project']['requires-python'])")
    
    echo "Frontend requires Node.js: $FRONTEND_NODE_VERSION"
    echo "Backend requires Python: $BACKEND_PYTHON_VERSION"
    
    # Validate current environment meets requirements
    node --version
    python --version
```

## Risk Mitigation Strategies

### 1. Fallback Testing

If cross-version testing fails, fall back to current development testing:

```yaml
- name: Fallback to current development
  if: failure()
  run: |
    echo "Cross-version testing failed, running current development tests"
    # Run tests with current codebase
```

### 2. Compatibility Warnings

```yaml
- name: Compatibility assessment
  run: |
    if [[ "${{ steps.versions.outputs.test_scenario }}" != "full-development" ]]; then
      echo "::warning::Testing with mixed versions - validate compatibility manually"
      echo "Frontend: ${{ steps.versions.outputs.frontend_ref }}"  
      echo "Backend: ${{ steps.versions.outputs.backend_ref }}"
    fi
```

### 3. Test Result Interpretation

```yaml
- name: Analyze test results
  if: always()
  run: |
    if [[ "${{ job.status }}" == "failure" && "${{ steps.versions.outputs.test_scenario }}" != "full-development" ]]; then
      echo "::error::Mixed version testing failed - may indicate compatibility issues"
      echo "Consider updating compatibility metadata or running integration tests"
    fi
```

## Success Metrics

### Workflow Quality Indicators

- **Test Coverage**: Both frontend and backend functionality validated
- **Compatibility Detection**: Version mismatches caught early  
- **Resource Efficiency**: Minimal redundant testing
- **Developer Experience**: Clear failure reasons and remediation steps

### Monitoring and Alerts

- Track cross-version test success rates
- Monitor for compatibility regression patterns
- Alert on schema version mismatches
- Dashboard for version compatibility matrix

## Rollout Strategy

### Phase 1: Parallel Testing (2 weeks)

- Run new workflow alongside existing
- Compare results and identify gaps
- Refine version detection logic

### Phase 2: Limited Deployment (2 weeks)  

- Enable for non-main branches only
- Gather developer feedback
- Address performance concerns

### Phase 3: Full Deployment (1 week)

- Replace existing end-to-end workflow
- Monitor for issues
- Document new process

## Conclusion

The recommended matrix testing approach provides the most comprehensive validation while managing complexity through intelligent version selection. Key benefits include:

- **Robust compatibility testing** between frontend/backend versions
- **Early detection** of breaking changes across components  
- **Maintainable configuration** with clear fallback strategies
- **Developer-friendly** failure modes and debugging information

This approach transforms the current backend-only testing into true end-to-end validation while maintaining the efficiency goals of the original proposal.
