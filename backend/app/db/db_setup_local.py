# Dev Setup script to initialize the database with necessary tables and data.
# This is intended for development use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.
import os
import asyncio
import logging
from dotenv import load_dotenv
from app.db.utils import (
    run_migrations,
    sessionmanager,
    reset_database_schema,
    execute_sql_file,
    check_if_new_migration_file_needed,
)
from app.api.config import get_settings
from app.db.data.data_seed_local import seed_dev_data
from app.db.validate_orm_online import validate_orm_classes_async
from app.db.validate_orm_alembic import check_migration_file_needed
from app.db.validate_db_synchronized import check_db_synchronization

load_dotenv("../../.env.local")


async def load_database():
    """
    Set up the development database by resetting, running migrations and seeding data.
    This function is idempotent - it can be run multiple times safely.
    """
    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    db_url = settings.db_conn_info["url"]

    db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

    print("\n" + "=" * 60)
    print(f"🚀 Starting development database setup for db {db_name}")

    await validate_orm_classes_async(db_url)

    # Initialize SessionManager
    print("\n🔌 Initializing database SessionManager...")
    db_conn_info = settings.db_conn_info.copy()
    db_conn_info["echo"] = False  # Override echo to suppress SQL output
    sessionmanager.init(**db_conn_info)
    async_engine = sessionmanager.get_engine()

    # Reset database to ensure clean state
    await reset_database_schema(async_engine)

    print("\n🔄 Running migrations...")
    # Set environment variable to control SQLAlchemy logging during migrations

    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"
    await run_migrations(async_engine=async_engine, target_version="head")

    # This check happens here because alembic check does not take into account unapplied migrations
    print("\n🔍 Checking if a new migration file is needed...")
    await check_if_new_migration_file_needed(async_engine)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    print("\n🔍 Validating database synchronization with alembic head...")
    await check_db_synchronization()

    print("\n📊 Loading ISTA seed data...")
    sql_file_path = os.path.join(
        os.path.dirname(__file__), "data", "seed_data_ista_list.sql"
    )
    await execute_sql_file(async_engine, sql_file_path)

    print("\n🌱 Seeding development data...")
    await seed_dev_data(sessionmanager)
    print("\n✅ Development database setup complete.")

    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(load_database())
