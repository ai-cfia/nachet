# Frontend Workflow Migration Plan

## Current Frontend Analysis

### Technology Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (v5.2.6)
- **Testing**: Vitest with coverage reporting
- **Linting**: ESLint with TypeScript rules
- **Deployment**: Docker containerization
- **Node Version**: 18.16.0, NPM 9.8.1

### Current Workflow Structure
**File**: `frontend/.github/workflows/react-frontend-workflows.yml`

**Jobs**:
1. `lint-test`: Node.js linting and testing using reusable workflow
2. `markdown-check`: Documentation validation with custom config
3. `repo-standard`: Repository standards validation  
4. `build-and-push-gcr`: Docker build and push to GitHub Container Registry

**Triggers**: 
- Pull request events (opened, closed, synchronize)
- Runs on ALL changes currently (no path filtering)

### Build Process Analysis
**Package.json scripts**:
- `prebuild`: ESLint + TypeScript compilation check
- `build`: TypeScript compilation + Vite build
- `test`: Vitest execution
- `test:coverage`: Coverage reporting

**Docker Build**:
- Multi-stage Node.js 18 build
- Installs dependencies and builds application
- Exposes port 3000
- Uses startup script for runtime configuration

## Migration Strategy

### Phase 1: Create Root-Level Frontend Workflow

#### 1.1 New Workflow File
**Location**: `.github/workflows/frontend-ci.yml`

**Path-Based Triggering**:
```yaml
on:
  pull_request:
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-ci.yml'  # Self-trigger for workflow changes
    types:
      - opened
      - closed  
      - synchronize
```

#### 1.2 Job Migration Strategy

**Job 1: Frontend Lint and Test**
- Use existing `ai-cfia/github-workflows/.github/workflows/workflow-lint-test-node.yml`
- **Working Directory**: Set to `frontend/`
- **Key Parameters**:
  - `working-directory: frontend`
  - Node version: 18.16.0
  - NPM version: 9.8.1

**Job 2: Frontend Build Validation**
- Add explicit build validation step
- Run `npm run build` to ensure production build works
- Cache `node_modules` and `dist` for efficiency

**Job 3: Docker Build and Push**  
- Use existing `ai-cfia/github-workflows/.github/workflows/workflow-build-push-container-github-registry.yml`
- **Critical Change**: Docker context must be `frontend/` directory
- **Container name**: Keep as `nachet-frontend` or use repository name
- **Tag**: Use commit SHA for traceability

**Job 4: Repository Standards (Conditional)**
- Only run repo standards check if frontend-specific files changed
- Focus on frontend-related standards

#### 1.3 Workflow Dependencies
```yaml
jobs:
  frontend-lint-test:
    # ... lint and test job
    
  frontend-build:
    needs: frontend-lint-test
    # ... build validation
    
  frontend-docker:
    needs: [frontend-lint-test, frontend-build]
    # ... docker build and push
```

### Phase 2: Handle Monorepo-Specific Challenges

#### 2.1 Docker Context Path Issue
**Problem**: Docker build context will be root directory, not `frontend/`
**Solutions**:
1. **Option A**: Update Dockerfile to handle monorepo context
2. **Option B**: Use docker build context parameter in workflow
3. **Option C**: Copy approach with proper paths

**Recommended**: Use context parameter:
```yaml
- name: Build Docker Image
  run: |
    docker build \
      --context frontend \
      --file frontend/Dockerfile \
      --tag ${{ env.IMAGE_NAME }}:${{ github.sha }} \
      frontend/
```

#### 2.2 Working Directory Management
All Node.js commands need to run in `frontend/` directory:
```yaml
defaults:
  run:
    working-directory: frontend
```

#### 2.3 Dependency Caching
Implement Node.js dependency caching:
```yaml
- name: Cache Node.js dependencies
  uses: actions/cache@v3
  with:
    path: frontend/node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('frontend/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Phase 3: Configuration Updates

#### 3.1 Markdown Link Checking
**Current**: Uses `.mlc_config.json` in frontend directory
**Action**: Ensure path is correctly referenced in workflow:
```yaml
with:
  md-link-config-file-path: "frontend/.mlc_config.json"
