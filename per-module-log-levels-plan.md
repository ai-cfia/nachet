# Plan: Implement Per-Module Log Levels Using Loguru's Filter Function

## Current State Analysis

**Current Logging System**:

- Uses **Loguru** for all backend logging (`backend/app/service/logs.py`)
- Single global `LOG_LEVEL` environment variable (defaults to "INFO")
- All modules use the same log level via `LogService.setup_logging()`
- Console output configured at line 255: `logger.add(sys.stdout, format=cls.custom_formatter, level=log_level)`

**Key Files**:

- `backend/app/service/logs.py` - LogService implementation
- `backend/app/api/config.py` - Settings with `log_level: str = "INFO"` (line 82)
- `backend/app/main.py` - Application initialization

---

## Solution: Loguru Filter Function Approach

Based on the GitHub issue (<https://github.com/Delgan/loguru/issues/1301#issuecomment-2663065215>), Loguru supports per-module log levels through its **filter** parameter. Here's how it works:

### **Concept**

```python
# Instead of just:
logger.add(sys.stdout, level="INFO")

# Use a filter function that checks the module name:
def module_filter(record):
    # Get module name from record
    module = record["name"]

    # Apply per-module levels
    if module.startswith("app.service.inference"):
        return record["level"].no >= logger.level("DEBUG").no
    elif module.startswith("app.datastore"):
        return record["level"].no >= logger.level("WARNING").no
    else:
        return record["level"].no >= logger.level("INFO").no

logger.add(sys.stdout, filter=module_filter, level="DEBUG")  # Must be lowest level
```

---

## Implementation Plan

### **Option 1: Environment Variable Configuration (Recommended)**

Allow users to configure per-module levels via environment variables:

```bash
# .env
LOG_LEVEL=INFO  # Global default
LOG_LEVEL_INFERENCE=DEBUG  # app.service.inference.*
LOG_LEVEL_WORKFLOWS=DEBUG  # app.service.inference.workflows
LOG_LEVEL_DATASTORE=WARNING  # app.datastore.*
LOG_LEVEL_BLOB=ERROR  # app.blob.*
```

**Changes Required**:

#### 1. **Update `Settings` class** (`backend/app/api/config.py`):

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Global log level
    log_level: str = "INFO"

    # Per-module log levels (optional overrides)
    log_level_inference: str | None = None  # app.service.inference
    log_level_workflows: str | None = None  # app.service.inference.workflows
    log_level_datastore: str | None = None  # app.datastore
    log_level_blob: str | None = None  # app.blob
    log_level_api: str | None = None  # app.api

    @computed_field
    @property
    def module_log_levels(self) -> dict[str, str]:
        """Build module-specific log level mapping"""
        levels = {}
        if self.log_level_inference:
            levels["app.service.inference"] = self.log_level_inference.upper()
        if self.log_level_workflows:
            levels["app.service.inference.workflows"] = self.log_level_workflows.upper()
        if self.log_level_datastore:
            levels["app.datastore"] = self.log_level_datastore.upper()
        if self.log_level_blob:
            levels["app.blob"] = self.log_level_blob.upper()
        if self.log_level_api:
            levels["app.api"] = self.log_level_api.upper()
        return levels
```

#### 2. **Update `LogService.setup_logging`** (`backend/app/service/logs.py`):

```python
@classmethod
def setup_logging(cls, config: Optional[Dict[str, Any]] = None):
    # ... existing setup code ...

    log_level = config.get("log_level", "INFO").upper()
    module_levels = config.get("module_log_levels", {})  # New parameter

    # Remove default loguru handler
    logger.remove()

    # Create filter function for per-module levels
    def module_filter(record):
        module_name = record["name"]

        # Check for exact match first, then prefixes (longest match wins)
        for module_prefix, level in sorted(module_levels.items(), key=lambda x: -len(x[0])):
            if module_name.startswith(module_prefix):
                min_level = logger.level(level).no
                return record["level"].no >= min_level

        # Default to global log level
        min_level = logger.level(log_level).no
        return record["level"].no >= min_level

    # Determine the minimum level across all modules (must be lowest)
    all_levels = [log_level] + list(module_levels.values())
    min_level = min(all_levels, key=lambda l: logger.level(l).no)

    # Console logging with filter
    logger.add(
        sys.stdout,
        format=cls.custom_formatter,
        level=min_level,  # Must be the lowest level
        filter=module_filter
    )

    # ... rest of OTEL setup (apply same filter to OTEL bridge) ...
```

#### 3. **Update `create_app` to pass module levels**:

```python
# In config.py lifespan function:
LogService.setup_logging({
    "enable_otel": settings.otel_enabled,
    "otel_exporter_protocol": settings.otel_exporter_protocol.lower(),
    "otel_exporter_endpoint": settings.otel_exporter_endpoint,
    "log_level": settings.log_level.upper(),
    "module_log_levels": settings.module_log_levels,  # NEW
})
```

---

### **Option 2: Configuration File Approach** (Alternative)

For more complex scenarios, use a dedicated config file:

```yaml
# config/logging.yaml
global_level: INFO

modules:
  app.service.inference.workflows: DEBUG
  app.service.inference: DEBUG
  app.datastore: WARNING
  app.blob: ERROR
  app.api.routes: INFO
```

Load with:

```python
import yaml

with open("config/logging.yaml") as f:
    logging_config = yaml.safe_load(f)
```

---

## Usage Examples

### **Example 1: Debug Only Workflows**

```bash
export LOG_LEVEL=INFO
export LOG_LEVEL_WORKFLOWS=DEBUG

# Result:
# - Most modules: INFO level
# - app.service.inference.workflows: DEBUG level (verbose DBOS workflow logs)
```

### **Example 2: Debug All Inference, Quiet Datastore**

```bash
export LOG_LEVEL=INFO
export LOG_LEVEL_INFERENCE=DEBUG
export LOG_LEVEL_DATASTORE=ERROR

# Result:
# - app.service.inference.*: DEBUG (all inference methods)
# - app.datastore.*: ERROR only (quiet database queries)
# - Everything else: INFO
```

### **Example 3: Production Debugging**

```bash
# Normal production:
export LOG_LEVEL=INFO

# Investigating upload issues:
export LOG_LEVEL_INFERENCE=DEBUG  # Enable debug for validation/preprocessing
export LOG_LEVEL_BLOB=DEBUG  # Enable debug for blob operations

# No need to restart - just reload app
```

### **Example 4: Debugging /inf Endpoint Specifically**

```bash
export LOG_LEVEL=INFO
export LOG_LEVEL_WORKFLOWS=DEBUG  # See DBOS workflow execution
export LOG_LEVEL_INFERENCE=DEBUG  # See all inference API calls

# Now logs will show:
# - Detailed workflow steps (=== WORKFLOW STARTED ===, etc.)
# - ML model API calls with timing
# - Image preprocessing details
# - All without flooding logs with datastore queries
```

---

## Benefits

✅ **Granular control** - Debug specific modules without flooding logs
✅ **Zero performance impact** - Filtering happens at logger level
✅ **Easy configuration** - Environment variables (12-factor app)
✅ **Backward compatible** - Falls back to LOG_LEVEL if no overrides
✅ **Production-friendly** - Can enable debug for specific modules without noise
✅ **Hierarchical** - `app.service.inference` applies to all sub-modules unless overridden
✅ **Dynamic** - Change levels without code changes, just env vars

---

## Implementation Steps

1. **Update `Settings` class** - Add per-module level fields and `module_log_levels` computed property
2. **Update `LogService.setup_logging`** - Add filter function with module-level logic
3. **Update `setup_console_only_logging`** - Apply same filter logic for consistency
4. **Update OTEL bridge** - Ensure filter applies to OTEL logs too
5. **Test** - Verify filtering works correctly for different module combinations
6. **Document** - Add examples to README or .env.template

---

## Testing Strategy

```python
# Test script to verify per-module levels
from app.service.logs import LogService

LogService.setup_logging({
    "log_level": "INFO",
    "module_log_levels": {
        "app.service.inference": "DEBUG",
        "app.datastore": "WARNING",
    }
})

logger = LogService.get_logger()

# From inference module (should log DEBUG)
logger.bind(name="app.service.inference.workflows").debug("This should appear")
logger.bind(name="app.service.inference.workflows").info("This should appear")

# From datastore module (should NOT log INFO)
logger.bind(name="app.datastore.image").info("This should NOT appear")
logger.bind(name="app.datastore.image").warning("This should appear")

# From other modules (should use global INFO)
logger.bind(name="app.api.routes").debug("This should NOT appear")
logger.bind(name="app.api.routes").info("This should appear")
```

---

## Files to Modify

1. `backend/app/api/config.py` (Settings class)
2. `backend/app/service/logs.py` (LogService.setup_logging + setup_console_only_logging)
3. `backend/.env.template` (documentation)
4. Optional: `backend/config/logging.yaml` (if using config file approach)

---

## Recommended Approach

**Use Option 1 (Environment Variables)** because:

- Follows 12-factor app principles
- Easy to change without code changes
- Works well with Docker/Kubernetes
- Backward compatible
- Matches existing LOG_LEVEL pattern
- No additional config files to manage

---

## Example .env.template Addition

```bash
# Logging configuration
LOG_LEVEL=INFO  # Global default log level (DEBUG, INFO, WARNING, ERROR)

# Per-module log level overrides (optional)
# These override the global LOG_LEVEL for specific modules
# LOG_LEVEL_INFERENCE=DEBUG       # app.service.inference.* (all inference methods)
# LOG_LEVEL_WORKFLOWS=DEBUG       # app.service.inference.workflows (DBOS workflows)
# LOG_LEVEL_DATASTORE=WARNING     # app.datastore.* (database queries)
# LOG_LEVEL_BLOB=DEBUG            # app.blob.* (blob storage operations)
# LOG_LEVEL_API=INFO              # app.api.* (API routes)
```

---

## Key Implementation Details

### **Module Name Resolution**

Loguru's `record["name"]` contains the fully qualified module name where the log was called:

- `app.service.inference.workflows` for logs in workflows.py
- `app.datastore.image` for logs in datastore/image.py
- `app.blob.manager` for logs in blob/manager.py

### **Matching Logic**

The filter uses **longest prefix match** to allow hierarchical configuration:

```python
# If you have:
LOG_LEVEL_INFERENCE=INFO
LOG_LEVEL_WORKFLOWS=DEBUG

# Then:
# app.service.inference.workflows → DEBUG (specific override)
# app.service.inference.image_validation → INFO (parent module)
# app.datastore.image → INFO (global default)
```

### **Minimum Level Requirement**

Loguru requires the sink's `level` parameter to be set to the **lowest level** across all modules:

```python
# If you configure:
LOG_LEVEL=INFO
LOG_LEVEL_WORKFLOWS=DEBUG

# Then the sink level must be DEBUG:
logger.add(sys.stdout, level="DEBUG", filter=module_filter)

# The filter then handles per-module filtering
```

---

## Total Estimated Time

- **Environment Variable Approach**: ~30 minutes
- **Testing**: ~15 minutes
- **Documentation**: ~15 minutes
- **Total**: ~60 minutes

---

## Future Enhancements

1. **Runtime Configuration API**: Add endpoint to change log levels without restart
2. **Logging UI**: Web interface to view/change module log levels
3. **Auto-detection**: Automatically discover all modules and suggest levels
4. **Performance Metrics**: Track log volume per module for optimization
