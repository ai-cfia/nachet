# RBAC Service Design Documentation

## Overview

This document describes the Role-Based Access Control (RBAC) implementation for the Nachet backend API. The design prioritizes **security** and **simplicity** with real-time role checking and no caching.

### Key Features

- **Centralized authorization** via `ROUTE_POLICIES` dictionary mapping routes to required roles
- **Direct data access** - `RbacService` calls `RbacDataService` methods directly (no wrapper layers)
- **No caching** - all role checks query database in real-time for immediate revocation
- **Type-safe** role constants via `Role` enum
- **Active flag checking** on all entities (users, roles, role assignments)
- **Simplified architecture** - removed unnecessary wrapper methods and unused dependency classes

## Architecture

### Components

1. **RbacDataService** (backend/app/datastore/rbac.py)
   - Data access layer for RBAC operations
   - Single-query role checks using SQLAlchemy
   - Validates all `active` flags for security

2. **RbacService** (backend/app/service/rbac.py)
   - Business logic layer with centralized route authorization
   - `Role` enum for type-safe role constants
   - `ROUTE_POLICIES` dictionary for centralized route-to-role mapping
   - `authorize_request()` method - single entry point for all authorization
   - Calls `RbacDataService` methods directly (no wrapper layers)

## Database Schema

```text
users → rbac_user_role → rbac_role
```

The RBAC service queries these tables to check if a user has the required role(s).

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

This ensures deactivated users, roles, or role assignments are immediately invalid.

## Available Roles

Defined in `Role` enum (backend/app/service/rbac.py:9-20):

```python
class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    UPLOADER = "uploader"
    VERIFIER = "verifier"
    ORG_ADMIN = "org_admin"
```

**Note**: Add new roles to this enum as needed. These should match role names in the `rbac_role` database table.

## Authorization Approach

The RBAC system uses **centralized authorization** for all routes:

### How It Works

1. **Define policies** in `ROUTE_POLICIES` dictionary mapping `(HTTP_METHOD, route_path)` to required roles
2. **Call `authorize_request()`** in route handlers to enforce authorization
3. **Service checks** if user has any of the required roles via `RbacDataService`
4. **Raises 403** if user lacks required roles

**Advantages**:

- Single source of truth for all route permissions
- Easy to audit and maintain all authorization rules in one place
- Centralized policy management
- No duplicate authorization logic across routes
- Direct database access without unnecessary wrapper layers

**Location**: `RbacService.ROUTE_POLICIES` in backend/app/service/rbac.py

## Usage Examples

### Example 1: Protecting a Route

**Step 1**: Add route policy to `ROUTE_POLICIES`:

```python
# In backend/app/service/rbac.py
ROUTE_POLICIES: Dict[Tuple[str, str], Optional[List[Role]]] = {
    # ... existing routes ...
    ("DELETE", "/pictures/{picture_id}"): [Role.ADMIN],
    ("POST", "/pictures"): [Role.UPLOADER, Role.ADMIN],
    ("GET", "/seeds"): [Role.USER, Role.VIEWER, Role.ADMIN],
    ("GET", "/health"): None,  # No role required, just authentication
}
```

**Step 2**: Call `authorize_request()` in your route:

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
    """Only admins can delete pictures (enforced by ROUTE_POLICIES)"""
    await RbacService.authorize_request(request, current_user)
    # User is guaranteed to have ADMIN role
    ...
```

### Example 2: Multiple Roles (OR Logic)

```python
# In ROUTE_POLICIES
("POST", "/pictures"): [Role.UPLOADER, Role.ADMIN],

