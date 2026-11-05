# Blob Storage Module

The blob storage module provides a unified, provider-agnostic interface for managing cloud blob storage operations in the Nachet application. It implements a clean architecture with abstract interfaces, comprehensive error handling, and robust validation using Pydantic models.

## Architecture Overview

The module follows a layered architecture with clear separation of concerns:

```text
blob/
├── __init__.py              # Public API exports
├── interface.py             # Abstract base class defining the contract
├── manager.py               # Singleton manager for client lifecycle
├── models.py                # Pydantic models for validation
├── exceptions.py            # Custom exception hierarchy
├── azure/                   # Azure-specific implementation
│   ├── storage.py           # Main Azure implementation
│   ├── client.py            # Client factory and configuration
│   └── operations/          # Operation-specific classes
└── tests/                   # Comprehensive test suite
```

## Key Components

### Core Interface (`interface.py`)

Defines the `BlobStorageInterface` abstract base class that all storage providers must implement:

- **Blob Operations**: upload, download, delete, copy, move
- **Container Operations**: create, delete, list, properties
- **Security**: SAS token generation, access control
- **Metadata**: blob/container metadata and tags
- **Utilities**: URL generation, tier management

### Singleton Manager (`manager.py`)

The `BlobStorageManager` implements the singleton pattern following Azure SDK best practices:

- **Thread-Safe**: Single `BlobServiceClient` instance reused across requests
- **Performance Optimized**: Connection pooling and memory efficiency
- **Health Monitoring**: Built-in health checks and connection validation
- **Lifecycle Management**: Initialization, refresh, and cleanup operations

### Azure Implementation (`azure/`)

Production-ready Azure Blob Storage implementation using composition pattern:

- **`AzureBlobStorage`**: Main facade implementing `BlobStorageInterface`
- **Operation Classes**: Specialized classes for different operation types
  - `BlobOperations`: Core blob CRUD operations
  - `ContainerOperations`: Container management
  - `SecurityOperations`: SAS tokens and access control
  - `MetadataOperations`: Metadata and tags management
  - `AdvancedOperations`: Copy, move, and advanced features
  - `TierOperations`: Storage tier management

## Usage Examples

### Basic Setup

```python
from app.blob import get_blob_storage

# Get the singleton client (FastAPI dependency)
async def upload_file(storage = Depends(get_blob_storage)):
    result = await storage.upload_blob("container", "file.txt", data)
```

### Context Manager

```python
from app.blob import blob_storage_context

async with blob_storage_context() as storage:
    result = await storage.upload_blob("container", "file.txt", data)
    properties = await storage.get_blob_properties("container", "file.txt")
```

### Direct Client Creation

```python
from app.blob import create_blob_storage_client

config = {
    "connection_string": "DefaultEndpointsProtocol=https;..."
}
storage = create_blob_storage_client("azure", config)
```

## Configuration

### Azure Blob Storage

Required configuration parameters:

```python
config = {
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=...",
    # Optional parameters
    "max_connections": 20,
    "timeout": 30,
    "retry_total": 3
}
```

### Environment Variables

The module expects these environment variables:

- `NACHET_AZURE_STORAGE_CONNECTION_STRING`: Azure Storage connection string
- `NACHET_DATA`: Base configuration for blob storage settings

## Error Handling

The module defines a comprehensive exception hierarchy:

```python
from app.blob.exceptions import (
    BlobStorageError,           # Base exception
    BlobNotFoundError,          # Blob doesn't exist
    ContainerNotFoundError,     # Container doesn't exist
    PermissionError,           # Access denied
    ConnectionError,           # Network/connection issues
    ValidationError,           # Invalid parameters
    QuotaExceededError,        # Storage quota exceeded
)
```

### Error Handling Best Practices

```python
try:
    result = await storage.upload_blob("container", "file.txt", data)
except BlobNotFoundError:
    # Handle missing blob
    pass
except PermissionError:
    # Handle access issues
    pass
except BlobStorageError as e:
    # Handle general blob storage errors
    logger.error(f"Blob operation failed: {e}")
```

## Models and Validation

The module uses Pydantic models for request/response validation:

```python
from app.blob.models import (
    BlobInfo,              # Blob metadata and properties
    ContainerInfo,         # Container information
    UploadResult,          # Upload operation result
    SASTokenInfo,          # SAS token details
    UploadOptions,         # Upload configuration
    DownloadOptions,       # Download configuration
)
```

## Testing

The module includes comprehensive tests in the `tests/` directory:

### Running Tests

```bash
# Run all blob storage tests
cd backend/app/blob
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_file_operations.py -v        # File operations
uv run pytest tests/test_container_operations.py -v   # Container operations
uv run pytest tests/test_sas_operations.py -v         # SAS token operations
uv run pytest tests/test_azure_connectivity.py -v     # Connectivity tests
```

### Test Categories

- **File Operations**: Upload, download, delete, copy, move operations
- **Container Operations**: Container lifecycle and management
- **SAS Operations**: Security token generation and validation
- **Connectivity**: Network connectivity and health checks

## Production Deployment

### Performance Considerations

- **Singleton Pattern**: Uses single `BlobServiceClient` for optimal performance
- **Connection Pooling**: Automatic connection reuse and pooling
- **Thread Safety**: All operations are thread-safe for concurrent use
- **Memory Efficiency**: Single client instance reduces memory footprint

### Monitoring and Health Checks

```python
from app.blob.manager import BlobStorageHealthCheck

# Basic health check
health = await BlobStorageHealthCheck.check_connection()

# Health check with retry logic
health = await BlobStorageHealthCheck.check_with_retry(max_retries=3)
```

### Initialization

The module should be initialized during application startup:

```python
from app.blob.manager import initialize_blob_storage

async def startup():
    await initialize_blob_storage(settings)
```

## Security Features

- **SAS Token Generation**: Fine-grained access control with expiration
- **Permission Management**: Granular permissions (read, write, delete, list)
- **Container-level Security**: Container-specific access tokens
- **Metadata Protection**: Secure metadata and tag operations

## Future Extensibility

The modular architecture supports easy addition of new storage providers:

1. Implement `BlobStorageInterface` for the new provider
2. Add provider-specific configuration handling
3. Update the factory function in `__init__.py`
4. Add comprehensive tests for the new implementation

## API Reference

For detailed API documentation, see the docstrings in:

- `interface.py`: Complete interface specification
- `azure/storage.py`: Azure-specific implementation details
- `manager.py`: Manager and lifecycle operations
- `models.py`: Data models and validation schemas
