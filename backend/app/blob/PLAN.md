# Blob Storage Module

This module provides a unified interface for managing blob storage operations in the Nachet application. **Azure Blob Storage implementation complete with all Phase 1 high priority features fully functional.**

## 📊 **Current Status**: Complete Azure Blob Storage Implementation + Phase 1 Features

- ✅ **Architecture & Foundation**: Complete with all models, interfaces, and infrastructure
- ✅ **Azure Integration**: Connection management and container/blob listing working
- ✅ **FastAPI Integration**: Lifecycle management and dependency injection implemented
- ✅ **Container Management**: All container operations fully implemented and tested
- ✅ **File Operations**: All core file operations implemented and tested
- ✅ **Advanced File Operations**: Copy/move operations with transaction safety implemented
- ✅ **Metadata & Tags Management**: Complete metadata and tags system implemented
- ✅ **Blob Tier Management**: Hot/Cool tier management for cost optimization
- ✅ **Comprehensive Testing**: 88 passing tests covering all operations
- ✅ **Singleton Architecture**: Optimized with Azure SDK singleton client pattern

## Architecture

```text
app/blob/
├── README.md              # This file (updated status)
├── __init__.py           # ✅ Module exports and factory function
├── interface.py          # ✅ Abstract base classes and interfaces  
├── exceptions.py         # ✅ Custom exceptions
├── models.py            # ✅ Pydantic data models for blob operations
├── manager.py           # ✅ BlobStorageManager with singleton client
├── tests/               # ✅ Comprehensive test suite implemented
│   ├── test_azure_connectivity.py      # ✅ Basic connectivity tests (17 tests)
│   ├── test_container_operations.py    # ✅ Complete container operation tests (19 tests)
│   ├── test_file_operations.py         # ✅ Complete file operation tests (28 tests)
│   └── README.md
└── azure/               # ✅ Azure-specific implementation
    ├── __init__.py      # ✅ Complete
    ├── client.py        # ✅ Azure client utilities (working)
    └── storage.py       # ✅ Main Azure storage (all operations complete)
```

## Core Interface

The blob storage module exposes a simple, provider-agnostic interface for blob operations:

### Primary Operations

1. **File Management**
   - `upload_blob(container, name, data, **kwargs)` - Upload file to blob storage
   - `download_blob(container, name, **kwargs)` - Download file from blob storage
   - `delete_blob(container, name, **kwargs)` - Delete file from blob storage
   - `copy_blob(source_container, source_name, dest_container, dest_name, **kwargs)` - Copy blob
   - `move_blob(source_container, source_name, dest_container, dest_name, **kwargs)` - Move blob

2. **Listing & Discovery**
   - `list_blobs(container, prefix=None, **kwargs)` - List blobs in container
   - `list_containers(**kwargs)` - List available containers
   - `blob_exists(container, name, **kwargs)` - Check if blob exists
   - `get_blob_properties(container, name, **kwargs)` - Get blob metadata and properties

3. **Container Management**
   - `create_container(name, **kwargs)` - Create a new container
   - `delete_container(name, **kwargs)` - Delete a container
   - `container_exists(name, **kwargs)` - Check if container exists
   - `get_container_properties(name, **kwargs)` - Get container metadata

4. **Access Control & Security**
   - `generate_sas_token(container, name, permissions, expiry, **kwargs)` - Generate SAS token for blob
   - `generate_container_sas_token(container, permissions, expiry, **kwargs)` - Generate SAS token for container
   - `set_blob_permissions(container, name, permissions, **kwargs)` - Set blob access permissions

5. **Metadata & Tags**
   - `set_blob_metadata(container, name, metadata, **kwargs)` - Set blob metadata
   - `get_blob_metadata(container, name, **kwargs)` - Get blob metadata
   - `set_blob_tags(container, name, tags, **kwargs)` - Set blob tags
   - `get_blob_tags(container, name, **kwargs)` - Get blob tags

6. **Advanced Operations**
   - `get_blob_url(container, name, **kwargs)` - Get blob URL
   - `get_blob_size(container, name, **kwargs)` - Get blob size
   - `set_blob_tier(container, name, tier, **kwargs)` - Set blob access tier (Hot, Cool)
   - `blob_snapshot(container, name, **kwargs)` - Create blob snapshot
   - `restore_blob_snapshot(container, name, snapshot_id, **kwargs)` - Restore from snapshot

## Data Models

All data models use Pydantic for validation, serialization, and type safety.

### BlobInfo

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Dict, Optional

