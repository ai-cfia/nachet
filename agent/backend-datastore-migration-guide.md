# Backend Datastore Migration Guide

## Overview

This document details the specific backend files that need to be updated to migrate from package-based datastore imports to direct source integration in the existing monorepo structure.

## Current Backend Structure Analysis

The backend currently imports datastore in the following ways:

- Package imports: `import datastore`, `import nachet as nachet_datastore`
- Module imports: `from datastore import db`, `from datastore import azure_storage`
- Relative imports through storage API: `import storage.datastore_storage_api as datastore`

## Files Requiring Updates

### 1. Primary Files (Critical)

#### `backend/storage/datastore_storage_api.py`

**Current imports:**

```python
import datastore
from datastore import db
from datastore import user as user_datastore
import nachet as nachet_datastore
import datastore.bin.upload_picture_set
```

**Updated imports:**

```python
# Direct imports from copied source
from datastore import db
from datastore.db.queries import user as user_datastore
from nachet import get_seed_info, upload_picture_unknown, upload_pictures
from nachet import get_ml_structure, register_inference_result
from nachet import new_perfect_inference_feeback, new_correction_inference_feedback
from nachet import find_validated_pictures, delete_picture_set_with_archive
from nachet import get_picture_sets_info, get_picture_inference, get_picture_blob
from datastore import create_picture_set, delete_picture_set_permanently, new_user
from datastore.bin import upload_picture_set
```

#### `backend/app.py`

**Current imports:**

```python
import storage.datastore_storage_api as datastore  # noqa: E402
from datastore import azure_storage  # noqa: E402
```

**Updated imports:**

```python
import storage.datastore_storage_api as datastore  # noqa: E402
from datastore.blob import azure_storage_api as azure_storage  # noqa: E402
```

### 2. Test Files (Important)

#### `backend/tests/test_datastore_storage_api.py`

**Current imports:**

```python
import storage.datastore_storage_api as datastore
```

**No changes needed** - This imports through the storage API, which remains the same.

#### `backend/tests/test_manage_folders.py`

**Current imports:**

```python
from storage.datastore_storage_api import DatastoreError
```

**No changes needed** - This imports the exception class from the storage API wrapper.

### 3. Configuration Files

#### `backend/requirements.txt`

**Remove:**

```
nachet-datastore @git+https://github.com/ai-cfia/ailab-datastore.git@231-split-nachet-config-secrets
```

**Add dependencies that were previously included in the datastore package:**

```
azure-storage-blob>=12.0.0
azure-identity>=1.0.0
psycopg2-binary>=2.9.0
asyncpg>=0.28.0
```

#### `backend/requirements.txt.local`

**Remove:**

```
nachet-datastore @git+https://github.com/ai-cfia/ailab-datastore.git@231-split-nachet-config-secrets
```

**Add the same dependencies as above.**

## Step-by-Step Migration Process

### Step 1: Backup and Branch

```bash
cd backend
git checkout -b datastore-direct-integration
git commit -am "Backup before datastore integration migration"
```

### Step 2: Copy Datastore Source

```bash
# From the backend directory
mkdir -p datastore nachet
cp -r ../datastore/datastore/* ./datastore/
cp -r ../datastore/nachet/* ./nachet/
```

### Step 3: Update Primary Files

#### Update `storage/datastore_storage_api.py`

Replace the imports section (lines 1-11) with the new direct imports:

```python
"""
This module provide an absraction to the nachet-datastore interface.
"""
import os
from datastore import db
from datastore.db.queries import user as user_datastore
from nachet import (
    get_seed_info, upload_picture_unknown, upload_pictures,
    get_ml_structure, register_inference_result,
    new_perfect_inference_feeback, new_correction_inference_feedback,
    find_validated_pictures, delete_picture_set_with_archive,
    get_picture_sets_info, get_picture_inference, get_picture_blob
)
from datastore import create_picture_set, delete_picture_set_permanently, new_user
from datastore.bin import upload_picture_set
import nachet.db.queries.seed as seed_queries
```

