from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import traceback
from fastapi import HTTPException, status

from app.db.utils import sessionmanager
from app.datastore import ModelDataService
from app.service.logs import LogService
from app.service.rbac import RbacService
from app.exceptions import ModelNotFoundError


class ModelService:
    """
    Service layer for Model operations.

    Access Control:
    - GET operations (get_all, get_by_id, get_by_task_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only

    System Invariants:
    - Deletion is soft delete (sets active=False) to maintain referential integrity
    - Only active models are returned by default
    - Each model must be associated with a task
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for ModelService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active models.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "models" key containing list of model data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Retrieve all models
                models = await data_service.get_all()

                return {
                    "models": [
                        {
                            "id": str(model.id),
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
                            "active": model.active,
                            "date_created": model.date_created.isoformat(),
                            "date_updated": model.date_updated.isoformat(),
                        }
                        for model in models
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to retrieve models: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve models",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve models: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, model_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a model by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            model_id: The model UUID to retrieve

        Returns:
            Dictionary containing model data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Retrieve model
                model = await data_service.get_by_id(model_id)
                if not model:
                    raise ModelNotFoundError(f"Model {model_id} not found")

                return {
                    "id": str(model.id),
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
                    "active": model.active,
                    "date_created": model.date_created.isoformat(),
                    "date_updated": model.date_updated.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except ModelNotFoundError as e:
            logger = ModelService._get_logger()
            logger.warning(
                f"Model not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to retrieve model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed retrieve model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve model: {str(e)}",
            )

    @staticmethod
    async def get_by_task_id(user_id: UUID, task_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active models for a specific task.

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
                        {
                            "id": str(model.id),
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
                            "active": model.active,
                            "date_created": model.date_created.isoformat(),
                            "date_updated": model.date_updated.isoformat(),
                        }
                        for model in models
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

    @staticmethod
    async def create(
        user_id: UUID,
        task_id: int,
        name: str,
        endpoint_name: str,
        api_url: str,
        api_key: str,
        created_by: str,
        date_model_training: datetime,
        content_type: str = "application/json",
        deployment_platform: str = "on-prem",
        version: Optional[str] = None,
        description: Optional[str] = None,
        job_name: Optional[str] = None,
        dataset: Optional[str] = None,
        artifacts_url: Optional[str] = None,
        sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new model.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            task_id: Model task ID
            name: Model name
            endpoint_name: Endpoint name for the model
            api_url: API URL for the model
            api_key: API key for authentication
            created_by: User who created the model
            date_model_training: Date when the model was trained
            content_type: Content type (default: "application/json")
            deployment_platform: Deployment platform (default: "on-prem")
            version: Model version (optional)
            description: Model description (optional)
            job_name: Training job name (optional)
            dataset: Training dataset ID (optional)
            artifacts_url: URL to model artifacts (optional)
            sha256: SHA256 hash of model (optional)

        Returns:
            Dictionary containing the created model data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Create the model
                model = await data_service.create(
                    task_id=task_id,
                    name=name,
                    endpoint_name=endpoint_name,
                    api_url=api_url,
                    api_key=api_key,
                    created_by=created_by,
                    date_model_training=date_model_training,
                    content_type=content_type,
                    deployment_platform=deployment_platform,
                    version=version,
                    description=description,
                    job_name=job_name,
                    dataset=dataset,
                    artifacts_url=artifacts_url,
                    sha256=sha256,
                )
                await session.commit()

                logger = ModelService._get_logger()
                logger.info(
                    f"Created model: {model.name}",
                    model_id=str(model.id),
                    task_id=task_id,
                    user_id=str(user_id),
                )

                return {
                    "id": str(model.id),
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
                    "active": model.active,
                    "date_created": model.date_created.isoformat(),
                    "date_updated": model.date_updated.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to create model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_name=name,
                task_id=task_id,
            )
            logger.debug(
                "Traceback for failed create model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create model: {str(e)}",
            )

    @staticmethod
    async def update(
        user_id: UUID,
        model_id: UUID,
        task_id: Optional[int] = None,
        name: Optional[str] = None,
        endpoint_name: Optional[str] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        created_by: Optional[str] = None,
        date_model_training: Optional[datetime] = None,
        content_type: Optional[str] = None,
        deployment_platform: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        job_name: Optional[str] = None,
        dataset: Optional[str] = None,
        artifacts_url: Optional[str] = None,
        sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing model.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            model_id: The model UUID to update
            task_id: New task ID (if provided)
            name: New name (if provided)
            endpoint_name: New endpoint name (if provided)
            api_url: New API URL (if provided)
            api_key: New API key (if provided)
            created_by: New creator (if provided)
            date_model_training: New training date (if provided)
            content_type: New content type (if provided)
            deployment_platform: New deployment platform (if provided)
            version: New version (if provided)
            description: New description (if provided)
            job_name: New job name (if provided)
            dataset: New dataset (if provided)
            artifacts_url: New artifacts URL (if provided)
            sha256: New SHA256 hash (if provided)

        Returns:
            Dictionary containing the updated model data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Update the model
                model = await data_service.update(
                    model_id=model_id,
                    task_id=task_id,
                    name=name,
                    endpoint_name=endpoint_name,
                    api_url=api_url,
                    api_key=api_key,
                    created_by=created_by,
                    date_model_training=date_model_training,
                    content_type=content_type,
                    deployment_platform=deployment_platform,
                    version=version,
                    description=description,
                    job_name=job_name,
                    dataset=dataset,
                    artifacts_url=artifacts_url,
                    sha256=sha256,
                )
                if not model:
                    raise ModelNotFoundError(f"Model {model_id} not found")

                await session.commit()

                logger = ModelService._get_logger()
                logger.info(
                    f"Updated model: {model.name}",
                    model_id=str(model.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(model.id),
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
                    "active": model.active,
                    "date_created": model.date_created.isoformat(),
                    "date_updated": model.date_updated.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except ModelNotFoundError as e:
            logger = ModelService._get_logger()
            logger.warning(
                f"Model not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to update model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed update model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update model: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, model_id: UUID) -> Dict[str, str]:
        """
        Soft delete a model (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            model_id: The model UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = ModelDataService(session)

                # Soft delete the model
                model = await data_service.soft_delete(model_id)
                if not model:
                    raise ModelNotFoundError(f"Model {model_id} not found")

                await session.commit()

                logger = ModelService._get_logger()
                logger.info(
                    f"Deleted model: {model_id}",
                    model_id=str(model_id),
                    user_id=str(user_id),
                )

                return {"message": f"Model {model_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except ModelNotFoundError as e:
            logger = ModelService._get_logger()
            logger.warning(
                f"Model not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                model_id=str(model_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = ModelService._get_logger()
            logger.error(
                f"Failed to delete model: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                model_id=str(model_id),
            )
            logger.debug(
                "Traceback for failed delete model",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete model: {str(e)}",
            )