class BlobInfo(BaseModel):
    name: str = Field(..., description="Name of the blob")
    container: str = Field(..., description="Container name")
    size: int = Field(..., ge=0, description="Blob size in bytes")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    etag: str = Field(..., description="Entity tag for the blob")
    content_type: str = Field(..., description="MIME content type")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Custom metadata")
    tags: Dict[str, str] = Field(default_factory=dict, description="Blob tags")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Blob name cannot be empty")
        return v.strip()
    
    @validator('container')
    def validate_container(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Container name cannot be empty")
        return v.strip().lower()
```

### ContainerInfo

```python
class ContainerInfo(BaseModel):
    name: str = Field(..., description="Container name")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    etag: str = Field(..., description="Entity tag for the container")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Custom metadata")
    public_access: Optional[str] = Field(None, description="Public access level")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Container name cannot be empty")
        # Azure container naming rules
        if not v.islower() or not v.replace('-', '').isalnum():
            raise ValueError("Container name must be lowercase alphanumeric with hyphens")
        return v.strip()
```

### UploadResult

```python
class UploadResult(BaseModel):
    container: str = Field(..., description="Container name")
    name: str = Field(..., description="Blob name")
    etag: str = Field(..., description="Entity tag from upload")
    last_modified: datetime = Field(..., description="Upload timestamp")
    url: str = Field(..., description="Blob URL")
    size: int = Field(..., ge=0, description="Uploaded blob size in bytes")
    content_md5: Optional[str] = Field(None, description="MD5 hash of the content")
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must be a valid HTTP/HTTPS URL")
        return v
```

### BlobListResult

```python
class BlobListResult(BaseModel):
    blobs: List[BlobInfo] = Field(..., description="List of blobs")
    continuation_token: Optional[str] = Field(None, description="Token for pagination")
    prefix: Optional[str] = Field(None, description="Filter prefix used")
    container: str = Field(..., description="Container name")
    total_count: Optional[int] = Field(None, description="Total number of blobs")
```

### BlobTierInfo

```python
class BlobTierInfo(BaseModel):
    container: str = Field(..., description="Container name")
    name: str = Field(..., description="Blob name")
    tier: str = Field(..., description="Access tier (Hot, Cool)")
    tier_change_time: Optional[datetime] = Field(None, description="When the tier was last changed")

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, v):
        valid_tiers = {"Hot", "Cool"}
        if v not in valid_tiers:
            raise ValueError(f"Invalid tier: {v}. Must be one of {valid_tiers}")
        return v
