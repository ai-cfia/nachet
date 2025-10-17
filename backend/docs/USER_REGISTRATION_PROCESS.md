# User Registration Process Documentation

## Overview

The Nachet backend implements a two-stage user registration system designed for secure onboarding of new users. This process ensures that only authorized administrators can grant system access while preventing abuse through automatic tracking of registration requests.

## Architecture

### Registration Flow

```text
┌─────────────────┐
│  New User       │
│  Authenticates  │
│  via Azure AD   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  System checks if user exists   │
│  in users table                 │
└────────┬────────────────────────┘
         │
         ├─── User exists ──────► Access granted
         │
         └─── User not found ───► Check pending_registration
                                   │
                                   ├─── Already pending ──► Show "pending" message
                                   │
                                   └─── New request ──────► Create pending_registration entry
                                                            Show "pending" message

┌──────────────────┐
│  CFIA Admin      │
│  Reviews pending │
│  registrations   │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Admin assigns user to          │
│  organization via API           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  System creates:                │
│  - User record                  │
│  - Default folder               │
│  - User-role mapping            │
│  - Removes pending entry        │
└─────────────────────────────────┘
         │
         ▼
    User can access system
```

## Database Schema

### Tables Involved

#### 1. `pending_registration` Table

Temporary storage for users awaiting organization assignment.

```sql
CREATE TABLE pending_registration (
    azure_ad_oid VARCHAR(255) PRIMARY KEY,  -- Azure AD Object ID (unique identifier)
    email VARCHAR(255),                     -- User's email address
    date_created TIMESTAMP DEFAULT NOW()    -- When registration was requested
);
```

**Key characteristics:**

- Primary key is `azure_ad_oid` (string, not UUID)
- No `active` field - uses hard deletes only
- Temporary table - entries deleted after successful registration
- No foreign keys - standalone table

#### 2. `users` Table

Main user records after successful registration.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,                    -- User's Azure AD OID as UUID
    email VARCHAR(255) NOT NULL,
    organization UUID REFERENCES organization(id),
    default_folder_id UUID REFERENCES folder(id),
    registered_by UUID REFERENCES users(id), -- Admin who registered this user
    active BOOLEAN DEFAULT TRUE,
    date_created TIMESTAMP DEFAULT NOW(),
    date_updated TIMESTAMP DEFAULT NOW()
);
```

**Notable fields:**

- `id`: Matches Azure AD OID (converted to UUID)
- `registered_by`: Tracks which admin onboarded the user (NULL for pre-seeded users)
- `default_folder_id`: Auto-created folder for user's data

#### 3. `rbac_user_role` Table

Maps users to their organizational roles.

```sql
CREATE TABLE rbac_user_role (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES rbac_role(id),
    active BOOLEAN DEFAULT TRUE,
    date_created TIMESTAMP DEFAULT NOW(),
    date_updated TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);
```

## Code Components

### 1. Service Layer: `UserService`

Location: `app/service/user.py`

#### `check_user_registration(user: User) -> bool`

**Purpose**: Verify if an authenticated user is registered in the system.

**Behavior**:

- Checks if user exists in `users` table by Azure AD OID
- If user exists → returns `True`
- If user doesn't exist:
  - Checks `pending_registration` table
  - If not pending → creates pending entry
  - Returns `False`

**Usage**: Called by authentication middleware after JWT validation.

```python
# Example usage
from app.service.user import UserService

is_registered = await UserService.check_user_registration(user)
if not is_registered:
    return JSONResponse(
        status_code=403,
        content={"detail": "Registration pending"}
    )
```

**Flow**:

```text
user (from JWT token)
    │
    ├─► Query users table by user.oid
    │
    ├─► User found? → Return True
    │
    └─► User not found:
            │
            ├─► Query pending_registration by user.oid
            │
            ├─► Pending entry exists? → Return False
            │
            └─► No pending entry:
                    │
                    ├─► Create pending_registration(azure_ad_oid=user.oid, email=user.email)
                    │
                    ├─► Log creation
                    │
                    └─► Return False
