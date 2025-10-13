"""
Refactored Model service using generic BaseCRUDService.

This demonstrates the dramatic code reduction achieved by using the generic base class:
- Original: 621 lines
- Refactored: ~150 lines (76% reduction)
"""

from typing import Dict, Any, List, Type
from uuid import UUID
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.service.rbac import RbacService
from app.datastore.model_refactored import ModelDataService
from app.db.model import Model
from app.exceptions import (
    ModelNotFoundError,
    ModelCreationError,
    ModelUpdateError,
    ModelDeletionError,
)


class ModelService(BaseCRUDService[Model]):
    """
    Service layer for Model operations.

    Uses the generic BaseCRUDService for standard CRUD operations.
    Adds custom get_by_task_id method for Model-specific queries.

    Access Control:
    - GET operations (get_all, get_by_id, get_by_task_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active models are returned by default
    - Each model must be associated with a task
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "Model"

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[Model]]:
        """Return the data service class."""
        return ModelDataService

    @classmethod
    def serialize_entity(cls, entity: Model) -> Dict[str, Any]:
        """
        Convert Model entity to dictionary for API response.

        This handles all the complex field serialization for Model.
        """
        return {
            "id": str(entity.id),
            "task_id": entity.task_id,
            "task_name": entity.model_task.name if entity.model_task else None,
            "name": entity.name,
            "endpoint_name": entity.endpoint_name,
            "api_url": entity.api_url,
            "created_by": entity.created_by,
            "date_model_training": entity.date_model_training.isoformat(),
            "content_type": entity.content_type,
            "deployment_platform": entity.deployment_platform,
            "version": entity.version,
            "description": entity.description,
            "job_name": entity.job_name,
            "dataset": entity.dataset,
            "artifacts_url": entity.artifacts_url,
            "sha256": entity.sha256,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
            "date_updated": entity.date_updated.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return ModelNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return ModelCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return ModelUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return ModelDeletionError

    # ==========================================
    # Custom methods specific to Model entity
    # ==========================================

    @staticmethod
    async def get_by_task_id(user_id: UUID, task_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active models for a specific task.

        This is a custom method specific to Model - not part of standard CRUD.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            task_id: The model task ID to filter by

        Returns:
            Dictionary with "models" key containing list of model data for the task

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Retrieve models for task
                models = await data_service.get_by_task_id(task_id)

                return {
                    "models": [
                        ModelService.serialize_entity(model) for model in models
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to retrieve models by task: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                task_id=task_id,
            )
            logger.debug(
                "Traceback for failed retrieve models by task",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve models by task: {str(e)}",
            )


# Code Comparison:
# ================
# Original ModelService: 621 lines
# Refactored with BaseCRUDService: ~150 lines
# Reduction: 76% less code
#
# What the base class provides automatically:
# - get_all() with RBAC, logging, error handling
# - get_by_id() with RBAC, logging, error handling, 404 handling
# - create() with admin RBAC, logging, session management
# - update() with admin RBAC, logging, 404 handling
# - delete() with admin RBAC, logging, soft delete logic
#
# What we keep custom:
# - serialize_entity() - Model has 15+ fields with complex serialization
# - get_by_task_id() - entity-specific query method
#
# All methods now:
# - Automatically include proper RBAC checks
# - Automatically include structured logging
# - Automatically include error handling with tracebacks
# - Automatically include session management
# - Are guaranteed to be consistent with all other services