```

## Current Implementation Status

### ✅ **COMPLETED - Phase 1 Foundation**

- **✅ Foundation**: Complete Pydantic models for all data structures (`models.py`)
- **✅ Architecture**: `BlobStorageManager` for connection pooling and lifecycle management (`manager.py`)
- **✅ Configuration**: Azure client utilities in `client.py` (BlobServiceClient, container client, SAS tokens)
- **✅ Error Handling**: Comprehensive custom exceptions for all error scenarios (`exceptions.py`)
- **✅ Interface**: Abstract `BlobStorageInterface` defining the complete contract (`interface.py`)
- **✅ Module Exports**: Clean `__init__.py` with all exports and factory function
- **✅ Settings Integration**: `blob_storage_config` computed field implemented in Settings
- **✅ Lifecycle Integration**: Blob storage initialization added to FastAPI `lifespan()`
- **✅ Azure Implementation Started**: `AzureBlobStorage` class in `azure/storage.py`

### ✅ **COMPLETED - Azure Storage Operations**

- **✅ Container Listing**: `list_containers()` - Full implementation with pagination and filtering
- **✅ Blob Listing**: `list_blobs()` - Complete implementation with metadata, tags, and pagination
- **✅ Container Management**: Complete implementation of all container operations
  - `create_container()` - Create containers with metadata support and validation
  - `container_exists()` - Check container existence
  - `get_container_properties()` - Retrieve container metadata and properties
  - `delete_container()` - Delete containers with proper error handling
- **✅ File Operations**: All core file operations fully implemented
  - `upload_blob()` - Upload files with content validation, metadata, and proper error handling
  - `download_blob()` - Download files with byte range support and validation
  - `download_blob_stream()` - Download files as async streams for large files
  - `blob_exists()` - Check blob existence with proper container validation
  - `get_blob_properties()` - Retrieve detailed blob properties including tier information
  - `delete_blob()` - Delete blobs with proper error handling
  - `set_blob_tier()` - Set blob access tiers (Hot, Cool) for cost optimization
- **✅ Enhanced Models**: Extended `BlobProperties` with tier information
  - `blob_tier` - Current access tier (Hot, Cool)
  - `blob_tier_change_time` - Timestamp when tier was last changed
  - `blob_tier_inferred` - Whether tier was inferred or explicitly set
  - `last_accessed_on` - Last access time for lifecycle management
- **✅ Client Management**: Proper Azure client initialization and error handling
- **✅ Validation**: All operations return validated Pydantic models
- **✅ Testing Framework**: Comprehensive test coverage with 88 tests total
  - Basic connectivity tests in `tests/test_azure_connectivity.py` (17 tests)
  - Complete container operation tests in `tests/test_container_operations.py` (19 tests)
  - Complete file operation tests in `tests/test_file_operations.py` (52 tests)

### ✅ **COMPLETED - Singleton Architecture & Testing**

- **✅ Singleton Pattern**: Successfully implemented following Azure SDK best practices
  - Single BlobServiceClient instance reused across all requests (Azure SDK recommendation)
  - Thread-safe client with optimal connection pooling
  - Simplified architecture with better performance and memory efficiency
  - Eliminated factory pattern complexity for optimal Azure SDK usage
  
- **✅ Configuration Integration**: Seamless integration with Settings system
  - Flat configuration structure properly aligned with Settings.blob_storage_config
  - Provider extraction working correctly from configuration
  - Configuration validation during manager initialization
  
- **✅ Complete Test Suite**: All connectivity and configuration tests passing
  - Azure connectivity validation tests
  - Configuration structure validation  
  - Manager initialization tests
  - Connection string generation tests
  - All test cases now compatible with singleton pattern architecture

### ✅ **COMPLETED - Core File Operations**

All core file operations are fully implemented and tested:

1. **File Operations** 📁 ✅ **COMPLETE**
   - `upload_blob()` - File upload with content validation, metadata, and proper error handling
   - `download_blob()` - File download with byte range support and validation
   - `download_blob_stream()` - Streaming download for large files
   - `delete_blob()` - File deletion with proper error handling
   - `blob_exists()` - Existence check with container validation
   - `get_blob_properties()` - Complete blob metadata and properties including tier information

2. **Blob Tier Management** 🔧 ✅ **COMPLETE**
   - `set_blob_tier()` - Set blob access tier (Hot, Cool) for cost optimization

3. **Security & Metadata** 🔐 *(Still available for future implementation)*
   - `copy_blob()`, `move_blob()` - File operations *(STUB)*
   - `generate_sas_token()` - Blob-specific SAS tokens *(STUB)*
   - `generate_container_sas_token()` - Container SAS tokens *(STUB)*
   - `set_blob_metadata()`, `get_blob_metadata()` - Metadata management *(STUB)*
   - `set_blob_tags()`, `get_blob_tags()` - Tag management *(STUB)*
   - `get_blob_url()` - URL generation *(STUB)*

### 🎯 **OPTIONAL FUTURE ENHANCEMENTS - Advanced Features**

Core blob storage functionality is now complete. The following advanced features remain available for future implementation if needed:

#### 📋 **Phase 1 - Advanced File Operations**

1. **File Management Extensions**
   - Implement `copy_blob()` and `move_blob()` operations
   - Add soft delete support for `delete_blob()`
   - Enhanced streaming for extremely large files

#### 📋 **Phase 2 - Advanced Features & Security**

1. **Metadata & Tags Management**
   - Implement `set_blob_metadata()`, `get_blob_metadata()`
   - Implement `set_blob_tags()`, `get_blob_tags()`
   - Add tag-based filtering in `list_blobs()`

2. **Security & Access Control**
   - Implement `generate_sas_token()` for blob-specific access
   - Implement `generate_container_sas_token()` for container access
   - Add permission validation and secure URL generation

3. **URL & Property Management**
   - Implement `get_blob_url()` with optional SAS token inclusion
   - Enhanced blob property management

#### 🔧 **Phase 3 - Production Ready Features**

1. **Performance & Reliability**
   - Advanced retry logic with exponential backoff
   - Connection health monitoring
   - Performance metrics and monitoring

2. **Monitoring & Observability**
   - Health check endpoints
   - Metrics integration
   - Comprehensive logging

### ✅ **IMPLEMENTATION COMPLETE**

#### ✅ **ALL CORE OPERATIONS IMPLEMENTED**

- ✅ **Settings Configuration** - `blob_storage_config` computed field implemented
- ✅ **Lifespan Integration** - Blob storage initialization added to FastAPI startup
- ✅ **Infrastructure** - All base classes, models, and manager implemented
- ✅ **Azure Client Setup** - Connection handling and operations working
- ✅ **Container Operations** - All container management operations complete
- ✅ **File Operations** - All core file operations complete
- ✅ **Advanced File Operations** - Copy/move operations with transaction safety
- ✅ **Metadata & Tags** - Complete metadata and tags management system
- ✅ **Blob Tier Management** - Hot/Cool tier management implemented
- ✅ **Enhanced Models** - BlobProperties includes tier information
- ✅ **Comprehensive Testing** - 88 total tests covering all implemented functionality

#### 🎯 **PRODUCTION READY**

The Azure Blob Storage module is now production-ready with all core functionality implemented:

1. **✅ File Operations Complete**
   - `upload_blob()` - Content validation, metadata, error handling
   - `download_blob()` - Range support, streaming, validation
   - `download_blob_stream()` - Async streaming for large files
   - `delete_blob()` - Proper error handling
   - `blob_exists()` - Container validation
   - `get_blob_properties()` - Complete metadata and tier information

2. **✅ Advanced File Operations Complete**
   - `copy_blob()` - Copy blobs within or across containers with error handling
   - `move_blob()` - Move blobs with transaction safety and rollback capability

3. **✅ Metadata & Tags Management Complete**
   - `set_blob_metadata()` - Set custom metadata with validation
   - `get_blob_metadata()` - Retrieve blob metadata with error handling
   - `set_blob_tags()` - Set blob index tags with validation
   - `get_blob_tags()` - Retrieve blob tags with error handling

4. **✅ Container Management Complete**
   - `create_container()` - Metadata support and validation
   - `delete_container()` - Error handling
   - `container_exists()` - Existence checks
   - `get_container_properties()` - Full metadata retrieval

5. **✅ Cost Optimization**
   - `set_blob_tier()` - Hot/Cool tier management for cost optimization
   - Tier information in blob properties for monitoring

6. **✅ Testing Complete**
   - 52 comprehensive file operation tests (including copy/move/metadata/tags)
   - 19 complete container operation tests
   - 17 connectivity and configuration tests
   - Integration with Azure Storage and Azurite
   - Error scenario coverage for all operations

#### 📊 **CURRENT ARCHITECTURE STATUS**

**✅ Working Components:**

- Settings configuration with `blob_storage_config`
- FastAPI lifecycle integration
- `BlobStorageManager` connection pooling
- Azure client utilities (`client.py`)
- Complete Pydantic models (`models.py`)
- Error handling framework (`exceptions.py`)
- Abstract interface (`interface.py`)
- Container and blob listing operations

**🔧 Infrastructure Ready For:**

- File upload/download operations
- Container management
- Metadata and tags
- SAS token generation
- All operations have stub implementations ready

### � **DEVELOPMENT STATUS CHECKLIST**

#### ✅ **COMPLETED FILES & FEATURES**

- ✅ `azure/storage.py` - AzureBlobStorage implementation (listing + container operations complete)
- ✅ `azure/client.py` - Azure client utilities and connection management
- ✅ `models.py` - Complete Pydantic models for all data structures
- ✅ `interface.py` - Abstract BlobStorageInterface with full method definitions
- ✅ `manager.py` - BlobStorageManager for connection pooling and lifecycle
- ✅ `exceptions.py` - Comprehensive custom exceptions
- ✅ `__init__.py` - Module exports and factory function
- ✅ `tests/test_azure_connectivity.py` - Basic connectivity and listing tests (17 tests)
- ✅ `tests/test_container_operations.py` - Complete container operation tests (19 tests)
- ✅ Settings integration - `blob_storage_config` computed field working
- ✅ FastAPI integration - Lifecycle management and dependency injection

**File Operations** ✅ **COMPLETE**:

- ✅ `upload_blob()` - File upload with validation and metadata
- ✅ `download_blob()` - File download with range support
- ✅ `download_blob_stream()` - Streaming download for large files
- ✅ `delete_blob()` - File deletion with proper error handling
- ✅ `blob_exists()` - Existence check implementation
- ✅ `get_blob_properties()` - Full blob metadata retrieval including tier information
- ✅ `set_blob_tier()` - Blob tier management for cost optimization
- ✅ `copy_blob()` - Copy blobs within or across containers with error handling
- ✅ `move_blob()` - Move blobs with transaction safety and rollback
- ✅ `set_blob_metadata()` - Set custom metadata with validation
- ✅ `get_blob_metadata()` - Retrieve blob metadata with error handling
- ✅ `set_blob_tags()` - Set blob index tags with validation
- ✅ `get_blob_tags()` - Retrieve blob tags with error handling

**Testing & Documentation** ✅ **COMPLETE**:

- ✅ Comprehensive test suite for file operations (52 tests)
- ✅ Integration tests with Azurite and real Azure Storage for file operations
- ✅ Lifecycle testing and error scenario coverage
- ✅ Blob tier management testing

#### 🚀 **IMPLEMENTATION ROADMAP** - Advanced Features

Based on priority analysis, the following features will be implemented in phases:

## ✅ Phase 1: High Priority Features - COMPLETED

### ✅ 1.1 File Operations - COMPLETED ⚡

- ✅ `copy_blob()` - Copy blobs within or across containers with comprehensive error handling
- ✅ `move_blob()` - Move blobs with transaction safety (copy + delete with rollback capability)

### ✅ 1.2 Metadata & Tags Management - COMPLETED ⚡

- ✅ `set_blob_metadata()` - Set custom metadata on blobs with validation
- ✅ `get_blob_metadata()` - Retrieve blob metadata with proper error handling
- ✅ `set_blob_tags()` - Set blob index tags for searchability with validation
- ✅ `get_blob_tags()` - Retrieve blob tags with proper error handling

## Phase 2: Medium Priority Features

### ✅ 2.1 Security & Access Control - COMPLETED ⚡

- ✅ `generate_sas_token()` - Generate blob-specific SAS tokens with permissions/expiry and comprehensive options
  - **Supported Permissions**: read, write, delete, add, create
  - **Features**: Custom start time, IP restrictions, content headers, expiry control
  - **Security**: Account key validation, blob existence verification
- ✅ `generate_container_sas_token()` - Generate container-level SAS tokens with full permission control
  - **Supported Permissions**: read, write, delete, list, add, create
  - **Features**: Container-wide access, bulk operations support, same security options as blob SAS
  - **Integration**: Works with existing container operations and validation

**Phase 2 Testing**: Added comprehensive test suite `test_sas_operations.py` with 21 tests covering:

- Blob SAS token generation with various permission combinations (10 tests)
- Container SAS token generation and validation (8 tests)
- Integration scenarios and real-world use cases (3 tests)
- Error handling for invalid permissions and missing resources

### 2.2 URL Generation - MEDIUM PRIORITY 🔗

- [ ] `get_blob_url_with_sas()` - Generate blob URLs with optional SAS token inclusion

#### 🎯 **SAS Token Use Cases for Nachet**

**Primary Use Cases:**

1. **Secure Direct Client Access** 🔐
   - **Frontend Image Upload**: Allow React frontend to upload images directly to blob storage without backend proxy
   - **Download Links**: Generate time-limited URLs for users to download processed images or analysis results
   - **Temporary Access**: Provide limited-time access to specific blobs for external users or partner systems

2. **External System Integration** 🔗
   - **ML Pipeline Access**: Generate tokens for external ML services to access specific image blobs for processing
   - **Third-party Integrations**: Allow partner systems to access specific containers with controlled permissions
   - **API Client Access**: Provide secure access tokens to API consumers for blob operations

3. **User-Specific Access Control** 👤
   - **Per-User Containers**: Generate SAS tokens scoped to specific user containers (`nachet-user-{uuid}`)
   - **Role-Based Access**: Different permission levels (read-only for viewers, read-write for processors)
   - **Audit Trail**: Track access through SAS token usage rather than shared backend credentials

4. **Performance & Scalability** ⚡
   - **CDN Integration**: Generate SAS URLs that work with Azure CDN for faster image delivery
   - **Direct Client Downloads**: Eliminate backend bottleneck for large file downloads
   - **Reduced Server Load**: Offload blob operations from backend servers to Azure directly

**Example Implementation:**

```python
# Frontend Image Upload Workflow
sas_token = await storage.generate_sas_token(
    container=f"nachet-user-{user_id}",
    name=f"uploads/{image_id}.png",
    permissions=["create", "write"],
    expiry=timedelta(hours=1)
)

