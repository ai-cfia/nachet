# RBAC Service Design Documentation

## Overview

This document describes the Role-Based Access Control (RBAC) implementation for the Nachet backend API. The design prioritizes **security**, **flexibility**, and **real-time authorization** with database-driven policies and no caching.

### Key Features

- **Database-driven authorization** - All route permissions and roles stored in database
- **Two authorization patterns**:
  - Route-based: `authorize_request()` for HTTP endpoint protection
  - Role-based: `verify_user_has_role()` for business logic authorization
- **Organization-scoped roles** - Roles are associated with organizations
- **No caching** - All role checks query database in real-time for immediate revocation
- **Active flag checking** on all entities (users, roles, role assignments, resources, permissions)
- **Flexible permission model** - Resources, permissions, and role mappings managed in database

## Architecture

### Components

1. **RbacDataService** (backend/app/datastore/rbac.py)
   - Data access layer for route-based RBAC operations
   - `user_has_route_access()` - Checks if user can access a specific HTTP route
   - Single-query role checks using SQLAlchemy with proper joins
   - Validates all `active` flags for security

2. **OrganizationDataService** (backend/app/datastore/organization.py)
   - Data access layer for organization-based role operations
   - `user_has_role()` - Checks if user has specific role in organization
   - `get_user_organization_id()` - Gets user's organization

3. **RbacService** (backend/app/service/rbac.py)
   - Business logic layer with two authorization methods:
     - `authorize_request()` - Route-based authorization (for HTTP endpoints)
     - `verify_user_has_role()` - Role-based authorization (for business logic)
   - `get_user_organization_id()` - Helper to get user's organization
   - Calls DataService methods directly (no wrapper layers)

## Database Schema

### Core RBAC Tables

```text
┌─────────────────────────────────────────────────────────────┐
│                    Route Authorization                      │
└─────────────────────────────────────────────────────────────┘

users → rbac_user_role → rbac_role → rbac_role_permission_resource
                                              ↓                ↓
                                       rbac_resource    rbac_permission

┌─────────────────────────────────────────────────────────────┐
│                Organization-Based Roles                     │
└─────────────────────────────────────────────────────────────┘

users → organization
          ↓
rbac_role (organization_id)
          ↓
rbac_user_role
```

### Key Tables

- **users**: User accounts with organization association
- **organization**: Organizations (e.g., CFIA, partner organizations)
- **rbac_role**: Roles scoped to organizations (e.g., "cfia_admin", "org_admin")
- **rbac_user_role**: Junction table linking users to roles
- **rbac_resource**: Protected resources (HTTP routes like "GET_/pipelines")
- **rbac_permission**: Permission types (e.g., "allow")
- **rbac_role_permission_resource**: Maps which roles have which permissions on which resources

## Security Design Decisions

### No Caching

**Decision**: RBAC checks do NOT use caching.

**Rationale**:

- **Immediate Revocation**: Role changes take effect instantly
- **Compliance**: Meets SOC2, HIPAA immediate access revocation requirements
- **Audit Trail**: Database logs show exact access times
- **No Stale Permissions**: Prevents unauthorized access during cache TTL
- **Simplicity**: No cache invalidation complexity

**Performance**: Single EXISTS queries with proper joins are fast enough for production use.

### Active Flag Checking

All queries verify `active = TRUE` on:

- `users.active`
- `rbac_user_role.active`
- `rbac_role.active`
- `rbac_resource.active`
- `rbac_permission.active`
- `rbac_role_permission_resource.active`

This ensures deactivated users, roles, or permissions are immediately invalid.

## Authorization Patterns

The RBAC system supports **two authorization patterns**:

### 1. Route-Based Authorization (HTTP Endpoints)

Use `authorize_request()` to protect API routes based on database-stored route permissions.

**How It Works**:

1. Route permissions stored as resources in database (e.g., "GET_/pipelines", "DELETE_/pictures/{id}")
2. Roles are granted "allow" permission on specific route resources
3. `authorize_request()` checks if user's roles have access to the requested route
4. Raises 403 if user lacks access

**When to Use**: Protecting HTTP API endpoints

**Location**: Routes call `RbacService.authorize_request(request, user)`

### 2. Role-Based Authorization (Business Logic)

Use `verify_user_has_role()` to check if user has specific organizational role.

**How It Works**:

1. Roles are scoped to organizations in database
2. Users are assigned roles through `rbac_user_role` table
3. `verify_user_has_role()` checks if user has specified role in organization
4. Raises 403 if user lacks role

**When to Use**: Business logic requiring specific organizational roles (e.g., only "cfia_admin" can create device brands)

**Location**: Service methods call `RbacService.verify_user_has_role(user_id, role_name, org_id)`

## Common Roles

While roles are database-managed, common roles include:

- **cfia_admin**: CFIA administrator (Canadian Food Inspection Agency)
- **org_admin**: Organization administrator
- **user**: Regular user
- **viewer**: Read-only access
- **uploader**: Can upload data
- **verifier**: Can verify/approve data

**Note**: Roles are stored in `rbac_role` table and can be added/modified without code changes.

## Usage Examples

### Example 1: Route-Based Authorization (HTTP Endpoints)

Protect an API route using database-stored route permissions:

```python
from fastapi import APIRouter, Request, Depends
from app.service.rbac import RbacService
from app.service.auth import User, get_current_user

router = APIRouter()

@router.delete("/pictures/{picture_id}")
async def delete_picture(
    picture_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a picture.

    Authorization: Checks database for route permission on "DELETE_/pictures/{picture_id}"
    """
    await RbacService.authorize_request(request, current_user)
    # User is guaranteed to have permission for this route
    # ... business logic ...
```

**Database Setup**: The route resource "DELETE_/pictures/{picture_id}" must exist in `rbac_resource` table with appropriate role mappings.

### Example 2: Role-Based Authorization (Business Logic)

Check if user has specific organizational role:

```python
from uuid import UUID
from app.service.rbac import RbacService

class DeviceBrandService:
    @staticmethod
    async def create(user_id: UUID, name: str):
        """
        Create device brand.

        Authorization: Only CFIA admins can create brands
        """
        # Get user's organization
        user_org_id = await RbacService.get_user_organization_id(user_id)

        # Verify user has cfia_admin role
        await RbacService.verify_user_has_role(user_id, "cfia_admin", user_org_id)

        # User is guaranteed to be cfia_admin
        # ... create brand logic ...
```

### Example 3: Read Operations (Any Authenticated User)

```python
from app.service.rbac import RbacService

class DeviceBrandService:
    @staticmethod
    async def get_all(user_id: UUID):
        """
        Get all device brands.

        Authorization: Any authenticated user (just verify user exists)
        """
        # Verify user is associated with an organization
        await RbacService.get_user_organization_id(user_id)

        # ... fetch brands logic ...
```

### Example 4: Optional Organization ID

`verify_user_has_role()` can auto-lookup organization if not provided:

```python
# With organization_id
await RbacService.verify_user_has_role(user_id, "cfia_admin", org_id)

# Without organization_id (auto-lookup)
await RbacService.verify_user_has_role(user_id, "cfia_admin")
```

### Example 5: Direct Data Access for Advanced Use Cases

For advanced scenarios where you need to query RBAC data directly:

```python
from app.db.utils import sessionmanager
from app.datastore import RbacDataService, OrganizationDataService
from uuid import UUID

async def my_function(user_id: UUID):
    async with sessionmanager.get_session() as session:
        # Route-based checks
        rbac_service = RbacDataService(session)
        has_access = await rbac_service.user_has_route_access(
            user_id, "GET", "/pipelines"
        )

        # Organization-based checks
        org_service = OrganizationDataService(session)
        org_id = await org_service.get_user_organization_id(user_id)
        is_admin = await org_service.user_has_role(user_id, org_id, "cfia_admin")
```

## API Reference

### RbacService Methods

#### `authorize_request(request: Request, user: User) -> None`

**Route-based authorization** - validates user has database permission for the route.

**How it works**:

1. Extracts HTTP method and route path from request
2. Constructs resource name (e.g., "GET_/pipelines")
3. Queries database to check if user's roles have "allow" permission on resource
4. Raises 403 if user lacks access

**Usage**:

```python
await RbacService.authorize_request(request, current_user)
```

**Raises**: `HTTPException(403)` if user lacks route access

**Database Query**: Checks `user → rbac_user_role → rbac_role → rbac_role_permission_resource → rbac_resource/rbac_permission`

#### `verify_user_has_role(user_id: UUID, role_name: str, organization_id: Optional[UUID] = None) -> None`

**Role-based authorization** - validates user has specific role in organization.

**Args**:

- `user_id`: The user's UUID
- `role_name`: The role name to verify (e.g., "cfia_admin")
- `organization_id`: Optional organization UUID (will be looked up if not provided)

**Usage**:

```python
# With organization_id
await RbacService.verify_user_has_role(user_id, "cfia_admin", org_id)

# Auto-lookup organization_id
await RbacService.verify_user_has_role(user_id, "cfia_admin")
```

**Raises**: `HTTPException(403)` if:

- User doesn't have the role
- User not associated with organization (when org_id is None)

**Database Query**: Checks `user → rbac_user_role → rbac_role` where role matches organization and name

#### `get_user_organization_id(user_id: UUID) -> UUID`

**Helper method** - gets user's organization ID.

**Returns**: Organization UUID

**Raises**: `HTTPException(403)` if user not associated with organization

**Usage**:

```python
org_id = await RbacService.get_user_organization_id(user_id)
```

