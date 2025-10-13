# Generic CRUD Service Architecture Proposal

**Status:** Proposed Refactoring
**Current Issue:** 2000+ lines of duplicated code across services
**Impact:** High maintenance burden, inconsistency risk

---

## Current State Problem

### Code Duplication Analysis

```text
ModelService:        600 lines (90% boilerplate)
PipelineService:     400 lines (90% boilerplate)
DeviceBrandService:  200 lines (90% boilerplate)
DeviceModelService:  200 lines (90% boilerplate)
DeviceLensService:   200 lines (90% boilerplate)
---------------------------------------------------
TOTAL:              1600+ lines of nearly identical code
```

**Every service repeats:**

- RBAC authentication checks
- Error handling with try/except blocks
- Logging with tracebacks
- HTTPException raising with status codes
- Session management
- Custom exception handling
- UUID to string conversion
- Dictionary response building

**Maintenance issues:**

1. Bug fix requires changing 5+ files
2. New feature (e.g., audit logging) requires updating all services
3. Inconsistency creeps in over time
4. New developers copy-paste incorrectly

---

## Proposed Architecture: Generic Base Service

### Design Pattern: Generic + Template Method

```python
# app/service/base_crud.py

from typing import TypeVar, Generic, Type, Dict, Any, List, Optional, Callable
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.db.data.data_constants import ROLE_CFIA_ADMIN
from app.service.logs import LogService
from app.service.rbac import RbacService

T = TypeVar('T')  # Database model type


class BaseCRUDService(Generic[T]):
    """
    Generic CRUD service providing standard operations for all entities.

    This eliminates code duplication while allowing customization through:
    - Serialization hooks
    - Validation hooks
    - Custom query modifications

    Usage:
        class ModelService(BaseCRUDService[Model]):
            entity_name = "model"
            data_service_class = ModelDataService
            not_found_exception = ModelNotFoundError
    """

    # Subclasses must define these
    entity_name: str = None
    entity_name_plural: str = None  # Optional, defaults to entity_name + "s"
    data_service_class: Type = None
    not_found_exception: Type[Exception] = None

    # Singleton logger
    _logger = None

    def __init_subclass__(cls, **kwargs):
        """Validate that subclasses define required attributes."""
        super().__init_subclass__(**kwargs)
        if not cls.entity_name_plural:
            cls.entity_name_plural = f"{cls.entity_name}s"

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @classmethod
    def serialize_entity(cls, entity: T) -> Dict[str, Any]:
        """
        Convert entity to dictionary. Override in subclass for custom fields.

        Default implementation handles common fields.
        Override for entity-specific serialization.
        """
        return {
            "id": str(entity.id),
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }

    @classmethod
    async def get_all(
        cls,
        user_id: UUID,
        include_inactive: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all entities.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            include_inactive: Whether to include inactive entities (default: False)

        Returns:
            Dictionary with entity_name_plural key containing list of entity data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Verify user exists
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = cls.data_service_class(session)
                entities = await data_service.get_all()

                return {
                    cls.entity_name_plural: [
                        cls.serialize_entity(entity)
                        for entity in entities
                        if include_inactive or entity.active
                    ]
                }

        except HTTPException:
            raise
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to retrieve {cls.entity_name_plural}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                f"Traceback for failed retrieve {cls.entity_name_plural}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {cls.entity_name_plural}: {str(e)}",
            )

    @classmethod
    async def get_by_id(cls, user_id: UUID, entity_id: UUID) -> Dict[str, Any]:
        """
        Retrieve an entity by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            entity_id: The entity UUID to retrieve

        Returns:
            Dictionary containing entity data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = cls.data_service_class(session)
                entity = await data_service.get_by_id(entity_id)

                if not entity:
                    raise cls.not_found_exception(
                        f"{cls.entity_name.capitalize()} {entity_id} not found"
                    )

                return cls.serialize_entity(entity)

        except HTTPException:
            raise
        except cls.not_found_exception as e:
            logger = cls._get_logger()
            logger.warning(
                f"{cls.entity_name.capitalize()} not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to retrieve {cls.entity_name}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed retrieve {cls.entity_name}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve {cls.entity_name}: {str(e)}",
            )

    @classmethod
    async def create(
        cls,
        user_id: UUID,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new entity.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            **kwargs: Entity-specific creation parameters

        Returns:
            Dictionary containing the created entity data

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
                data_service = cls.data_service_class(session)
                entity = await data_service.create(**kwargs)
                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"Created {cls.entity_name}: {getattr(entity, 'name', entity.id)}",
                    entity_id=str(entity.id),
                    user_id=str(user_id),
                )

                return cls.serialize_entity(entity)

        except HTTPException:
            raise
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to create {cls.entity_name}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                f"Traceback for failed create {cls.entity_name}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {cls.entity_name}: {str(e)}",
            )

    @classmethod
    async def update(
        cls,
        user_id: UUID,
        entity_id: UUID,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update an existing entity.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            entity_id: The entity UUID to update
            **kwargs: Fields to update

        Returns:
            Dictionary containing the updated entity data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = cls.data_service_class(session)
                entity = await data_service.update(entity_id, **kwargs)

                if not entity:
                    raise cls.not_found_exception(
                        f"{cls.entity_name.capitalize()} {entity_id} not found"
                    )

                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"Updated {cls.entity_name}: {getattr(entity, 'name', entity.id)}",
                    entity_id=str(entity.id),
                    user_id=str(user_id),
                )

                return cls.serialize_entity(entity)

        except HTTPException:
            raise
        except cls.not_found_exception as e:
            logger = cls._get_logger()
            logger.warning(
                f"{cls.entity_name.capitalize()} not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to update {cls.entity_name}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed update {cls.entity_name}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {cls.entity_name}: {str(e)}",
            )

    @classmethod
    async def delete(cls, user_id: UUID, entity_id: UUID) -> Dict[str, str]:
        """
        Soft delete an entity (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            entity_id: The entity UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            user_org_id = await RbacService.get_user_organization_id(user_id)
            await RbacService.verify_user_has_role(
                user_id, ROLE_CFIA_ADMIN, user_org_id
            )

            async with sessionmanager.get_session() as session:
                data_service = cls.data_service_class(session)
                entity = await data_service.soft_delete(entity_id)

                if not entity:
                    raise cls.not_found_exception(
                        f"{cls.entity_name.capitalize()} {entity_id} not found"
                    )

                await session.commit()

                logger = cls._get_logger()
                logger.info(
                    f"Deleted {cls.entity_name}: {entity_id}",
                    entity_id=str(entity_id),
                    user_id=str(user_id),
                )

                return {
                    "message": f"{cls.entity_name.capitalize()} {entity_id} deleted successfully"
                }

        except HTTPException:
            raise
        except cls.not_found_exception as e:
            logger = cls._get_logger()
            logger.warning(
                f"{cls.entity_name.capitalize()} not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = cls._get_logger()
            logger.error(
                f"Failed to delete {cls.entity_name}: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                entity_id=str(entity_id),
            )
            logger.debug(
                f"Traceback for failed delete {cls.entity_name}",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {cls.entity_name}: {str(e)}",
            )
```