```

#### `register_user(admin_user_id, azure_ad_oid, organization_id, email) -> Dict`

**Purpose**: Register a pending user by assigning them to an organization (CFIA admin only).

**Authorization**: Requires CFIA administrator role.

**Parameters**:

- `admin_user_id` (UUID): ID of admin performing registration
- `azure_ad_oid` (str): Azure AD Object ID of user to register
- `organization_id` (UUID): Organization to assign user to
- `email` (str): User's email address

**Process**:

1. Verify admin has CFIA admin role
2. Create user record with `id=azure_ad_oid`
3. Create default folder for user
4. Assign user to organization's admin role
5. Delete pending registration entry
6. Return serialized user data

**Example**:

```python
result = await UserService.register_user(
    admin_user_id=UUID("admin-uuid"),
    azure_ad_oid="user-azure-oid",
    organization_id=UUID("org-uuid"),
    email="newuser@example.com"
)
# Returns: {"id": "...", "email": "...", "organization_id": "...", ...}
```

**Auto-created resources**:

- **User record**: With `registered_by` field set to admin
- **Default folder**:
  - Name: "default"
  - Prefix: `{org_folder_prefix}/{username}` (e.g., "cfia/john.doe")
  - Links to user via `default_folder_id`
- **Role assignment**: User assigned to organization's admin role

### 2. Data Layer: `PendingRegistrationDataService`

Location: `app/datastore/pending_registration.py`

**Note**: Does NOT inherit from `BaseCRUDDataService` due to:

- No `active` field (hard deletes only)
- Primary key is string, not UUID
- Simpler requirements (temporary table)

#### Methods

**`get_by_azure_oid(azure_ad_oid: str) -> Optional[PendingRegistration]`**

```python
# Retrieve pending registration by Azure AD OID
pending = await service.get_by_azure_oid("azure-oid-string")
```

**`create(azure_ad_oid: str, email: Optional[str] = None) -> PendingRegistration`**

```python
# Create new pending registration
pending = await service.create(
    azure_ad_oid="azure-oid-string",
    email="user@example.com"
)
```

**`delete(azure_ad_oid: str) -> bool`**

```python
# Hard delete pending registration (returns True if found and deleted)
deleted = await service.delete("azure-oid-string")
```

### 3. API Routes

Location: `app/api/routes.py` (or route modules)

#### Registration Check Endpoint

**Endpoint**: Typically integrated into authentication flow

```python
@router.get("/check-registration")
async def check_registration(
    current_user: User = Depends(get_current_user)
):
    """Check if authenticated user is registered."""
    is_registered = await UserService.check_user_registration(current_user)

    if not is_registered:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Registration pending. Please contact an administrator.",
                "status": "pending"
            }
        )

    return {"status": "registered"}
