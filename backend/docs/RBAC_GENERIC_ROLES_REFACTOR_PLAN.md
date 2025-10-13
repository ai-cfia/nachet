# RBAC Generic Role Names Refactor - Implementation Plan

**Status:** Planning Phase
**Date Created:** 2025-10-13
**Pre-requisite:** System is pre-production, can reseed databases

## Overview

Simplify RBAC architecture by using generic role names ("admin", "user") for all organizations, with CFIA cross-org authority determined by checking if user's organization matches the CFIA org ID from config.

## Architecture Changes

### Current State

- **Role names:** `"cfia_admin"`, `"external_admin"`, `"admin_{org}_{random}"`, etc.
- **RBAC checks:** Hardcode `ROLE_CFIA_ADMIN` string constant from `app/db/data/data_constants.py`
- **OrganizationService:** Generates unique role names with random suffixes via `_generate_role_name()`
- **CFIA authority:** Based on role name matching "cfia_admin"

### Target State

- **Role names:** `"admin"`, `"user"` (all orgs), plus `"verifier"` (CFIA only)
- **Authority logic:** Check if `user_org_id == CFIA_ORG_ID` + `role_name == "admin"` → cross-org authority
- **Config:** Already has `cfia_organization_id` in Settings (line 74 of `app/api/config.py`)
- **Constants:** New `app/service/constants.py` for business logic (not seeding)

### Key Design Decisions

1. **Generic role names:** All organizations get roles named "admin" and "user"
2. **Organization-scoped:** The `organization_id` FK provides the context
3. **CFIA identification:** Via environment variable `CFIA_ORGANIZATION_ID` (UUID)
4. **Authority determination:** Business logic checks org ID, not role name
5. **CFIA-specific roles:** CFIA org can have additional roles like "verifier"

## Files to Create

### 1. `app/service/constants.py` (~30 lines)

New constants file for service layer (NOT for database seeding):

```python
"""
Service-layer constants.

These constants are used for business logic authorization checks.
Role names are generic across all organizations.
"""

from uuid import UUID
from app.api.config import get_settings

# Generic role name constants (used across all organizations)
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_VERIFIER = "verifier"  # CFIA-specific role (other orgs don't have this)

def get_cfia_org_id() -> UUID:
    """
    Get CFIA organization ID from config.

    This ID is used to determine if a user has cross-organization authority.
    CFIA admins (users with "admin" role in CFIA org) can access all org data.

    Returns:
        UUID of CFIA organization

    Raises:
        ValueError: If CFIA_ORGANIZATION_ID not configured
    """
    settings = get_settings()
    if not settings.cfia_organization_id:
        raise ValueError(
            "CFIA_ORGANIZATION_ID not configured in environment. "
            "This is required to determine cross-organization authority."
        )
    return UUID(settings.cfia_organization_id)
```

**Why separate from data_constants.py?**

- `data_constants.py` is for database seeding (test/dev environments)
- `constants.py` is for service layer business logic (all environments)
- Separation of concerns: seeding vs. runtime authorization

## Files to Modify

### 2. `app/service/rbac.py` (+60 lines)

Add helper methods to encapsulate CFIA authority logic:

**New methods:**

```python
from app.service.constants import ROLE_ADMIN, get_cfia_org_id

@staticmethod
async def is_user_cfia_admin(user_id: UUID) -> bool:
    """
    Check if user is CFIA admin (has cross-organization authority).

    A user is a CFIA admin if:
    1. User belongs to CFIA organization (org_id == CFIA_ORG_ID)
    2. User has "admin" role in that organization

    Args:
        user_id: The user's UUID

    Returns:
        True if user is CFIA admin, False otherwise
    """
    try:
        user_org_id = await RbacService.get_user_organization_id(user_id)
        cfia_org_id = get_cfia_org_id()

        if user_org_id != cfia_org_id:
            return False

        # Check if user has "admin" role in CFIA org
        async with sessionmanager.get_session() as session:
            has_role = await OrganizationDataService(session).user_has_role(
                user_id, user_org_id, ROLE_ADMIN
            )

        return has_role
    except Exception:
        return False

@staticmethod
async def verify_user_is_cfia_admin(user_id: UUID) -> UUID:
    """
    Verify user is CFIA admin (has cross-organization authority).

    CFIA admins have authority to create/update/delete resources across
    all organizations in the system.

    Args:
        user_id: The user's UUID

    Returns:
        UUID of CFIA organization

    Raises:
        HTTPException: 403 if user is not CFIA admin
    """
    user_org_id = await RbacService.get_user_organization_id(user_id)
    cfia_org_id = get_cfia_org_id()

    if user_org_id != cfia_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires CFIA administrator authority"
        )

    # Verify user has "admin" role in CFIA org
    await RbacService.verify_user_has_role(user_id, ROLE_ADMIN, user_org_id)

    return user_org_id

@staticmethod
async def verify_user_is_org_admin(user_id: UUID) -> UUID:
    """
    Verify user is admin in their organization.

    Unlike CFIA admin, org admins only have authority within their own
    organization's data (org-scoped authority).

    Args:
        user_id: The user's UUID

    Returns:
        UUID of user's organization

    Raises:
        HTTPException: 403 if user is not admin in their org
    """
    user_org_id = await RbacService.get_user_organization_id(user_id)

    # Verify user has "admin" role in their org
    await RbacService.verify_user_has_role(user_id, ROLE_ADMIN, user_org_id)

    return user_org_id
```

