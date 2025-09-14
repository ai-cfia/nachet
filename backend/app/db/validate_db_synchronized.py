import os
import asyncio
from dotenv import load_dotenv
from app.api.config import get_settings
from app.db.utils import sessionmanager, validate_database_startup


async def check_db_synchronization():
    """Check if the database is synchronized with the alembic head."""

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    db_url = settings.db_conn_info["url"]

    db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

    print("\n" + "=" * 60)

    # Initialize SessionManager
    print("\n🔌 Initializing database SessionManager...")
    sessionmanager.init(**settings.db_conn_info)
    async_engine = sessionmanager.get_engine()

    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"

    print(
        f"\n🔍 Checking if the database {db_name} is synchronized with the alembic head..."
    )
    await validate_database_startup(async_engine)


if __name__ == "__main__":
    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")
    # os.environ["TESTING"] = "true" # for debugging the validate_database_startup function

    asyncio.run(check_db_synchronization())
