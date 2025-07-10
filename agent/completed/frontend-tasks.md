# Frontend Workflow Migration Tasks

## Current State Analysis

### ✅ **What's Working**

- **Root-level workflows exist**: `frontend-build.yml` and `frontend-lint.yml` are implemented
- **Path-based triggering**: Both workflows correctly trigger on `frontend/**` changes
- **Monorepo awareness**: Both use `workflow-*-mono.yml` variants for monorepo context
- **Working directory setup**: Properly configured with `working-directory: frontend`
- **Sophisticated version checking**: `frontend-lint.yml` includes semantic version comparison

### ⚠️ **Critical Issues to Fix**

#### 1. **Invalid Path References**

**Problem**: Both workflows reference non-existent file

```yaml
# Line 7 in both frontend-build.yml and frontend-lint.yml:
- '.github/workflows/frontend-ci.yml'  # ❌ This file doesn't exist!
```

**Fix Required**:

```yaml
# Should be:
- '.github/workflows/frontend-build.yml'
- '.github/workflows/frontend-lint.yml'
```

#### 2. **Inconsistent Concurrency Groups**

**Problem**: Both workflows use same concurrency group

```yaml
# Both files use:
group: frontend-ci-${{ github.ref }}  # ❌ Will cause conflicts
```

**Fix Required**:

```yaml
# frontend-build.yml should use:
group: frontend-build-${{ github.ref }}

# frontend-lint.yml should use:
group: frontend-lint-${{ github.ref }}
```

#### 3. **Missing Package.json Context**

**Problem**: Both workflows look for `package.json` in root, but it's in `frontend/`

```yaml
paths:
  - 'package.json'    # ❌ Should be 'frontend/package.json'
  - '.nvmrc'          # ❌ Should be 'frontend/.nvmrc' 
  - 'tsconfig.json'   # ❌ Should be 'frontend/tsconfig.json'
```

## Task Checklist

### 🔥 **URGENT - Fix Immediately**

- [ ] **Fix Path References**
  - [ ] Update `frontend-build.yml` line 7: Change to `.github/workflows/frontend-build.yml`
  - [ ] Update `frontend-lint.yml` line 7: Change to `.github/workflows/frontend-lint.yml`

- [ ] **Fix File Path Context**
  - [ ] Update both workflows to use `frontend/package.json` instead of `package.json`
  - [ ] Update both workflows to use `frontend/.nvmrc` instead of `.nvmrc`
  - [ ] Update both workflows to use `frontend/tsconfig.json` instead of `tsconfig.json`

- [ ] **Fix Concurrency Groups**
  - [ ] Update `frontend-build.yml` to use `frontend-build-${{ github.ref }}`
  - [ ] Update `frontend-lint.yml` to use `frontend-lint-${{ github.ref }}`

### 📋 **Testing Tasks**

- [ ] **Create Test PR**
  - [ ] Make a small change to `frontend/src/` directory
  - [ ] Verify both workflows trigger correctly
  - [ ] Check that no workflow conflicts occur

- [ ] **Validate Workflow Jobs**
  - [ ] Confirm `frontend-lint.yml` version checking works correctly
  - [ ] Confirm `frontend-build.yml` container build succeeds
  - [ ] Verify lint/test jobs complete successfully

- [ ] **Path Trigger Validation**
  - [ ] Test that changes to `frontend/` trigger both workflows
  - [ ] Test that changes to other directories don't trigger frontend workflows
  - [ ] Verify workflow-specific file changes trigger appropriately

### 🔧 **Optimization Tasks**

- [ ] **Workflow Efficiency**
  - [ ] Consider if both workflows should run simultaneously or be combined
  - [ ] Evaluate if version checking should be in build workflow instead
  - [ ] Review if separate markdown checking is needed in both workflows

- [ ] **Dependency Management**
  - [ ] Verify Node.js and npm version extraction works correctly
  - [ ] Test that version dependencies are properly passed between jobs
  - [ ] Ensure proper job ordering with `needs:` dependencies

### 📊 **Validation Checklist**

- [ ] **Workflow Syntax**
  - [ ] Run `yamllint` on both workflow files
  - [ ] Validate YAML syntax is correct
  - [ ] Check all referenced actions exist

- [ ] **Monorepo Integration**
  - [ ] Confirm `IS_MONOREPO: true` environment variable is used correctly
  - [ ] Verify `working-directory: frontend` is properly set
  - [ ] Test that Docker builds work with monorepo context

- [ ] **Security and Secrets**
  - [ ] Verify `secrets: inherit` is working properly
  - [ ] Test that container registry access works
  - [ ] Confirm no sensitive information is exposed

## Current Workflow Comparison

### Original (frontend/.github/workflows/react-frontend-workflows.yml)

- ✅ Simple, straightforward workflow
- ✅ All-in-one approach (lint, test, build, push)
- ❌ No path-based triggering
- ❌ Not monorepo-aware

### Migrated (Root workflows)

- ✅ Path-based triggering implemented
- ✅ Monorepo-aware with proper working directories
- ✅ Sophisticated version checking
- ❌ Invalid path references (critical)
- ❌ Missing context for file paths

## Next Steps Priority

1. **IMMEDIATE**: Fix the path reference issues (deployment blocker)
2. **URGENT**: Correct file path contexts for monorepo structure  
3. **HIGH**: Test workflows with actual PR changes
4. **MEDIUM**: Optimize workflow efficiency and job dependencies
5. **LOW**: Consider workflow consolidation vs separation

## Success Criteria

### Phase 1 (Critical)

- [ ] Both workflows execute without errors
- [ ] Path-based triggering works correctly
- [ ] No workflow conflicts or failures

### Phase 2 (Functional)

- [ ] Version checking works correctly
- [ ] Container builds succeed
- [ ] Lint and test jobs pass

### Phase 3 (Optimized)

- [ ] Efficient job execution
- [ ] Proper dependency handling
- [ ] Clean, maintainable workflow structure