```

#### User Registration Endpoint

**Endpoint**: `POST /register-user` (CFIA admin only)

```python
@router.post("/register-user")
async def register_user(
    request: RegisterUserRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Register a pending user by assigning them to an organization.

    Requires CFIA admin role.
    """
    result = await UserService.register_user(
        admin_user_id=UUID(current_user.oid),
        azure_ad_oid=request.azure_ad_oid,
        organization_id=request.organization_id,
        email=request.email
    )

    return result
```

**Request Body**:

```json
{
    "azure_ad_oid": "user-azure-ad-oid",
    "organization_id": "org-uuid",
    "email": "user@example.com"
}
```

**Response**:

```json
{
    "id": "user-uuid",
    "email": "user@example.com",
    "organization_id": "org-uuid",
    "organization_name": "CFIA",
    "default_folder_id": "folder-uuid",
    "active": true,
    "date_created": "2025-10-17T12:00:00",
    "date_updated": "2025-10-17T12:00:00"
}
```

## RBAC Integration

### Role Assignment

During registration, users are automatically assigned to their organization's **admin role**. This is retrieved by:

```python
# Get organization's admin role
stmt = select(RbacRole).where(
    RbacRole.organization_id == organization_id,
    RbacRole.name == "admin",
    RbacRole.active == True
)
org_admin_role = await session.execute(stmt).scalar_one()
```

### CFIA Admin Verification

The `register_user` operation requires CFIA admin authority:

```python
from app.service.rbac import RbacService

await RbacService.verify_user_is_cfia_admin(admin_user_id)
```

This checks:

1. User has a role in the CFIA organization
2. That role is the "admin" role
3. CFIA is identified by `CFIA_ORGANIZATION_ID` environment variable

## Environment Configuration

### Required Variables

```bash
# .env.test.local or .env
CFIA_ORGANIZATION_ID="uuid-of-cfia-organization"
CFIA_ADMIN_ROLE_ID="uuid-of-cfia-admin-role"
```

These values:

- Must match the organization and role IDs in the database
- Are used for RBAC authorization checks
- Should be consistent across all deployment environments

### Configuration Loading

```python
from app.api.config import get_settings

settings = get_settings()
cfia_org_id = settings.cfia_organization_id
cfia_admin_role_id = settings.cfia_admin_role_id
```

## Security Considerations

### 1. Abuse Prevention

**Problem**: Malicious actors could spam registration requests.

**Solution**:

- Automatic tracking in `pending_registration` prevents duplicate requests
- Each Azure AD OID can only have one pending entry
- Failed authentication at Azure AD level prevents unauthorized access

### 2. Authorization Levels

**CFIA Admin (Cross-Organization Authority)**:

- Can register users to any organization
- Can view/manage all pending registrations
- Identified by role in CFIA organization

**Organization Admin (Org-Scoped Authority)**:

- Cannot register new users
- Can only manage existing users in their organization
- Identified by "admin" role in their specific organization

### 3. Audit Trail

All registrations are tracked:

- `users.registered_by`: Which admin registered the user
- `users.date_created`: When registration occurred
- `pending_registration.date_created`: When request was made

## Testing

### Test Database Setup

The test database includes:

- Pre-seeded CFIA organization
- Pre-seeded CFIA admin role
- Test user with CFIA admin privileges

**Environment**: `.env.test.local`

```bash
CFIA_ORGANIZATION_ID="12345678-1234-1234-1234-123456789012"
CFIA_ADMIN_ROLE_ID="87654321-4321-4321-4321-210987654321"
```

### Test Scenarios

#### 1. New User Authentication

```python
async def test_new_user_creates_pending_registration():
    """Verify new users are added to pending_registration."""
    user = User(oid="new-user-oid", email="new@example.com")

    is_registered = await UserService.check_user_registration(user)

    assert is_registered is False

    # Verify pending entry was created
    async with sessionmanager.get_session() as session:
        pending_service = PendingRegistrationDataService(session)
        pending = await pending_service.get_by_azure_oid("new-user-oid")
        assert pending is not None
        assert pending.email == "new@example.com"
```

#### 2. User Registration by Admin

```python
async def test_cfia_admin_can_register_user():
    """Verify CFIA admin can register pending users."""
    admin_id = UUID("test-admin-uuid")
    org_id = UUID("test-org-uuid")

    result = await UserService.register_user(
        admin_user_id=admin_id,
        azure_ad_oid="pending-user-oid",
        organization_id=org_id,
        email="pending@example.com"
    )

    assert result["email"] == "pending@example.com"
    assert result["organization_id"] == str(org_id)
    assert result["default_folder_id"] is not None

    # Verify pending entry was deleted
    async with sessionmanager.get_session() as session:
        pending_service = PendingRegistrationDataService(session)
        pending = await pending_service.get_by_azure_oid("pending-user-oid")
        assert pending is None
```

#### 3. Non-Admin Cannot Register

```python
async def test_non_cfia_admin_cannot_register_user():
    """Verify non-CFIA admins cannot register users."""
    non_admin_id = UUID("regular-user-uuid")

    with pytest.raises(HTTPException) as exc_info:
        await UserService.register_user(
            admin_user_id=non_admin_id,
            azure_ad_oid="pending-user-oid",
            organization_id=UUID("org-uuid"),
            email="pending@example.com"
        )

    assert exc_info.value.status_code == 403
    assert "CFIA administrator" in exc_info.value.detail
```

## Database Migrations

### Adding `registered_by` Field

The `registered_by` field was added to track which admin registered each user.

**Migration**: `alembic/versions/xxx_add_registered_by_to_users.py`

```python
def upgrade() -> None:
    op.add_column('users',
        sa.Column('registered_by', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_users_registered_by',
        'users', 'users',
        ['registered_by'], ['id']
    )

def downgrade() -> None:
    op.drop_constraint('fk_users_registered_by', 'users')
    op.drop_column('users', 'registered_by')
```

### Creating `pending_registration` Table

**Migration**: `alembic/versions/xxx_create_pending_registration.py`

```python
def upgrade() -> None:
    op.create_table(
        'pending_registration',
        sa.Column('azure_ad_oid', sa.String(255), primary_key=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('date_created', sa.TIMESTAMP(), server_default=sa.func.now())
    )

def downgrade() -> None:
    op.drop_table('pending_registration')
```

## Error Handling

### Common Errors

#### 1. User Already Registered

```python
# Attempting to register an already-registered user
# The check_user_registration will return True, preventing duplicate registration
```

#### 2. Insufficient Permissions

```python
# HTTP 403: This operation requires CFIA administrator authority
# Raised when non-CFIA admin attempts registration
```

#### 3. Organization Not Found

```python
# HTTP 500: Organization admin role not found
# Raised when organization doesn't have required roles set up
```

#### 4. Pending Registration Not Found

```python
# Attempting to register a user who never authenticated
# Should create pending entry first via check_user_registration
```

### Error Response Format

```json
{
    "detail": "Error message",
    "status_code": 403
}
```

## Best Practices

### 1. Always Check Registration Before Access

```python
@router.get("/protected-resource")
async def protected_resource(current_user: User = Depends(get_current_user)):
    # Verify user is registered
    if not await UserService.check_user_registration(current_user):
        raise HTTPException(403, "Registration pending")

    # Continue with business logic
    ...
```

### 2. Use Transactions for Registration

The `register_user` method uses database transactions to ensure:

- User, folder, and role are created atomically
- Pending entry is deleted only after successful creation
- Rollback on any error

```python
async with sessionmanager.get_session() as session:
    # All operations in one transaction
    user = await data_service.create(...)
    folder = Folder(...)
    session.add(folder)
    await pending_service.delete(azure_ad_oid)
    await session.commit()  # Atomic commit
```

### 3. Log Registration Events

```python
logger.info(
    "User registered successfully",
    admin_user_id=str(admin_user_id),
    user_id=str(user.id),
    organization_id=str(organization_id),
)
```

## Future Enhancements

### Potential Improvements

1. **Email Notifications**
   - Notify users when their registration is pending
   - Notify admins of new registration requests
   - Notify users when registration is approved

2. **Self-Service Registration UI**
   - Admin dashboard to view pending registrations
   - Bulk registration operations
   - Registration request filtering/search

3. **Registration Expiry**
   - Auto-delete pending registrations after N days
   - Require users to re-authenticate if expired

4. **Registration Approval Workflow**
   - Multi-step approval process
   - Different approval levels (org admin → CFIA admin)
   - Rejection with reason tracking

5. **Role Selection During Registration**
   - Allow admin to choose initial role (admin/user/verifier)
   - Currently defaults to admin role

## Troubleshooting

### Issue: User Shows as "Pending" But Should Be Registered

**Cause**: User record exists but `check_user_registration` returns False.

**Solution**:

```sql
-- Verify user exists
SELECT * FROM users WHERE id = 'user-uuid';

-- Check if user has active role
SELECT * FROM rbac_user_role WHERE user_id = 'user-uuid' AND active = true;
```

### Issue: Admin Cannot Register Users

**Cause**: Admin doesn't have CFIA admin role.

**Solution**:

```sql
-- Check admin's roles
SELECT r.name, r.organization_id
FROM rbac_user_role ur
JOIN rbac_role r ON ur.role_id = r.id
WHERE ur.user_id = 'admin-uuid' AND ur.active = true;

-- Verify CFIA admin role ID matches environment variable
SELECT id FROM rbac_role
WHERE name = 'admin'
  AND organization_id = 'cfia-org-uuid';
```

### Issue: Duplicate Pending Registrations

**Cause**: Should not happen due to primary key constraint.

**Solution**: Check for application bugs creating entries outside the service layer.

## Related Documentation

- [RBAC Documentation](./nachet-rbac-documentation.md)
- [JWT Validation](./nachet-jwt-validation.md)
- [Service CRUD Pattern](./SERVICE_CRUD_PATTERN_SPEC.md)
- [Folder Management](./nachet-manage-folders.md)

## Changelog

### 2025-10-17

- Added two-stage registration process
- Implemented `pending_registration` table
- Added `registered_by` tracking field
- Created `check_user_registration` method
- Created `register_user` method
- Integrated with RBAC authorization
