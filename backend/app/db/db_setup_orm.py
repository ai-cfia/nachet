# Setup script to initialize the ORM defined database using ORM models.
# This is intended for development and testing use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.

import os
import asyncio
from dotenv import load_dotenv

# import logging
from app.db.utils import (
    sessionmanager,
    reset_database_schema,
    # execute_sql_file,
)
from app.api.config import get_settings
from app.db.model import Base


async def load_database():
    """
    Set up the ORM defined database by resetting and recreating the schema using the ORM models.
    This function is idempotent - it can be run multiple times safely.
    """
    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    db_url = settings.db_conn_info["url"]

    db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

    print("\n" + "=" * 60)
    print(f"🚀 Starting testing database setup for db {db_name}")

    # Initialize SessionManager
    print("\n🔌 Initializing database SessionManager...")
    sessionmanager.init(**settings.db_conn_info)
    async_engine = sessionmanager.get_engine()

    # Reset database to ensure clean state
    await reset_database_schema(async_engine)

    # Create the database schema
    print("\n🔄 Creating database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("\n✅ ORM defined database setup complete.")
    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")
    os.environ["NACHET_SCHEMA"] = "nachet_orm"

    asyncio.run(load_database())