---

## Usage Examples

### Simple Entity (Before vs After)

#### Before (200 lines)

```python
class DeviceBrandService:
    _logger = None

    @classmethod
    def _get_logger(cls):
        # 5 lines

    @staticmethod
    async def get_all(user_id: UUID):
        # 70 lines of boilerplate

    @staticmethod
    async def get_by_id(user_id: UUID, brand_id: UUID):
        # 70 lines of boilerplate

    # ... 3 more methods, 200+ total lines
```

#### After (20 lines)

```python
class DeviceBrandService(BaseCRUDService[DeviceBrand]):
    entity_name = "device_brand"
    entity_name_plural = "device_brands"
    data_service_class = DeviceBrandDataService
    not_found_exception = DeviceBrandNotFoundError

    @classmethod
    def serialize_entity(cls, brand: DeviceBrand) -> Dict[str, Any]:
        return {
            **super().serialize_entity(brand),
            "name": brand.name,
            "description": brand.description,
        }
```

### Complex Entity with Custom Logic

```python
class ModelService(BaseCRUDService[Model]):
    entity_name = "model"
    data_service_class = ModelDataService
    not_found_exception = ModelNotFoundError

    @classmethod
    def serialize_entity(cls, model: Model) -> Dict[str, Any]:
        """Custom serialization for Model entity."""
        return {
            **super().serialize_entity(model),
            "task_id": model.task_id,
            "task_name": model.model_task.name if model.model_task else None,
            "name": model.name,
            "endpoint_name": model.endpoint_name,
            "api_url": model.api_url,
            "created_by": model.created_by,
            "date_model_training": model.date_model_training.isoformat(),
            "content_type": model.content_type,
            "deployment_platform": model.deployment_platform,
            "version": model.version,
            "description": model.description,
            "job_name": model.job_name,
            "dataset": model.dataset,
            "artifacts_url": model.artifacts_url,
            "sha256": model.sha256,
        }

    @classmethod
    async def get_by_task_id(cls, user_id: UUID, task_id: int):
        """Custom method specific to Model service."""
        # Can still add custom methods alongside inherited CRUD
        ...
```

### Entity with Custom Validation

