# SQLAlchemy ORM Model Validation

This document provides comprehensive approaches for validating SQLAlchemy ORM classes to ensure they're properly defined and consistent with database schemas.

## Overview

SQLAlchemy ORM validation helps catch common issues before they cause runtime errors:

- Missing primary keys or table names
- Broken relationship mappings
- Schema inconsistencies between models and database
- Type mismatches and constraint violations
- Invalid foreign key references

## 1. Built-in SQLAlchemy Validation

The simplest validation uses SQLAlchemy's built-in mapper configuration:

```python
from sqlalchemy.orm import configure_mappers
from sqlalchemy.exc import InvalidRequestError

def validate_orm_classes():
    """Validate all registered ORM classes."""
    try:
        # This will raise exceptions if there are mapping issues
        configure_mappers()
        print("✅ All ORM classes are valid")
        return True
    except InvalidRequestError as e:
        print(f"❌ ORM validation failed: {e}")
        return False

# Usage
if __name__ == "__main__":
    from database import Base  # Import your models
    is_valid = validate_orm_classes()
```

## 2. Comprehensive Validation Function

For detailed validation with specific error reporting:

```python
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import InvalidRequestError, ArgumentError
from typing import List, Type, Dict, Any
import logging

def validate_sqlalchemy_models(base_class: Type[DeclarativeBase]) -> Dict[str, Any]:
    """
    Comprehensive validation of SQLAlchemy ORM models.
    
    Returns:
        Dict with validation results and detailed error information
    """
    validation_results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'model_count': 0,
        'relationship_count': 0,
        'models_validated': []
    }
    
    try:
        # Get all registered models
        models = []
        for mapper in base_class.registry.mappers:
            models.append(mapper.class_)
        
        validation_results['model_count'] = len(models)
        
        # Validate each model
        for model in models:
            model_result = validate_single_model(model)
            validation_results['models_validated'].append({
                'name': model.__name__,
                'valid': model_result['valid'],
                'errors': model_result['errors'],
                'warnings': model_result['warnings']
            })
            
            if not model_result['valid']:
                validation_results['valid'] = False
                validation_results['errors'].extend(model_result['errors'])
            
            validation_results['warnings'].extend(model_result['warnings'])
            validation_results['relationship_count'] += model_result['relationship_count']
        
        # Test mapper configuration
        try:
            configure_mappers()
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Mapper configuration failed: {e}")
        
    except Exception as e:
        validation_results['valid'] = False
        validation_results['errors'].append(f"Global validation error: {e}")
    
    return validation_results

def validate_single_model(model_class: Type) -> Dict[str, Any]:
    """Validate a single SQLAlchemy model."""
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'relationship_count': 0
    }
    
    try:
        mapper = inspect(model_class)
        
        # Check table name
        if not hasattr(model_class, '__tablename__'):
            result['errors'].append(f"{model_class.__name__}: Missing __tablename__")
            result['valid'] = False
        
        # Check primary key
        if not mapper.primary_key:
            result['errors'].append(f"{model_class.__name__}: No primary key defined")
            result['valid'] = False
        
        # Validate columns
        for column in mapper.columns:
            column_result = validate_column(model_class.__name__, column)
            if not column_result['valid']:
                result['valid'] = False
                result['errors'].extend(column_result['errors'])
            result['warnings'].extend(column_result['warnings'])
        
        # Validate relationships
        for rel_name, relationship in mapper.relationships.items():
            rel_result = validate_relationship(model_class.__name__, rel_name, relationship)
            if not rel_result['valid']:
                result['valid'] = False
                result['errors'].extend(rel_result['errors'])
            result['warnings'].extend(rel_result['warnings'])
            result['relationship_count'] += 1
        
    except Exception as e:
        result['valid'] = False
        result['errors'].append(f"{model_class.__name__}: Validation error - {e}")
    
    return result

def validate_column(model_name: str, column) -> Dict[str, Any]:
    """Validate a single column."""
    result = {'valid': True, 'errors': [], 'warnings': []}
    
    # Check for nullable primary keys
    if column.primary_key and column.nullable:
        result['warnings'].append(f"{model_name}.{column.name}: Primary key is nullable")
    
    # Check for missing types
    if column.type is None:
        result['errors'].append(f"{model_name}.{column.name}: Missing column type")
        result['valid'] = False
    
    # Check string columns without length
    if hasattr(column.type, 'length') and column.type.length is None:
        if str(column.type).startswith('VARCHAR'):
            result['warnings'].append(f"{model_name}.{column.name}: VARCHAR without length specification")
    
    return result

def validate_relationship(model_name: str, rel_name: str, relationship) -> Dict[str, Any]:
    """Validate a single relationship."""
    result = {'valid': True, 'errors': [], 'warnings': []}
    
    try:
        # Check if target class exists
        if not relationship.mapper:
            result['errors'].append(f"{model_name}.{rel_name}: Cannot resolve target class")
            result['valid'] = False
        
        # Check back_populates consistency
        if hasattr(relationship, 'back_populates') and relationship.back_populates:
            target_class = relationship.mapper.class_
            if not hasattr(target_class, relationship.back_populates):
                result['errors'].append(
                    f"{model_name}.{rel_name}: back_populates '{relationship.back_populates}' "
                    f"not found in {target_class.__name__}"
                )
                result['valid'] = False
        
    except Exception as e:
        result['errors'].append(f"{model_name}.{rel_name}: Relationship validation error - {e}")
        result['valid'] = False
    
    return result
```

