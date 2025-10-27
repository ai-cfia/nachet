#!/usr/bin/env python3
"""
Test database cleanup script.
This script drops the test database schema and all its data.
"""

import os
import subprocess
import sys
import toml
from pathlib import Path


def run_command(command, env=None, shell=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, shell=shell, check=True, capture_output=True, text=True, env=env
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error: {e.stderr}")
        return None


def get_schema_version():
    """Extract schema version from pyproject.toml."""
    try:
        config = toml.load("pyproject.toml")
        version = config["tool"]["nachet-db"]["db-schema-version"]
        print(f"Schema version: {version}")
        return version
    except Exception as e:
        print(f"Failed to extract schema version: {e}")
        sys.exit(1)


def cleanup_database():
    """Clean up the test database schema."""
    # Get required environment variables
    pg_host = os.getenv("PG_TEST_HOST", "127.0.0.1")
    pg_port = os.getenv("PG_TEST_PORT", "5432")
    pg_user = os.getenv("PG_TEST_USER")
    pg_db = os.getenv("PG_TEST_DB")
    pg_password = os.getenv("PG_TEST_PASS")

    if not all([pg_user, pg_db, pg_password]):
        print("Error: Missing required environment variables:")
        print("Required: PG_TEST_USER, PG_TEST_DB, PG_TEST_PASS")
        print(
            "Optional: PG_TEST_HOST (default: 127.0.0.1), PG_TEST_PORT (default: 5432)"
        )
        sys.exit(1)

    # Set up environment for psql commands
    env = os.environ.copy()
    if pg_password:
        env["PGPASSWORD"] = pg_password

    print(f"check testing database if it exists: {pg_db}")
    check_db_cmd = f"psql -h {pg_host} -p {pg_port} -U {pg_user} -lqt | cut -d \\| -f 1 | grep -w {pg_db}"
    db_exists = run_command(check_db_cmd, env=env)
    if not db_exists:
        print(f"Database {pg_db} does not exist. Nothing to clean up.")
        sys.exit(0)

    # Get schema version
    schema_version = get_schema_version()
    schema_name = f"nachet_{schema_version}"

    print(f"Cleaning up database schema: {schema_name}")

    # Drop schema with CASCADE to remove all objects
    print("Dropping schema and all its objects...")
    drop_schema_cmd = f'psql -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -c "DROP SCHEMA IF EXISTS \\"{schema_name}\\" CASCADE;"'
    result = run_command(drop_schema_cmd, env=env)

    if result is not None:
        print(f"Schema {schema_name} has been dropped successfully!")
    else:
        print(f"Failed to drop schema {schema_name}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clean up test database schema")
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt and force cleanup",
    )
    args = parser.parse_args()

    print("Cleaning up test database...")

    # Change to datastore directory if not already there
    if not Path("pyproject.toml").exists():
        print("Error: Must be run from the datastore directory")
        sys.exit(1)

    # Ask for confirmation unless forced
    if not args.force:
        response = input(
            "Are you sure you want to drop the test database schema? This will delete all test data. (y/N): "
        )
        if response.lower() not in ["y", "yes"]:
            print("Cleanup cancelled.")
            sys.exit(0)
    else:
        print("Force cleanup mode - skipping confirmation.")

    cleanup_database()


if __name__ == "__main__":
    main()