# In route handler
@router.post("/pictures")
async def upload_picture(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Uploaders OR admins can upload pictures"""
    await RbacService.authorize_request(request, current_user)
    # User has at least one of the specified roles
    ...
```

### Example 3: No Role Required (Authentication Only)

```python
# In ROUTE_POLICIES
("GET", "/seeds"): None,  # Just authentication, no specific role

# In route handler
@router.get("/seeds")
async def get_seeds(
    current_user: User = Depends(get_current_user)
):
    """All authenticated users can access"""
    # Only authentication required, no specific role needed
    ...
```

### Example 4: Direct Data Access for Advanced Use Cases

For advanced scenarios where you need to check roles programmatically:

```python
from app.db.utils import sessionmanager
from app.datastore.rbac import RbacDataService
from uuid import UUID

async def my_function(user_id: UUID):
    async with sessionmanager.get_session() as session:
        data_service = RbacDataService(session)

        # Check if user has specific role
        is_admin = await data_service.user_has_role(user_id, "admin")

        # Check if user has any of multiple roles
        can_upload = await data_service.user_has_any_role(
            user_id,
            ["uploader", "admin"]
        )

        # Get all user roles (for debugging/admin UI)
        user_roles = await data_service.get_user_roles(user_id)
```

## API Reference

### RbacService

#### `authorize_request(request: Request, user: User) -> None`

**Centralized authorization method** - validates user has required role(s) for the route.

**How it works**:

1. Extracts HTTP method and route path from request
2. Looks up required roles in `ROUTE_POLICIES` dictionary
3. If roles are required, checks user has at least one role
4. Raises 403 if user lacks required roles

**Usage**:

```python
await RbacService.authorize_request(request, current_user)
```

**Raises**: `HTTPException(403)` if user lacks required role(s)

#### `ROUTE_POLICIES: Dict[Tuple[str, str], Optional[List[Role]]]`

**Centralized route policy mapping** - defines which routes require which roles.

**Format**: `(HTTP_METHOD, route_path_template) -> List[required_roles] or None`

**Examples**:

```python
("DELETE", "/pictures/{picture_id}"): [Role.ADMIN],
("POST", "/pictures"): [Role.UPLOADER, Role.ADMIN],
("GET", "/health"): None,  # No role required
```

### RbacDataService

#### `user_has_role(user_id: UUID, role_name: str) -> bool`

Check if user has specific role.

**SQL Query**:

```sql
SELECT EXISTS (
    SELECT 1
    FROM users u
    JOIN rbac_user_role ur ON u.id = ur.user_id
    JOIN rbac_role r ON ur.role_id = r.id
    WHERE u.id = :user_id
      AND r.name = :role_name
      AND u.active = TRUE
      AND ur.active = TRUE
      AND r.active = TRUE
)
```

#### `user_has_any_role(user_id: UUID, role_names: List[str]) -> bool`

Check if user has ANY of the specified roles (OR logic).

#### `get_user_roles(user_id: UUID) -> List[str]`

Get all active role names for a user.

#### `get_roles_for_resource(resource_name: str, permission_name: str = None) -> List[str]`

Get all roles that have access to a specific resource.

Optionally filter by permission type (e.g., only roles with "write" permission on "picture" resource).

**Args**:

- `resource_name`: The name of the resource (e.g., "picture", "folder")
- `permission_name`: Optional permission filter (e.g., "read", "write", "delete")

**Returns**: List of role names that have access to the resource.

**Usage**:

```python
# Get all roles that can access "picture" resource
picture_roles = await RbacDataService(session).get_roles_for_resource("picture")

# Get only roles with "delete" permission on "picture" resource
delete_roles = await RbacDataService(session).get_roles_for_resource("picture", "delete")
```

## Error Responses

When a user lacks required role(s), the API returns HTTP 403 Forbidden:

**Single role required:**

```json
{
  "detail": "Access denied to DELETE /pictures/{picture_id}. Required role (any of): admin"
}
```

**Multiple roles (OR logic):**

```json
{
  "detail": "Access denied to POST /pictures. Required role (any of): uploader, admin"
}
```

**Status code**: `403 Forbidden`

## Testing Considerations

### Unit Tests

- Mock `RbacDataService` to test business logic
- Test role enum values
- Test exception raising

### Integration Tests

- Test actual database queries
- Test with active/inactive users and roles
- Test role assignment changes

### Example Test

```python
from app.db.utils import sessionmanager
from app.datastore.rbac import RbacDataService

async def test_user_has_role():
    # Setup: Create user with role in database
    user_id = UUID("...")

    async with sessionmanager.get_session() as session:
        data_service = RbacDataService(session)

        # Test: Check role
        has_admin = await data_service.user_has_role(user_id, "admin")
        assert has_admin is True

        # Test: Check missing role
        has_viewer = await data_service.user_has_role(user_id, "viewer")
        assert has_viewer is False
```

## Future Enhancements

### Optional: Permission-Resource Model

The database includes tables for fine-grained permissions:

- `rbac_permission` (e.g., "read", "write", "delete")
- `rbac_resource` (e.g., "picture", "folder", "annotation")
- `rbac_role_permission_resource` (junction table)

If needed, extend `RbacDataService` to support permission-resource checks:

```python
async def user_has_permission(
    user_id: UUID,
    permission_name: str,
    resource_name: str
) -> bool:
    """Check if user's role grants specific permission on resource"""
    ...
```

This would enable fine-grained access control like:

- User has "write" permission on "picture" resource
- User has "delete" permission on "folder" resource

## Migration Guide

### Adding New Routes with RBAC

1. **Add route policy to `ROUTE_POLICIES`** in backend/app/service/rbac.py:

   ```python
   ROUTE_POLICIES: Dict[Tuple[str, str], Optional[List[Role]]] = {
       # ... existing routes ...
       ("POST", "/your-endpoint"): [Role.USER, Role.ADMIN],
       ("DELETE", "/your-endpoint/{id}"): [Role.ADMIN],
       ("GET", "/public-endpoint"): None,  # No role required
   }
   ```

2. **Call `authorize_request()` in your route**:

   ```python
   from fastapi import Request, Depends
   from app.service.rbac import RbacService
   from app.service.auth import User, get_current_user

   @router.post("/your-endpoint")
   async def your_endpoint(
       request: Request,
       current_user: User = Depends(get_current_user),
   ):
       await RbacService.authorize_request(request, current_user)
       # Your logic here - user is guaranteed to have required role
       ...
   ```

**Tips**:

- Use `None` in `ROUTE_POLICIES` for routes that only require authentication (no specific role)
- Use list of roles for OR logic: `[Role.USER, Role.ADMIN]` means user needs USER **or** ADMIN
- Route path must match FastAPI's path template exactly (e.g., `/pictures/{picture_id}`)

### Adding New Roles

1. **Add to database**: Insert into `rbac_role` table
2. **Add to enum**: Update `Role` enum in backend/app/service/rbac.py
3. **Assign to users**: Insert into `rbac_user_role` table

## Troubleshooting

### Issue: User has role but gets 403

**Check**:

1. Verify `users.active = TRUE`
2. Verify `rbac_user_role.active = TRUE`
3. Verify `rbac_role.active = TRUE`
4. Verify role name matches exactly (case-sensitive)

### Issue: Performance concerns

**Solution**:

- Database queries are optimized with EXISTS
- Joins are efficient with proper foreign keys
- Consider adding indexes if performance issues occur (not needed initially)

### Issue: Need to check roles programmatically

**Solution**: Use `RbacDataService` directly:

```python
from app.db.utils import sessionmanager
from app.datastore.rbac import RbacDataService

async with sessionmanager.get_session() as session:
    data_service = RbacDataService(session)
    if await data_service.user_has_role(user_id, "admin"):
        # Admin-specific logic
        ...
```

## Summary

The RBAC service provides:

- ✅ **Centralized authorization** - `ROUTE_POLICIES` dictionary as single source of truth
- ✅ **Simplified architecture** - removed wrapper methods, direct `RbacDataService` calls
- ✅ **Secure, real-time role checking** - no caching, immediate access revocation
- ✅ **Type-safe role constants** - `Role` enum prevents typos
- ✅ **Clean FastAPI integration** - one line call to `authorize_request()`
- ✅ **Easy to audit** - all route permissions visible in one place
- ✅ **Active flag enforcement** - validates users, roles, and assignments are active

### Authorization Flow

1. Define policies in `ROUTE_POLICIES` → 2. Call `authorize_request()` → 3. Service checks via `RbacDataService` → 4. Raises 403 if unauthorized

The design prioritizes simplicity, security, and maintainability by using centralized policies and direct database access without unnecessary abstraction layers.
