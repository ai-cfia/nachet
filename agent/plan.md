# Monorepo GitHub Actions Workflow Migration Plan

## Current State Analysis

### Repository Structure
- **Root**: Contains basic repo standards and markdown checking workflows
- **Backend**: Python Quart application with Docker containerization workflows
- **Frontend**: React application with Node.js workflows and container builds
- **Datastore**: Python package with sophisticated CI/CD including version bumping and package publishing
  - **Note**: Currently publishes both `nachet-datastore` and `fertiscan-datastore` packages
  - **Future**: Will be simplified to only `nachet-datastore` after fertiscan removal

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

## Phase 1: Critical Immediate Fixes (BEFORE Migration)

### 1.1 Fix Current Broken Workflows
**CRITICAL**: Several workflow files need immediate fixes before migration can proceed:

1. **Backend Build Workflow is Empty**
   - File: `.github/workflows/backend-build.yml` 
   - Status: Completely empty - needs implementation

2. **Frontend Path References Invalid**
   - File: `.github/workflows/frontend-build.yml`
   - Issue: References non-existent `.github/workflows/frontend-ci.yml`
   - Fix: Update path to `.github/workflows/frontend-build.yml`

3. **Missing Backend Lint Workflow**
   - Current backend workflow includes lint+test+build
   - Need separate workflows or consolidation strategy

### 1.2 Implement Backend Workflows
**File**: `.github/workflows/backend-build.yml` (currently empty)
```yaml
name: Backend Build and Test
on:
  pull_request:
    paths:
      - 'backend/**'
      - 'datastore/**'  # Critical dependency
    types: [opened, closed, synchronize]

defaults:
  run:
    working-directory: backend

jobs:
  lint-test:
    uses: ai-cfia/github-workflows/.github/workflows/workflow-lint-test-python.yml@main
    with:
      working-directory: backend
    secrets: inherit
    
  build-push:
    uses: ai-cfia/github-workflows/.github/workflows/workflow-build-push-container-github-registry-mono.yml@main
    with:
      working-directory: backend
      container-name: ${{ github.event.repository.name }}-backend
      tag: ${{ github.sha }}
      registry: ghcr.io/ai-cfia
    secrets: inherit
```

## Phase 2: Consolidate Workflows to Root Level

### 2.1 Create Path-Based Workflow Triggers
Move all workflows to root `.github/workflows/` and implement path-based triggers using:
```yaml
on:
  pull_request:
    paths:
      - 'backend/**'
      - 'datastore/**'  # Since backend depends on datastore
```

### 2.2 Frontend Workflow Consolidation
**Current State**: `frontend-build.yml` exists but has incorrect path references
**Action**: Fix path references and ensure consistency

### 2.3 Datastore Workflow Strategy
**Current Complexity**: Handles dual-package publishing (nachet-datastore + fertiscan-datastore)
**Short-term**: Maintain existing dual-package support for workflow stability
**Long-term**: Simplify to nachet-datastore only after fertiscan removal

## Phase 3: Implement Cross-Service Dependencies

### 3.1 Backend-Datastore Dependency Management
- When datastore changes, automatically trigger backend CI
- Implement workflow dependencies using `workflow_run` events
- Consider package version compatibility checks

### 3.2 Workflow Orchestration
**New file**: `.github/workflows/monorepo-orchestrator.yml`
- Detect which services have changed
- Trigger appropriate downstream builds
- Handle cross-service dependencies

## Phase 4: Optimization and Enhancement

### 4.1 Conditional Job Execution
Implement smart job execution that only runs relevant tests:
- Use `tj-actions/changed-files` (already used in datastore)
- Skip unnecessary jobs when changes don't affect specific services

### 4.2 Parallel Execution Strategy
- Run independent service builds in parallel
- Sequence dependent builds (datastore → backend)

### 4.3 Caching Strategy
- Implement dependency caching for faster builds
- Docker layer caching for container builds
- Python package caching for backend/datastore

## IMMEDIATE ACTION PLAN (Priority Order)

### Step 1: Fix Critical Broken Workflows (URGENT)
**Timeline**: Complete within 24 hours for basic CI/CD functionality