```python
class PipelineService(BaseCRUDService[Pipeline]):
    entity_name = "pipeline"
    data_service_class = PipelineDataService
    not_found_exception = PipelineNotFoundError

    @classmethod
    async def create(cls, user_id: UUID, **kwargs):
        """Override create to add validation."""
        # Custom validation
        if not kwargs.get('data'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline data is required",
            )

        # Call parent implementation
        return await super().create(user_id, **kwargs)

    # Keep existing custom methods untouched
    @staticmethod
    async def get_pipelines():
        """Legacy method - preserved for backward compatibility."""
        # Existing implementation stays
        ...
```

---

## Code Reduction Comparison

### Current (Duplicated)

```text
ModelService:            600 lines
PipelineService (new):   400 lines
DeviceBrandService:      200 lines
DeviceModelService:      200 lines
DeviceLensService:       200 lines
----------------------------------------
TOTAL:                  1600 lines
```

### With Generic Base

```text
BaseCRUDService:         400 lines (ONE implementation)

ModelService:             40 lines (config + serialization)
PipelineService:          60 lines (config + custom methods)
DeviceBrandService:       20 lines (config only)
DeviceModelService:       30 lines (config + relationship)
DeviceLensService:        20 lines (config only)
----------------------------------------
TOTAL:                   570 lines (64% reduction!)
```

---

## Migration Strategy

### Phase 1: Create Base Class (Week 1)

1. Create `app/service/base_crud.py`
2. Implement `BaseCRUDService` with all 5 methods
3. Add comprehensive tests for base class
4. Document usage patterns

### Phase 2: Migrate Simplest Service (Week 2)

1. Migrate DeviceLensService (simplest, 20 lines)
2. Update tests to ensure behavior unchanged
3. Run full test suite
4. Document any issues

### Phase 3: Migrate Remaining Services (Week 3-4)

1. Migrate DeviceBrandService
2. Migrate DeviceModelService
3. Migrate ModelService (most complex)
4. Migrate PipelineService (keep old methods too)

### Phase 4: Cleanup (Week 5)

1. Remove old code
2. Update documentation
3. Update SERVICE_CRUD_PATTERN_SPEC.md to use base class

---

## Benefits

### Development

- ✅ **New service in 20 lines** instead of 600
- ✅ **Guaranteed consistency** - no copy-paste errors
- ✅ **Type-safe** with generics
- ✅ **Easy to extend** - override methods as needed

### Maintenance

- ✅ **Single source of truth** - bug fixes in one place
- ✅ **Feature additions easy** - add audit logging once, applies everywhere
- ✅ **Testing simplified** - test base class thoroughly once
- ✅ **Less code to review** - PRs are 20 lines not 600

### Code Quality

- ✅ **DRY principle** - no duplication
- ✅ **Open/Closed principle** - open for extension, closed for modification
- ✅ **Single Responsibility** - base handles boilerplate, subclass handles business logic
- ✅ **Liskov Substitution** - any CRUD service is substitutable

---

## Tradeoffs

### Advantages

- **90% less code** to write and maintain
- **Guaranteed consistency** across all services
- **Easier to add cross-cutting concerns** (audit, caching, etc.)
- **Faster development** of new services

### Disadvantages

- **More abstract** - requires understanding generics
- **Less explicit** - behavior defined in base class
- **Learning curve** - new developers need to learn the pattern
- **Customization may require overrides** - but still better than copy-paste

---

## Testing Strategy

### Base Class Tests

Test the generic implementation thoroughly:

- Test with mock entity (all 5 CRUD operations)
- Test RBAC enforcement
- Test error handling and logging
- Test serialization hooks

### Service-Specific Tests

Focus only on customizations:

- Test custom serialization
- Test custom validation
- Test additional methods
- Integration tests remain unchanged

---

## Recommendation

**Implement the generic base class.**

### Why

1. Current approach has 64% code duplication
2. Maintenance burden scales linearly with services
3. Inconsistency risk increases over time
4. Pattern is well-understood (Django ORM, Rails, etc.)
5. Easy migration path (one service at a time)

### When

- **Short term**: Current code works, no urgent need
- **Next sprint**: Create BaseCRUDService
- **Within 2 months**: Migrate all services

### Alternative

If base class is too complex, at minimum create **utility functions** for the repeated blocks:

```python
# app/service/crud_utils.py

async def handle_get_all(entity_name, data_service_class, serializer, user_id):
    """Reusable get_all implementation."""
    # Same logic, but as a function

async def handle_get_by_id(entity_name, data_service_class, serializer, user_id, entity_id):
    """Reusable get_by_id implementation."""
    # Same logic
```

Then services call these utilities, reducing duplication by ~50%.

---

## Conclusion

The current spec document is useful for **documentation** but encourages **anti-pattern** (copy-paste).

**Recommended action:**

1. Keep the spec as a reference for the pattern
2. Add a section recommending the generic base class approach
3. Implement BaseCRUDService as the **preferred** way forward
4. Gradually migrate existing services

**Bottom line:** Good engineers write DRY code. The base class approach is industry standard and significantly better than copy-paste.
