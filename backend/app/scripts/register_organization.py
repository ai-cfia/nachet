#!/usr/bin/env python3
"""
Organization Registration CLI Tool

This script allows CFIA administrators to create new organizations from the command line.

Usage:
    # List all organizations
    python register_organization.py --list

    # Create a new organization
    python register_organization.py --create \
        --name "Organization Name" \
        --description "Organization Description" \
        --folder-prefix "org-prefix" \
        --admin <admin_user_id>

    # Show help
    python register_organization.py --help

Requirements:
    - Must have access to the database
    - Must provide a valid CFIA admin user ID
    - Organization name must be unique
    - Folder prefix should be lowercase, alphanumeric with hyphens
"""

import asyncio
import argparse
import sys
from uuid import UUID
from typing import Optional
from dotenv import load_dotenv

# Add the app directory to the path
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.db.utils import sessionmanager
from app.db.model import Organization, Users
from app.service.organization import OrganizationService
from app.api.config import get_settings


async def list_organizations():
    """List all organizations."""
    print("\n" + "="*80)
    print("ORGANIZATIONS")
    print("="*80 + "\n")

    async with sessionmanager.get_session() as session:
        stmt = select(Organization).where(Organization.active.is_(True)).order_by(Organization.name)
        result = await session.execute(stmt)
        orgs = result.scalars().all()

        if not orgs:
            print("No organizations found.")
            return

        for i, org in enumerate(orgs, 1):
            print(f"{i}. ID: {org.id}")
            print(f"   Name: {org.name}")
            print(f"   Description: {org.description}")
            print(f"   Folder Prefix: {org.folder_prefix or 'N/A'}")
            print(f"   Active: {org.active}")
            print(f"   Created: {org.date_created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()

        print(f"Total: {len(orgs)} organization(s)")
        print()


async def verify_admin_user(admin_user_id: UUID) -> bool:
    """Verify that the admin user exists and is active."""
    async with sessionmanager.get_session() as session:
        stmt = select(Users).where(
            Users.id == admin_user_id,
            Users.active.is_(True)
        )
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print(f"\n❌ ERROR: Admin user with ID {admin_user_id} not found or inactive.")
            return False

        print(f"\n✓ Admin user verified: {admin_user.email or 'No email'}")
        return True


async def check_organization_exists(name: str) -> bool:
    """Check if an organization with the given name already exists."""
    async with sessionmanager.get_session() as session:
        stmt = select(Organization).where(Organization.name == name)
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()
        return org is not None


async def create_organization(
    name: str,
    description: str,
    folder_prefix: Optional[str],
    admin_user_id: UUID
):
    """Create a new organization."""
    print("\n" + "="*80)
    print("ORGANIZATION CREATION")
    print("="*80 + "\n")

    # Verify admin user
    if not await verify_admin_user(admin_user_id):
        return False

    # Check if organization already exists
    if await check_organization_exists(name):
        print(f"\n❌ ERROR: An organization with the name '{name}' already exists.")
        return False

    # Validate folder prefix format
    if folder_prefix:
        if not folder_prefix.replace('-', '').replace('_', '').isalnum():
            print(f"\n❌ ERROR: Folder prefix '{folder_prefix}' contains invalid characters.")
            print("   Folder prefix should only contain lowercase letters, numbers, hyphens, and underscores.")
            return False
        if folder_prefix != folder_prefix.lower():
            print(f"\n⚠️  WARNING: Folder prefix will be converted to lowercase: '{folder_prefix.lower()}'")
            folder_prefix = folder_prefix.lower()

    print("\n📋 Organization Details:")
    print(f"   Name: {name}")
    print(f"   Description: {description}")
    print(f"   Folder Prefix: {folder_prefix or 'None (will use default)'}")
    print(f"   Admin ID: {admin_user_id}")
    print()

    # Confirm creation
    confirmation = input("⚠️  Are you sure you want to create this organization? (yes/no): ")
    if confirmation.lower() not in ['yes', 'y']:
        print("\n❌ Organization creation cancelled.")
        return False

    try:
        print("\n🔄 Creating organization...")

        # Call the OrganizationService.create method
        result = await OrganizationService.create(
            user_id=admin_user_id,
            name=name,
            description=description,
            folder_prefix=folder_prefix
        )

        print("\n✅ SUCCESS: Organization created successfully!")
        print("\n📊 Organization Details:")
        print(f"   Organization ID: {result['id']}")
        print(f"   Name: {result['name']}")
        print(f"   Description: {result['description']}")
        print(f"   Folder Prefix: {result['folder_prefix']}")
        print(f"   Date Created: {result['date_created']}")
        print()

        # Display created RBAC roles
        if 'rbac_roles' in result and result['rbac_roles']:
            print("🔐 RBAC Roles Created:")
            for role in result['rbac_roles']:
                print(f"   - {role['name']}: {role['description']} (ID: {role['id']})")
            print()

        print("📝 Next Steps:")
        print("   1. Users can now be registered to this organization")
        print("   2. Admin users will need to be assigned the 'admin' role")
        print("   3. Regular users will need to be assigned the 'user' role")
        print()

        return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to create organization: {str(e)}")
        import traceback
        print("\nFull error:")
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Organization Registration CLI Tool for Nachet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all organizations
  python register_organization.py --list

  # Create a new organization
  python register_organization.py --create \\
    --name "Canadian Food Inspection Agency" \\
    --description "CFIA main organization" \\
    --folder-prefix "cfia" \\
    --admin <admin_user_id>

  # Create organization without folder prefix (will use default)
  python register_organization.py --create \\
    --name "Test Lab" \\
    --description "Testing laboratory" \\
    --admin <admin_user_id>

Notes:
  - The admin user must be a CFIA admin with proper permissions
  - Organization names must be unique
  - Folder prefixes should be lowercase with hyphens (e.g., "my-org")
  - Two RBAC roles are automatically created: "admin" and "user"
        """
    )

    parser.add_argument('--list', action='store_true',
                       help='List all organizations')

    parser.add_argument('--create', action='store_true',
                       help='Create a new organization')

    parser.add_argument('--name', metavar='NAME',
                       help='Organization name (required for --create)')

    parser.add_argument('--description', metavar='DESC',
                       help='Organization description (required for --create)')

    parser.add_argument('--folder-prefix', metavar='PREFIX',
                       help='Folder prefix for the organization (optional, lowercase recommended)')

    parser.add_argument('--admin', metavar='ADMIN_ID',
                       help='Admin user ID (UUID) performing the creation (required for --create)')

    args = parser.parse_args()

    if not os.getenv("NACHET_SCHEMA"):
        load_dotenv(".env.local")
        print("✓ Loaded environment variables from .env.local")

    # Initialize database connection using the standard pattern
    try:
        settings = get_settings()
        if settings is None:
            raise ValueError("Settings instance could not be created")

        # Initialize SessionManager with settings
        db_conn_info = settings.db_conn_info.copy()
        db_conn_info["echo"] = False  # Suppress SQL output for cleaner CLI
        sessionmanager.init(**db_conn_info)

        print(f"✓ Connected to database: {settings.db_name}")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize database connection: {e}")
        print("\nMake sure you have:")
        print("  1. Set up the NACHET_DATA environment variable")
        print("  2. Configured the database connection string")
        print("  3. Run database migrations")
        sys.exit(1)

    try:
        # Handle list command
        if args.list:
            await list_organizations()
            return

        # Handle create command
        if args.create:
            if not args.name or not args.description or not args.admin:
                parser.error("--create requires --name, --description, and --admin")

            try:
                admin_id = UUID(args.admin)
            except ValueError as e:
                print(f"\n❌ ERROR: Invalid UUID format for admin: {e}")
                sys.exit(1)

            success = await create_organization(
                name=args.name,
                description=args.description,
                folder_prefix=args.folder_prefix,
                admin_user_id=admin_id
            )
            sys.exit(0 if success else 1)

        # If no command specified, show help
        parser.print_help()

    finally:
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
