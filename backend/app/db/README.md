# Database Module (`backend/app/db`)

This module provides database management functionality for the Nachet seed identification system, including ORM models, database utilities, migrations, and validation tools.

## Overview

The database module manages a PostgreSQL database with the `nachet` schema, handling user authentication, image metadata, ML model information, and inference results. It uses SQLAlchemy ORM with async support and Alembic for database migrations.

## Core Components

### ORM Models (`model.py`)

Defines SQLAlchemy models for the database schema:

- **Base**: SQLAlchemy declarative base with async support
- **User**: User accounts and authentication
- **Picture**: Image metadata and storage references
- **PictureSet**: Collections of related pictures
- **Inference**: ML model inference results
- **InferenceResult**: Individual inference predictions
- **Model**: ML model configurations and metadata
- **ModelTask**: Categorization of model types
- **Seed**: Seed classification data

Key features:

- UUID-based primary keys for security
- Automatic timestamps (`date_created`, `date_updated`)
- JSON metadata columns for flexible data storage
- Foreign key relationships with proper cascading

### Database Utilities (`utils.py`)

Core database management functions:

- **SessionManager**: Async database session management with connection pooling
- **Database operations**: Schema reset, initialization, cleanup
- **Alembic integration**: Migration execution and validation
- **SQL execution**: Direct SQL command execution utilities

### Setup Scripts

- **`db_setup_orm.py`**: Initialize database schema using ORM models (development)
- **`db_setup_test.py`**: Test database setup and teardown
- **`db_setup_local.py`**: Local development database initialization

### Validation Tools

- **`validate_orm_online.py`**: Runtime ORM validation with database connection
- **`validate_orm_offline.py`**: Offline ORM class validation
- **`validate_db_synchronized.py`**: Check database sync with Alembic migrations

### Migration System (`alembic/`)

- **`alembic.ini`**: Alembic configuration with custom file naming
- **`env.py`**: Migration environment setup
- **`versions/`**: Database migration scripts

## Usage

### Running Database Tests

```bash
# Run all database tests
cd backend/app/db
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_basic_connectivity.py -v
uv run pytest tests/test_utils_session_manager.py -v
```

### Database Validation

```bash
# Validate ORM models with database connection
cd backend/app/db
uv run python validate_orm_online.py

# Check database synchronization with migrations
uv run python validate_db_synchronized.py

# Offline ORM validation
uv run python validate_orm_offline.py
```

### Database Setup (Development)

```bash
# Initialize database with ORM models
cd backend/app/db
uv run python db_setup_orm.py

# Setup test database
uv run python db_setup_test.py
```

### Migration Management

```bash
# Generate new migration
cd backend/app/db
export $(grep -v '^#' ../../.env.local | xargs)
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current migration status
alembic current
```

## Test Coverage

Comprehensive test suite covering:

- **Basic connectivity**: Database connection and session management
- **Session management**: Async session lifecycle and pooling
- **Schema operations**: Database reset and initialization
- **Alembic integration**: Migration execution and context management
- **SQL execution**: Direct SQL command execution
- **Cleanup operations**: Temporary database cleanup

## Architecture Notes

### Async Pattern

- Uses SQLAlchemy async engine with `AsyncSession`
- Session management through dependency injection
- Proper async context management for connections

### Security Features

- UUID-based entity IDs for multi-tenant isolation
- No sensitive data logging in production mode
- Encrypted model credentials support
- Proper connection string handling

### Development vs Production

- Development scripts are marked as non-production safe
- Separate configuration for test environments
- Environment-specific connection handling
- Comprehensive validation before deployment

## Dependencies

- **SQLAlchemy**: ORM and database abstraction
- **Alembic**: Database migration management
- **psycopg**: PostgreSQL async driver
- **aiosqlite**: SQLite async driver (testing)
- **pytest**: Testing framework
- **python-dotenv**: Environment configuration
