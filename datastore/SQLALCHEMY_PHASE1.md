# SQLAlchemy Phase 1 Implementation

This document describes the Phase 1 implementation of SQLAlchemy migration for the Nachet datastore, upgrading from schema version `nachet_0.0.12` to `nachet_0.0.13`.

## Overview

Phase 1 focuses on establishing the SQLAlchemy foundation:

- ✅ Add SQLAlchemy and Alembic dependencies
- ✅ Create SQLAlchemy models for existing database schema  
- ✅ Set up database connection and session management
- ✅ Update schema version to `nachet_0.0.13`
- ✅ Create Alembic migration infrastructure
- ✅ Provide usage examples and documentation

## What's New in Phase 1

### 1. Dependencies Added

Updated `pyproject.toml` with:
```toml
dependencies = [
    # ... existing dependencies ...
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0", 
    "asyncpg>=0.29.0",
]
```

### 2. SQLAlchemy Models

Created comprehensive models in `datastore/db/models/`:

- **`base.py`**: Base configuration with `nachet_0.0.13` schema
- **`nachet_models.py`**: Complete model definitions for all tables:
  - `ObjectType`, `User`, `PictureSet`, `Picture`
  - `Pipeline`, `Seed`, `Task`, `Model`, `ModelVersion`
  - `Inference`, `Object`, `PictureSeed`, `SeedObj`
  - `PipelineDefault`, `PipelineModel`

### 3. Database Connection Management

New file `datastore/db/sqlalchemy_db.py` provides:

- **Sync and Async Engines**: Support for both synchronous and asynchronous operations
- **Session Management**: Context managers for proper session handling
- **Connection String Handling**: Automatic conversion for async PostgreSQL
- **Table Management**: Create/drop functionality

### 4. Alembic Migration System

Complete Alembic setup:

- **`alembic.ini`**: Configuration file
- **`alembic/env.py`**: Environment setup with async support
- **Initial Migration**: `20250812_0304_001_initial_sqlalchemy_migration.py`
- **Documentation**: Usage instructions and examples

### 5. Schema Version Update

Updated schema version:
```toml
[tool.nachet-db]
db-schema-version = "0.0.13"
previous-db-schema-version = "0.0.12"
```

## File Structure

```
datastore/
├── pyproject.toml                          # Updated with SQLAlchemy deps
├── alembic.ini                            # Alembic configuration
├── alembic/
│   ├── env.py                             # Async-enabled environment
│   ├── script.py.mako                     # Migration template
│   ├── README                             # Migration usage guide
│   └── versions/
│       └── 20250812_0304_001_initial_sqlalchemy_migration.py
├── datastore/db/
│   ├── models/
│   │   ├── __init__.py                    # Model exports
│   │   ├── base.py                        # Base configuration
│   │   └── nachet_models.py               # All table models
│   └── sqlalchemy_db.py                   # Connection management
├── examples/
│   └── sqlalchemy_usage_example.py        # Usage examples
└── test_sqlalchemy_setup.py               # Verification script
```

## Usage Examples

### Basic Session Usage

```python
from datastore.db.sqlalchemy_db import get_async_session
from datastore.db.models import User

async with get_async_session() as session:
    user = User(email="user@example.com")
    session.add(user)
    # Session automatically commits on successful exit
```

### Querying with Relationships

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async with get_async_session() as session:
    stmt = select(User).options(selectinload(User.picture_sets))
    result = await session.execute(stmt)
    users = result.scalars().all()
```

### Migration Commands

```bash
# Apply all migrations
alembic upgrade head

# Generate new migration
alembic revision --autogenerate -m "Add new feature"

# Rollback one migration
alembic downgrade -1

# View history
alembic history
```

## Environment Setup

Set the database connection string:
```bash
export NACHET_DATA="postgresql://user:password@localhost:5432/nachet_db"
```

## Testing the Setup

Run the verification script:
```bash
cd datastore
python test_sqlalchemy_setup.py
```

## Backward Compatibility

Phase 1 maintains full backward compatibility:

- Existing raw SQL queries continue to work
- Current datastore API remains unchanged
- No breaking changes to existing functionality

## Next Phase Considerations

Future phases might include:

1. **Phase 2**: Gradual replacement of raw SQL queries with SQLAlchemy queries
2. **Phase 3**: Repository pattern implementation
3. **Phase 4**: Complete migration and cleanup of legacy code

## Key Benefits

1. **Type Safety**: SQLAlchemy models provide compile-time type checking
2. **Relationship Management**: Automatic handling of foreign key relationships
3. **Migration System**: Structured database schema evolution
4. **Async Support**: Full async/await compatibility
5. **IDE Support**: Better autocomplete and navigation
6. **Testing**: Easier unit testing with SQLAlchemy test utilities

## Testing

To test the Phase 1 implementation:

1. Set up environment variables
2. Run `alembic upgrade head` to create the new schema
3. Execute example scripts to verify functionality
4. Run existing tests to ensure backward compatibility

## Troubleshooting

Common issues and solutions:

1. **Import Errors**: Ensure all dependencies are installed with `uv sync` or `pip install -r requirements.txt`
2. **Connection Errors**: Verify `NACHET_DATA` environment variable is set correctly
3. **Migration Errors**: Check that the database user has schema creation permissions
4. **Schema Conflicts**: Ensure the `nachet_0.0.13` schema doesn't already exist

## Conclusion

Phase 1 establishes a solid foundation for SQLAlchemy adoption in the Nachet project. The implementation provides modern ORM capabilities while maintaining full backward compatibility with existing code.