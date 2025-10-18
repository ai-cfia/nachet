#!/usr/bin/env python3
"""
User Registration CLI Tool

This script allows CFIA admins to register pending users from the command line.

Usage:
    # List all pending registrations
    python register_user.py --list

    # Register a specific user
    python register_user.py --register <azure_ad_oid> --org <organization_id> --admin <admin_user_id>

    # Register a user by email
    python register_user.py --register-email <email> --org <organization_id> --admin <admin_user_id>

    # List all organizations
    python register_user.py --list-orgs

    # Show help
    python register_user.py --help

Requirements:
    - Must have access to the database
    - Must provide a valid CFIA admin user ID
    - User must exist in pending_registration table
"""

import asyncio
import argparse
import sys
import os
from uuid import UUID
from typing import Optional
from dotenv import load_dotenv

# # Add the app directory to the path
# import os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from app.db.utils import sessionmanager
from app.db.model import PendingRegistration, Organization, Users, RbacRole, RbacUserRole
from app.service.user import UserService
from app.datastore.pending_registration import PendingRegistrationDataService
from app.api.config import get_settings

async def list_pending_registrations():
    """List all pending user registrations."""
    print("\n" + "="*80)
    print("PENDING USER REGISTRATIONS")
    print("="*80 + "\n")

    async with sessionmanager.get_session() as session:
        # Get all pending registrations
        stmt = select(PendingRegistration).order_by(PendingRegistration.date_created.desc())
        result = await session.execute(stmt)
        pending_users = result.scalars().all()

        if not pending_users:
            print("No pending registrations found.")
            return

        for i, user in enumerate(pending_users, 1):
            print(f"{i}. Azure AD OID: {user.azure_ad_oid}")
            print(f"   Email: {user.email or 'N/A'}")
            print(f"   Date Created: {user.date_created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()

        print(f"Total: {len(pending_users)} pending registration(s)")
        print()


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
            print(f"   Created: {org.date_created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print()

        print(f"Total: {len(orgs)} organization(s)")
        print()


async def get_pending_user_by_email(email: str) -> Optional[PendingRegistration]:
    """Get pending registration by email."""
    async with sessionmanager.get_session() as session:
        stmt = select(PendingRegistration).where(PendingRegistration.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


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


async def verify_organization(org_id: UUID) -> bool:
    """Verify that the organization exists and is active."""
    async with sessionmanager.get_session() as session:
        stmt = select(Organization).where(
            Organization.id == org_id,
            Organization.active.is_(True)
        )
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()

        if not org:
            print(f"\n❌ ERROR: Organization with ID {org_id} not found or inactive.")
            return False

        print(f"✓ Organization verified: {org.name}")
        return True


async def assign_user_role(user_id: UUID, org_id: UUID, role_name: str = "user") -> bool:
    """
    Assign a role to a user in an organization.

    Args:
        user_id: UUID of the user
        org_id: UUID of the organization
        role_name: Name of the role to assign (default: "user")

    Returns:
        True if successful, False otherwise
    """
    try:
        async with sessionmanager.get_session() as session:
            # Find the role for this organization
            stmt = select(RbacRole).where(
                RbacRole.organization_id == org_id,
                RbacRole.name == role_name,
                RbacRole.active.is_(True)
            )
            result = await session.execute(stmt)
            role = result.scalar_one_or_none()

            if not role:
                print(f"\n⚠️  WARNING: Role '{role_name}' not found for organization {org_id}")
                return False

            # Check if user already has this role
            stmt = select(RbacUserRole).where(
                RbacUserRole.user_id == user_id,
                RbacUserRole.role_id == role.id
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✓ User already has '{role_name}' role")
                return True

            # Assign the role
            user_role = RbacUserRole(
                user_id=user_id,
                role_id=role.id,
                active=True
            )
            session.add(user_role)
            await session.commit()

            print(f"✓ Assigned '{role_name}' role to user")
            return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to assign role: {str(e)}")
        return False


async def register_user(azure_ad_oid: str, org_id: UUID, admin_user_id: UUID):
    """Register a user."""
    print("\n" + "="*80)
    print("USER REGISTRATION")
    print("="*80 + "\n")

    # Verify admin user
    if not await verify_admin_user(admin_user_id):
        return False

    # Verify organization
    if not await verify_organization(org_id):
        return False

    # Check if user is in pending registrations
    async with sessionmanager.get_session() as session:
        pending_service = PendingRegistrationDataService(session)
        pending_user = await pending_service.get_by_azure_oid(azure_ad_oid)

        if not pending_user:
            print(f"\n❌ ERROR: No pending registration found for Azure AD OID: {azure_ad_oid}")
            print("   The user must login at least once before they can be registered.")
            return False

        email = pending_user.email or "unknown@example.com"

        print("\n📋 Registration Details:")
        print(f"   Azure AD OID: {azure_ad_oid}")
        print(f"   Email: {email}")
        print(f"   Organization ID: {org_id}")
        print(f"   Admin ID: {admin_user_id}")
        print()

        # Confirm registration
        confirmation = input("⚠️  Are you sure you want to register this user? (yes/no): ")
        if confirmation.lower() not in ['yes', 'y']:
            print("\n❌ Registration cancelled.")
            return False

        try:
            print("\n🔄 Registering user...")

            # Call the UserService.register_user method
            result = await UserService.register_user(
                admin_user_id=admin_user_id,
                azure_ad_oid=azure_ad_oid,
                organization_id=org_id,
                email=email
            )

            print("\n✅ SUCCESS: User registered successfully!")
            print("\n📊 User Details:")
            print(f"   User ID: {result['id']}")
            print(f"   Email: {result['email']}")
            print(f"   Organization: {result['organization_name']}")
            print(f"   Default Folder ID: {result['default_folder_id']}")
            print(f"   Date Created: {result['date_created']}")
            print()

            # Assign default "user" role to the newly registered user
            print("🔄 Assigning default 'user' role...")
            await assign_user_role(UUID(result['id']), org_id, "user")

            return True

        except Exception as e:
            print(f"\n❌ ERROR: Failed to register user: {str(e)}")
            import traceback
            print("\nFull error:")
            traceback.print_exc()
            return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="User Registration CLI Tool for Nachet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all pending registrations
  python register_user.py --list

  # Register a user by Azure AD OID
  python register_user.py --register <azure_ad_oid> --org <org_id> --admin <admin_id>

  # Register a user by email
  python register_user.py --register-email user@example.com --org <org_id> --admin <admin_id>

  # List all organizations
  python register_user.py --list-orgs

Notes:
  - All IDs should be in UUID format
  - The admin user must be a CFIA admin with proper permissions
  - The user must have logged in at least once to appear in pending registrations
        """
    )

    parser.add_argument('--list', action='store_true',
                       help='List all pending user registrations')

    parser.add_argument('--list-orgs', action='store_true',
                       help='List all organizations')

    parser.add_argument('--register', metavar='AZURE_AD_OID',
                       help='Azure AD OID of the user to register')

    parser.add_argument('--register-email', metavar='EMAIL',
                       help='Email of the user to register')

    parser.add_argument('--org', metavar='ORG_ID',
                       help='Organization ID (UUID) to assign the user to')

    parser.add_argument('--admin', metavar='ADMIN_ID',
                       help='Admin user ID (UUID) performing the registration')

    parser.add_argument('--assign-role', nargs=2, metavar=('USER_ID', 'ROLE_NAME'),
                       help='Assign a role to a user: USER_ID ROLE_NAME (e.g., --assign-role <uuid> admin)')

    parser.add_argument('--assign-role-org', metavar='ORG_ID',
                       help='Organization ID for role assignment (required with --assign-role)')

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
            await list_pending_registrations()
            return

        # Handle list organizations command
        if args.list_orgs:
            await list_organizations()
            return

        # Handle assign role command
        if args.assign_role:
            if not args.assign_role_org:
                parser.error("--assign-role requires --assign-role-org")

            user_id_str, role_name = args.assign_role

            try:
                user_id = UUID(user_id_str)
                org_id = UUID(args.assign_role_org)
            except ValueError as e:
                print(f"\n❌ ERROR: Invalid UUID format: {e}")
                sys.exit(1)

            print(f"\n🔄 Assigning role '{role_name}' to user {user_id}...")
            success = await assign_user_role(user_id, org_id, role_name)
            sys.exit(0 if success else 1)

        # Handle register by email
        if args.register_email:
            if not args.org or not args.admin:
                parser.error("--register-email requires --org and --admin")

            # Look up the Azure AD OID by email
            pending_user = await get_pending_user_by_email(args.register_email)
            if not pending_user:
                print(f"\n❌ ERROR: No pending registration found for email: {args.register_email}")
                print("   The user must login at least once before they can be registered.")
                sys.exit(1)

            azure_ad_oid = pending_user.azure_ad_oid
            print(f"✓ Found pending registration: {azure_ad_oid}")

            try:
                org_id = UUID(args.org)
                admin_id = UUID(args.admin)
            except ValueError as e:
                print(f"\n❌ ERROR: Invalid UUID format: {e}")
                sys.exit(1)

            success = await register_user(azure_ad_oid, org_id, admin_id)
            sys.exit(0 if success else 1)

        # Handle register by OID
        if args.register:
            if not args.org or not args.admin:
                parser.error("--register requires --org and --admin")

            azure_ad_oid = args.register

            try:
                org_id = UUID(args.org)
                admin_id = UUID(args.admin)
            except ValueError as e:
                print(f"\n❌ ERROR: Invalid UUID format: {e}")
                sys.exit(1)

            success = await register_user(azure_ad_oid, org_id, admin_id)
            sys.exit(0 if success else 1)

        # If no command specified, show help
        parser.print_help()

    finally:
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