**Why these methods?**

- Encapsulate authority logic (DRY principle)
- Clear semantics: "CFIA admin" vs "org admin"
- Single source of truth for CFIA org ID checking
- Easy to test (mock these methods in tests)

### 3. `app/service/organization.py` (~50 lines changed)

**Remove:**

- `_generate_role_name()` method (lines 40-59) - no longer needed

**Update `_create_organization_roles()`:**

```python
@staticmethod
async def _create_organization_roles(
    session, organization_id: UUID, org_name: str
) -> Dict[str, UUID]:
    """
    Create the 2 standard roles for a new organization.

    All organizations get:
    - "admin" role: Administrator for the organization
    - "user" role: Standard user for the organization

    Note: CFIA organization also gets "verifier" role created separately.

    Args:
        session: Database session
        organization_id: UUID of the organization
        org_name: Name of the organization (for description only)

    Returns:
        Dictionary mapping role types to their UUIDs
    """
    # Create admin role
    admin_role = RbacRole(
        organization_id=organization_id,
        name="admin",  # Generic name, scoped by organization_id
        description=f"Administrator role for {org_name}",
        active=True,
    )

    # Create user role
    user_role = RbacRole(
        organization_id=organization_id,
        name="user",  # Generic name, scoped by organization_id
        description=f"User role for {org_name}",
        active=True,
    )

    session.add(admin_role)
    session.add(user_role)
    await session.flush()

    return {
        "admin": admin_role.id,
        "user": user_role.id,
    }
```

**Update docstrings:**

Change from:

```python
System Invariants:
- Each organization has 2 organization-specific RBAC roles created automatically:
  * admin_{org_prefix}_{random}: Admin role for the organization
  * user_{org_prefix}_{random}: User role for the organization
```

Change to:

```python
System Invariants:
- Each organization has 2 RBAC roles created automatically:
  * "admin": Administrator role (org-scoped by organization_id)
  * "user": User role (org-scoped by organization_id)
- CFIA organization also has "verifier" role for data verification
- Role authority determined by organization_id, not role name
```

### 4. `app/db/data/data_constants.py` (~20 lines changed)

**Update `seed_rbac_roles()`:**

```python
async def seed_rbac_roles(session: AsyncSession, organization_id: UUID) -> dict:
    """
    Seed the standard RBAC roles for an organization.

    Standard roles (all organizations):
    - "admin": Administrator role
    - "user": Standard user role

    CFIA-specific roles:
    - "verifier": Data verification role (only for CFIA)

    Args:
        session: Database session
        organization_id: The organization UUID to associate roles with

    Returns:
        Dictionary mapping role names to their UUIDs
    """
    # Determine if this is CFIA organization
    from app.api.config import get_settings
    settings = get_settings()
    is_cfia = (
        settings.cfia_organization_id and
        str(organization_id) == settings.cfia_organization_id
    )

    roles = [
        RbacRole(
            id=uuid.uuid5(organization_id, "admin"),
            organization_id=organization_id,
            name="admin",  # Generic name for all orgs
            description="Administrator with full organization access",
            active=True,
        ),
        RbacRole(
            id=uuid.uuid5(organization_id, "user"),
            organization_id=organization_id,
            name="user",  # Generic name for all orgs
            description="Standard user access",
            active=True,
        ),
    ]

    role_ids = {
        "admin": roles[0].id,
        "user": roles[1].id,
    }

    # Add CFIA-specific roles
    if is_cfia:
        verifier_role = RbacRole(
            id=uuid.uuid5(organization_id, "verifier"),
            organization_id=organization_id,
            name="verifier",
            description="CFIA data verification role",
            active=True,
        )
        roles.append(verifier_role)
        role_ids["verifier"] = verifier_role.id

    session.add_all(roles)
    return role_ids
```

**Remove deprecated constants:**