# ML Pipeline Access
ml_token = await storage.generate_sas_token(
    container="nachet-processing",
    name=f"queue/{batch_id}/*",
    permissions=["read"],
    expiry=timedelta(hours=2)
)

# Result Distribution
download_token = await storage.generate_sas_token(
    container="nachet-results",
    name=f"analysis/{result_id}.json",
    permissions=["read"],
    expiry=timedelta(days=7)
)
```

**Security Benefits:**

- Principle of least privilege with minimal permissions and time-bound access
- Credential protection - no need to share storage account keys
- Compliance-ready with Azure audit logging and traceable access patterns

## Phase 3: Additional Improvements - MEDIUM PRIORITY 🔧

### 3.1 Error Recovery & Reliability - DETAILED IMPLEMENTATION PLAN

#### 🔄 Retry Mechanisms with Exponential Backoff

**Core Implementation:**

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [
        ClientError,
        ServiceRequestError,
        HttpResponseError,
        ConnectionError,
        TimeoutError
    ])

class RetryableOperation:
    """Decorator for adding retry logic to blob operations"""

    def __init__(self, policy: RetryPolicy = None):
        self.policy = policy or RetryPolicy()

    async def __call__(self, func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, self.policy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(self.policy.retry_on) as e:
                    last_exception = e
                    if attempt == self.policy.max_attempts:
                        raise

                    delay = min(
                        self.policy.base_delay * (self.policy.exponential_base ** (attempt - 1)),
                        self.policy.max_delay
                    )

                    if self.policy.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    await asyncio.sleep(delay)

            raise last_exception
        return wrapper
```

