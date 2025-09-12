# Alembic Migration Testing Guide

This guide covers various approaches to test Alembic migrations to ensure database schema changes work correctly.

## 1. Basic Migration Test (Up/Down)

Test that migrations can successfully upgrade to the latest version and downgrade back to base:

```python
def test_migration_up_down():
    # Start with clean database
    alembic_cfg = Config("alembic.ini")
    
    # Migrate up to latest
    command.upgrade(alembic_cfg, "head")
    
    # Verify tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "rbac_role" in tables
    
    # Migrate down
    command.downgrade(alembic_cfg, "base")
    
    # Verify tables are gone
    tables = inspector.get_table_names()
    assert "users" not in tables
```

## 2. Step-by-Step Migration Test

Test each migration revision individually to catch issues in specific migrations:

```python
def test_migration_sequence():
    alembic_cfg = Config("alembic.ini")
    
    # Get all revisions
    script = ScriptDirectory.from_config(alembic_cfg)
    revisions = [rev.revision for rev in script.walk_revisions()]
    
    # Test each migration step
    for revision in reversed(revisions):
        command.upgrade(alembic_cfg, revision)
        # Add assertions for expected schema at each step
```

## 3. Data Preservation Test

Ensure that migrations don't lose existing data when transforming schema:

```python
def test_migration_preserves_data():
    # Insert test data in old schema
    old_engine.execute("INSERT INTO old_table VALUES (...)")
    
    # Run migration
    command.upgrade(alembic_cfg, "head")
    
    # Verify data still exists in new schema
    result = new_engine.execute("SELECT * FROM new_table")
    assert len(list(result)) > 0
```

## 4. Schema Validation Test

Compare the final migrated schema against what SQLAlchemy models expect:

```python
def test_migration_matches_models():
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    
    # Create tables from models
    Base.metadata.create_all(temp_engine)
    
    # Compare schemas
    migration_inspector = inspect(migration_engine)
    model_inspector = inspect(temp_engine)
    
    assert migration_inspector.get_table_names() == model_inspector.get_table_names()
```

## 5. Complete Test Suite

A comprehensive pytest test suite for migration validation:

```python
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

@pytest.fixture
def alembic_config():
    return Config("alembic.ini")

@pytest.fixture
def test_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()

def test_migrations_run_successfully(alembic_config, test_engine):
    """Test that all migrations run without errors"""
    alembic_config.set_main_option("sqlalchemy.url", str(test_engine.url))
    
    # Upgrade to head
    command.upgrade(alembic_config, "head")
    
    # Verify tables exist
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    
    expected_tables = ["users", "rbac_role", "folder", "picture", ...]
    for table in expected_tables:
        assert table in tables

def test_downgrade_migrations(alembic_config, test_engine):
    """Test that downgrades work"""
    alembic_config.set_main_option("sqlalchemy.url", str(test_engine.url))
    
    # Up then down
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    
    # Should have no tables
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    assert len(tables) == 0
```

## 6. Test Against Real Database

For more realistic testing, use an actual PostgreSQL database:

```bash
# Create test database
createdb test_migrations

# Run migration tests
NACHET_DATA=postgresql://user:pass@localhost/test_migrations pytest test_migrations.py

# Cleanup
dropdb test_migrations
```

## Key Testing Principles

1. **Forward and Backward**: Test both upgrade and downgrade operations
2. **Data Safety**: Ensure migrations don't lose or corrupt existing data
3. **Schema Consistency**: Verify migrated schema matches model definitions
4. **Isolation**: Each test should start with a clean database state
5. **Real Conditions**: Test against the same database type used in production

## Common Issues to Test For

- **Missing foreign key constraints**: Relationships that work in models but fail in migrations
- **Data type mismatches**: Column types that differ between models and migrations  
- **Index creation failures**: Missing or incorrectly defined indexes
- **Constraint violations**: Data that violates new constraints during migration
- **Circular dependencies**: Migration order issues with foreign keys

The key is testing both the technical correctness of migrations and their ability to preserve data integrity during schema changes.