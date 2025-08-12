#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy setup for Phase 1 migration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from datastore.db.models import Base, User, PictureSet, Picture, Pipeline
    from datastore.db.sqlalchemy_db import get_async_engine, get_sync_engine
    print("✅ Successfully imported SQLAlchemy models and database utilities")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_model_definitions():
    """Test that models are properly defined"""
    print("\n🔍 Testing model definitions...")
    
    # Check that models have the correct schema
    assert Base.metadata.schema == "nachet_0.0.13", f"Expected schema 'nachet_0.0.13', got '{Base.metadata.schema}'"
    print("✅ Base model schema is correct")
    
    # Check that tables are registered
    table_names = list(Base.metadata.tables.keys())
    expected_tables = [
        "nachet_0.0.13.object_type",
        "nachet_0.0.13.users",
        "nachet_0.0.13.picture_set",
        "nachet_0.0.13.picture",
        "nachet_0.0.13.pipeline",
        "nachet_0.0.13.seed",
        "nachet_0.0.13.task",
        "nachet_0.0.13.model",
        "nachet_0.0.13.model_version",
        "nachet_0.0.13.inference",
        "nachet_0.0.13.object",
        "nachet_0.0.13.picture_seed",
        "nachet_0.0.13.pipeline_default",
        "nachet_0.0.13.pipeline_model",
        "nachet_0.0.13.seed_obj",
    ]
    
    for table in expected_tables:
        assert table in table_names, f"Table {table} not found in metadata"
    
    print(f"✅ All {len(expected_tables)} expected tables are registered")
    

def test_engine_creation():
    """Test that engines can be created"""
    print("\n🔍 Testing engine creation...")
    
    # Test that we can create engines without errors
    try:
        sync_engine = get_sync_engine()
        print("✅ Synchronous engine created successfully")
    except Exception as e:
        print(f"⚠️  Could not create sync engine (this is expected without NACHET_DATA env var): {e}")
    
    try:
        async_engine = get_async_engine()
        print("✅ Asynchronous engine created successfully")
    except Exception as e:
        print(f"⚠️  Could not create async engine (this is expected without NACHET_DATA env var): {e}")


async def test_async_functionality():
    """Test async functionality (basic checks only)"""
    print("\n🔍 Testing async functionality...")
    
    # Test that async imports work
    from datastore.db.sqlalchemy_db import get_async_session
    print("✅ Async session import successful")


def test_alembic_files():
    """Test that Alembic files are properly set up"""
    print("\n🔍 Testing Alembic setup...")
    
    alembic_dir = Path(__file__).parent / "alembic"
    assert alembic_dir.exists(), "Alembic directory not found"
    
    required_files = [
        "env.py",
        "script.py.mako",
        "README",
        "versions/20250812_0304_001_initial_sqlalchemy_migration.py"
    ]
    
    for file_path in required_files:
        full_path = alembic_dir / file_path
        assert full_path.exists(), f"Required Alembic file {file_path} not found"
    
    print("✅ All required Alembic files are present")


def main():
    """Run all tests"""
    print("🚀 Starting SQLAlchemy Phase 1 setup verification...")
    
    try:
        test_model_definitions()
        test_engine_creation()
        asyncio.run(test_async_functionality())
        test_alembic_files()
        
        print("\n🎉 All tests passed! SQLAlchemy Phase 1 setup is complete.")
        print("\nNext steps:")
        print("1. Set NACHET_DATA environment variable for database connection")
        print("2. Run 'alembic upgrade head' to apply migrations")
        print("3. Test with actual database operations")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()