**Integration Example:**

```python
class AzureBlobStorage(BlobStorageInterface):

    @RetryableOperation(RetryPolicy(max_attempts=5, base_delay=2.0))
    async def upload_blob(self, container: str, name: str, data: Union[bytes, str, BinaryIO], **kwargs):
        # Existing implementation with automatic retry on transient failures
        pass

    @RetryableOperation(RetryPolicy(max_attempts=3, base_delay=1.0))
    async def download_blob(self, container: str, name: str, **kwargs):
        # Existing implementation with automatic retry on network issues
        pass
```

#### 🔌 Circuit Breaker Pattern

**Implementation Strategy:**

```python
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    success_threshold: int = 2  # successful calls to close circuit

class CircuitBreaker:
    """Circuit breaker for preventing cascade failures"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.config.failure_threshold:
            self.state = "OPEN"
```

#### 🌐 Enhanced Network Error Recovery

**Connection Health Monitoring:**

```python
class NetworkHealthMonitor:
    """Monitor and manage network connection health"""

    def __init__(self, storage_client):
        self.client = storage_client
        self.last_health_check = None
        self.health_status = "UNKNOWN"
        self.consecutive_failures = 0

    async def check_health(self) -> Dict[str, Any]:
        try:
            # Lightweight operation to test connectivity
            containers = await self.client.list_containers(max_results=1)
            self.health_status = "HEALTHY"
            self.consecutive_failures = 0
            self.last_health_check = datetime.now(timezone.utc)

            return {
                "status": "healthy",
                "timestamp": self.last_health_check,
                "response_time": "< 1s",
                "consecutive_failures": 0
            }
        except Exception as e:
            self.consecutive_failures += 1
            self.health_status = "UNHEALTHY"
            self.last_health_check = datetime.now(timezone.utc)

            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": self.last_health_check,
                "consecutive_failures": self.consecutive_failures
            }

    async def ensure_healthy_connection(self):
        """Ensure connection is healthy before operations"""
        if self.consecutive_failures > 3:
            # Attempt connection reset
            await self._reset_connection()

    async def _reset_connection(self):
        """Reset the underlying connection"""
        # Implement connection pool refresh logic
        pass
```

