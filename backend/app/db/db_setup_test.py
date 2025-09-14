# Tesst database setup script to initialize the database with necessary tables and data.
# This is intended for ci test use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.
import os
import asyncio

# import logging
from app.db.utils import (
    run_migrations,
    sessionmanager,
    reset_database_schema,
    execute_sql_file,
)
from app.api.config import get_settings
from app.db.data.data_seed_test import seed_test_data


async def load_database():
    """
    Set up the testing database by resetting, running migrations and seeding data.
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

    print("\n🔄 Running migrations...")
    # Set environment variable to control SQLAlchemy logging during migrations

    # os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    # os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"
    await run_migrations(async_engine=async_engine, target_version="head")

    # logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    print("\n📊 Loading ISTA seed data...")
    sql_file_path = os.path.join(
        os.path.dirname(__file__), "data", "seed_data_ista_test.sql"
    )
    await execute_sql_file(async_engine, sql_file_path)

    print("\n🌱 Seeding test data...")
    await seed_test_data(sessionmanager)
    print("\n✅ Testing database setup complete.")
    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(load_database())
