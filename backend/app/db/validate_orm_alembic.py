import os
import asyncio
from dotenv import load_dotenv
from app.api.config import get_settings
from app.db.utils import sessionmanager, check_if_new_migration_file_needed


async def check_migration_file_needed():
    """Check if a new migration file is needed."""

    settings = get_settings()
    if settings is None:
        raise ValueError("Settings instance could not be created")

    # db_url = settings.db_conn_info["url"]

    # db_name = settings.db_name if db_url.startswith("postgresql") else "SQLite"

    print("\n" + "=" * 60)

    # Initialize SessionManager
    print("\n🔌 Initializing database SessionManager...")
    sessionmanager.init(**settings.db_conn_info)
    async_engine = sessionmanager.get_engine()

    os.environ["SQLALCHEMY_MIGRATION_LOG_LEVEL"] = "WARNING"
    os.environ["ALEMBIC_MIGRATION_LOG_LEVEL"] = "WARNING"

    print(
        "\n🔍 Checking if a new migration file is needed to match the current ORM state"
    )
    await check_if_new_migration_file_needed(async_engine)


if __name__ == "__main__":
    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv("../../.env.local")

    asyncio.run(check_migration_file_needed())