```python
# DEPRECATED: Use constants from app/service/constants.py instead
# These are kept temporarily for backwards compatibility
ROLE_CFIA_ADMIN = "cfia_admin"  # ← Mark as deprecated, will be removed
ROLE_CFIA_USER = "cfia_user"    # ← Mark as deprecated
ROLE_CFIA_VERIFIER = "cfia_verifier"  # ← Mark as deprecated

# REMOVED: These were test stubs only
# ROLE_EXTERNAL_USER = "external_user"
# ROLE_EXTERNAL_ADMIN = "external_admin"
```

### 5. Update 5 service files (~10 lines each)

Replace RBAC pattern in:

- `app/service/base_crud.py` (3 occurrences in create/update/delete)
- `app/service/pipeline.py` (3 occurrences in create/update/delete)
- `app/service/model.py` (3 occurrences in create/update/delete)
- `app/service/device.py` (3 occurrences in create/update/delete)
- `app/service/organization.py` (5 occurrences in get_all/get_by_id/create/update/delete)

**Change from:**

```python
from app.db.data.data_constants import ROLE_CFIA_ADMIN

async def create(user_id: UUID, **kwargs):
    try:
        # Verify user is CFIA admin
        user_org_id = await RbacService.get_user_organization_id(user_id)
        await RbacService.verify_user_has_role(user_id, ROLE_CFIA_ADMIN, user_org_id)

        # ... create logic
```

**Change to:**

```python
from app.service.rbac import RbacService

async def create(user_id: UUID, **kwargs):
    try:
        # Verify user is CFIA admin (cross-org authority)
        await RbacService.verify_user_is_cfia_admin(user_id)

        # ... create logic
```

**Lines to change:**

- `app/service/base_crud.py`: Lines 453, 528, 617
- `app/service/pipeline.py`: Lines with `ROLE_CFIA_ADMIN` import and usage
- `app/service/model.py`: Lines with `ROLE_CFIA_ADMIN` import and usage
- `app/service/device.py`: Lines with `ROLE_CFIA_ADMIN` import and usage
- `app/service/organization.py`: Lines 10, 124, 188, 284, 372, 460

### 6. Update 6 test files (~20 lines each)

Update test mocks in:

- `tests/test_base_crud_service.py`
- `tests/test_pipeline_service.py`
- `tests/test_model_service.py`
- `tests/test_device_service.py`
- `tests/test_organization_service.py`
- `tests/test_rbac_service.py`

**Add mocks for new methods:**

```python
# Old mock pattern
mock_rbac = AsyncMock()
mock_rbac.get_user_organization_id = AsyncMock(return_value=org_id)
mock_rbac.verify_user_has_role = AsyncMock()

# New mock pattern
mock_rbac = AsyncMock()
mock_rbac.verify_user_is_cfia_admin = AsyncMock(return_value=cfia_org_id)
mock_rbac.verify_user_is_org_admin = AsyncMock(return_value=user_org_id)
mock_rbac.is_user_cfia_admin = AsyncMock(return_value=True)
```

**Test scenarios to update:**

1. CFIA admin tests: Mock `verify_user_is_cfia_admin()` to succeed
2. CFIA admin failure tests: Mock `verify_user_is_cfia_admin()` to raise 403
3. Org admin tests: Mock `verify_user_is_org_admin()` to succeed
4. Check tests: Mock `is_user_cfia_admin()` to return True/False

### 7. `.env.template` (+2 lines)

Add documentation for CFIA org ID:

```bash
# RBAC Configuration
# UUID of CFIA organization - used to determine cross-organization authority
# CFIA admins (users with "admin" role in this org) can access all org data
CFIA_ORGANIZATION_ID=
```

### 8. Documentation updates

**`docs/nachet-rbac-documentation.md`:**

- Update "Common Roles" section (line 138-148)
- Change examples from `"cfia_admin"` → `"admin"`
- Add explanation of CFIA authority via org ID
- Update code examples throughout

**`docs/BASE_CRUD_IMPLEMENTATION_SUMMARY.md`:**

- Update RBAC pattern examples
- Change `ROLE_CFIA_ADMIN` → `verify_user_is_cfia_admin()`

**`docs/SERVICE_CRUD_PATTERN_SPEC.md`:**

- Update RBAC pattern examples
- Show new authorization pattern

## Implementation Order

### **Phase 1: Foundation (no breaking changes)**

1. Create `app/service/constants.py`
2. Add new methods to `app/service/rbac.py`

### **Phase 2: Service Layer Updates**

1. Update `app/service/organization.py` (remove random suffix generation)
2. Update 5 service files (base_crud, pipeline, model, device, organization)
3. Update 6 test files

### **Phase 3: Database Layer Updates**