## 3. Database Schema Validation

Validate ORM models against actual database schema:

```python
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.schema import CreateTable

def validate_models_against_database(base_class: Type[DeclarativeBase], database_url: str) -> Dict[str, Any]:
    """Validate ORM models against actual database schema."""
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'schema_differences': []
    }
    
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Get database tables
        db_tables = set(inspector.get_table_names())
        
        # Get model tables
        model_tables = set()
        for mapper in base_class.registry.mappers:
            if hasattr(mapper.class_, '__tablename__'):
                model_tables.add(mapper.class_.__tablename__)
        
        # Check for missing tables
        missing_in_db = model_tables - db_tables
        missing_in_models = db_tables - model_tables
        
        if missing_in_db:
            result['warnings'].extend([f"Table '{table}' defined in models but missing in database" for table in missing_in_db])
        
        if missing_in_models:
            result['warnings'].extend([f"Table '{table}' exists in database but missing in models" for table in missing_in_models])
        
        # Validate each table structure
        for mapper in base_class.registry.mappers:
            if hasattr(mapper.class_, '__tablename__'):
                table_result = validate_table_structure(mapper, inspector)
                if not table_result['valid']:
                    result['valid'] = False
                    result['errors'].extend(table_result['errors'])
                result['warnings'].extend(table_result['warnings'])
                result['schema_differences'].extend(table_result['differences'])
    
    except Exception as e:
        result['valid'] = False
        result['errors'].append(f"Database validation error: {e}")
    
    return result

def validate_table_structure(mapper, inspector) -> Dict[str, Any]:
    """Validate individual table structure against database."""
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'differences': []
    }
    
    table_name = mapper.class_.__tablename__
    
    try:
        # Get database columns
        db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
        
        # Get model columns
        model_columns = {col.name: col for col in mapper.columns}
        
        # Compare columns
        for col_name, model_col in model_columns.items():
            if col_name not in db_columns:
                result['differences'].append(f"{table_name}.{col_name}: Column in model but missing in database")
            else:
                db_col = db_columns[col_name]
                # Compare types, nullable, etc.
                type_match = compare_column_types(model_col.type, db_col['type'])
                if not type_match:
                    result['differences'].append(f"{table_name}.{col_name}: Type mismatch - Model: {model_col.type}, DB: {db_col['type']}")
        
        # Check for extra columns in database
        for col_name in db_columns:
            if col_name not in model_columns:
                result['differences'].append(f"{table_name}.{col_name}: Column in database but missing in model")
    
    except Exception as e:
        result['errors'].append(f"Table {table_name} validation error: {e}")
        result['valid'] = False
    
    return result

def compare_column_types(model_type, db_type) -> bool:
    """Compare SQLAlchemy type with database type."""
    # Simplified type comparison - extend as needed
    model_type_str = str(model_type).upper()
    db_type_str = str(db_type).upper()
    
    # Handle common type mappings
    type_mappings = {
        'INTEGER': ['INT', 'INTEGER'],
        'VARCHAR': ['VARCHAR', 'TEXT'],
        'BOOLEAN': ['BOOLEAN', 'BOOL'],
        'DATETIME': ['TIMESTAMP', 'DATETIME'],
        'UUID': ['UUID']
    }
    
    for model_base, db_variants in type_mappings.items():
        if model_base in model_type_str:
            return any(variant in db_type_str for variant in db_variants)
    
    return model_type_str == db_type_str
```

