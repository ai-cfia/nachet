# User Registration CLI Tool

This tool allows CFIA administrators to register users from the command line.

## Prerequisites

1. **Database access**: You must have access to the Nachet database
2. **Environment setup**: `NACHET_DATA` environment variable must be configured
3. **Python dependencies**: All backend dependencies must be installed (`uv sync` or `pip install -r requirements.txt`)
4. **Admin credentials**: You need a valid CFIA admin user UUID

## Installation

```bash
cd /home/p4r0d1m3pxz/work/nachet/backend
# Install dependencies if not already done
uv sync
# or
pip install -r requirements.txt
```

## Usage

### List Pending Registrations

View all users who have logged in but are not yet registered:

```bash
python register_user.py --list
```

**Example output:**

```text
================================================================================
PENDING USER REGISTRATIONS
================================================================================

1. Azure AD OID: 12345678-1234-1234-1234-123456789abc
   Email: john.doe@example.com
   Date Created: 2025-10-17 10:30:45 UTC

2. Azure AD OID: 87654321-4321-4321-4321-cba987654321
   Email: jane.smith@example.com
   Date Created: 2025-10-17 11:15:22 UTC

Total: 2 pending registration(s)
```

### List Organizations

View all available organizations:

```bash
python register_user.py --list-orgs
```

**Example output:**

```text
================================================================================
ORGANIZATIONS
================================================================================

1. ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
   Name: Canadian Food Inspection Agency
   Description: CFIA main organization
   Folder Prefix: cfia
   Created: 2024-01-15 09:00:00 UTC

Total: 1 organization(s)
```

### Register a User by Azure AD OID

Register a user using their Azure Active Directory Object ID:

```bash
python register_user.py \
  --register <AZURE_AD_OID> \
  --org <ORGANIZATION_UUID> \
  --admin <ADMIN_USER_UUID>
```

**Example:**

```bash
python register_user.py \
  --register 12345678-1234-1234-1234-123456789abc \
  --org aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee \
  --admin 11111111-2222-3333-4444-555555555555
```

### Register a User by Email

Register a user using their email address (the script will look up their Azure AD OID):

```bash
python register_user.py \
  --register-email <EMAIL> \
  --org <ORGANIZATION_UUID> \
  --admin <ADMIN_USER_UUID>
```

**Example:**

```bash
python register_user.py \
  --register-email john.doe@example.com \
  --org aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee \
  --admin 11111111-2222-3333-4444-555555555555
```

## Registration Process

When you run a registration command, the script will:

1. ✓ Verify the admin user exists and is active
2. ✓ Verify the organization exists and is active
3. ✓ Check if the user is in the pending registrations table
4. 📋 Display registration details
5. ⚠️  Ask for confirmation
6. 🔄 Create the user account
7. 📁 Create a default folder for the user
8. 🗑️  Remove the user from pending registrations
9. ✅ Display success message

**Example registration flow:**

```text
================================================================================
USER REGISTRATION
================================================================================

✓ Admin user verified: admin@cfia-acia.gc.ca
✓ Organization verified: Canadian Food Inspection Agency

📋 Registration Details:
   Azure AD OID: 12345678-1234-1234-1234-123456789abc
   Email: john.doe@example.com
   Organization ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
   Admin ID: 11111111-2222-3333-4444-555555555555

⚠️  Are you sure you want to register this user? (yes/no): yes

🔄 Registering user...

✅ SUCCESS: User registered successfully!

📊 User Details:
   User ID: 12345678-1234-1234-1234-123456789abc
   Email: john.doe@example.com
   Organization: Canadian Food Inspection Agency
   Default Folder ID: ffff-gggg-hhhh-iiii-jjjjjjjjjjjj
   Date Created: 2025-10-17T12:30:45.123456
```

## Troubleshooting

### Error: "No pending registration found"

**Problem:** The user hasn't logged in yet, or their email is not in the system.

**Solution:**

1. Ask the user to log in to the application at least once
2. After they log in and see the "Account Registration Required" modal, they will appear in the pending registrations list
3. Run `python register_user.py --list` to verify they are now in the list

### Error: "Admin user not found or inactive"

**Problem:** The admin UUID provided doesn't exist or the user is inactive.

**Solution:**

1. Verify you're using the correct admin UUID
2. Check that the admin user is active in the database
3. Contact a database administrator if needed

### Error: "Organization not found or inactive"

**Problem:** The organization UUID is incorrect or the organization is inactive.

**Solution:**

1. Run `python register_user.py --list-orgs` to see available organizations
2. Copy the correct organization UUID from the list

### Error: "Failed to initialize database connection"

**Problem:** Cannot connect to the database.

**Solution:**

1. Verify `NACHET_DATA` environment variable is set
2. Check database connection string configuration
3. Ensure database migrations have been run
4. Verify database is accessible

## Security Notes

- ⚠️ This script requires CFIA admin privileges
- ⚠️ The script verifies admin permissions through the UserService.register_user() method
- ⚠️ All registration actions are logged in the database
- ⚠️ Users cannot register themselves - an admin must approve each registration

## What Happens During Registration

1. **User Account Creation**:
   - User ID is set to their Azure AD OID
   - User is assigned to the specified organization
   - `registered_by` field is set to the admin's UUID

2. **Default Folder Creation**:
   - A default folder is created automatically
   - Folder name: "default"
   - Folder prefix: `{organization_prefix}/{username}` (username extracted from email)
   - Permissions are set based on organization roles

3. **Cleanup**:
   - User is removed from the `pending_registration` table
   - User can now access the application normally

## Advanced Usage

### Using with `uv`

If you prefer using `uv` instead of `python`:

```bash
uv run python register_user.py --list
```

### Scripting Batch Registrations

You can create a shell script to register multiple users:

```bash
#!/bin/bash
# batch_register.sh

ORG_ID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ADMIN_ID="11111111-2222-3333-4444-555555555555"

# Register multiple users
python register_user.py --register-email user1@example.com --org "$ORG_ID" --admin "$ADMIN_ID"
python register_user.py --register-email user2@example.com --org "$ORG_ID" --admin "$ADMIN_ID"
python register_user.py --register-email user3@example.com --org "$ORG_ID" --admin "$ADMIN_ID"
```

## Help

For detailed help and all available options:

```bash
python register_user.py --help
```

## Related Documentation

- Main project README: `/home/p4r0d1m3pxz/work/nachet/README.md`
- Developer guide: `/home/p4r0d1m3pxz/work/nachet/DEVELOPER.md`
- Backend service documentation: `/home/p4r0d1m3pxz/work/nachet/backend/app/service/user.py`
