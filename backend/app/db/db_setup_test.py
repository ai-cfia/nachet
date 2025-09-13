# Tesst database setup script to initialize the database with necessary tables and data.
# This is intended for ci test use only and should not be run in production.
# This script is idempotent - it can be run multiple times safely.
import os
import asyncio
import logging
from tqdm import tqdm
from sqlalchemy import text
from app.db.utils import run_migrations, sessionmanager
from app.api.config import get_settings
from app.db.data.data_seed_test import seed_test_data


async def reset_database_schema(async_engine):
    """
    Reset the database by dropping and recreating the schema.
    This ensures a clean state for development.
    """
    print("🗑️  Resetting database schema...")

    async with async_engine.begin() as conn:
        # Drop and recreate the schema
        db_schema = os.getenv("NACHET_SCHEMA")
        db_user = os.getenv("DB_USER")
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {db_schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {db_schema}"))
        # Restore default permissions
        await conn.execute(text(f"GRANT ALL ON SCHEMA {db_schema} TO {db_user}"))
        await conn.execute(text(f"GRANT ALL ON SCHEMA {db_schema} TO public"))

    print("✅ Database schema reset complete")


async def execute_sql_file(async_engine, sql_file_path):
    """Execute a SQL file using the provided async engine."""
    print(f"📄 Executing SQL file: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as file:
        # read 15 lines
        sql_content = "".join([next(file) for _ in range(15)])

    # Split SQL statements (basic splitting on semicolons)
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    async with async_engine.begin() as conn:
        with tqdm(
            total=len(statements), desc="   Executing SQL statements", unit="stmt"
        ) as pbar:
            for i, statement in enumerate(statements):
                if statement:  # Skip empty statements
                    try:
                        await conn.execute(text(statement))
                        pbar.update(1)
                    except Exception as e:
                        print(f"\n❌ Error executing statement {i + 1}: {e}")
                        print(f"   Statement: {statement[:100]}...")
                        raise

    print(f"✅ Successfully executed {len(statements)} SQL statements")


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

    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"
    await run_migrations(async_engine=async_engine, target_version="head")

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    print("\n📊 Loading ISTA seed data...")
    sql_file_path = os.path.join(
        os.path.dirname(__file__), "data", "seed_data_ista_list.sql"
    )
    await execute_sql_file(async_engine, sql_file_path)

    print("\n🌱 Seeding test data...")
    await seed_test_data(sessionmanager)
    print("\n✅ Testing database setup complete.")
    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(load_database())