## 4. Testing Integration

Integrate validation with your test suite:

```python
import pytest
from database import Base

def test_orm_model_validation():
    """Test that all ORM models are properly defined."""
    validation_results = validate_sqlalchemy_models(Base)
    
    # Print detailed results
    if not validation_results['valid']:
        print(f"\n❌ ORM Validation Failed:")
        for error in validation_results['errors']:
            print(f"  • {error}")
    
    if validation_results['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in validation_results['warnings']:
            print(f"  • {warning}")
    
    print(f"\n📊 Summary:")
    print(f"  Models validated: {validation_results['model_count']}")
    print(f"  Relationships: {validation_results['relationship_count']}")
    
    assert validation_results['valid'], "ORM model validation failed"

def test_database_schema_consistency():
    """Test that models match database schema."""
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        pytest.skip("Database URL not provided")
    
    validation_results = validate_models_against_database(Base, DATABASE_URL)
    
    # Print schema differences
    if validation_results['schema_differences']:
        print(f"\n🔍 Schema Differences:")
        for diff in validation_results['schema_differences']:
            print(f"  • {diff}")
    
    # Fail if there are critical errors
    assert validation_results['valid'], "Database schema validation failed"
    
    # Warn about differences but don't fail
    if validation_results['schema_differences']:
        print("⚠️  Schema differences detected - review recommended")

def test_individual_models():
    """Test each model individually for detailed reporting."""
    validation_results = validate_sqlalchemy_models(Base)
    
    for model_result in validation_results['models_validated']:
        if not model_result['valid']:
            print(f"\n❌ {model_result['name']} validation failed:")
            for error in model_result['errors']:
                print(f"  • {error}")
        
        if model_result['warnings']:
            print(f"\n⚠️  {model_result['name']} warnings:")
            for warning in model_result['warnings']:
                print(f"  • {warning}")
```

## 5. CLI Validation Tool

Create a standalone validation script:

```python
#!/usr/bin/env python3
"""Database model validation CLI tool."""

import argparse
import sys
import os
from pathlib import Path

def print_detailed_results(validation_results):
    """Print detailed validation results."""
    print(f"\n📊 Validation Summary:")
    print(f"  Models: {validation_results['model_count']}")
    print(f"  Relationships: {validation_results['relationship_count']}")
    print(f"  Status: {'✅ PASSED' if validation_results['valid'] else '❌ FAILED'}")
    
    if validation_results['errors']:
        print(f"\n❌ Errors ({len(validation_results['errors'])}):")
        for error in validation_results['errors']:
            print(f"  • {error}")
    
    if validation_results['warnings']:
        print(f"\n⚠️  Warnings ({len(validation_results['warnings'])}):")
        for warning in validation_results['warnings']:
            print(f"  • {warning}")
    
    # Per-model breakdown
    if validation_results['models_validated']:
        print(f"\n🔍 Per-Model Results:")
        for model in validation_results['models_validated']:
            status = "✅" if model['valid'] else "❌"
            print(f"  {status} {model['name']}")
            if not model['valid']:
                for error in model['errors']:
                    print(f"    • {error}")

def print_database_results(db_results):
    """Print database validation results."""
    print(f"\n🗄️  Database Schema Validation:")
    print(f"  Status: {'✅ CONSISTENT' if db_results['valid'] else '❌ INCONSISTENT'}")
    
    if db_results['errors']:
        print(f"\n❌ Critical Errors:")
        for error in db_results['errors']:
            print(f"  • {error}")
    
    if db_results['schema_differences']:
        print(f"\n🔍 Schema Differences ({len(db_results['schema_differences'])}):")
        for diff in db_results['schema_differences']:
            print(f"  • {diff}")
    
    if db_results['warnings']:
        print(f"\n⚠️  Database Warnings:")
        for warning in db_results['warnings']:
            print(f"  • {warning}")

def main():
    parser = argparse.ArgumentParser(description='Validate SQLAlchemy ORM models')
    parser.add_argument('--database-url', help='Database URL for schema validation')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--models-module', default='database', help='Models module to import')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode - only show errors')
    
    args = parser.parse_args()
    
    # Import models
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path.cwd()))
        module = __import__(args.models_module)
        Base = getattr(module, 'Base')
    except (ImportError, AttributeError) as e:
        print(f"❌ Failed to import models: {e}")
        sys.exit(1)
    
    # Validate ORM models
    if not args.quiet:
        print("🔍 Validating ORM models...")
    
    validation_results = validate_sqlalchemy_models(Base)
    
    if args.verbose or not validation_results['valid']:
        print_detailed_results(validation_results)
    elif not args.quiet:
        status = "✅ PASSED" if validation_results['valid'] else "❌ FAILED"
        print(f"ORM Validation: {status} ({validation_results['model_count']} models)")
    
    # Validate against database if URL provided
    if args.database_url:
        if not args.quiet:
            print("🔍 Validating against database schema...")
        
        db_results = validate_models_against_database(Base, args.database_url)
        
        if args.verbose or not db_results['valid']:
            print_database_results(db_results)
        elif not args.quiet:
            status = "✅ CONSISTENT" if db_results['valid'] else "❌ INCONSISTENT"
            print(f"Schema Validation: {status}")
        
        validation_results['valid'] = validation_results['valid'] and db_results['valid']
    
    # Exit with appropriate code
    if validation_results['valid']:
        if not args.quiet:
            print("\n✅ All validations passed!")
        sys.exit(0)
    else:
        if not args.quiet:
            print("\n❌ Validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Usage Examples

### Basic Validation

```python
# Basic validation
from database import Base