```

#### 3.2 Environment Variables
**Current Build Args**:
- `ARG_PUBLIC_URL`
- `ARG_VITE_BACKEND_URL` 

**Monorepo Considerations**:
- May need to adjust backend URL for integration
- Ensure environment variables are scoped to frontend builds

### Phase 4: Testing and Validation Strategy

#### 4.1 Pre-Migration Testing
1. **Verify Current State**: Ensure existing frontend workflow is working
2. **Document Current Behavior**: Record build times, artifact sizes
3. **Test Docker Build Locally**: Validate container builds from monorepo root

#### 4.2 Migration Testing Plan
1. **Create New Workflow**: Add `frontend-ci.yml` alongside existing
2. **Test Trigger**: Create test PR touching only frontend files
3. **Verify Jobs**: Ensure all jobs run correctly with monorepo context
4. **Docker Validation**: Confirm container builds and pushes successfully
5. **Integration Test**: Test built container actually works

#### 4.3 Validation Checklist
- [ ] Workflow triggers only on frontend changes
- [ ] Node.js lint and test passes
- [ ] TypeScript compilation successful
- [ ] Vite build completes without errors
- [ ] Docker image builds from monorepo context
- [ ] Container pushes to GitHub Container Registry
- [ ] Image size and build time acceptable
- [ ] No duplicate workflows running

## Implementation Steps

### Step 1: Create New Frontend Workflow
```bash
# Create the new workflow file
touch .github/workflows/frontend-ci.yml
```

### Step 2: Implement Basic Structure
Start with lint-test job only, then add others incrementally:
1. Path-based triggering
2. Frontend lint-test job
3. Build validation
4. Docker build and push

### Step 3: Test with Sample PR
Create a test PR that:
- Changes a frontend file (e.g., update README.md in frontend/)
- Triggers only the frontend workflow
- Validates all jobs complete successfully

### Step 4: Monitor and Optimize
- Check build times vs. current workflow
- Optimize caching strategy
- Validate resource usage

### Step 5: Gradual Cutover
1. Run both workflows in parallel initially
2. Compare results and fix any discrepancies  
3. Disable old workflow once confident
4. Remove old workflow files

## Technical Implementation Details

### Sample Workflow Structure
```yaml
name: Frontend CI

on:
  pull_request:
    paths:
      - 'frontend/**'
    types: [opened, closed, synchronize]

defaults:
  run:
    working-directory: frontend

jobs:
  frontend-lint-test:
    uses: ai-cfia/github-workflows/.github/workflows/workflow-lint-test-node.yml@main
    with:
      working-directory: frontend
    secrets: inherit

  frontend-docker:
    needs: frontend-lint-test
    uses: ai-cfia/github-workflows/.github/workflows/workflow-build-push-container-github-registry.yml@main
    with:
      container-name: nachet-frontend
      tag: ${{ github.sha }}
      registry: ghcr.io/ai-cfia
      dockerfile-path: frontend/Dockerfile
      context-path: frontend
    secrets: inherit
```

## Risk Assessment and Mitigation

### High Risk
1. **Docker Context Issues**: Build failing due to wrong context
   - **Mitigation**: Test docker builds locally first
   - **Rollback**: Keep original workflow active during testing

2. **Dependency Path Issues**: Node modules or configs not found
   - **Mitigation**: Explicit working-directory settings
   - **Testing**: Validate all package.json scripts work

### Medium Risk  
1. **Workflow Trigger Issues**: Not triggering on correct changes
   - **Mitigation**: Test with various file change scenarios
   - **Monitoring**: Check workflow runs in GitHub Actions

2. **Performance Degradation**: Slower builds in monorepo
   - **Mitigation**: Implement aggressive caching
   - **Baseline**: Measure current build times

### Low Risk
1. **Environment Variable Issues**: Missing or incorrect env vars
   - **Mitigation**: Explicit environment configuration
   - **Testing**: Validate built container functionality

## Success Metrics

1. **Functional**:
   - ✅ Workflow triggers only on frontend changes
   - ✅ All existing jobs pass (lint, test, build, docker)
   - ✅ Docker image builds and deploys successfully

2. **Performance**:
   - ✅ Build time within 110% of current time
   - ✅ Docker image size unchanged
   - ✅ No resource waste (unnecessary job runs)

3. **Operational**:
   - ✅ Zero downtime during migration
   - ✅ All existing functionality preserved
   - ✅ Clear rollback path available

## Post-Migration Cleanup

1. **Remove Old Workflow**: Delete `frontend/.github/workflows/`
2. **Update Documentation**: Update frontend README to reflect monorepo
3. **Team Communication**: Notify team of new workflow behavior
4. **Monitor**: Watch for any issues in first few PRs 