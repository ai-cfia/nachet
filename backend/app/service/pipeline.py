"""
Pipeline service module.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
import traceback
from fastapi import HTTPException, status
from app.db.utils import sessionmanager
from app.datastore import PipelineDataService
from app.service.logs import LogService
from app.service.rbac import RbacService
from app.exceptions import PipelineNotFoundError


class PipelineService:
    """
    Service class to handle pipeline-related operations.
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for PipelineService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    @staticmethod
    async def get_pipelines() -> List[Dict[str, Any]]:
        """
        Retrieves the pipelines from the database.

        Returns:
            List of dictionaries representing the pipelines with their models.

        Raises:
            HTTPException: If database operation fails.
        """
        try:
            async with sessionmanager.get_session() as session:
                repository = PipelineDataService(session)
                pipelines = await repository.get_all_pipelines()

                result = []
                for pipeline in pipelines:
                    pipeline_dict = {
                        "pipeline_id": str(pipeline.id),
                        "pipeline_name": pipeline.name,
                        "created_by": pipeline.created_by,
                        "creation_date": pipeline.creation_date.isoformat()
                        if pipeline.creation_date
                        else None,
                        "description": pipeline.description,
                        "job_name": pipeline.job_name,
                        "version": pipeline.version,
                        "dataset": pipeline.dataset,
                        "identifiable": pipeline.identifiable or [],
                        "metrics": pipeline.metrics or [],
                        "models": [],
                    }

                    for pipeline_model in pipeline.pipeline_models:
                        if pipeline_model.active and pipeline_model.model.active:
                            model = pipeline_model.model
                            model_dict = {
                                "model_id": str(model.id),
                                "model_name": model.name,
                                "version": model.version,
                                "endpoint": model.api_url,
                                "api_key": model.api_key,
                                "content_type": model.content_type,
                                "deployment_platform": model.deployment_platform,
                                "endpoint_name": model.endpoint_name,
                            }
                            pipeline_dict["models"].append(model_dict)

                    result.append(pipeline_dict)

                return result

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve pipelines: {str(e)}"
            )

    @staticmethod
    async def get_model_endpoints_metadata() -> List[Dict[str, Any]]:
        """
        Retrieves model endpoints metadata from the database in the format expected by the frontend.

        Returns:
            List of ModelMetadata objects matching the frontend interface.

        Raises:
            HTTPException: If database operation fails.
        """
        try:
            async with sessionmanager.get_session() as session:
                repository = PipelineDataService(session)
                pipelines = await repository.get_all_pipelines()

                metadata_list = []

                for pipeline in pipelines:
                    # Get model names for this pipeline
                    pipeline_models = []
                    for pipeline_model in pipeline.pipeline_models:
                        pipeline_models.append(pipeline_model.model.name)
                        # if a model is inactive, the entire pipeline should be made inactive
                        # if a model is being replaced a new pipeline should be created

                    # Create a ModelMetadata entry for this pipeline
                    if pipeline_models:  # Only include pipelines that have models
                        metadata = {
                            "created_by": pipeline.created_by or "unknown",
                            "creation_date": pipeline.creation_date.isoformat()
                            if pipeline.creation_date
                            else pipeline.date_created.isoformat(),
                            "dataset": pipeline.dataset or "",
                            "description": pipeline.description or "",
                            "identifiable": pipeline.identifiable or [],
                            "job_name": pipeline.job_name or "",
                            "metrics": pipeline.metrics or [],
                            "model_name": pipeline.name,
                            "models": pipeline_models,
                            "pipeline_name": pipeline.name,
                            "pipeline_id": str(pipeline.id),
                            "version": pipeline.version or "",
                        }

                        # Use the new default column
                        metadata["default"] = pipeline.default or False

                        metadata_list.append(metadata)

                return metadata_list

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve model endpoints metadata: {str(e)}",
            )

    @staticmethod
    async def get_pipeline_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific pipeline by name.

        Args:
            name: The pipeline name to search for

        Returns:
            Dictionary representing the pipeline or None if not found.

        Raises:
            HTTPException: If database operation fails.
        """
        try:
            async with sessionmanager.get_session() as session:
                repository = PipelineDataService(session)
                pipeline = await repository.get_pipeline_by_name(name)

                if not pipeline:
                    return None

                pipeline_dict = {
                    "pipeline_id": str(pipeline.id),
                    "pipeline_name": pipeline.name,
                    "created_by": pipeline.created_by,
                    "creation_date": pipeline.creation_date.isoformat()
                    if pipeline.creation_date
                    else None,
                    "description": pipeline.description,
                    "job_name": pipeline.job_name,
                    "version": pipeline.version,
                    "dataset": pipeline.dataset,
                    "identifiable": pipeline.identifiable or [],
                    "metrics": pipeline.metrics or [],
                    "models": [],
                }

                for pipeline_model in pipeline.pipeline_models:
                    if pipeline_model.active and pipeline_model.model.active:
                        model = pipeline_model.model
                        model_dict = {
                            "model_id": str(model.id),
                            "model_name": model.name,
                            "version": model.version,
                            "endpoint": model.api_url,
                            "api_key": model.api_key,
                            "content_type": model.content_type,
                            "deployment_platform": model.deployment_platform,
                            "endpoint_name": model.endpoint_name,
                        }
                        pipeline_dict["models"].append(model_dict)

                return pipeline_dict

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve pipeline '{name}': {str(e)}",
            )

    @staticmethod
    async def get_all(user_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all active pipelines.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID

        Returns:
            Dictionary with "pipelines" key containing list of pipeline data

        Raises:
            HTTPException: 500 on database error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = PipelineDataService(session)

                # Retrieve all pipelines
                pipelines = await data_service.get_all_pipelines()

                return {
                    "pipelines": [
                        {
                            "id": str(pipeline.id),
                            "name": pipeline.name,
                            "created_by": pipeline.created_by,
                            "creation_date": pipeline.creation_date.isoformat()
                            if pipeline.creation_date
                            else None,
                            "description": pipeline.description,
                            "job_name": pipeline.job_name,
                            "version": pipeline.version,
                            "dataset": pipeline.dataset,
                            "identifiable": pipeline.identifiable,
                            "metrics": pipeline.metrics,
                            "default": pipeline.default,
                            "active": pipeline.active,
                            "date_created": pipeline.date_created.isoformat(),
                        }
                        for pipeline in pipelines
                    ]
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = PipelineService._get_logger()
            logger.error(
                f"Failed to retrieve pipelines: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
            )
            logger.debug(
                "Traceback for failed retrieve pipelines",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve pipelines: {str(e)}",
            )

    @staticmethod
    async def get_by_id(user_id: UUID, pipeline_id: UUID) -> Dict[str, Any]:
        """
        Retrieve a pipeline by ID.

        Access: Any authenticated user

        Args:
            user_id: The requesting user's UUID
            pipeline_id: The pipeline UUID to retrieve

        Returns:
            Dictionary containing pipeline data

        Raises:
            HTTPException: 404 if not found, 500 on error
        """
        try:
            # Just verify user exists and has valid organization
            await RbacService.get_user_organization_id(user_id)

            async with sessionmanager.get_session() as session:
                data_service = PipelineDataService(session)

                # Retrieve pipeline
                pipeline = await data_service.get_by_id(str(pipeline_id))
                if not pipeline:
                    raise PipelineNotFoundError(f"Pipeline {pipeline_id} not found")

                return {
                    "id": str(pipeline.id),
                    "name": pipeline.name,
                    "created_by": pipeline.created_by,
                    "creation_date": pipeline.creation_date.isoformat()
                    if pipeline.creation_date
                    else None,
                    "description": pipeline.description,
                    "job_name": pipeline.job_name,
                    "version": pipeline.version,
                    "dataset": pipeline.dataset,
                    "identifiable": pipeline.identifiable,
                    "metrics": pipeline.metrics,
                    "default": pipeline.default,
                    "active": pipeline.active,
                    "date_created": pipeline.date_created.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except PipelineNotFoundError as e:
            logger = PipelineService._get_logger()
            logger.warning(
                f"Pipeline not found: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = PipelineService._get_logger()
            logger.error(
                f"Failed to retrieve pipeline: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            logger.debug(
                "Traceback for failed retrieve pipeline",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve pipeline: {str(e)}",
            )

    @staticmethod
    async def create(
        user_id: UUID,
        name: str,
        data: Dict[str, Any],
        created_by: Optional[str] = None,
        creation_date: Optional[Any] = None,
        description: Optional[str] = None,
        job_name: Optional[str] = None,
        version: Optional[str] = None,
        dataset: Optional[str] = None,
        identifiable: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        default: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Create a new pipeline.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            name: Pipeline name
            data: Pipeline JSON data
            created_by: User who created the pipeline (optional)
            creation_date: Creation date (optional)
            description: Pipeline description (optional)
            job_name: Job name (optional)
            version: Pipeline version (optional)
            dataset: Dataset information (optional)
            identifiable: Identifiable seeds (optional)
            metrics: Pipeline metrics (optional)
            default: Whether this is the default pipeline (optional)

        Returns:
            Dictionary containing the created pipeline data

        Raises:
            HTTPException: 403 if unauthorized, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = PipelineDataService(session)

                # Create the pipeline
                pipeline = await data_service.create(
                    name=name,
                    data=data,
                    created_by=created_by,
                    creation_date=creation_date,
                    description=description,
                    job_name=job_name,
                    version=version,
                    dataset=dataset,
                    identifiable=identifiable,
                    metrics=metrics,
                    default=default,
                )
                await session.commit()

                logger = PipelineService._get_logger()
                logger.info(
                    f"Created pipeline: {pipeline.name}",
                    pipeline_id=str(pipeline.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(pipeline.id),
                    "name": pipeline.name,
                    "created_by": pipeline.created_by,
                    "creation_date": pipeline.creation_date.isoformat()
                    if pipeline.creation_date
                    else None,
                    "description": pipeline.description,
                    "job_name": pipeline.job_name,
                    "version": pipeline.version,
                    "dataset": pipeline.dataset,
                    "identifiable": pipeline.identifiable,
                    "metrics": pipeline.metrics,
                    "default": pipeline.default,
                    "active": pipeline.active,
                    "date_created": pipeline.date_created.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except Exception as e:
            logger = PipelineService._get_logger()
            logger.error(
                f"Failed to create pipeline: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                pipeline_name=name,
            )
            logger.debug(
                "Traceback for failed create pipeline",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create pipeline: {str(e)}",
            )

    @staticmethod
    async def update(
        user_id: UUID,
        pipeline_id: UUID,
        name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        creation_date: Optional[Any] = None,
        description: Optional[str] = None,
        job_name: Optional[str] = None,
        version: Optional[str] = None,
        dataset: Optional[str] = None,
        identifiable: Optional[Dict] = None,
        metrics: Optional[Dict] = None,
        default: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing pipeline.

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            pipeline_id: The pipeline UUID to update
            name: New name (if provided)
            data: New data (if provided)
            created_by: New creator (if provided)
            creation_date: New creation date (if provided)
            description: New description (if provided)
            job_name: New job name (if provided)
            version: New version (if provided)
            dataset: New dataset (if provided)
            identifiable: New identifiable seeds (if provided)
            metrics: New metrics (if provided)
            default: New default status (if provided)

        Returns:
            Dictionary containing the updated pipeline data

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = PipelineDataService(session)

                # Update the pipeline
                pipeline = await data_service.update(
                    pipeline_id=str(pipeline_id),
                    name=name,
                    data=data,
                    created_by=created_by,
                    creation_date=creation_date,
                    description=description,
                    job_name=job_name,
                    version=version,
                    dataset=dataset,
                    identifiable=identifiable,
                    metrics=metrics,
                    default=default,
                )
                if not pipeline:
                    raise PipelineNotFoundError(f"Pipeline {pipeline_id} not found")

                await session.commit()

                logger = PipelineService._get_logger()
                logger.info(
                    f"Updated pipeline: {pipeline.name}",
                    pipeline_id=str(pipeline.id),
                    user_id=str(user_id),
                )

                return {
                    "id": str(pipeline.id),
                    "name": pipeline.name,
                    "created_by": pipeline.created_by,
                    "creation_date": pipeline.creation_date.isoformat()
                    if pipeline.creation_date
                    else None,
                    "description": pipeline.description,
                    "job_name": pipeline.job_name,
                    "version": pipeline.version,
                    "dataset": pipeline.dataset,
                    "identifiable": pipeline.identifiable,
                    "metrics": pipeline.metrics,
                    "default": pipeline.default,
                    "active": pipeline.active,
                    "date_created": pipeline.date_created.isoformat(),
                }

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except PipelineNotFoundError as e:
            logger = PipelineService._get_logger()
            logger.warning(
                f"Pipeline not found for update: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = PipelineService._get_logger()
            logger.error(
                f"Failed to update pipeline: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            logger.debug(
                "Traceback for failed update pipeline",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update pipeline: {str(e)}",
            )

    @staticmethod
    async def delete(user_id: UUID, pipeline_id: UUID) -> Dict[str, str]:
        """
        Soft delete a pipeline (sets active=False).

        Access: CFIA admin only

        Args:
            user_id: The requesting user's UUID (must be cfia_admin)
            pipeline_id: The pipeline UUID to delete

        Returns:
            Success message dictionary

        Raises:
            HTTPException: 403 if unauthorized, 404 if not found, 500 on error
        """
        try:
            # Verify user is CFIA admin (cross-org authority)
            await RbacService.verify_user_is_cfia_admin(user_id)

            async with sessionmanager.get_session() as session:
                data_service = PipelineDataService(session)

                # Soft delete the pipeline
                pipeline = await data_service.soft_delete(str(pipeline_id))
                if not pipeline:
                    raise PipelineNotFoundError(f"Pipeline {pipeline_id} not found")

                await session.commit()

                logger = PipelineService._get_logger()
                logger.info(
                    f"Deleted pipeline: {pipeline_id}",
                    pipeline_id=str(pipeline_id),
                    user_id=str(user_id),
                )

                return {"message": f"Pipeline {pipeline_id} deleted successfully"}

        except HTTPException:
            # Re-raise HTTPExceptions (including RBAC errors) as-is
            raise
        except PipelineNotFoundError as e:
            logger = PipelineService._get_logger()
            logger.warning(
                f"Pipeline not found for deletion: {str(e)}",
                error=str(e),
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        except Exception as e:
            logger = PipelineService._get_logger()
            logger.error(
                f"Failed to delete pipeline: {str(e)}",
                error=str(e),
                error_type=type(e).__name__,
                user_id=str(user_id),
                pipeline_id=str(pipeline_id),
            )
            logger.debug(
                "Traceback for failed delete pipeline",
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete pipeline: {str(e)}",
            )