1. **Implement Backend Build Workflow**
   ```bash
   # File: .github/workflows/backend-build.yml
   # Status: Currently empty - implement using template above
   ```

2. **Fix Frontend Path References**
   ```yaml
   # In .github/workflows/frontend-build.yml, fix line 7:
   - '.github/workflows/frontend-ci.yml'  # WRONG - doesn't exist
   + '.github/workflows/frontend-build.yml'  # CORRECT
   ```

3. **Create Backend Lint Workflow**
   ```bash
   # File: .github/workflows/backend-lint.yml
   # Status: Missing - needed for separation of concerns
   ```

### Step 2: Test Current Workflow Functionality
1. Create test PRs for each service
2. Verify path-based triggering works
3. Validate container builds succeed
4. Check all workflows execute without errors

### Step 3: Gradual Migration (Post-Basic Functionality)
1. Enhance existing workflows with better path targeting
2. Implement cross-service dependency handling
3. Add workflow orchestration for complex scenarios
4. Optimize for performance and caching

### Step 4: Long-term Cleanup (Future Phases)
1. Remove fertiscan-datastore package publishing after fertiscan removal
2. Simplify datastore workflows to nachet-only
3. Remove old workflow files from subdirectories
4. Update documentation to reflect monorepo structure

## Updated Implementation Priority

### CRITICAL (Fix Immediately - Deployment Blocker)
1. **Fix empty backend-build.yml** - Currently prevents any backend CI/CD
2. **Fix frontend path references** - Currently causes workflow failures  
3. **Test basic functionality** - Ensure workflows execute successfully

### High Priority (Immediate - This Week)
1. **Backend workflow implementation** - Core deployment requirement
2. **Datastore-Backend dependency handling** - Critical for backend functionality
3. **Path-based triggering validation** - Foundation for monorepo CI
4. **Container build verification** - Ensure Docker builds work from monorepo context

### Medium Priority (Next Phase)
1. **Frontend workflow consolidation** - Already partially working
2. **Workflow orchestration optimization** - Performance improvements
3. **Advanced caching strategies** - Build speed optimization

### Low Priority (Future - Post Deployment)
1. **Fertiscan removal from datastore** - Technical debt cleanup
2. **Advanced cross-service integration testing** - Enhanced validation
3. **Performance optimizations** - Nice-to-have improvements
4. **Documentation updates** - Reflect final monorepo structure

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

### Phase 1 Success (Critical for Deployment)
1. ✅ Backend-build.yml workflow implemented and functional
2. ✅ Frontend path references fixed and workflows execute
3. ✅ All workflows trigger correctly on relevant path changes
4. ✅ Container builds succeed from monorepo context
5. ✅ No workflow execution failures on test PRs

### Phase 2 Success (Full Monorepo CI/CD)
1. ✅ Backend builds trigger on backend/ changes
2. ✅ Backend builds trigger on datastore/ changes (dependency)
3. ✅ No duplicate or unnecessary workflow runs
4. ✅ All existing functionality preserved
5. ✅ Build times remain reasonable
6. ✅ Package publishing still works for datastore (dual-package temporarily)

### Future Success (Post-Fertiscan Removal)
1. ✅ Datastore simplified to nachet-only package
2. ✅ Old workflow files removed from subdirectories
3. ✅ Documentation updated to reflect monorepo structure

## Risk Mitigation

### Immediate Risk Mitigation
1. **Fix Critical Issues First**: Address empty workflows and broken references before migration
2. **Test in Isolation**: Validate each workflow individually before integration
3. **Rollback Strategy**: Keep original workflows as backup during testing phase
4. **Small Incremental Changes**: Implement and test one workflow at a time

### Migration Risk Mitigation  
1. **Gradual Migration**: Implement alongside existing workflows initially
2. **Comprehensive Testing**: Test all scenarios before removing old workflows
3. **Documentation**: Document all changes and new workflow behavior
4. **Monitoring**: Monitor workflow execution success rates during transition

### Long-term Risk Mitigation
1. **Fertiscan Deprecation Plan**: Maintain dual-package support until fertiscan removal is complete
2. **Backward Compatibility**: Ensure existing integrations continue to work
3. **Performance Monitoring**: Track build times and resource usage during migration
