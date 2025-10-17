# Organization Registration CLI Tool

This tool allows CFIA administrators to create new organizations from the command line.

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

### List All Organizations

View all active organizations in the system:

```bash
python register_organization.py --list
```

**Example output:**

```text
================================================================================
ORGANIZATIONS
================================================================================

1. ID: 12345678-1234-1234-1234-123456789012
   Name: Canadian Food Inspection Agency
   Description: CFIA main organization
   Folder Prefix: cfia
   Active: True
   Created: 2024-01-15 09:00:00 UTC

2. ID: 87654321-4321-4321-4321-210987654321
   Name: Test Organization
   Description: Default test organization for development
   Folder Prefix: test-org
   Active: True
   Created: 2024-01-15 09:00:00 UTC

Total: 2 organization(s)
```

### Create a New Organization

Create a new organization with a folder prefix:

```bash
python register_organization.py --create \
  --name "Organization Name" \
  --description "Organization Description" \
  --folder-prefix "org-prefix" \
  --admin <ADMIN_USER_UUID>
```

**Example:**

```bash
python register_organization.py --create \
  --name "Canadian Food Inspection Agency" \
  --description "CFIA main organization for seed identification" \
  --folder-prefix "cfia" \
  --admin 11111111-2222-3333-4444-555555555555
```

**Create organization without folder prefix (will use default):**

```bash
python register_organization.py --create \
  --name "Research Lab" \
  --description "Research laboratory organization" \
  --admin 11111111-2222-3333-4444-555555555555
```

## Organization Creation Process

When you run a creation command, the script will:

1. ✓ Verify the admin user exists and is active
2. ✓ Check that the organization name is unique
3. ✓ Validate the folder prefix format (if provided)
4. 📋 Display organization details
5. ⚠️  Ask for confirmation
6. 🔄 Create the organization
7. 🔐 Automatically create RBAC roles (admin, user)
8. ✅ Display success message with next steps

**Example creation flow:**

```text
================================================================================
ORGANIZATION CREATION
================================================================================

✓ Admin user verified: admin@cfia-acia.gc.ca

📋 Organization Details:
   Name: Canadian Food Inspection Agency
   Description: CFIA main organization for seed identification
   Folder Prefix: cfia
   Admin ID: 11111111-2222-3333-4444-555555555555

⚠️  Are you sure you want to create this organization? (yes/no): yes

🔄 Creating organization...

✅ SUCCESS: Organization created successfully!

📊 Organization Details:
   Organization ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
   Name: Canadian Food Inspection Agency
   Description: CFIA main organization for seed identification
   Folder Prefix: cfia
   Date Created: 2025-10-17T12:30:45.123456

🔐 RBAC Roles Created:
   - admin: Administrator role for Canadian Food Inspection Agency (ID: xxxx-yyyy-zzzz)
   - user: User role for Canadian Food Inspection Agency (ID: aaaa-bbbb-cccc)

📝 Next Steps:
   1. Users can now be registered to this organization
   2. Admin users will need to be assigned the 'admin' role
   3. Regular users will need to be assigned the 'user' role
```

## What Happens During Organization Creation

1. **Organization Record Creation**:
   - Unique organization ID is generated
   - Name and description are stored
   - Folder prefix is set (or left as None for default)
   - Active status is set to True

2. **RBAC Role Creation**:
   - **"admin" role**: Created automatically for organization administrators
   - **"user" role**: Created automatically for regular users
   - These roles are organization-scoped (tied to the organization_id)

3. **Folder Structure**:
   - If a folder prefix is provided, it will be used for all user folders
   - Format: `{organization_folder_prefix}/{username}`
   - Example: `cfia/john.doe` for a user in the CFIA organization

## Folder Prefix Guidelines

The folder prefix is used to organize user folders in the blob storage system.

**Best Practices:**

