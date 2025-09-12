import asyncio
import os
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import inspect, text
from app.db.model import Base
from app.api.config import Settings


def run_upgrade(connection, cfg):
    """Run alembic upgrade within a synchronous connection context."""
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


async def validate_migrations():
    """Validate migrations by running them then testing ORM compatibility."""
    try:
        print("🔄 Running migrations on test database...")

        # Run migrations using async pattern

        test_db_url = Settings().db_conn_info["url"]

        temp_db_name = test_db_url.split("///")[-1]
        print(f"Using temporary database at: {temp_db_name}")
        # Ensure clean slate by removing file if it exists (for idempotent tests)
        try:
            os.unlink(temp_db_name)
        except FileNotFoundError:
            pass  # File doesn't exist, which is what we want

        async_engine = create_async_engine(test_db_url, echo=False)

        # Change to the correct directory for alembic to find migrations
        original_cwd = os.getcwd()
        db_dir = os.path.dirname(__file__)  # This is the app/db directory
        os.chdir(db_dir)

        try:
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
        finally:
            os.chdir(original_cwd)
        try:
            # First, run migrations in their own transaction
            async with async_engine.begin() as conn:
                # Check current alembic version before migration
                try:
                    current_version = await conn.run_sync(
                        lambda sync_conn: sync_conn.execute(
                            text("SELECT version_num FROM alembic_version")
                        ).fetchone()
                    )
                    print(
                        f"Current alembic version before migration: {current_version}"
                    )
                except Exception:
                    print("No alembic_version table exists yet")

                await conn.run_sync(run_upgrade, alembic_cfg)
                print("✅ Migrations completed successfully \n\n\n")

            # Now check the results in a separate transaction to ensure visibility
            async with async_engine.begin() as conn:
                # Check alembic version after migration
                try:
                    version_after = await conn.run_sync(
                        lambda sync_conn: sync_conn.execute(
                            text("SELECT version_num FROM alembic_version")
                        ).fetchone()
                    )
                    print(f"Alembic version after migration: {version_after} \n\n\n")
                except Exception as e:
                    print(f"No alembic_version table found after migration: {e}")

                # Check if there are tables already
                existing_tables = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_table_names()
                )

                # Test ORM compatibility by attempting create_all
                print("🔍 Testing ORM create_all compatibility...")
                await conn.run_sync(Base.metadata.create_all)
                print("✅ ORM create_all succeeded - no conflicts detected")
                tables_after_create = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_table_names()
                )

                # Store table info for final summary
                return {
                    "success": True,
                    "existing_tables": existing_tables,
                    "tables_after_create": tables_after_create,
                }

        except Exception as orm_error:
            print(f"❌ ORM create_all failed - conflicts detected: {orm_error}")
            return {"success": False, "error": str(orm_error)}
        finally:
            # Close the engine and cleanup the temporary database
            await async_engine.dispose()
            try:
                os.unlink(temp_db_name)
            except Exception:
                pass  # Ignore cleanup errors

    except Exception as e:
        print(f"❌ Migration validation failed with error: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """Main entry point for migration validation."""
    print("=" * 60)
    print("Running Migration Validation")
    print("=" * 60)

    result = await validate_migrations()

    print("\n" + "=" * 60)
    print("MIGRATION VALIDATION SUMMARY")
    print("=" * 60)

    if isinstance(result, dict) and result.get("success"):
        print("Migration validation: ✅ PASSED")
        print("\n📊 TABLE SUMMARY:")
        print("-" * 40)
        existing = result.get("existing_tables", [])
        after_create = result.get("tables_after_create", [])

        print(f"Tables after migrations: {len(existing)}")
        for table in sorted(existing):
            print(f"  • {table}")

        print(f"\nTables after ORM create_all: {len(after_create)}")
        for table in sorted(after_create):
            print(f"  • {table}")

        # Show differences
        new_tables = set(after_create) - set(existing)
        if new_tables:
            print(
                f"\n⚠️  New tables created by ORM (not in migrations): {len(new_tables)}"
            )
            for table in sorted(new_tables):
                print(f"  • {table}")
        else:
            print("\n✅ No new tables created by ORM - migrations and ORM are in sync")
    else:
        print("Migration validation: ❌ FAILED")
        if isinstance(result, dict) and "error" in result:
            print(f"Error: {result['error']}")

    print("=" * 60)

    return result.get("success", False) if isinstance(result, dict) else result


if __name__ == "__main__":
    asyncio.run(main())
