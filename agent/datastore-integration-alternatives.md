# Datastore Integration Alternatives

## Current Problem

The current implementation uses the datastore as a Python package, which creates several challenges:

1. **Debugging Complexity**: Hard to trace through nested package imports
2. **Development Friction**: Package imports obscure the actual code being executed
3. **Testing Difficulties**: Mocking and testing becomes more complex
4. **Code Navigation**: IDEs struggle with package-based imports for navigation
5. **Deployment Complexity**: Package management adds overhead

## Current Architecture Analysis

The backend currently imports datastore through:

```python
import storage.datastore_storage_api as datastore
```

Which then imports various datastore modules:

```python
import datastore
import datastore.db
import nachet as nachet_datastore
import datastore.bin.upload_picture_set
```

## Alternative Solutions

### 1. Direct Source Integration (Recommended)

**Approach**: Copy datastore source code directly into backend project structure

**Pros**:

- Complete visibility into all code
- Easy debugging and tracing
- No package import complexity
- IDE navigation works perfectly
- Simplified testing

**Cons**:

- Code duplication between projects
- Manual synchronization needed for updates
- Larger repository size

**Implementation**:

```text
backend/
├── datastore/
│   ├── db/
│   │   ├── queries/
│   │   ├── metadata/
│   │   └── __init__.py
│   ├── blob/
│   └── __init__.py
├── storage/
│   └── datastore_storage_api.py  # Simplified wrapper
└── app.py
```

### 2. Git Submodules

**Approach**: Use git submodules to include datastore as source code

**Pros**:

- Source code visibility
- Version control for datastore changes
- No package management
- Easy to update specific versions

**Cons**:

- Git submodule complexity
- Team coordination required
- Deployment scripts need updates

**Implementation**:

```bash
cd backend
git submodule add <datastore-repo-url> datastore
```

### 3. Monorepo Structure

**Approach**: Restructure the entire project as a monorepo

**Pros**:

- Single source of truth
- Shared code visible to all components
- Simplified dependency management
- Better cross-component refactoring

**Cons**:

- Major restructuring required
- Different deployment strategies needed
- Larger repository

**Implementation**:

```text
nachet/
├── shared/
│   └── datastore/
├── backend/
├── frontend/
└── deployment/
```

### 4. API Service Approach

**Approach**: Convert datastore into a standalone API service

**Pros**:

- Clear service boundaries
- Language-agnostic interface
- Scalable architecture
- Easy to test with API mocking

**Cons**:

- Additional service to maintain
- Network latency considerations
- More complex deployment

**Implementation**:

```text
datastore-service/  # FastAPI or similar
backend/           # Calls datastore via HTTP
frontend/          # Remains unchanged
```

### 5. Symbolic Links

**Approach**: Use symbolic links to include datastore source in backend

**Pros**:

- Source code visibility
- No code duplication
- Easy to implement

**Cons**:

- OS-dependent
- Issues with Docker/containers
- Git doesn't handle symlinks well

### 6. Build-Time Integration

**Approach**: Copy datastore source during build process

**Pros**:

- Clean development environment
- Automated synchronization
- No runtime package dependencies

**Cons**:

- Build complexity
- CI/CD pipeline changes needed

**Implementation**:

```bash
# In Dockerfile or build script
COPY ../datastore/datastore ./backend/datastore
```

## Recommended Implementation Plan

### Phase 1: Direct Source Integration (Quick Win)

1. **Copy datastore source**:

   ```bash
   cp -r ../datastore/datastore ./backend/
   cp -r ../datastore/nachet ./backend/
   ```

2. **Update imports in storage/datastore_storage_api.py**:

   ```python
   # Before
   import datastore
   import nachet as nachet_datastore
   
   # After
   from datastore import db
   from datastore import user as user_datastore
   from nachet import queries
   ```

3. **Remove package dependencies**:
   - Remove datastore from requirements.txt
   - Update import paths throughout backend

### Phase 2: Clean Up Architecture

1. **Flatten the abstraction**:
   - Move commonly used functions directly into datastore_storage_api.py
   - Remove unnecessary wrapper layers
   - Simplify the API surface

2. **Improve error handling**:
   - Create specific exception types
   - Add better error context
   - Implement proper logging

### Phase 3: Testing Improvements

1. **Add unit tests**:
   - Test datastore functions directly
   - Mock database connections easily
   - Test error scenarios

2. **Integration testing**:
   - Test with real database
   - Performance testing
   - End-to-end scenarios

## Migration Steps

### Step 1: Backup Current State

```bash
git checkout -b backup-before-datastore-migration
git commit -am "Backup before datastore integration changes"
```

### Step 2: Copy Source Code

```bash
cd backend
mkdir -p datastore nachet
cp -r ../datastore/datastore/* ./datastore/
cp -r ../datastore/nachet/* ./nachet/
```

### Step 3: Update Imports

Update all files that import from datastore package to use local imports:

```python
# storage/datastore_storage_api.py
from datastore import db
from datastore.db.queries import user as user_queries
from nachet.db.queries import seed as seed_queries
```

### Step 4: Test Everything

```bash
python -m pytest tests/
python app.py  # Verify server starts
```

### Step 5: Update Dependencies

Remove datastore from requirements.txt and any setup.py files.

## Benefits After Migration

1. **Debugging**: Set breakpoints directly in datastore code
2. **Code Navigation**: Jump to definitions works perfectly
3. **Refactoring**: Safe refactoring across datastore and backend
4. **Testing**: Direct unit testing of datastore functions
5. **Documentation**: Code is self-documenting through direct visibility

## Potential Issues and Solutions

### Issue: Code Synchronization

**Solution**: Use git hooks or CI/CD to sync changes from main datastore repo

### Issue: Multiple Backend Services

**Solution**: Create shared library or use build-time copying for all services

### Issue: Large Repository Size

**Solution**: Use git LFS for large files, or implement sparse checkouts

## Next Steps

1. **Validate Approach**: Try the direct integration approach in a feature branch
2. **Measure Impact**: Compare debugging experience before/after
3. **Team Alignment**: Ensure all team members understand new structure
4. **Update Documentation**: Update README and development guides
5. **CI/CD Updates**: Modify build processes as needed

This migration will significantly improve the development experience while maintaining all existing functionality.