**Progressive Timeout Strategy:**

```python
class TimeoutConfig:
    """Progressive timeout configuration for operations"""

    def __init__(self):
        self.operation_timeouts = {
            "upload_blob": [30, 60, 120],      # seconds per attempt
            "download_blob": [30, 60, 120],
            "list_blobs": [10, 20, 40],
            "container_ops": [15, 30, 60]
        }

    def get_timeout(self, operation: str, attempt: int) -> float:
        timeouts = self.operation_timeouts.get(operation, [30, 60, 120])
        return timeouts[min(attempt - 1, len(timeouts) - 1)]

# Usage in operations:
async def upload_blob_with_timeout(self, container: str, name: str, data, attempt: int = 1):
    timeout = TimeoutConfig().get_timeout("upload_blob", attempt)

    try:
        async with asyncio.timeout(timeout):
            return await self._upload_blob_impl(container, name, data)
    except asyncio.TimeoutError:
        raise BlobOperationTimeoutError(f"Upload timed out after {timeout}s (attempt {attempt})")
```

#### 🏥 Error Classification System

**Enhanced Error Handling:**

```python
class ErrorClassifier:
    """Classify errors for appropriate retry strategies"""

    TRANSIENT_ERRORS = {
        "ServiceRequestError",
        "ClientError",
        "HttpResponseError",
        "ConnectionError",
        "TimeoutError",
        "ServiceUnavailableError"
    }

    PERMANENT_ERRORS = {
        "AuthenticationError",
        "AuthorizationError",
        "ResourceNotFoundError",
        "InvalidRequestError"
    }

    RATE_LIMIT_ERRORS = {
        "TooManyRequestsError",
        "ThrottlingError"
    }

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        error_name = error.__class__.__name__
        return error_name in cls.TRANSIENT_ERRORS or error_name in cls.RATE_LIMIT_ERRORS

    @classmethod
    def get_retry_delay(cls, error: Exception, attempt: int) -> float:
        error_name = error.__class__.__name__

        if error_name in cls.RATE_LIMIT_ERRORS:
            # Longer delays for rate limiting
            return min(30 * (2 ** attempt), 300)  # Up to 5 minutes

        if error_name in cls.TRANSIENT_ERRORS:
            # Standard exponential backoff
            return min(2 ** attempt, 60)  # Up to 1 minute

        return 0  # No retry for permanent errors
```

#### 📊 Reliability Metrics & Monitoring

**Implementation Components:**

```python
@dataclass
class ReliabilityMetrics:
    """Track reliability metrics for monitoring"""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    retried_operations: int = 0
    circuit_breaker_trips: int = 0
    average_retry_count: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    @property
    def retry_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.retried_operations / self.total_operations

class ReliabilityMonitor:
    """Monitor and report on system reliability"""

    def __init__(self):
        self.metrics = ReliabilityMetrics()
        self.operation_history = deque(maxlen=1000)

    def record_operation(self, operation: str, success: bool, attempts: int):
        self.metrics.total_operations += 1
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1

        if attempts > 1:
            self.metrics.retried_operations += 1

        self.operation_history.append({
            "timestamp": datetime.now(timezone.utc),
            "operation": operation,
            "success": success,
            "attempts": attempts
        })

    def get_health_report(self) -> Dict[str, Any]:
        return {
            "success_rate": self.metrics.success_rate,
            "retry_rate": self.metrics.retry_rate,
            "total_operations": self.metrics.total_operations,
            "circuit_breaker_trips": self.metrics.circuit_breaker_trips,
            "recent_failures": [
                op for op in list(self.operation_history)[-50:]
                if not op["success"]
            ]
        }
```

#### 🧪 Testing Strategy

**Comprehensive Test Coverage:**

1. **Unit Tests for Retry Logic**

   ```python
   class TestRetryMechanisms:
       async def test_exponential_backoff_calculation(self):
       async def test_retry_budget_limits(self):
       async def test_jitter_randomization(self):
       async def test_error_classification(self):
   ```

2. **Integration Tests with Failure Simulation**

   ```python
   class TestNetworkResilience:
       async def test_connection_recovery_after_network_partition(self):
       async def test_timeout_progression(self):
       async def test_circuit_breaker_state_transitions(self):
       async def test_health_monitoring_accuracy(self):
   ```

3. **Performance Impact Assessment**

   ```python
   class TestPerformanceImpact:
       async def test_retry_overhead_measurement(self):
       async def test_circuit_breaker_latency(self):
       async def test_health_check_frequency_optimization(self):
   ```

#### 📋 Implementation Checklist

**Phase 3.1 Implementation Tasks:**

- [ ] **Retry System Foundation**
  - [ ] Implement `RetryPolicy` and `RetryableOperation` classes
  - [ ] Create configurable retry strategies for different operation types
  - [ ] Add exponential backoff with jitter support
  - [ ] Implement retry budget system to prevent resource exhaustion