- ✅ Use lowercase letters
- ✅ Use hyphens for word separation (e.g., `my-org`)
- ✅ Keep it short and meaningful (e.g., `cfia`, `lab-1`, `test-org`)
- ❌ Avoid spaces
- ❌ Avoid special characters except hyphens and underscores
- ❌ Avoid uppercase letters (will be converted to lowercase)

**Valid Examples:**

```bash
--folder-prefix "cfia"
--folder-prefix "research-lab"
--folder-prefix "inspection-team-1"
--folder-prefix "test_org"
```

**Invalid Examples:**

```bash
--folder-prefix "My Org"           # Contains spaces
--folder-prefix "org@123"          # Contains special characters
--folder-prefix "Org/Name"         # Contains slashes
```

## Troubleshooting

### Error: "Admin user not found or inactive"

**Problem:** The admin UUID provided doesn't exist or the user is inactive.

**Solution:**

1. Verify you're using the correct admin UUID
2. Check that the admin user is active in the database
3. Contact a database administrator if needed

### Error: "An organization with the name 'X' already exists"

**Problem:** An organization with the same name already exists.

**Solution:**

1. Choose a different organization name
2. Or use `--list` to view existing organizations
3. Update or reactivate the existing organization if appropriate

### Error: "Folder prefix 'X' contains invalid characters"

**Problem:** The folder prefix contains characters that aren't allowed.

**Solution:**

1. Use only lowercase letters, numbers, hyphens, and underscores
2. Remove spaces and special characters
3. Example: Change "My Org!" to "my-org"

### Error: "Failed to initialize database connection"

**Problem:** Cannot connect to the database.

**Solution:**

1. Verify `NACHET_DATA` environment variable is set
2. Check database connection string configuration
3. Ensure database migrations have been run
4. Verify database is accessible

## Security Notes

- ⚠️ This script requires CFIA admin privileges
- ⚠️ The script verifies admin permissions through the OrganizationService.create() method
- ⚠️ All creation actions are logged in the database
- ⚠️ Organization names must be unique across the system
- ⚠️ Only CFIA admins can create organizations

## RBAC Role Assignment

After creating an organization, you need to assign roles to users:

### Using the User Registration Script

When registering users to this organization, they will automatically get the "user" role assigned by the `register_user.py` script.

### Assigning Admin Roles

To assign the "admin" role to a user, use the `register_user.py` script with the `--assign-role` flag:

```bash
python register_user.py --assign-role <USER_UUID> admin --assign-role-org <ORG_UUID>
```

**Example:**

```bash
python register_user.py --assign-role 12345678-1234-1234-1234-123456789abc admin \
  --assign-role-org aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

## Advanced Usage

### Using with `uv`

If you prefer using `uv` instead of `python`:

```bash
uv run python register_organization.py --list
```

### Scripting Multiple Organization Creation

You can create a shell script to create multiple organizations:

```bash
#!/bin/bash
# batch_create_orgs.sh

ADMIN_ID="11111111-2222-3333-4444-555555555555"

# Create CFIA organization
python register_organization.py --create \
  --name "Canadian Food Inspection Agency" \
  --description "CFIA main organization" \
  --folder-prefix "cfia" \
  --admin "$ADMIN_ID"

# Create research lab organization
python register_organization.py --create \
  --name "Research Laboratory" \
  --description "Research lab for seed analysis" \
  --folder-prefix "research-lab" \
  --admin "$ADMIN_ID"

# Create test organization
python register_organization.py --create \
  --name "Test Organization" \
  --description "Testing and development organization" \
  --folder-prefix "test-org" \
  --admin "$ADMIN_ID"
```

## Help

For detailed help and all available options:

```bash
python register_organization.py --help
```

## Related Documentation

- User registration: `/home/p4r0d1m3pxz/work/nachet/backend/app/scripts/REGISTER_USER_README.md`
- RBAC documentation: `/home/p4r0d1m3pxz/work/nachet/backend/docs/nachet-rbac-documentation.md`
- Main project README: `/home/p4r0d1m3pxz/work/nachet/README.md`
- Developer guide: `/home/p4r0d1m3pxz/work/nachet/DEVELOPER.md`