### RbacDataService Methods

#### `user_has_route_access(user_id: UUID, method: str, path: str) -> bool`

Check if user has access to specific HTTP route.

**Args**:

- `user_id`: The user's UUID
- `method`: HTTP method (e.g., "GET", "POST", "DELETE")
- `path`: Route path template (e.g., "/pipelines", "/pictures/{id}")

**Returns**: `True` if user has access, `False` otherwise

**SQL Query**:

```sql
SELECT EXISTS (
    SELECT 1
    FROM users u
    JOIN rbac_user_role ur ON u.id = ur.user_id
    JOIN rbac_role r ON ur.role_id = r.id
    JOIN rbac_role_permission_resource rpr ON r.id = rpr.role_id
    JOIN rbac_resource res ON rpr.resource_id = res.id
    JOIN rbac_permission p ON rpr.permission_id = p.id
    WHERE u.id = :user_id
      AND res.name = :resource_name  -- e.g., "GET_/pipelines"
      AND p.name = 'allow'
      AND u.active = TRUE
      AND ur.active = TRUE
      AND r.active = TRUE
      AND rpr.active = TRUE
      AND res.active = TRUE
      AND p.active = TRUE
)
```

### OrganizationDataService Methods

#### `user_has_role(user_id: UUID, organization_id: UUID, role_name: str) -> bool`

Check if user has specific role in organization.

**Args**:

- `user_id`: The user's UUID
- `organization_id`: The organization UUID
- `role_name`: The role name (e.g., "cfia_admin")

**Returns**: `True` if user has role, `False` otherwise

**SQL Query**:

```sql
SELECT EXISTS (
    SELECT 1
    FROM rbac_user_role ur
    JOIN rbac_role r ON ur.role_id = r.id
    JOIN users u ON ur.user_id = u.id
    WHERE u.id = :user_id
      AND r.organization_id = :organization_id
      AND r.name = :role_name
      AND u.active = TRUE
      AND ur.active = TRUE
      AND r.active = TRUE
)
```

#### `get_user_organization_id(user_id: UUID) -> Optional[UUID]`

Get the organization ID for a user.

**Returns**: Organization UUID if found, None otherwise

## Error Responses

### Route-Based Authorization Errors

When a user lacks route access, the API returns HTTP 403 Forbidden:

```json
{
  "detail": "Access denied to DELETE /pictures/{picture_id}"
}
```

### Role-Based Authorization Errors

When a user lacks required role:

```json
{
  "detail": "User does not have required role: cfia_admin"
}
```

When user not associated with organization:

```json
{
  "detail": "User not associated with an organization"
}
```

**Status code**: `403 Forbidden`

## Testing Considerations

### Unit Tests

See comprehensive test suite in `backend/tests/test_rbac_service.py`:

- Mock `RbacDataService` and `OrganizationDataService` to test business logic
- Test both authorization patterns (route-based and role-based)
- Test exception raising scenarios
- Test organization lookup logic

**Coverage**: 100% test coverage on `RbacService`

### Test Examples

#### Testing Route-Based Authorization

```python
from app.service.rbac import RbacService
from unittest.mock import Mock, AsyncMock

async def test_authorize_request_with_access(monkeypatch):
    """User with route permission should be allowed access."""
    # Mock request
    request = Mock()
    request.method = "GET"
    route_mock = Mock()
    route_mock.path = "/pipelines"
    request.scope = {"route": route_mock}

    # Mock user
    user = Mock()
    user.oid = str(uuid4())

    # Mock RbacDataService
    mock_data_service = AsyncMock()
    mock_data_service.user_has_route_access = AsyncMock(return_value=True)

    # Should not raise exception
    await RbacService.authorize_request(request, user)
```

#### Testing Role-Based Authorization

```python
async def test_verify_user_has_role_success(monkeypatch):
    """User with role should pass verification."""
    user_id = uuid4()
    org_id = uuid4()
    role_name = "cfia_admin"

    # Mock OrganizationDataService
    mock_data_service = AsyncMock()
    mock_data_service.user_has_role = AsyncMock(return_value=True)

    # Should not raise exception
    await RbacService.verify_user_has_role(user_id, role_name, org_id)
```

### Integration Tests

- Test actual database queries
- Test with active/inactive users and roles
- Test role assignment changes
- Test organization associations

## Database Management

### Adding Route Permissions

1. **Create resource** in `rbac_resource` table:

   ```sql
   INSERT INTO rbac_resource (id, name, active)
   VALUES (uuid_generate_v4(), 'DELETE_/pictures/{picture_id}', TRUE);
   ```

2. **Get or create permission** in `rbac_permission` table (typically "allow"):

   ```sql
   SELECT id FROM rbac_permission WHERE name = 'allow';
   ```

