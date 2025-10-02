# Datastore Directory Structure

This document describes the organization and purpose of directories and files within the Nachet datastore package.

## Root Level

```text
datastore/
├── BinTest/                    # Binary testing utilities
├── bin/                        # Executable scripts and binaries
├── build/                      # Build artifacts and compiled files
├── datastore/                  # Core datastore package source code
├── img/                        # Test images and media files
├── include/                    # Header files and includes
├── lib/                        # Library dependencies
├── nachet/                     # Nachet-specific datastore implementations
├── nachet_datastore.egg-info/  # Package metadata (generated)
├── tests/                      # Test suite
├── doc/                        # Documentation files
├── LICENSE                     # License file
├── README.md                   # Main documentation
├── TESTING.md                  # Testing documentation
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Python dependencies
├── uv.lock                     # UV package manager lock file
└── custom_exceptions.py        # Custom exception definitions
```

## Core Package Structure (`datastore/`)

### Blob Storage (`datastore/blob/`)

```text
blob/
├── __init__.py
├── azure_storage_api/          # Azure Blob Storage integration
│   └── __init__.py
└── storage-download/           # Download utilities
    └── __init__.py
```

### Database Operations (`datastore/db/`)

```text
db/
├── __init__.py
├── metadata/                   # Metadata management
│   ├── __init__.py
│   ├── picture_set/            # Picture set metadata
│   │   └── __init__.py
│   ├── template/               # JSON templates
│   │   ├── picture-empty-template.json
│   │   └── pictureSet-template-system.json
│   └── validator/              # Data validation
│       └── __init__.py
└── queries/                    # Database query modules
    ├── __init__.py
    ├── picture/                # Picture-related queries
    │   └── __init__.py
    └── user/                   # User-related queries
        └── __init__.py
```

## Nachet Implementation (`nachet/`)

### Database Schema and Migrations (`nachet/db/`)

```text
db/
├── bytebase/                   # Database schema migrations
│   ├── *.sql                   # SQL migration files
│   ├── schema_nachet_*.sql     # Schema definitions
│   └── trigger_*.sql           # Database triggers
├── metadata/                   # Nachet metadata handlers
│   ├── inference/              # ML inference metadata
│   ├── machine_learning/       # ML model metadata
│   └── picture/                # Picture metadata
└── queries/                    # Nachet-specific queries
    ├── inference/              # Inference queries
    ├── machine_learning/       # ML queries
    └── seed/                   # Seed identification queries
```

### Documentation (`nachet/doc/`)

```text
doc/
├── deployment-mass-import.md   # Mass import deployment guide
├── inference-feedback.md      # Inference feedback documentation
├── inference-results.md       # Inference results documentation
├── nachet-architecture.md     # System architecture overview
├── nachet-manage-folders.md   # Folder management guide
└── trusted-user-upload.md     # Trusted user upload process
```

## Testing Structure (`tests/`)

### Test Organization

```text
tests/
├── __init__.py
├── nachet/                     # Nachet-specific tests
│   ├── UnProcessedFilesException/  # Exception handling tests
│   ├── db/                     # Database tests
│   │   ├── test_*.py          # Unit tests
│   │   └── *.json             # Test data files
│   ├── *.json                 # Mock inference data
│   └── test_*.py              # Core functionality tests
├── test_*.py                  # General datastore tests
└── test_data_*.sql            # Test database schemas
```

## Key Files and Templates

### Configuration Templates

The following templates are maintained within the package structure:

- `datastore/db/metadata/template/picture-empty-template.json` - Empty picture metadata template
- `datastore/db/metadata/template/pictureSet-template-system.json` - Picture set system template

### Utilities

- `BinTest/` - Binary testing scripts for mass import and picture uploads
- `custom_exceptions.py` - Custom exception definitions

### Generated/Build Artifacts

- `nachet_datastore.egg-info/` - Python package metadata
- `build/` - Compiled build artifacts
- `lib/` and `include/` - Virtual environment dependencies

## Purpose and Function

This datastore package provides:

1. **Database Abstraction** - Unified interface for PostgreSQL operations
2. **Blob Storage Integration** - Azure Blob Storage management
3. **Metadata Management** - Structured handling of picture and inference metadata
4. **Schema Versioning** - Bytebase-managed database migrations
5. **Testing Framework** - Comprehensive test suite for all components
6. **Configuration Management** - Templates and validators for data structures

The structure separates core datastore functionality from Nachet-specific implementations, allowing for modular development and potential reuse across different applications.
