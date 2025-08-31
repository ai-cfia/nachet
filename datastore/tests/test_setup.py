#!/usr/bin/env python3
"""
Test database setup script that mimics the GitHub Actions workflow.
This script sets up the test database schema and populates it with test data.
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
        sys.exit(1)


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


def setup_database():
    """Set up the test database schema and data."""
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
    env["PGPASSWORD"] = pg_password

    # Get schema version
    schema_version = get_schema_version()
    schema_name = f"nachet_{schema_version}"

    # Define file paths
    base_path = Path.cwd()
    schema_file = (
        base_path / "nachet" / "db" / "bytebase" / f"schema_nachet_{schema_version}.sql"
    )
    constants_file = (
        base_path
        / "nachet"
        / "db"
        / "bytebase"
        / f"constants_nachet_{schema_version}.sql"
    )
    test_data_file = base_path / "tests" / f"test_data_nachet_{schema_version}.sql"

    # Check if required files exist
    missing_files = []
    for file_path in [schema_file, constants_file, test_data_file]:
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print("Error: Missing required SQL files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        sys.exit(1)

    print(f"Drop testing database if it exists: {pg_db}")
    drop_db_cmd = f"dropdb -h {pg_host} -p {pg_port} -U {pg_user} --if-exists {pg_db}"
    run_command(drop_db_cmd, env=env)

    print(f"Creating a database: {pg_db} on {pg_host}:{pg_port} as user {pg_user}")
    create_db_cmd = f"createdb -h {pg_host} -p {pg_port} -U {pg_user} {pg_db}"
    run_command(create_db_cmd, env=env)

    print(f"Setting up database schema: {schema_name}")

    # Step 1: Create schema
    print("Creating schema...")
    create_schema_cmd = f'psql -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -c "CREATE SCHEMA IF NOT EXISTS \\"{schema_name}\\""'
    run_command(create_schema_cmd, env=env)

    # Step 2: Apply schema file
    print("Applying schema structure...")
    schema_cmd = f"psql --set ON_ERROR_STOP=1 -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -f {schema_file}"
    run_command(schema_cmd, env=env)

    # Step 3: Apply constants file
    print("Applying constants data...")
    constants_cmd = f"psql --set ON_ERROR_STOP=1 -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -f {constants_file}"
    run_command(constants_cmd, env=env)

    # Step 4: Apply test data file
    print("Applying test data...")
    test_data_cmd = f"psql --set ON_ERROR_STOP=1 -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -f {test_data_file}"
    run_command(test_data_cmd, env=env)

    # Step 5: Verify setup
    print("Verifying schema setup...")
    verify_cmd = f'psql -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -c "\\dt \\"{schema_name}\\".*" -c "\\df \\"{schema_name}\\".*" -c "SELECT * FROM \\"{schema_name}\\".seed;"'
    result = run_command(verify_cmd, env=env)
    print("Verification output:")
    print(result)

    # Step 6: Verify critical test data was loaded
    print("Verifying test data...")
    verification_queries = [
        f'SELECT COUNT(*) as model_count FROM \\"{schema_name}\\".model',
        f'SELECT COUNT(*) as pipeline_count FROM \\"{schema_name}\\".pipeline',
        f'SELECT COUNT(*) as pipeline_model_count FROM \\"{schema_name}\\".pipeline_model',
        f'SELECT COUNT(*) as user_count FROM \\"{schema_name}\\".users',
    ]

    for query in verification_queries:
        result = run_command(
            f'psql -h {pg_host} -p {pg_port} -U {pg_user} -d {pg_db} -t -c "{query}"',
            env=env,
        )
        count = int(result.strip())
        table_name = query.split("as ")[1].split(" ")[0].replace("_count", "")
        print(f"  {table_name}: {count} records")
        if count == 0:
            print(f"ERROR: No {table_name} found in test data!")
            sys.exit(1)

    print("Test data verification passed!")

    print("Database setup completed successfully!")
    print(f"Schema: {schema_name}")
    print(f"Connection: postgresql://{pg_user}:***@{pg_host}:{pg_port}/{pg_db}")


def main():
    """Main entry point."""
    print("Setting up test database...")

    # Change to datastore directory if not already there
    if not Path("pyproject.toml").exists():
        print("Error: Must be run from the datastore directory")
        sys.exit(1)

    setup_database()


if __name__ == "__main__":
    main()