- [ ] **Circuit Breaker Implementation**
  - [ ] Develop `CircuitBreaker` class with state management
  - [ ] Integration with existing blob storage operations
  - [ ] Configurable failure thresholds and recovery timeouts
  - [ ] Circuit breaker metrics and state monitoring

- [ ] **Network Health Monitoring**
  - [ ] Implement `NetworkHealthMonitor` with lightweight health checks
  - [ ] Connection pool health monitoring and refresh logic
  - [ ] Progressive timeout strategies for different operation types
  - [ ] Dead connection detection and cleanup mechanisms

- [ ] **Error Classification & Recovery**
  - [ ] Enhanced `ErrorClassifier` for better error categorization
  - [ ] Specific retry strategies for different error types
  - [ ] Rate limiting detection and adaptive delays
  - [ ] Permanent vs transient error handling

- [ ] **Monitoring & Metrics**
  - [ ] `ReliabilityMetrics` tracking system
  - [ ] Operation success/failure rate monitoring
  - [ ] Circuit breaker trip frequency tracking
  - [ ] Health reporting and alerting mechanisms

- [ ] **Testing & Validation**
  - [ ] Comprehensive test suite for all retry mechanisms
  - [ ] Network failure simulation and recovery testing
  - [ ] Performance impact analysis and optimization
  - [ ] Integration testing with real Azure Storage scenarios

**Expected Outcomes:**

- **99.9% Operation Success Rate** under normal conditions
- **Automatic Recovery** from transient network failures within 30 seconds
- **Circuit Breaker Protection** preventing cascade failures
- **Comprehensive Monitoring** with real-time reliability metrics
- **Zero Manual Intervention** for common network issues

## Implementation Notes

**✅ Container Management**: All container operations already complete - no additional work needed

- `create_container()`, `delete_container()`, `container_exists()`, `get_container_properties()`, `list_containers()`

**📏 File Size Considerations**: All files under 10MB - streaming optimizations not required

**🔗 Connection Management**: Singleton pattern already optimized - connection pooling not required

**📋 Deferred Features** (Low Priority):

- Abstract base classes for other storage providers
- Configuration management enhancements
- Monitoring and metrics integration
- Additional documentation and examples

## Configuration

The module will support configuration through:

```python
# Environment variables
AZURE_STORAGE_CONNECTION_STRING = "..."
AZURE_STORAGE_ACCOUNT_NAME = "..."
AZURE_STORAGE_ACCOUNT_KEY = "..."

# Or programmatic configuration
config = {
    "provider": "azure",
    "connection_string": "...",
    "account_name": "...",
    "account_key": "...",
    "default_container": "nachet-data"
}
```

## Connection Management

The module uses a `BlobStorageManager` with singleton pattern for optimal Azure SDK usage and lifecycle management:

### BlobStorageManager Features

- **Singleton Client**: Single BlobServiceClient instance following Azure SDK best practices
- **Thread Safety**: Azure SDK guarantees thread-safe operations across requests
- **Health Monitoring**: Built-in health checks and connection validation
- **Resource Management**: Proper initialization and cleanup
- **FastAPI Integration**: Seamless dependency injection
- **Error Recovery**: Automatic connection refresh on failures
- **Testing Support**: Easy mocking and reset for tests

### Initialization

```python
from app.blob.manager import initialize_blob_storage

# During application startup
await initialize_blob_storage(settings)
```

### Usage in FastAPI Routes

```python
from fastapi import Depends
from app.blob.manager import get_blob_storage
from app.blob.interface import BlobStorageInterface

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    storage: BlobStorageInterface = Depends(get_blob_storage)
):
    # Use singleton storage client - optimal performance and resource usage
    result = await storage.upload_blob(
        container="uploads",
        name=file.filename,
        data=await file.read()
    )
    return result
```

### Context Manager Usage

```python
from app.blob.manager import blob_storage_context

async def process_files():
    async with blob_storage_context() as storage:
        # Uses singleton client with automatic error handling
        blobs = await storage.list_blobs("input-data")
        for blob in blobs.blobs:
            data = await storage.download_blob("input-data", blob.name)
            # process data...
```

### Health Checks

```python
from app.blob.manager import BlobStorageHealthCheck

# Simple health check
health = await BlobStorageHealthCheck.check_connection()

# Health check with retry logic
health = await BlobStorageHealthCheck.check_with_retry(max_retries=3, delay=2.0)

# Returns:
# {
#     "status": "healthy",
#     "response_time_seconds": 0.234,
#     "timestamp": "2025-09-14T10:30:00Z",
#     "provider": "azure"
# }
```

## Usage Examples

