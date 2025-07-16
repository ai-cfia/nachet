# Database Connection Leak Fix Plan

## Problem Summary

The Nachet backend tests are showing PostgreSQL connection leaks with warnings like:

```Text
ResourceWarning: connection <psycopg.Connection [INERROR]> was deleted while still open. Please use 'with' or '.close()' to close the connection
```

## Root Cause Analysis

Three critical functions in `storage/datastore_storage_api.py` are creating database connections but not properly closing them:

1. **`get_all_seeds()` (lines 53-63)**
2. **`get_pipelines()` (lines 130-140)**
3. **`get_all_seeds_names()` (lines 66-76)**

These functions follow a **bad pattern**:

```python
async def get_all_seeds() -> list:
    try:
        connection = get_connection()
        cursor = get_cursor(connection)
        return await nachet_datastore.get_seed_info(cursor)
        # ❌ Missing end_query(connection, cursor)
    except Exception as error:
        raise SeedNotFoundError(error.args[0])
        # ❌ Missing end_query(connection, cursor)
```

## Solution Strategy

### Good Pattern (already used in some functions)

```python
def get_user_id(email: str) -> str:
    try:
        connection = get_connection()
        cursor = get_cursor(connection)
        # ... database operations ...
        end_query(connection, cursor)  # ✅ Properly closed
        return result
    except Exception as error:
        end_query(connection, cursor)  # ✅ Properly closed in error case
        raise DatastoreError(error)
```

### Improved Pattern (recommended fix)

```python
async def get_all_seeds() -> list:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = get_cursor(connection)
        result = await nachet_datastore.get_seed_info(cursor)
        return result
    except Exception as error:
        raise SeedNotFoundError(error.args[0])
    finally:
        if connection and cursor:
            end_query(connection, cursor)
```

## Implementation Plan

### Phase 1: Fix Connection Leaks (High Priority)

1. **Fix `get_all_seeds()` function**
   - Add proper `end_query()` calls in try-finally block
   - Ensure connections are closed in both success and error cases

2. **Fix `get_pipelines()` function**
   - Add proper `end_query()` calls in try-finally block
   - Ensure connections are closed in both success and error cases

3. **Fix `get_all_seeds_names()` function**
   - Add proper `end_query()` calls in try-finally block
   - Ensure connections are closed in both success and error cases

### Phase 2: Testing and Validation (Medium Priority)

1. **Test the fixes**
   - Run the test suite to verify connection leaks are resolved
   - Ensure no ResourceWarning messages appear
   - Verify all tests still pass

### Phase 3: Future Improvements (Low Priority)

1. **Consider context manager pattern**
   - Evaluate implementing a database context manager for more robust connection handling
   - This would be a larger refactoring but would prevent future leaks

## Files to Modify

- **Primary file**: `/home/p4r0d1m3pxz/work/nachet/backend/storage/datastore_storage_api.py`
  - Functions: `get_all_seeds()`, `get_pipelines()`, `get_all_seeds_names()`

## Expected Outcome

After implementing these fixes:

- ✅ No more PostgreSQL connection leak warnings
- ✅ Proper resource cleanup in all database operations
- ✅ Test suite runs cleanly without ResourceWarnings
- ✅ Improved application stability and resource management

## Risk Assessment

- **Low risk**: Changes are minimal and follow existing patterns in the codebase
- **High impact**: Fixes critical resource leaks that could cause production issues
- **Easy rollback**: Changes can be easily reverted if issues arise

## Testing Strategy

1. Run tests before fixes to confirm warnings exist
2. Apply fixes one function at a time
3. Run tests after each fix to verify warnings are resolved
4. Ensure no functional regressions in the affected functions
