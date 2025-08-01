# Datastore Testing Guide

This guide explains how to set up and run tests for the Nachet datastore package.

## Prerequisites

- PostgreSQL database server running
- Azure Storage Emulator (Azurite) running on `localhost:10000` for blob storage tests
- Python dependencies installed (`uv sync` or `pip install -r requirements.txt`)
- Environment variables configured

## Environment Setup

1. Configure your test database and blob storage environment variables in `.env.test`:

   ```bash
   PG_TEST_DB="nachet-test"
   PG_TEST_USER="postgres"
   PG_TEST_PASS="postgres"
   PG_TEST_HOST="localhost"
   PG_TEST_PORT="12432"

   # Required for datastore tests
   NACHET_DB_URL="postgresql://postgres:postgres@localhost:12432/nachet-test"
   NACHET_SCHEMA="nachet_0.0.12"
   NACHET_STORAGE_URL="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;"
   NACHET_BLOB_ACCOUNT="devstoreaccount1"
   NACHET_BLOB_KEY="Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
   ```

2. Ensure your PostgreSQL server is running and accessible with these credentials.

3. **For blob storage tests**: Start Azure Storage Emulator (Azurite):

   ```bash
   # Using Docker
   docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite
   
   # Or using npm (if installed globally)
   azurite --silent --location /tmp/azurite --debug /tmp/azurite/debug.log
   ```

## Running Tests

### Step 1: Set up the test database schema

Before running tests, you need to set up the database schema and load test data:

```bash
cd /home/p4r0d1m3pxz/work/nachet/datastore

# Load environment variables and run database setup
set -a && source .env.test && set +a && uv run python tests/test_setup.py
```

This will:

- Create the `nachet_0.0.12` schema in your test database
- Apply the database structure from `nachet/db/bytebase/schema_nachet_0.0.12.sql`
- Load constants from `nachet/db/bytebase/constants_nachet_0.0.12.sql`
- Insert test data from `tests/test_data_nachet_0.0.12.sql`

### Step 2: Run the tests

```bash
# Run all tests with verbose output
set -a && source .env.test && set +a && uv run python -m pytest tests/ -v

# Run specific test files
set -a && source .env.test && set +a && uv run python -m pytest tests/test_datastore.py -v
set -a && source .env.test && set +a && uv run python -m pytest tests/nachet/db/test_metadata.py -v
```

### Step 3: Clean up (optional)

After testing, you can clean up the test database:

```bash
# This will drop the test schema and all its data
set -a && source .env.test && set +a && uv run python tests/test_cleanup.py
```

## Test Structure

- `tests/test_setup.py` - Database schema setup script
- `tests/test_cleanup.py` - Database cleanup script  
- `tests/test_data_nachet_0.0.12.sql` - Test data for the database
- `tests/nachet/db/` - Database-specific tests
- `tests/test_*.py` - Various component tests

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running on the specified host/port
- Check that the database specified in `PG_TEST_DB` exists
- Ensure the user has sufficient privileges to create/drop schemas

### Blob Storage Connection Issues

- **Tests timeout or fail with authentication errors**: Ensure Azurite is running on `localhost:10000`
- **"Server failed to authenticate" errors**: Check that the `NACHET_STORAGE_URL` includes the correct `BlobEndpoint=http://localhost:10000/devstoreaccount1;`
- **Connection refused errors**: Start Azurite before running tests that interact with blob storage
- For tests that require blob storage (like `test_datastore.py`), Azurite must be running

### Schema Version Mismatch

- The schema version is read from `pyproject.toml` under `[tool.nachet-db].db-schema-version`
- Ensure the corresponding SQL files exist in `nachet/db/bytebase/`

### Test Data Issues

- If tests fail due to missing data, re-run the setup script
- Check that `test_data_nachet_0.0.12.sql` contains the expected test records

### Test Types

- **Database-only tests**: Tests like those in `tests/nachet/db/` only require PostgreSQL
- **Full integration tests**: Tests like `test_datastore.py` require both PostgreSQL and Azurite running