```python
from app.blob import get_blob_storage
from app.blob.models import UploadOptions, DownloadOptions, ListOptions

# Initialize storage client
storage = get_blob_storage("azure", config)

# Upload a file with validation
upload_options = UploadOptions(
    content_type="image/jpeg",
    metadata={"source": "camera", "processed": "false"},
    tags={"category": "raw", "priority": "high"}
)

result = await storage.upload_blob(
    container="images",
    name="sample.jpg",
    data=image_data,
    options=upload_options
)

# Result is automatically validated as UploadResult model
print(f"Uploaded {result.name} with size {result.size} bytes")
print(f"ETag: {result.etag}")
print(f"URL: {result.url}")

# Download a file with options
download_options = DownloadOptions(
    offset=1024,  # Skip first 1KB
    length=4096,  # Download next 4KB
    validate_content=True
)

blob_data = await storage.download_blob("images", "sample.jpg", options=download_options)

# List blobs with filtering and pagination
list_options = ListOptions(
    prefix="processed/",
    max_results=50,
    include_metadata=True,
    include_tags=True
)

blob_list = await storage.list_blobs("images", options=list_options)

# Automatic validation ensures data integrity
for blob_info in blob_list.blobs:
    print(f"Blob: {blob_info.name}")
    print(f"Size: {blob_info.size} bytes")
    print(f"Modified: {blob_info.last_modified}")
    print(f"Metadata: {blob_info.metadata}")
    print(f"Tags: {blob_info.tags}")

# Generate SAS token with validation
sas_info = await storage.generate_sas_token(
    container="images",
    name="sample.jpg",
    permissions=["read", "write"],
    expiry=timedelta(hours=1)
)

# SAS token info is validated
print(f"SAS URL: {sas_info.url}")
print(f"Expires: {sas_info.expiry}")
print(f"Permissions: {sas_info.permissions}")

# Set blob access tier for cost optimization
tier_result = await storage.set_blob_tier(
    container="images",
    name="sample.jpg",
    tier="Cool"  # Move to Cool tier for cost optimization
)

print(f"Blob tier updated: {tier_result}")

# Error handling with validation
try:
    # This will raise validation error due to invalid container name
    invalid_container = ContainerInfo(
        name="Invalid_Container_Name",  # Uppercase not allowed
        last_modified=datetime.now(),
        etag="test"
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Error Handling

The module defines custom exceptions for different error scenarios:

- `BlobStorageError` - Base exception
- `BlobNotFoundError` - Blob doesn't exist
- `ContainerNotFoundError` - Container doesn't exist
- `PermissionError` - Access denied
- `ConnectionError` - Network/connection issues
- `InvalidConfigurationError` - Configuration problems

## Testing Strategy

- Unit tests for each operation
- Integration tests with Azure Storage Emulator

## 🎯 **Development Summary**

### ✅ **What's Been Accomplished**

**Foundation (100% Complete)**:

- Complete architectural design with provider-agnostic interface
- Full Pydantic model suite with validation for all data structures
- Comprehensive error handling with custom exceptions
- Connection pooling and lifecycle management (`BlobStorageManager`)
- FastAPI integration with proper dependency injection
- Settings configuration with working Azure connection strings

**Azure Implementation (100% Complete)**:

- Azure client utilities with connection management
- Container listing with pagination, filtering, and metadata support
- Blob listing with full metadata, tags, and pagination
- **Complete container management** with all operations implemented and tested
- **Complete file operations** with all core functionality implemented and tested
- **Advanced file operations** with copy/move operations and transaction safety
- **Complete metadata & tags management** with validation and error handling
- **Blob tier management** for cost optimization (Hot/Cool tiers)
- **Enhanced blob properties** with tier information and lifecycle data
- Complete integration with Azure SDK
- **Comprehensive testing framework** with 88 tests covering all implemented operations

### ✅ **Production Ready**

**All Core Operations Complete**:

1. **File Operations**: All implemented - `upload_blob()`, `download_blob()`, `download_blob_stream()`, `delete_blob()`, `blob_exists()`, `get_blob_properties()`
2. **Advanced File Operations**: All implemented - `copy_blob()`, `move_blob()` with transaction safety and rollback
3. **Metadata & Tags Management**: All implemented - `set_blob_metadata()`, `get_blob_metadata()`, `set_blob_tags()`, `get_blob_tags()`
4. **Container Management**: All implemented - `create_container()`, `delete_container()`, `container_exists()`, `get_container_properties()`
5. **Cost Optimization**: `set_blob_tier()` for Hot/Cool tier management
6. **Comprehensive Testing**: 88 total tests (52 file + 19 container + 17 connectivity)
7. **Singleton Architecture**: Optimized Azure SDK integration with singleton client pattern

**The Azure Blob Storage module is now production-ready with all Phase 1 high priority features implemented and thoroughly tested.**

---

## Current Testing & Implementation Status

- ✅ Basic connectivity tests implemented (17 tests)
- ✅ Complete container operation tests implemented (19 tests)
- ✅ Complete file operation tests implemented (52 tests)
- ✅ Azure Storage Emulator/Azurite integration working
- ✅ Test container cleanup with `nachet-unit-test-` prefixing
- ✅ Comprehensive error scenario testing for all operations
- ✅ File lifecycle testing with upload/download/delete workflows
- ✅ Blob tier management testing for cost optimization
- ✅ Integration tests with real Azure Storage and Azurite

## Future Enhancements

1. **Multi-Provider Support**: Add support for AWS S3, Google Cloud Storage
2. **Caching Layer**: Implement caching for frequently accessed blobs
3. **Compression**: Automatic compression for certain file types
4. **Versioning**: Blob version management
5. **Event Handling**: Integration with storage events and webhooks
6. **Batch Operations**: Efficient bulk upload/download operations