#### Update `app.py`

Change the azure_storage import (line 24):

```python
from datastore.blob import azure_storage_api as azure_storage  # noqa: E402
```

### Step 4: Update Function Calls

In `storage/datastore_storage_api.py`, update these function calls:

#### `get_all_seeds()` function (line ~47)

```python
async def get_all_seeds() -> list:
    """
    Return all seeds name register in the Datastore.
    """
    try:
        connection = get_connection()
        cursor = get_cursor(connection)
        return await get_seed_info(cursor)
    except Exception as error:
        raise SeedNotFoundError(error.args[0])
```

#### `get_picture_id()` function (line ~89)

```python
async def get_picture_id(cursor, user_id, image, container_client) :
    """
    Return the picture_id of the image
    """
    try:
        return await upload_picture_unknown(cursor, str(user_id), image, container_client)
    except Exception as error:
        raise DatastoreError(error)
```

#### `upload_pictures()` function (line ~95)

```python
async def upload_pictures(cursor, user_id, picture_set_id, container_client, pictures, seed_name, seed_id: str, zoom_level: float = None, nb_seeds: int = None) :
    try :
        return await upload_pictures(cursor, user_id, picture_set_id, container_client, pictures, seed_name, seed_id, zoom_level, nb_seeds)
    except Exception as error:
        raise DatastoreError(error)
```

#### `get_pipelines()` function (line ~113)

```python
async def get_pipelines() -> list:
    """
    Retrieves the pipelines from the Datastore
    """
    try:
        connection = get_connection()
        cursor = get_cursor(connection)
        pipelines = await get_ml_structure(cursor)
        return pipelines
    except Exception as error:
        raise GetPipelinesError(error.args[0])
```

### Step 5: Update Requirements

Remove the datastore package line from both `requirements.txt` and `requirements.txt.local`:

```bash
# Remove this line from both files:
# nachet-datastore @git+https://github.com/ai-cfia/ailab-datastore.git@231-split-nachet-config-secrets
```

Add missing dependencies:

```bash
echo "azure-storage-blob>=12.0.0" >> requirements.txt
echo "azure-identity>=1.0.0" >> requirements.txt
echo "psycopg2-binary>=2.9.0" >> requirements.txt
echo "asyncpg>=0.28.0" >> requirements.txt
```

### Step 6: Update Docker Files

#### `Dockerfile`

Ensure the copied datastore directories are included in the Docker build:

```dockerfile
COPY datastore/ ./datastore/
COPY nachet/ ./nachet/
```

#### `Dockerfile.local`

Same as above:

```dockerfile
COPY datastore/ ./datastore/
COPY nachet/ ./nachet/
```

### Step 7: Test the Migration

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start the server
python app.py
```

## Post-Migration Benefits

1. **Direct Debugging**: You can now set breakpoints directly in datastore code
2. **IDE Navigation**: Jump to definition works for all datastore functions
3. **Simplified Imports**: No more package import confusion
4. **Local Testing**: Easy to modify and test datastore functions locally

## Validation Checklist

- [ ] Backend starts without import errors
- [ ] All tests pass
- [ ] Can set breakpoints in datastore code
- [ ] IDE navigation works for datastore functions
- [ ] Docker builds successfully
- [ ] No package import errors in logs

## Rollback Plan

If issues arise:

```bash
git checkout main
git branch -D datastore-direct-integration
```

Then restore the original package-based approach.

## Files Not Requiring Changes

The following files do **NOT** need updates:

- All test files (they import through the storage API wrapper)
- Model files (no direct datastore imports)
- Auth files (no direct datastore imports)
- Pipeline files (no direct datastore imports)

## Additional Notes

- The storage API wrapper (`datastore_storage_api.py`) continues to provide the same interface to the rest of the backend
- This migration is backward-compatible for all calling code
- The main changes are internal to the storage layer
- Consider adding logging to track the migration success