3. **Map role to resource** in `rbac_role_permission_resource`:

   ```sql
   INSERT INTO rbac_role_permission_resource (id, role_id, permission_id, resource_id, active)
   VALUES (
       uuid_generate_v4(),
       (SELECT id FROM rbac_role WHERE name = 'admin'),
       (SELECT id FROM rbac_permission WHERE name = 'allow'),
       (SELECT id FROM rbac_resource WHERE name = 'DELETE_/pictures/{picture_id}'),
       TRUE
   );
   ```

### Adding Organization Roles

1. **Create role** in `rbac_role` table:

   ```sql
   INSERT INTO rbac_role (id, name, organization_id, active)
   VALUES (
       uuid_generate_v4(),
       'org_admin',
       (SELECT id FROM organization WHERE name = 'CFIA'),
       TRUE
   );
   ```

2. **Assign role to user** in `rbac_user_role`:

   ```sql
   INSERT INTO rbac_user_role (id, user_id, role_id, active)
   VALUES (
       uuid_generate_v4(),
       (SELECT id FROM users WHERE email = 'user@example.com'),
       (SELECT id FROM rbac_role WHERE name = 'org_admin'),
       TRUE
   );
   ```

### Resource Naming Convention

Routes are stored as resources using the pattern: `{HTTP_METHOD}_{route_path}`

**Examples**:

- `GET_/pipelines`
- `POST_/pictures`
- `DELETE_/pictures/{picture_id}`
- `PUT_/users/{user_id}`

**Important**: Route path must match FastAPI's path template exactly, including parameter placeholders.

## Migration from Hardcoded Policies

If migrating from old hardcoded `ROUTE_POLICIES`:

### Old Pattern (Deprecated)

```python
# DON'T USE - This pattern is deprecated
ROUTE_POLICIES = {
    ("DELETE", "/pictures/{id}"): [Role.ADMIN],
}
```

### New Pattern (Current)

**Route-Based (HTTP endpoints)**:

```python
@router.delete("/pictures/{id}")
async def delete_picture(request: Request, user: User = Depends(get_current_user)):
    await RbacService.authorize_request(request, user)
    # ... business logic ...
```

**Role-Based (Business logic)**:

```python
async def create_brand(user_id: UUID, name: str):
    user_org_id = await RbacService.get_user_organization_id(user_id)
    await RbacService.verify_user_has_role(user_id, "cfia_admin", user_org_id)
    # ... business logic ...
```

## Troubleshooting

### Issue: User has route permission but gets 403

**Check**:

1. Verify resource name format: `{METHOD}_{path}` (e.g., "GET_/pipelines")
2. Verify `rbac_resource.active = TRUE`
3. Verify `rbac_permission.active = TRUE` and name is "allow"
4. Verify `rbac_role_permission_resource.active = TRUE`
5. Verify `rbac_user_role.active = TRUE`
6. Verify `rbac_role.active = TRUE`
7. Verify `users.active = TRUE`

### Issue: User has role but role verification fails

**Check**:

1. Verify role is in correct organization: `rbac_role.organization_id`
2. Verify user is in same organization: `users.organization`
3. Verify role name matches exactly (case-sensitive)
4. Verify all `active` flags are TRUE

### Issue: Performance concerns

**Solution**:

- Database queries are optimized with EXISTS and proper joins
- No N+1 query problems
- Consider adding indexes on foreign keys if needed (likely already present)
- Monitor query performance with database logging

### Issue: Route path not matching

**Check**:

1. Route path in database must match FastAPI template exactly
2. Include parameter placeholders: `/pictures/{picture_id}` not `/pictures/123`
3. No trailing slashes (unless FastAPI route has one)

## Summary

The RBAC service provides:

- ✅ **Database-driven authorization** - No hardcoded policies, all permissions in database
- ✅ **Two authorization patterns** - Route-based for HTTP endpoints, role-based for business logic
- ✅ **Organization-scoped roles** - Roles tied to organizations for multi-tenant support
- ✅ **Secure, real-time checking** - No caching, immediate access revocation
- ✅ **Clean separation** - RbacDataService for routes, OrganizationDataService for roles
- ✅ **Easy to audit** - All permissions visible in database
- ✅ **Active flag enforcement** - Validates all entities are active
- ✅ **Comprehensive testing** - 100% test coverage with unit and integration tests

### Authorization Flow

**Route-Based**:

1. Create route resource in DB → 2. Call `authorize_request()` → 3. Service checks via `RbacDataService` → 4. Raises 403 if unauthorized

**Role-Based**:

1. Assign role to user in DB → 2. Call `verify_user_has_role()` → 3. Service checks via `OrganizationDataService` → 4. Raises 403 if unauthorized

The design prioritizes **security**, **flexibility**, and **maintainability** by using database-driven policies that can be modified without code changes, while maintaining strict real-time access control.