results = validate_sqlalchemy_models(Base)
if results['valid']:
    print("All models are valid!")
else:
    for error in results['errors']:
        print(f"Error: {error}")
```

### Command Line Usage

```bash
# Basic validation
python validate_models.py

# Verbose output
python validate_models.py --verbose

# Include database schema validation
python validate_models.py --database-url postgresql://user:pass@localhost/db

# Quiet mode (only errors)
python validate_models.py --quiet --database-url $DATABASE_URL

# Custom models module
python validate_models.py --models-module app.models --verbose
```

### CI/CD Integration

```yaml
# In .github/workflows/ci.yml
- name: Validate Database Models
  run: |
    cd backend
    python app/controller/db/validate_models.py --database-url ${{ secrets.DATABASE_URL }}
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
```

## Common Validation Issues

### 1. Missing Primary Key

```python
# ❌ Invalid
class BadModel(Base):
    __tablename__ = "bad_model"
    name: Mapped[str] = mapped_column(String(50))

# ✅ Valid
class GoodModel(Base):
    __tablename__ = "good_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
```

### 2. Broken Relationships

```python
# ❌ Invalid - back_populates mismatch
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship("User", back_populates="posts")  # Wrong name!

# ✅ Valid - matching back_populates
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="posts")
```

### 3. Missing Table Name

```python
# ❌ Invalid
class BadModel(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

# ✅ Valid
class GoodModel(Base):
    __tablename__ = "good_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
```

## Best Practices

1. **Run validation regularly** - Include in CI/CD pipeline
2. **Validate before migrations** - Ensure models are correct before generating migrations
3. **Test against multiple environments** - Validate against dev, staging, and production schemas
4. **Use verbose mode during development** - Get detailed feedback on model issues
5. **Fix warnings early** - Address warnings before they become errors
6. **Document validation requirements** - Make validation part of your development process

## Integration with Development Workflow

### Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
echo "Validating database models..."
cd backend
python app/controller/db/validate_models.py --quiet
if [ $? -ne 0 ]; then
    echo "❌ Model validation failed. Commit aborted."
    exit 1
fi
```

### Make Target

```makefile
# In Makefile
.PHONY: validate-models
validate-models:
	cd backend && python app/controller/db/validate_models.py --verbose

.PHONY: validate-models-db
validate-models-db:
	cd backend && python app/controller/db/validate_models.py --database-url $(DATABASE_URL) --verbose
```

This comprehensive validation system helps maintain high-quality ORM models and prevents common deployment issues related to schema mismatches and relationship errors.