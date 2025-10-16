"""
Shared fixtures for integration tests.

These fixtures provide real database connections and test data
for integration testing without mocks.
"""

import os
import pytest
import pytest_asyncio
from uuid import UUID
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


@pytest_asyncio.fixture(scope="session")
async def init_db():
    """
    Initialize the database sessionmanager for the test session.

    This fixture runs once per test session and:
    1. Checks if the test database schema exists
    2. If NOT found: Automatically runs app/db/db_setup_test.py
    3. Initializes the sessionmanager with the test database connection

    The database setup is automatic - you don't need to manually run any scripts!

    Requirements:
    - PostgreSQL server accessible at DB_HOST:DB_PORT
    - Credentials in .env.test.local (DB_USER, DB_PASSWORD, DB_NAME)
    """
    from app.db.utils import sessionmanager
    import subprocess

    # Build database URL from environment variables
    db_user = os.getenv("DB_USER", "nachetuser")
    db_password = os.getenv("DB_PASSWORD", "nachetpass")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "12432")
    db_name = os.getenv("DB_NAME", "nachetdb")
    db_schema = os.getenv("NACHET_SCHEMA", "nachet-backend-test")

    database_url = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?options=-c%20search_path%3D{db_schema}"

    # Verify database connection is available
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password
    check_cmd = f'psql -h {db_host} -p {db_port} -U {db_user} -d {db_name} -c "SELECT 1 FROM \\"{db_schema}\\".seed LIMIT 1" 2>&1'
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        # Database schema not found - try to set it up automatically
        print("\n" + "="*77)
        print("Test database schema not found. Running automatic setup...")
        print("="*77 + "\n")

        # Find the database setup script
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/
        setup_script = backend_dir / "app" / "db" / "db_setup_test.py"

        if not setup_script.exists():
            error_msg = f"""
=============================================================================
ERROR: Cannot find database setup script!

Expected location: {setup_script}

The integration tests require a PostgreSQL database with the nachet schema.

Manual setup:
    cd {backend_dir}
    python app/db/db_setup_test.py
=============================================================================
"""
            pytest.skip(error_msg)

        # Run the setup script (it uses settings from .env.test.local automatically)
        try:
            print(f"Running: python {setup_script}")
            result = subprocess.run(
                ["python", str(setup_script)],
                cwd=str(backend_dir),
                env=env,  # Uses environment with loaded .env.test.local
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print("\n" + "="*77)
                print("✓ Database setup completed successfully!")
                print("="*77 + "\n")
                print(result.stdout)
            else:
                error_msg = f"""
=============================================================================
ERROR: Database setup script failed!

Exit code: {result.returncode}

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
=============================================================================
"""
                pytest.skip(error_msg)
        except subprocess.TimeoutExpired:
            pytest.skip("Database setup script timed out after 5 minutes")
        except Exception as e:
            pytest.skip(f"Failed to run database setup script: {e}")

    # Initialize sessionmanager
    sessionmanager.init(
        url=database_url,
        echo=False,  # Set to True for SQL debugging
        pool_size=5,
        max_overflow=10,
    )

    yield

    # Cleanup: close the sessionmanager
    await sessionmanager.close()


@pytest_asyncio.fixture(scope="function")
async def integration_db_session(init_db):
    """
    Provide a real async database session for integration tests.

    IMPORTANT: This session COMMITS data to make it visible across multiple sessions.
    The service layer opens NEW sessions for RBAC and queries, so test data must be committed.

    Usage in tests:
        1. Add test data to session: session.add(entity)
        2. COMMIT immediately: await session.commit()  # Makes data visible to service layer
        3. Track for cleanup: cleanup_list.append(entity.id)

    Cleanup happens via the cleanup_test_seeds fixture which tracks and deletes test data.

    No mocks - this is a real connection to the test PostgreSQL database.
    """
    from app.db.utils import sessionmanager

    async with sessionmanager.get_session() as session:
        yield session
        # Final commit at end (data should already be committed during test)
        # Cleanup happens in cleanup_test_seeds fixture
        await session.commit()


@pytest_asyncio.fixture(scope="session")
def test_organization() -> UUID:
    """
    Return the pre-seeded test organization UUID from db_setup_test.py.

    This organization is created during database setup with admin roles already configured.

    Returns:
        UUID of the pre-seeded test organization: 12345678-1234-1234-1234-123456789012
    """
    return UUID("12345678-1234-1234-1234-123456789012")


@pytest_asyncio.fixture(scope="session")
def test_user() -> UUID:
    """
    Return the pre-seeded test user UUID from db_setup_test.py.

    This user is created during database setup and is already associated with
    the test organization, so RBAC checks will pass.

    User details:
        - ID: 8ea46a6b-7d37-4fbb-a66f-775112376e16
        - Email: test.user@inspection.gc.ca
        - Organization: 12345678-1234-1234-1234-123456789012
        - Role: Admin (87654321-4321-4321-4321-210987654321)

    Returns:
        UUID of the pre-seeded test user
    """
    return UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16")


@pytest_asyncio.fixture(scope="session")
def test_admin_user() -> UUID:
    """
    Return the pre-seeded test user UUID (who has admin role).

    The pre-seeded test user already has the Admin role assigned, so we can
    use the same user for admin operations.

    User details:
        - ID: 8ea46a6b-7d37-4fbb-a66f-775112376e16
        - Email: test.user@inspection.gc.ca
        - Organization: 12345678-1234-1234-1234-123456789012
        - Role: Admin (87654321-4321-4321-4321-210987654321)

    Returns:
        UUID of the pre-seeded admin user
    """
    return UUID("8ea46a6b-7d37-4fbb-a66f-775112376e16")


@pytest_asyncio.fixture(scope="session")
def test_regular_user() -> UUID:
    """
    Return a user UUID that does NOT have CFIA admin role.

    This user is associated with the test organization but lacks the CFIA admin
    role, so they should be denied for CUD operations on seeds.

    For integration tests, we can use a random UUID since the RBAC check
    will fail because this user_id is not in rbac_user_role table with CFIA admin role.

    Returns:
        UUID of a non-admin test user
    """
    # This UUID is not in the rbac_user_role table, so RBAC will deny access
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture(scope="function")
async def cleanup_test_seeds(integration_db_session: AsyncSession):
    """
    Cleanup fixture to track and remove test seeds created during tests.

    Yields a list that tests can append seed IDs to for cleanup.
    """
    created_seed_ids = []

    yield created_seed_ids

    # Cleanup: hard delete test seeds
    if created_seed_ids:
        from app.db.model import Seed
        from sqlalchemy import delete

        stmt = delete(Seed).where(Seed.id.in_(created_seed_ids))
        await integration_db_session.execute(stmt)
        await integration_db_session.flush()


@pytest_asyncio.fixture(scope="function")
async def cleanup_test_organizations(integration_db_session: AsyncSession):
    """
    Cleanup fixture to track and remove test organizations and their RBAC roles.

    Organizations have associated RBAC roles that must be deleted first due to
    foreign key constraints. This fixture handles cleanup in the correct order:
    1. Delete RBAC roles associated with the organization
    2. Delete the organization itself

    Yields a list that tests can append organization IDs to for cleanup.
    """
    created_organization_ids = []

    yield created_organization_ids

    # Cleanup: hard delete organizations and their roles
    if created_organization_ids:
        from app.db.model import Organization, RbacRole
        from sqlalchemy import delete

        # First delete RBAC roles associated with these organizations
        role_stmt = delete(RbacRole).where(
            RbacRole.organization_id.in_(created_organization_ids)
        )
        await integration_db_session.execute(role_stmt)

        # Then delete the organizations
        org_stmt = delete(Organization).where(
            Organization.id.in_(created_organization_ids)
        )
        await integration_db_session.execute(org_stmt)
        await integration_db_session.flush()


@pytest_asyncio.fixture(scope="function")
async def cleanup_test_users(integration_db_session: AsyncSession):
    """
    Cleanup fixture to track and remove test users.

    Users may have foreign key dependencies from folders, annotations, and objects.
    This fixture performs hard delete of users after first deleting dependent folders.

    Order of deletion:
    1. Delete folders associated with the users
    2. Delete the users themselves

    Yields a list that tests can append user IDs to for cleanup.
    """
    created_user_ids = []

    yield created_user_ids

    # Cleanup: hard delete folders first, then users
    if created_user_ids:
        from app.db.model import Users, Folder
        from sqlalchemy import delete

        # First delete folders that reference these users
        folder_stmt = delete(Folder).where(Folder.user_id.in_(created_user_ids))
        await integration_db_session.execute(folder_stmt)

        # Then delete the users
        stmt = delete(Users).where(Users.id.in_(created_user_ids))
        await integration_db_session.execute(stmt)
        await integration_db_session.flush()


@pytest_asyncio.fixture(scope="function")
async def cleanup_test_folders(integration_db_session: AsyncSession):
    """
    Cleanup fixture to track and remove test folders (directories).

    Folders may have foreign key dependencies from pictures and other entities.
    This fixture performs hard delete of folders.

    Yields a list that tests can append folder IDs to for cleanup.
    """
    created_folder_ids = []

    yield created_folder_ids

    # Cleanup: hard delete folders
    if created_folder_ids:
        from app.db.model import Folder
        from sqlalchemy import delete

        stmt = delete(Folder).where(Folder.id.in_(created_folder_ids))
        await integration_db_session.execute(stmt)
        await integration_db_session.flush()


@pytest_asyncio.fixture(scope="session")
def test_org_admin_role() -> UUID:
    """
    Return the pre-seeded admin role UUID from db_setup_test.py.

    This role is created during database setup for the test organization.

    Role details:
        - ID: 87654321-4321-4321-4321-210987654321
        - Name: Admin
        - Organization: 12345678-1234-1234-1234-123456789012

    Returns:
        UUID of the pre-seeded admin role
    """
    return UUID("87654321-4321-4321-4321-210987654321")


@pytest_asyncio.fixture(scope="session")
def test_org_user_role() -> UUID:
    """
    Return the pre-seeded user role UUID from db_setup_test.py.

    This role is referenced in the default folder creation.

    Role details:
        - ID: cf75fcb9-b237-529a-a991-0fb69fb5ec1f
        - Name: User
        - Organization: 12345678-1234-1234-1234-123456789012

    Returns:
        UUID of the pre-seeded user role
    """
    return UUID("cf75fcb9-b237-529a-a991-0fb69fb5ec1f")
