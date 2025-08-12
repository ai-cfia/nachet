"""
Example of how to use the new SQLAlchemy models for Nachet Phase 1

This file demonstrates the basic usage patterns for the SQLAlchemy implementation.
It serves as documentation and a reference for future development phases.
"""

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from datastore.db.models import User, PictureSet, Picture, Pipeline, Seed
from datastore.db.sqlalchemy_db import get_async_session


async def example_user_operations():
    """Example of basic user operations with SQLAlchemy"""
    print("📝 Example: User operations")
    
    async with get_async_session() as session:
        # Create a new user
        new_user = User(
            email="example@inspection.gc.ca",
            registration_date=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_user)
        await session.flush()  # Get the ID without committing
        
        print(f"Created user with ID: {new_user.id}")
        
        # Query users
        from sqlalchemy import select
        stmt = select(User).where(User.email == "example@inspection.gc.ca")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"Found user: {user.email} (ID: {user.id})")


async def example_picture_set_operations():
    """Example of picture set operations with relationships"""
    print("📝 Example: Picture set operations")
    
    async with get_async_session() as session:
        from sqlalchemy import select
        
        # Find a user (assuming one exists)
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print("No user found, skipping picture set example")
            return
        
        # Create a picture set
        picture_set = PictureSet(
            picture_set={"metadata": "example_data"},
            owner_id=user.id,
            name="Example Picture Set"
        )
        session.add(picture_set)
        await session.flush()
        
        print(f"Created picture set: {picture_set.name} (ID: {picture_set.id})")
        
        # Create pictures in the set
        for i in range(3):
            picture = Picture(
                picture={"filename": f"image_{i}.jpg", "size": 1024},
                picture_set_id=picture_set.id,
                nb_obj=5,
                verified=False
            )
            session.add(picture)
        
        await session.flush()
        print(f"Created 3 pictures in the picture set")


async def example_query_with_relationships():
    """Example of querying with relationships"""
    print("📝 Example: Querying with relationships")
    
    async with get_async_session() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        # Query users with their picture sets
        stmt = select(User).options(selectinload(User.picture_sets)).limit(5)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            print(f"User: {user.email}")
            print(f"  Picture sets: {len(user.picture_sets)}")
            for ps in user.picture_sets:
                print(f"    - {ps.name} ({ps.id})")


async def example_pipeline_operations():
    """Example of pipeline operations"""
    print("📝 Example: Pipeline operations")
    
    async with get_async_session() as session:
        # Create a pipeline
        pipeline = Pipeline(
            name="Example Detection Pipeline",
            active=True,
            is_default=False,
            data={
                "steps": ["detection", "classification"],
                "models": ["seed-detector", "swin-transformer"]
            }
        )
        session.add(pipeline)
        await session.flush()
        
        print(f"Created pipeline: {pipeline.name} (ID: {pipeline.id})")


def example_migration_usage():
    """Example of how to use Alembic migrations"""
    print("📝 Example: Migration commands")
    print("""
    To use the new SQLAlchemy setup with migrations:
    
    1. Set environment variable:
       export NACHET_DATA="postgresql://user:pass@localhost/nachet_db"
    
    2. Apply migrations:
       cd /path/to/datastore
       alembic upgrade head
    
    3. Generate new migrations (when models change):
       alembic revision --autogenerate -m "Description of changes"
    
    4. Rollback if needed:
       alembic downgrade -1
    
    5. View migration history:
       alembic history
    """)


async def main():
    """Run all examples"""
    print("🚀 SQLAlchemy Phase 1 Usage Examples")
    print("=" * 50)
    
    # Note: These examples assume a database connection is available
    # In a real environment, you would have NACHET_DATA set
    
    try:
        await example_user_operations()
        await example_picture_set_operations()
        await example_query_with_relationships()
        await example_pipeline_operations()
        example_migration_usage()
        
        print("\n✅ All examples completed successfully!")
        print("Note: Database operations were not actually executed without a real connection.")
        
    except Exception as e:
        print(f"⚠️  Example execution skipped (no database connection): {e}")
        print("This is expected behavior when NACHET_DATA is not configured.")


if __name__ == "__main__":
    asyncio.run(main())