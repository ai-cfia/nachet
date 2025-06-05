# Monorepo GitHub Actions Workflow Migration Plan

## Current State Analysis

### Repository Structure
- **Root**: Contains basic repo standards and markdown checking workflows
- **Backend**: Python Flask application with Docker containerization workflows
- **Frontend**: React application with Node.js workflows and container builds
- **Datastore**: Python package with sophisticated CI/CD including version bumping and package publishing

### Existing Workflows Overview

#### Root Level (`.github/workflows/`)
- `workflows.yml`: Basic markdown and repo standards validation

#### Backend (`.github/workflows/`)
- `workflows.yml`: Python linting, testing, coverage, Docker build/push to GHCR
- `project-issue-status.yml`: Project management automation

#### Frontend (`.github/workflows/`)
- `react-frontend-workflows.yml`: Node.js linting, testing, container build/push
- `project-issue-status.yml`: Project management automation

#### Datastore (`.github/workflows/`)
- `workflows.yml`: Complex workflow with file change detection, version bumping for multiple packages
- `publish-package.yml`: Package publishing to PyPI
- `project-issue-status.yml`: Project management automation

## Phase 1: Consolidate Workflows to Root Level

### 1.1 Create Path-Based Workflow Triggers
Move all workflows to root `.github/workflows/` and implement path-based triggers using:
```yaml
on:
  pull_request:
    paths:
      - 'backend/**'
      - 'datastore/**'  # Since backend depends on datastore
```

### 1.2 Backend Workflow Migration
**New file**: `.github/workflows/backend-ci.yml`

**Triggers**: 
- Changes in `backend/**`
- Changes in `datastore/**` (dependency)

**Jobs**:
- Python linting and testing (using existing `workflow-lint-test-python.yml`)
- Docker build and push to GHCR
- Integration with datastore changes

### 1.3 Frontend Workflow Migration  
**New file**: `.github/workflows/frontend-ci.yml`

**Triggers**:
- Changes in `frontend/**`

**Jobs**:
- Node.js linting and testing
- Docker build and push to GHCR

### 1.4 Datastore Workflow Enhancement
**New file**: `.github/workflows/datastore-ci.yml`

**Triggers**:
- Changes in `datastore/**`

**Jobs**:
- All existing datastore workflows
- Trigger backend builds when datastore changes (since backend depends on it)

## Phase 2: Implement Cross-Service Dependencies

### 2.1 Backend-Datastore Dependency Management
- When datastore changes, automatically trigger backend CI
- Implement workflow dependencies using `workflow_run` events
- Consider package version compatibility checks

### 2.2 Workflow Orchestration
**New file**: `.github/workflows/monorepo-orchestrator.yml`
- Detect which services have changed
- Trigger appropriate downstream builds
- Handle cross-service dependencies

## Phase 3: Optimization and Enhancement

### 3.1 Conditional Job Execution
Implement smart job execution that only runs relevant tests:
- Use `tj-actions/changed-files` (already used in datastore)
- Skip unnecessary jobs when changes don't affect specific services

### 3.2 Parallel Execution Strategy
- Run independent service builds in parallel
- Sequence dependent builds (datastore → backend)

### 3.3 Caching Strategy
- Implement dependency caching for faster builds
- Docker layer caching for container builds
- Python package caching for backend/datastore

## Phase 4: Migration Execution Plan

### Step 1: Create New Root-Level Workflows
1. Create `backend-ci.yml` with path-based triggers
2. Create `frontend-ci.yml` with path-based triggers  
3. Create `datastore-ci.yml` with enhanced triggering
4. Test all workflows with sample PRs

### Step 2: Update Existing Root Workflow
1. Enhance `workflows.yml` to be monorepo-aware
2. Add path-based triggering for repo standards
3. Consolidate project issue status workflows

### Step 3: Validation Phase
1. Create test PRs for each service
2. Verify correct workflow triggering
3. Validate cross-service dependency handling
4. Check Docker builds are working correctly

### Step 4: Cleanup
1. Remove old workflow files from subdirectories
2. Update documentation in each service
3. Update README files to reflect monorepo structure

## Implementation Priority

### High Priority (Immediate)
1. **Backend workflow migration** - Core requirement
2. **Datastore-Backend dependency handling** - Critical for backend functionality
3. **Path-based triggering implementation** - Foundation for monorepo CI

### Medium Priority 
1. Frontend workflow migration
2. Workflow orchestration optimization
3. Advanced caching strategies

### Low Priority
1. Advanced cross-service integration testing
2. Performance optimizations
3. Documentation updates

## Key Technical Considerations

### Dockerfile Context Issues
- Root-level workflows will need to handle Docker builds with correct context paths
- Update Dockerfile paths and build contexts for monorepo structure

### Package Dependencies
- Backend imports from datastore - ensure proper package installation in CI
- Consider using local package installation during CI builds

### Environment Variables and Secrets
- Consolidate secrets management at root level
- Ensure service-specific environment variables are properly scoped

### Testing Strategy
- Maintain existing test coverage
- Add integration tests for cross-service functionality
- Consider end-to-end testing across services

## Success Criteria

1. ✅ Backend builds trigger on backend/ changes
2. ✅ Backend builds trigger on datastore/ changes (dependency)
3. ✅ No duplicate or unnecessary workflow runs
4. ✅ All existing functionality preserved
5. ✅ Build times remain reasonable
6. ✅ Container builds succeed from monorepo context
7. ✅ Package publishing still works for datastore

## Risk Mitigation

1. **Gradual Migration**: Implement alongside existing workflows initially
2. **Rollback Plan**: Keep original workflows as backup during testing
3. **Comprehensive Testing**: Test all scenarios before removing old workflows
4. **Documentation**: Document all changes and new workflow behavior
