# Service CRUD Pattern Specification

**Version:** 1.0
**Date:** 2025-01-12
**Status:** Standard

## Table of Contents

1. [Overview](#overview)
2. [Pattern Architecture](#pattern-architecture)
3. [Prerequisites](#prerequisites)
4. [Implementation Guide](#implementation-guide)
5. [Code Templates](#code-templates)
6. [Testing Template](#testing-template)
7. [Checklist](#checklist)
8. [Examples](#examples)

---

## Overview

This specification defines the standard pattern for implementing CRUD (Create, Read, Update, Delete) operations in the Nachet backend services. This pattern ensures:

- **Consistent API structure** across all services
- **Proper RBAC (Role-Based Access Control)** with authentication checks
- **Structured logging** with error tracebacks
- **Comprehensive error handling** with custom exceptions
- **Soft delete** for referential integrity
- **Full test coverage** with mocking

### Reference Implementations

- `app/service/device.py` - DeviceBrandService, DeviceModelService, DeviceLensService
- `app/service/model.py` - ModelService
- `app/service/pipeline.py` - PipelineService (new CRUD methods)
- `app/service/base_crud.py` - **BaseCRUDService** (recommended generic implementation)

---

## **RECOMMENDED: Generic Base Class Approach**

**⚠️ IMPORTANT:** Before implementing CRUD operations using the templates below, consider using the **Generic Base Class** approach instead. This eliminates code duplication and follows DRY principles.

### Why Use the Generic Approach?

- **64% less code**: Reduces 600 lines to ~40 lines per service
- **Single source of truth**: All CRUD logic in one place
- **Guaranteed consistency**: Same error handling, logging, RBAC patterns across all services
- **Easier to maintain**: Bug fixes and improvements apply to all services
- **Industry standard**: Python generics are a common pattern for this use case

### Quick Start with BaseCRUDService

**Step 1:** Create a DataService that extends `BaseCRUDDataService`:

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

**Step 2:** Create a Service that extends `BaseCRUDService`:

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
            # Add other fields
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

**That's it!** Your service now has all 5 CRUD methods with RBAC, logging, and error handling.

### Full Documentation

For complete documentation on the generic approach, see:

- **Implementation**: `app/service/base_crud.py`
- **Tests**: `tests/test_base_crud_service.py`
- **Proposal**: `docs/GENERIC_CRUD_SERVICE_PROPOSAL.md`

### When to Use Templates Below

The templates below are provided for:

1. **Reference**: Understanding the pattern in detail
2. **Custom logic**: Services that need significant customization beyond CRUD
3. **Legacy code**: Understanding existing services that haven't been migrated

**For new services, use the generic base class approach above.**

---

## Pattern Architecture

### Three-Layer Architecture

```text
┌─────────────────────────────────────┐
│   Service Layer (Business Logic)   │
│   - RBAC checks                     │
│   - Logging                         │
│   - Exception handling              │
│   - Data transformation             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   DataService Layer (Data Access)   │
│   - Database queries                │
│   - ORM operations                  │
│   - Relationship loading            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Database Layer (SQLAlchemy ORM)   │
│   - Models                          │
│   - Relationships                   │
└─────────────────────────────────────┘
```

### Access Control Pattern

- **GET operations** (`get_all`, `get_by_id`): Any authenticated user
- **CUD operations** (`create`, `update`, `delete`): CFIA admin only

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

## Implementation Guide

### Step 1: Add Custom Exceptions

**File:** `app/exceptions.py`

Add entity-specific exceptions at the end of the file, before `log_error()`:

```python
class {Entity}Error(Exception):
    pass


class {Entity}NotFoundError({Entity}Error):
    pass


class {Entity}CreationError({Entity}Error):
    pass


class {Entity}UpdateError({Entity}Error):
    pass


class {Entity}DeletionError({Entity}Error):
    pass
```

**Example:**

```python
class SeedError(Exception):
    pass

class SeedNotFoundError(SeedError):
    pass
```

---

### Step 2: Create DataService Layer

**File:** `app/datastore/{entity}.py` (create new file)

```python
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import {Entity}


class {Entity}DataService:
    """Data access layer for {Entity} database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[{Entity}]:
        """
        Retrieve all active {entity}s.

        Returns:
            List of {Entity} objects
        """
        query = (
            select({Entity})
            .where({Entity}.active.is_(True))
            # Add relationship loading if needed:
            # .options(selectinload({Entity}.related_entity))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, {entity}_id: UUID) -> Optional[{Entity}]:
        """
        Retrieve a {entity} by ID.

        Args:
            {entity}_id: The {entity} UUID

        Returns:
            {Entity} object if found and active, None otherwise
        """
        query = (
            select({Entity})
            .where({Entity}.id == {entity}_id)
            .where({Entity}.active.is_(True))
            # Add relationship loading if needed
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        # Add required fields
        name: str,
        # Add optional fields with defaults
        description: Optional[str] = None,
    ) -> {Entity}:
        """
        Create a new {entity}.

        Args:
            name: {Entity} name
            description: Optional description

        Returns:
            The created {Entity} object
        """
        {entity} = {Entity}(
            name=name,
            description=description,
            active=True,
        )
        self.session.add({entity})
        await self.session.flush()
        await self.session.refresh({entity})
        return {entity}

    async def update(
        self,
        {entity}_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[{Entity}]:
        """
        Update a {entity}.

        Args:
            {entity}_id: The {entity} UUID
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Updated {Entity} object if found, None otherwise
        """
        {entity} = await self.get_by_id({entity}_id)
        if not {entity}:
            return None

        if name is not None:
            {entity}.name = name
        if description is not None:
            {entity}.description = description

        await self.session.flush()
        await self.session.refresh({entity})
        return {entity}

    async def soft_delete(self, {entity}_id: UUID) -> Optional[{Entity}]:
        """
        Soft delete a {entity} by setting active to False.

        Args:
            {entity}_id: The {entity} UUID

        Returns:
            The soft-deleted {Entity} object if found, None otherwise
        """
        query = select({Entity}).where({Entity}.id == {entity}_id)
        result = await self.session.execute(query)
        {entity} = result.scalar_one_or_none()

        if not {entity}:
            return None

        {entity}.active = False
        await self.session.flush()
        await self.session.refresh({entity})
        return {entity}
```

---

### Step 3: Export DataService

**File:** `app/datastore/__init__.py`

Add import and export:

```python
from .{entity} import {Entity}DataService

__all__ = [
    # ... existing exports
    "{Entity}DataService",
]
```

---

### Step 4: Create Service Layer

**File:** `app/service/{entity}.py` (create new file)

```python
from typing import List, Dict, Any, Optional
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.datastore import {Entity}DataService
from app.db.data.data_constants import ROLE_CFIA_ADMIN
from app.service.logs import LogService
from app.service.rbac import RbacService
from app.exceptions import {Entity}NotFoundError


class {Entity}Service:
    """
    Service layer for {Entity} operations.

    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active {entity}s are returned by default
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for {Entity}Service."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active {entity}s.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "{entity}s" key containing list of {entity} data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = {Entity}DataService(session)

                # Retrieve all {entity}s
                {entity}s = await data_service.get_all()

                return {
                    "{entity}s": [
                        {
                            "id": str({entity}.id),
                            "name": {entity}.name,
                            "description": {entity}.description,
                            "active": {entity}.active,
                            "date_created": {entity}.date_created.isoformat(),
                            # Add other fields as needed
                        }
                        for {entity} in {entity}s
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = {Entity}Service._get_logger()
            logger.error(
                f"Failed to retrieve {entity}s: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve {entity}s",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity}s: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, {entity}_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a {entity} by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            {entity}_id: The {entity} UUID to retrieve

        Returns:
            Dictionary containing {entity} data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = {Entity}DataService(session)

                # Retrieve {entity}
                {entity} = await data_service.get_by_id({entity}_id)
                if not {entity}:
                    raise {Entity}NotFoundError(f"{Entity} {{entity}_id} not found")

                return {
                    "id": str({entity}.id),
                    "name": {entity}.name,
                    "description": {entity}.description,
                    "active": {entity}.active,
                    "date_created": {entity}.date_created.isoformat(),
                    # Add other fields as needed
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except {Entity}NotFoundError as e:
            logger = {Entity}Service._get_logger()
            logger.warning(
                f"{Entity} not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = {Entity}Service._get_logger()
            logger.error(
                f"Failed to retrieve {entity}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            logger.debug(
                "Traceback for failed retrieve {entity}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {entity}: {str(e)}",
            )

    @staticmethod
    async def create(
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new {entity}.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: {Entity} name
            description: Optional description

        Returns:
            Dictionary containing the created {entity} data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = {Entity}DataService(session)

                # Create the {entity}
                {entity} = await data_service.create(
                    name=name,
                    description=description,
                )
                await session.commit()

                logger = {Entity}Service._get_logger()
                logger.info(
                    f"Created {entity}: {{entity}.name}",
                    {entity}_id=str({entity}.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str({entity}.id),
                    "name": {entity}.name,
                    "description": {entity}.description,
                    "active": {entity}.active,
                    "date_created": {entity}.date_created.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = {Entity}Service._get_logger()
            logger.error(
                f"Failed to create {entity}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                {entity}_name=name,
            )
            logger.debug(
                "Traceback for failed create {entity}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {entity}: {str(e)}",
            )

    @staticmethod
    async def update(
        user_id: UUID,
        {entity}_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing {entity}.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            {entity}_id: The {entity} UUID to update
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Dictionary containing the updated {entity} data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = {Entity}DataService(session)

                # Update the {entity}
                {entity} = await data_service.update(
                    {entity}_id={entity}_id,
                    name=name,
                    description=description,
                )
                if not {entity}:
                    raise {Entity}NotFoundError(f"{Entity} {{entity}_id} not found")

                await session.commit()

                logger = {Entity}Service._get_logger()
                logger.info(
                    f"Updated {entity}: {{entity}.name}",
                    {entity}_id=str({entity}.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str({entity}.id),
                    "name": {entity}.name,
                    "description": {entity}.description,
                    "active": {entity}.active,
                    "date_created": {entity}.date_created.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except {Entity}NotFoundError as e:
            logger = {Entity}Service._get_logger()
            logger.warning(
                f"{Entity} not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = {Entity}Service._get_logger()
            logger.error(
                f"Failed to update {entity}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            logger.debug(
                "Traceback for failed update {entity}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {entity}: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, {entity}_id: UUID) -> Dict[str, str]:
        """
        Soft delete a {entity} (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            {entity}_id: The {entity} UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is cfia_admin
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = {Entity}DataService(session)

                # Soft delete the {entity}
                {entity} = await data_service.soft_delete({entity}_id)
                if not {entity}:
                    raise {Entity}NotFoundError(f"{Entity} {{entity}_id} not found")

                await session.commit()

                logger = {Entity}Service._get_logger()
                logger.info(
                    f"Deleted {entity}: {{entity}_id}",
                    {entity}_id=str({entity}_id),
                    user_id=str(user_id),
                )

                return {"message": f"{Entity} {{entity}_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except {Entity}NotFoundError as e:
            logger = {Entity}Service._get_logger()
            logger.warning(
                f"{Entity} not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = {Entity}Service._get_logger()
            logger.error(
                f"Failed to delete {entity}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                {entity}_id=str({entity}_id),
            )
            logger.debug(
                "Traceback for failed delete {entity}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {entity}: {str(e)}",
            )
```

---

### Step 5: Export Service

**File:** `app/service/__init__.py`

Add import and export:

```python
from .{entity} import {Entity}Service

__all__ = [
    # ... existing exports
    "{Entity}Service",
]
```

---

### Step 6: Create Comprehensive Tests

**File:** `tests/test_{entity}_service.py` (create new file)

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
        mock_data_service.get_all = AsyncMock(return_value=[{entity}1, {entity}2])
        monkeypatch.setattr(
            "app.service.{entity}.{Entity}DataService",
            lambda session: mock_data_service,
        )

        # Call service
        result = await {Entity}Service.get_all(user_id)

        # Verify
        assert "{entity}s" in result
        assert len(result["{entity}s"]) == 2
        assert result["{entity}s"][0]["name"] == "{Entity} 1"
        assert result["{entity}s"][1]["name"] == "{Entity} 2"


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

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock updated {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id
        {entity}.name = "{Entity} 1 Updated"
        {entity}.description = "Updated description"
        {entity}.active = True
        {entity}.date_created = datetime(2024, 1, 1, tzinfo=timezone.utc)

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock {entity}
        {entity} = Mock(spec={Entity})
        {entity}.id = {entity}_id

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            pass

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
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
        user_org_id = uuid4()
        {entity}_id = uuid4()

        # Mock RbacService
        async def mock_get_org_id(uid):
            return user_org_id

        async def mock_verify_role(uid, role, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required role: {role}",
            )

        monkeypatch.setattr(
            "app.service.{entity}.RbacService.get_user_organization_id",
            mock_get_org_id,
        )
        monkeypatch.setattr(
            "app.service.{entity}.RbacService.verify_user_has_role",
            mock_verify_role,
        )

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await {Entity}Service.delete(user_id, {entity}_id)

        assert exc_info.value.status_code == 403
```

---

## Code Templates

### Relationship Loading Examples

For entities with relationships, add `selectinload` or `joinedload`:

```python
# One-to-Many (use selectinload)
.options(selectinload(Entity.related_items))

# Many-to-One (use joinedload)
.options(joinedload(Entity.parent))

# Nested relationships
.options(
    selectinload(Entity.related_items)
    .selectinload(RelatedItem.sub_items)
)
```

### Optional Fields Pattern

For optional updates:

```python
if field is not None:
    entity.field = field
```

For optional returns (can be null):

```python
"field": entity.field if entity.field else None,
```

### Date/DateTime Handling

```python
# DateTime with timezone
"date_field": entity.date_field.isoformat(),

# Date only
"date_field": entity.date_field.isoformat() if entity.date_field else None,
```

---

## Testing Template

### Minimum Test Coverage

Every service must have tests for:

1. ✅ `get_all` - success case
2. ✅ `get_by_id` - success case
3. ✅ `get_by_id` - 404 not found case
4. ✅ `create` - admin success case
5. ✅ `create` - 403 unauthorized case
6. ✅ `update` - success case
7. ✅ `update` - 404 not found case
8. ✅ `delete` - success case
9. ✅ `delete` - 404 not found case
10. ✅ `delete` - 403 unauthorized case

### **Minimum: 10 test cases**

---

## Checklist

Use this checklist when implementing CRUD for a new entity:

### Phase 1: Exceptions

- [ ] Add `{Entity}Error` base exception to `app/exceptions.py`
- [ ] Add `{Entity}NotFoundError` to `app/exceptions.py`
- [ ] Add `{Entity}CreationError` to `app/exceptions.py`
- [ ] Add `{Entity}UpdateError` to `app/exceptions.py`
- [ ] Add `{Entity}DeletionError` to `app/exceptions.py`

### Phase 2: DataService Layer

- [ ] Create `app/datastore/{entity}.py`
- [ ] Implement `{Entity}DataService` class
- [ ] Implement `get_all()` method with relationship loading
- [ ] Implement `get_by_id()` method
- [ ] Implement `create()` method with all required fields
- [ ] Implement `update()` method with optional field handling
- [ ] Implement `soft_delete()` method
- [ ] Add import to `app/datastore/__init__.py`
- [ ] Add to `__all__` in `app/datastore/__init__.py`

### Phase 3: Service Layer

- [ ] Create `app/service/{entity}.py`
- [ ] Add all required imports
- [ ] Implement `{Entity}Service` class
- [ ] Add singleton logger (`_logger`, `_get_logger()`)
- [ ] Implement `get_all(user_id)` with RBAC
- [ ] Implement `get_by_id(user_id, {entity}_id)` with RBAC and 404 handling
- [ ] Implement `create(user_id, ...)` with admin RBAC
- [ ] Implement `update(user_id, {entity}_id, ...)` with admin RBAC
- [ ] Implement `delete(user_id, {entity}_id)` with admin RBAC
- [ ] Add import to `app/service/__init__.py`
- [ ] Add to `__all__` in `app/service/__init__.py`

### Phase 4: Testing

- [ ] Create `tests/test_{entity}_service.py`
- [ ] Add test environment setup
- [ ] Implement `Test{Entity}ServiceGetAll` with success test
- [ ] Implement `Test{Entity}ServiceGetById` with success and 404 tests
- [ ] Implement `Test{Entity}ServiceCreate` with success and 403 tests
- [ ] Implement `Test{Entity}ServiceUpdate` with success and 404 tests
- [ ] Implement `Test{Entity}ServiceDelete` with success, 404, and 403 tests
- [ ] Run tests: `uv run pytest tests/test_{entity}_service.py -v`
- [ ] Verify all tests pass (minimum 10/10)

### Phase 5: Code Quality

- [ ] Run linter: `uv run ruff check app/datastore/{entity}.py app/service/{entity}.py --fix`
- [ ] Verify no linting errors
- [ ] Final test run to ensure linter didn't break anything

### Phase 6: Documentation (Optional)

- [ ] Add docstrings to all public methods
- [ ] Document any special business logic
- [ ] Update API documentation if applicable

---

## Examples

### Example 1: Simple Entity (DeviceBrand)

**Files:**

- `app/datastore/device.py` → `DeviceBrandDataService`
- `app/service/device.py` → `DeviceBrandService`
- `tests/test_device_service.py` → `TestDeviceBrandService*`

**Fields:**

- `id`: UUID (primary key)
- `name`: str (required)
- `description`: str (optional)
- `active`: bool (soft delete)

**Relationships:** None (simple entity)

### Example 2: Entity with Foreign Key (DeviceModel)

**Files:**

- `app/datastore/device.py` → `DeviceModelDataService`
- `app/service/device.py` → `DeviceModelService`
- `tests/test_device_service.py` → `TestDeviceModelService*`

**Fields:**

- `id`: UUID (primary key)
- `name`: str (required)
- `description`: str (optional)
- `brand_id`: UUID (foreign key to DeviceBrand)
- `active`: bool (soft delete)

**Relationships:**

```python
.options(selectinload(DeviceModel.device_brand))
```

**Response includes parent:**

```python
"brand_id": str(model.brand_id),
"brand_name": model.brand.name if model.brand else None,
```

### Example 3: Complex Entity (Model)

**Files:**

- `app/datastore/model.py` → `ModelDataService`
- `app/service/model.py` → `ModelService`
- `tests/test_model_service.py` → `TestModelService*`

**Fields:** 15+ fields including:

- Required: `task_id`, `name`, `endpoint_name`, `api_url`, `api_key`, `created_by`, `date_model_training`
- Optional: `version`, `description`, `job_name`, `dataset`, `artifacts_url`, `sha256`

**Relationships:**

```python
.options(selectinload(Model.model_task))
```

### Example 4: Entity with Complex Data (Pipeline)

**Files:**

- `app/datastore/pipeline.py` → `PipelineDataService`
- `app/service/pipeline.py` → `PipelineService` (new CRUD methods added)
- `tests/test_pipeline_service.py` → `TestPipelineService*`

**Special Considerations:**

- Has JSON fields (`data`, `identifiable`, `metrics`)
- Has nested relationships (pipeline → pipeline_models → models)
- Existing methods preserved, new CRUD methods added separately

**Pattern:**

- Keep existing business logic methods untouched
- Add new standardized CRUD methods following the pattern
- Both coexist in same service class

---

## Common Pitfalls

### ❌ Don't

1. **Don't hard delete** - always use soft delete (active=False)
2. **Don't skip RBAC checks** - all methods need authentication
3. **Don't skip logging** - use singleton logger for all errors
4. **Don't forget session.commit()** - required for CUD operations
5. **Don't use bare exceptions** - catch specific exceptions first
6. **Don't skip tests** - minimum 10 test cases required
7. **Don't modify existing methods** - add new ones if needed
8. **Don't forget relationship loading** - use selectinload/joinedload

### ✅ Do

1. **Do verify user exists** - `RbacService.get_user_organization_id(user_id)`
2. **Do verify admin role** - `RbacService.verify_user_has_role()` for CUD
3. **Do log all errors** - with traceback for debugging
4. **Do use custom exceptions** - `{Entity}NotFoundError` for 404s
5. **Do convert UUIDs to strings** - in service layer responses
6. **Do handle None values** - for optional fields
7. **Do test both success and failure** - for each operation
8. **Do run linter** - before committing code

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-12 | Initial specification based on Device, Model, and Pipeline services |

---

## References

- **DeviceService Implementation:** `app/service/device.py`
- **ModelService Implementation:** `app/service/model.py`
- **PipelineService Implementation:** `app/service/pipeline.py`
- **Test Examples:** `tests/test_device_service.py`, `tests/test_model_service.py`, `tests/test_pipeline_service.py`
- **Database Models:** `app/db/model.py`
- **RBAC Service:** `app/service/rbac.py`
- **Logging Service:** `app/service/logs.py`

---

## Support

For questions or clarifications about this specification:

1. Review the reference implementations listed above
2. Check existing tests for examples
3. Consult with the backend team lead

---

### **End of Specification**
