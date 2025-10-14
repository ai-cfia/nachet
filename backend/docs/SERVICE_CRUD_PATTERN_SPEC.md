# Service CRUD Pattern Specification

**Version:** 2.0  
**Date:** 2025-10-14  
**Status:** Standard

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start-two-step-implementation)
3. [Advanced Usage Patterns](#advanced-usage-patterns)
4. [Prerequisites](#prerequisites)
5. [Implementation Checklist](#implementation-checklist)
6. [Testing Requirements](#testing-requirements)
7. [Examples](#examples)

---

## Overview

**ALL CRUD operations MUST use `BaseCRUDService`** - no exceptions.

`BaseCRUDService` provides a fully implemented generic CRUD service with:

- ✅ All 5 CRUD operations (get_all, get_by_id, create, update, delete)
- ✅ RBAC enforcement (GET for any user, CUD for CFIA admin)
- ✅ Pagination, filtering, and sorting
- ✅ Error handling and structured logging
- ✅ Soft delete (sets active=False)
- ✅ Consistent response formats

### Benefits

- **64% less code**: ~40 lines instead of ~600 lines per service
- **Zero duplication**: All CRUD logic in one place
- **Guaranteed consistency**: Same patterns across all services
- **Easier maintenance**: Bug fixes apply everywhere
- **Industry standard**: Python generics pattern

### Reference Implementations

- `app/service/base_crud.py` - BaseCRUDService implementation
- `app/service/device.py` - DeviceBrandService, DeviceModelService (simple examples)
- `app/service/model.py` - ModelService (with overrides)
- `tests/test_base_crud_service.py` - Comprehensive tests

---

## Quick Start: Two-Step Implementation

### Step 1: Create DataService extending BaseCRUDDataService

```python
from typing import Type
from sqlalchemy.orm import selectinload
from app.service.base_crud import BaseCRUDDataService
from app.db.model import YourEntity

class YourEntityDataService(BaseCRUDDataService[YourEntity]):
    @classmethod
    def get_model_class(cls) -> Type[YourEntity]:
        return YourEntity

    def get_query_options(self) -> list:
        """Optional: Add relationship loading."""
        return [selectinload(YourEntity.related_field)]
```

### Step 2: Create a Service that extends `BaseCRUDService`

```python
from typing import Dict, Any, Type
from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.exceptions import (
    YourEntityNotFoundError,
    YourEntityCreationError,
    YourEntityUpdateError,
    YourEntityDeletionError,
)
from app.db.model import YourEntity

class YourEntityService(BaseCRUDService[YourEntity]):
    @classmethod
    def get_entity_name(cls) -> str:
        return "YourEntity"

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[YourEntity]]:
        return YourEntityDataService

    @classmethod
    def serialize_entity(cls, entity: YourEntity) -> Dict[str, Any]:
        return {
            "id": str(entity.id),
            "name": entity.name,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return YourEntityNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return YourEntityCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return YourEntityUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return YourEntityDeletionError
```

**That's it!** Your service now has all 5 CRUD methods with RBAC, logging, pagination, and error handling.

---

## Advanced Usage Patterns

### Pattern 1: Override Methods (For CRUD Modifications)

Override base class methods when you need to modify standard CRUD behavior:

**Example: OrganizationService (override `create()` to add RBAC roles)**

```python
class OrganizationService(BaseCRUDService[Organization]):
    # get_all(), get_by_id(), update(), delete() inherited ✅
    
    @classmethod
    async def create(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """Override create() to add custom role creation logic."""
        # Call RBAC check
        await RbacService.verify_user_is_cfia_admin(user_id)
        
        async with sessionmanager.get_session() as session:
            data_service = cls.get_data_service_class()(session)
            
            # Create organization (standard)
            organization = await data_service.create(**kwargs)
            
            # CUSTOM LOGIC: Create 2 RBAC roles for organization
            admin_role = RbacRole(
                organization_id=organization.id,
                name="admin",
                description=f"Admin role for {organization.name}"
            )
            user_role = RbacRole(
                organization_id=organization.id,
                name="user",
                description=f"User role for {organization.name}"
            )
            session.add(admin_role)
            session.add(user_role)
            
            await session.commit()
            await session.refresh(organization)
            
            return cls.serialize_entity(organization)
```

### Pattern 2: Add Custom Methods (For Non-CRUD Operations)

Add additional methods alongside inherited CRUD operations:

**Example: ModelService (adds `get_by_task_id()` custom query)**

```python
class ModelService(BaseCRUDService[Model]):
    # get_all(), get_by_id(), create(), update(), delete() inherited ✅
    
    @classmethod
    async def get_all(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """Override to change response key from 'items' to 'models'."""
        result = await super().get_all(user_id, **kwargs)
        result["models"] = result.pop("items")  # Rename key
        return result
    
    @staticmethod
    async def get_by_task_id(user_id: UUID, task_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Custom method: Get models filtered by task_id (not standard CRUD)."""
        await RbacService.get_user_organization_id(user_id)
        
        async with sessionmanager.get_session() as session:
            data_service = ModelDataService(session)
            models = await data_service.get_by_task_id(task_id)
            return {"models": [ModelService.serialize_entity(m) for m in models]}
```

**Key Points:**

- ✅ **Standard CRUD** methods inherited from `BaseCRUDService`
- ✅ **Override** `get_all()` to customize response format
- ✅ **Add** `get_by_task_id()` for custom business logic
- ✅ Both patterns work together seamlessly

### Pattern 3: Complex Serialization

Override `serialize_entity()` for complex field transformations:

```python
class YourEntityService(BaseCRUDService[YourEntity]):
    @classmethod
    def serialize_entity(cls, entity: YourEntity) -> Dict[str, Any]:
        """Custom serialization with nested objects."""
        return {
            "id": str(entity.id),
            "name": entity.name,
            # Include related entity data
            "parent_id": str(entity.parent_id) if entity.parent_id else None,
            "parent_name": entity.parent.name if entity.parent else None,
            # Transform dates
            "date_created": entity.date_created.isoformat(),
            # Include nested collections
            "children": [
                {"id": str(child.id), "name": child.name}
                for child in entity.children
            ] if entity.children else [],
        }
```

---

## Prerequisites

Before implementing CRUD operations for a new entity, ensure:

1. **Database Model** exists in `app/db/model.py`
2. Model has:
   - `id` field (UUID primary key)
   - `active` field (Boolean for soft delete)
   - `date_created` field (DateTime with timezone)
   - `date_updated` field (DateTime with timezone, optional)
3. **Alembic migration** has been created and applied

---

## Implementation Checklist

### Phase 1: Database Model & Exceptions

- [ ] Database model exists in `app/db/model.py` with required fields (id, active, date_created)
- [ ] Alembic migration created and applied
- [ ] Add custom exceptions to `app/exceptions.py`:
  - `{Entity}Error` (base exception)
  - `{Entity}NotFoundError`
  - `{Entity}CreationError`
  - `{Entity}UpdateError`
  - `{Entity}DeletionError`

**Example exceptions:**

```python
class YourEntityError(Exception):
    pass

class YourEntityNotFoundError(YourEntityError):
    pass

class YourEntityCreationError(YourEntityError):
    pass

class YourEntityUpdateError(YourEntityError):
    pass

class YourEntityDeletionError(YourEntityError):
    pass
```

### Phase 2: DataService Layer (Minimal)

- [ ] Create `app/datastore/{entity}.py`
- [ ] Implement `{Entity}DataService(BaseCRUDDataService[{Entity}])`
- [ ] Override `get_model_class()` to return entity class
- [ ] Override `get_query_options()` if relationships need eager loading (optional)
- [ ] Export in `app/datastore/__init__.py`

**Example:**

```python
from typing import Type
from sqlalchemy.orm import selectinload
from app.service.base_crud import BaseCRUDDataService
from app.db.model import YourEntity

class YourEntityDataService(BaseCRUDDataService[YourEntity]):
    @classmethod
    def get_model_class(cls) -> Type[YourEntity]:
        return YourEntity

    def get_query_options(self) -> list:
        """Optional: Add relationship loading."""
        return [selectinload(YourEntity.related_field)]
```

### Phase 3: Service Layer (Minimal)

- [ ] Create `app/service/{entity}.py`
- [ ] Implement `{Entity}Service(BaseCRUDService[{Entity}])`
- [ ] Override 7 required methods:
  - `get_entity_name()` - Return entity name string
  - `get_data_service_class()` - Return DataService class
  - `serialize_entity()` - Convert entity to dict
  - `get_not_found_exception()` - Return NotFoundError class
  - `get_creation_exception()` - Return CreationError class
  - `get_update_exception()` - Return UpdateError class
  - `get_deletion_exception()` - Return DeletionError class
- [ ] Export in `app/service/__init__.py`

### Phase 4: Testing (Minimum 10 Tests Required)

- [ ] Create `tests/test_{entity}_service.py`
- [ ] Test `get_all()` - success case
- [ ] Test `get_by_id()` - success case
- [ ] Test `get_by_id()` - 404 not found
- [ ] Test `create()` - admin success
- [ ] Test `create()` - 403 unauthorized
- [ ] Test `update()` - success case
- [ ] Test `update()` - 404 not found
- [ ] Test `delete()` - success case
- [ ] Test `delete()` - 404 not found
- [ ] Test `delete()` - 403 unauthorized
- [ ] Run tests: `uv run pytest tests/test_{entity}_service.py -v`
- [ ] Verify all tests pass

### Phase 5: Code Quality

- [ ] Run linter: `uv run ruff check app/datastore/{entity}.py app/service/{entity}.py --fix`
- [ ] Verify no linting errors
- [ ] Final test run to ensure linter didn't break anything

---

## Testing Requirements

### Minimum Test Coverage

Every service MUST have these 10 test cases:

1. ✅ `get_all()` - success case (any authenticated user)
2. ✅ `get_by_id()` - success case (any authenticated user)
3. ✅ `get_by_id()` - 404 not found
4. ✅ `create()` - admin success (CFIA admin only)
5. ✅ `create()` - 403 unauthorized (non-admin user)
6. ✅ `update()` - success case (CFIA admin only)
7. ✅ `update()` - 404 not found
8. ✅ `delete()` - success case (CFIA admin only)
9. ✅ `delete()` - 404 not found
10. ✅ `delete()` - 403 unauthorized (non-admin user)

### Test Template

Use this template for `tests/test_{entity}_service.py`:

```python
"""
Tests for {Entity}Service - CRUD operations for {entity}s.

Access Control:
- GET operations: Any authenticated user
- CUD operations: CFIA admin only
"""

import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, status
from dotenv import load_dotenv

from app.service.{entity} import {Entity}Service
from app.db.model import {Entity}

# Load test environment
if not os.getenv("NACHET_SCHEMA"):
    load_dotenv(".env.test.local")


class Test{Entity}ServiceGetAll:
    """Test {Entity}Service.get_all method."""

    @pytest.mark.asyncio
    async def test_get_all_success_authenticated_user(self, monkeypatch):
        """Any authenticated user should be able to list all {entity}s."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        {entity}1_id = uuid4()
        {entity}2_id = uuid4()

        # Mock {entity}s
        {entity}1 = Mock(spec={Entity})
        {entity}1.id = {entity}1_id
        {entity}1.name = "{Entity} 1"
        {entity}1.description = "Test {entity} 1"
        {entity}1.active = True
        {entity}1.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        {entity}2 = Mock(spec={Entity})
        {entity}2.id = {entity}2_id
        {entity}2.name = "{Entity} 2"
        {entity}2.description = "Test {entity} 2"
        {entity}2.active = True
        {entity}2.date_created = datetime(2024, 2, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_all = AsyncMock(return_value=([{entity}1, {entity}2], 2))
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.get_all(user_id)

        # Verify
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "{Entity} 1"
        assert result["items"][1]["name"] == "{Entity} 2"
        assert result["total"] == 2


class Test{Entity}ServiceGetById:
    """Test {Entity}Service.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, monkeypatch):
        """Any authenticated user should be able to retrieve a {entity} by ID."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id
        {entity}.name = "{Entity} 1"
        {entity}.description = "Test {entity}"
        {entity}.active = True
        {entity}.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value={entity})
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.get_by_id(user_id, {entity}_id)

        # Verify
        assert result["name"] == "{Entity} 1"
        assert result["id"] == str({entity}_id)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, monkeypatch):
        """Should return 404 if {entity} not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service - {entity} not found
        mock_data_service = AsyncMock()
        mock_data_service.get_by_id = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.get_by_id(user_id, {entity}_id)

        assert exc_info.value.status_code == 404


class Test{Entity}ServiceCreate:
    """Test {Entity}Service.create method."""

    @pytest.mark.asyncio
    async def test_create_success_as_cfia_admin(self, monkeypatch):
        """CFIA admin should be able to create new {entity}s."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id
        {entity}.name = "{Entity} 1"
        {entity}.description = "Test {entity}"
        {entity}.active = True
        {entity}.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.create = AsyncMock(return_value={entity})
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.create(
            user_id=user_id,
            name="{Entity} 1",
        )

        # Verify
        assert result["name"] == "{Entity} 1"
        assert result["id"] == str({entity}_id)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403."""
        user_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.create(user_id=user_id, name="{Entity} 1")

        assert exc_info.value.status_code == 403


class Test{Entity}ServiceUpdate:
    """Test {Entity}Service.update method."""

    @pytest.mark.asyncio
    async def test_update_success(self, monkeypatch):
        """CFIA admin should be able to update {entity}s."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock updated {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id
        {entity}.name = "{Entity} 1 Updated"
        {entity}.description = "Updated description"
        {entity}.active = True
        {entity}.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value={entity})
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.update(
            user_id, {entity}_id, name="{Entity} 1 Updated"
        )

        # Verify
        assert result["name"] == "{Entity} 1 Updated"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, monkeypatch):
        """Should return 404 if {entity} not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.update = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.update(user_id, {entity}_id, name="Updated")

        assert exc_info.value.status_code == 404


class Test{Entity}ServiceDelete:
    """Test {Entity}Service.delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self, monkeypatch):
        """CFIA admin should be able to soft delete {entity}s."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value={entity})
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.delete(user_id, {entity}_id)

        # Verify
        assert "message" in result
        assert "deleted successfully" in result["message"]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch):
        """Should return 404 if {entity} not found."""
        from app.db.utils import sessionmanager

        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(sessionmanager, "get_session", lambda: mock_session)

        # Mock data service
        mock_data_service = AsyncMock()
        mock_data_service.soft_delete = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.delete(user_id, {entity}_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_unauthorized_non_admin(self, monkeypatch):
        """Non-admin users should get 403 when deleting."""
        user_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_verify_admin(uid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a CFIA admin",
            )

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_is_cfia_admin",
            mock_verify_admin,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.delete(user_id, {entity}_id)

        assert exc_info.value.status_code == 403
```

**Note:** This template uses BaseCRUDService behavior:

- `get_all()` returns pagination data with `items`, `total`, `offset`, `limit`, `has_more`
- All methods use `verify_user_is_cfia_admin()` for CUD operations
- Mock `get_all()` to return tuple: `(list_of_entities, total_count)`

---

## Examples

### Example 1: Simple Entity (DeviceBrand)

**Minimal implementation - only ~40 lines per service!**

**DataService:** `app/datastore/device.py`

```python
from typing import Type
from app.service.base_crud import BaseCRUDDataService
from app.db.model import DeviceBrand

class DeviceBrandDataService(BaseCRUDDataService[DeviceBrand]):
    @classmethod
    def get_model_class(cls) -> Type[DeviceBrand]:
        return DeviceBrand
```

**Service:** `app/service/device.py`

```python
from typing import Dict, Any, Type
from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.datastore.device import DeviceBrandDataService
from app.db.model import DeviceBrand
from app.exceptions import (
    DeviceBrandNotFoundError,
    DeviceCreationError,
    DeviceUpdateError,
    DeviceDeletionError,
)

class DeviceBrandService(BaseCRUDService[DeviceBrand]):
    @classmethod
    def get_entity_name(cls) -> str:
        return "DeviceBrand"
    
    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[DeviceBrand]]:
        return DeviceBrandDataService
    
    @classmethod
    def serialize_entity(cls, entity: DeviceBrand) -> Dict[str, Any]:
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }
    
    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return DeviceBrandNotFoundError
    
    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return DeviceCreationError
    
    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return DeviceUpdateError
    
    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return DeviceDeletionError
```

**Result:** All 5 CRUD methods automatically available with RBAC, logging, pagination!

### Example 2: Entity with Foreign Key Relationship (DeviceModel)

**DataService with eager loading:**

```python
from typing import Type
from sqlalchemy.orm import selectinload
from app.service.base_crud import BaseCRUDDataService
from app.db.model import DeviceModel

class DeviceModelDataService(BaseCRUDDataService[DeviceModel]):
    @classmethod
    def get_model_class(cls) -> Type[DeviceModel]:
        return DeviceModel
    
    def get_query_options(self) -> list:
        """Load device_brand relationship."""
        return [selectinload(DeviceModel.device_brand)]
```

**Service with nested serialization:**

```python
class DeviceModelService(BaseCRUDService[DeviceModel]):
    # ... (other methods same as Example 1) ...
    
    @classmethod
    def serialize_entity(cls, entity: DeviceModel) -> Dict[str, Any]:
        return {
            "id": str(entity.id),
            "name": entity.name,
            "description": entity.description,
            "brand_id": str(entity.brand_id),
            "brand_name": entity.device_brand.name if entity.device_brand else None,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }
```

### Example 3: Service with Method Override (OrganizationService)

See [Pattern 1](#pattern-1-override-methods-for-crud-modifications) above for complete example.

### Example 4: Service with Additional Custom Methods (ModelService)

See [Pattern 2](#pattern-2-add-custom-methods-for-non-crud-operations) above for complete example.

---

## Common Patterns & Tips

### Relationship Loading

```python
# One-to-Many (use selectinload)
return [selectinload(Entity.related_items)]

# Many-to-One (use selectinload or joinedload)
return [selectinload(Entity.parent)]

# Nested relationships
return [
    selectinload(Entity.related_items)
    .selectinload(RelatedItem.sub_items)
]
```

### Optional Fields in Serialization

```python
# Handle null values
"field": entity.field if entity.field else None,

# Handle relationships
"parent_name": entity.parent.name if entity.parent else None,
```

### Date/DateTime Formatting

```python
# DateTime with timezone
"date_field": entity.date_field.isoformat(),

# Optional date
"date_field": entity.date_field.isoformat() if entity.date_field else None,
```

---

## Common Pitfalls

### ❌ Don't

1. **Don't hard delete** - BaseCRUDService uses soft delete (active=False)
2. **Don't skip RBAC** - All methods have built-in RBAC enforcement
3. **Don't reimplement CRUD** - Always extend BaseCRUDService
4. **Don't forget relationship loading** - Use `get_query_options()` for eager loading
5. **Don't skip tests** - Minimum 10 test cases required

### ✅ Do

1. **Do extend BaseCRUDService** - Required for all services
2. **Do override when needed** - For custom logic in CRUD operations
3. **Do add custom methods** - For domain-specific queries
4. **Do test thoroughly** - Cover success and failure cases
5. **Do use linter** - Run ruff before committing

---

## Reference Documentation

- **BaseCRUDService Implementation:** `app/service/base_crud.py`
- **BaseCRUDDataService Implementation:** `app/service/base_crud.py`
- **Example Services:** `app/service/device.py`, `app/service/model.py`
- **Example Tests:** `tests/test_device_service.py`, `tests/test_base_crud_service.py`
- **Database Models:** `app/db/model.py`
- **RBAC Service:** `app/service/rbac.py`

---

## Support

For questions or issues:

1. Review `app/service/base_crud.py` for implementation details
2. Check `app/service/device.py` for simple examples
3. Review `tests/test_base_crud_service.py` for comprehensive test patterns
4. Consult backend team for complex scenarios

---

**Version:** 2.0  
**Last Updated:** 2025-10-14  
**Status:** Standard - All services MUST use BaseCRUDService