1. Update `app/db/data/data_constants.py` (change seeding to generic names)
2. Update `.env.template` documentation

### **Phase 4: Documentation**

1. Update all documentation files

### **Phase 5: Database Reseed**

1. Reseed dev/test databases with new role names
2. Update `CFIA_ORGANIZATION_ID` in environment configs

## Testing Strategy

### Unit Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific service tests
uv run pytest tests/test_base_crud_service.py -v
uv run pytest tests/test_rbac_service.py -v
uv run pytest tests/test_organization_service.py -v
```

### Integration Tests

1. **CFIA admin authority:** Verify CFIA admin can create/update/delete in any org
2. **External org admin authority:** Verify external admin can only modify their org data
3. **Organization creation:** Verify new orgs get "admin" and "user" roles
4. **CFIA verifier role:** Verify CFIA org has "verifier" role
5. **Role name validation:** Verify roles are named "admin"/"user" not "admin_{org}_{random}"

### Manual Testing

1. Create CFIA organization with UUID matching `CFIA_ORGANIZATION_ID`
2. Create test user in CFIA org with "admin" role
3. Verify CFIA admin can access other org resources
4. Create external organization
5. Create test user in external org with "admin" role
6. Verify external admin cannot access other org resources

## Breaking Changes

### Database Schema

- Role names change from `"cfia_admin"` → `"admin"`
- Role names change from `"admin_{org}_{random}"` → `"admin"`
- Requires database reseed (drop and recreate roles)

### Pre-production Status

- System hasn't reached production
- Can safely reseed dev/test databases
- No data migration required

### Config Requirements

- **Must set:** `CFIA_ORGANIZATION_ID` in environment variables
- System will raise `ValueError` at startup if not configured

## Rollback Plan

If issues arise:

1. **Revert code changes:**

   ```bash
   git revert <commit-hash>
   ```

2. **Reseed databases with old schema:**
   - Use old seeding functions with `"cfia_admin"` role names

3. **Update environment:**
   - Remove `CFIA_ORGANIZATION_ID` if needed (optional for old code)

## Estimated Effort

### Lines of Code

- **New files:** ~30 lines (constants.py)
- **Modified code:** ~250 lines across 20 files
- **Total:** ~280 lines changed

### Time Estimate

- **Phase 1:** 30 minutes (foundation)
- **Phase 2:** 1 hour (service updates)
- **Phase 3:** 30 minutes (database layer)
- **Phase 4:** 30 minutes (documentation)
- **Phase 5:** 30 minutes (database reseed)
- **Testing:** 1 hour (unit + integration tests)
- **Total:** ~4 hours

## Benefits

✅ **Cleaner architecture:** Generic role names, no random suffixes
✅ **Explicit authority:** CFIA cross-org authority based on org ID, not role name
✅ **Simpler role creation:** No need for unique name generation
✅ **Config-driven:** CFIA org ID in environment variable
✅ **Extensible:** Easy to add more orgs with special roles (just check org ID)
✅ **Centralized logic:** All authority checks in RbacService
✅ **Better testability:** Mock `verify_user_is_cfia_admin()` instead of complex chains
✅ **Maintainable:** Single source of truth for authority determination

## Risks and Mitigations

### Risk: CFIA_ORGANIZATION_ID not configured

**Mitigation:** System validates at startup, fails fast with clear error message

### Risk: Wrong UUID configured for CFIA org

**Mitigation:** Startup validation checks org exists and is active, document UUID in env template

### Risk: Forgetting to update a service file

**Mitigation:** Comprehensive grep for `ROLE_CFIA_ADMIN` imports, systematic file updates

### Risk: Test mocks outdated

**Mitigation:** Run full test suite after changes, tests will fail if mocks incorrect

### Risk: Database state inconsistent

**Mitigation:** Pre-production status allows full database reseed, no migration needed

## Success Criteria

✅ All unit tests pass
✅ All integration tests pass
✅ CFIA admin can access all org data
✅ External admin can only access own org data
✅ New orgs created with "admin" and "user" roles
✅ CFIA org has "verifier" role
✅ No `ROLE_CFIA_ADMIN` imports in service layer
✅ `CFIA_ORGANIZATION_ID` configured in all environments

## Next Steps After Completion

1. Update API endpoints to expose pagination parameters (from previous work)
2. Consider adding more CFIA-specific roles (e.g., "auditor", "supervisor")
3. Add org admin UI for managing users/roles within their org
4. Implement audit logging for CFIA cross-org access
5. Add rate limiting for CFIA admin operations

---

**Document Status:** Draft Plan
**Last Updated:** 2025-01-13
**Ready for Review:** Yes
**Ready for Execution:** Pending approval
