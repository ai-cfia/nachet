"""
Pipeline service module.
"""

from typing import List, Dict, Any, Optional, Type
from fastapi import HTTPException
from app.db.utils import sessionmanager
from app.datastore import PipelineDataService
from app.service.base_crud import BaseCRUDService
from app.service.logs import LogService
from app.db.model import Pipeline, PipelineDefault, PipelineModel
from app.exceptions import (
    PipelineNotFoundError,
    PipelineCreationError,
    PipelineUpdateError,
    PipelineDeletionError,
    PipelineDefaultNotFoundError,
    PipelineDefaultCreationError,
    PipelineDefaultUpdateError,
    PipelineDefaultDeletionError,
    PipelineModelNotFoundError,
    PipelineModelCreationError,
    PipelineModelUpdateError,
    PipelineModelDeletionError,
)


class PipelineService(BaseCRUDService[Pipeline]):
    """
    Service class to handle pipeline-related operations.
    
    Extends BaseCRUDService to provide standard CRUD operations with RBAC.
    Also includes legacy methods for specialized pipeline queries.
    
    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only
    """

    # Singleton logger for the service
    _logger = None

    @classmethod
    def _get_logger(cls):
        """Get or create singleton logger for PipelineService."""
        if cls._logger is None:
            cls._logger = LogService.get_logger()
        return cls._logger

    # ========================================
    # BaseCRUDService Required Methods
    # ========================================

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "Pipeline"

    @classmethod
    def get_data_service_class(cls) -> Type[PipelineDataService]:
        """Return the data service class for Pipeline."""
        return PipelineDataService

    @classmethod
    def serialize_entity(cls, entity: Pipeline) -> Dict[str, Any]:
        """
        Convert Pipeline entity to dictionary for API response.
        
        Args:
            entity: The Pipeline object to serialize
            
        Returns:
            Dictionary representation of the pipeline
        """
        return {
            "id": str(entity.id),
            "name": entity.name,
            "created_by": entity.created_by,
            "creation_date": entity.creation_date.isoformat()
            if entity.creation_date
            else None,
            "description": entity.description,
            "job_name": entity.job_name,
            "version": entity.version,
            "dataset": entity.dataset,
            "identifiable": entity.identifiable,
            "metrics": entity.metrics,
            "default": entity.default,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return Pipeline-specific NotFoundError exception class."""
        return PipelineNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return Pipeline-specific CreationError exception class."""
        return PipelineCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return Pipeline-specific UpdateError exception class."""
        return PipelineUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return Pipeline-specific DeletionError exception class."""
        return PipelineDeletionError

    # ========================================
    # Legacy Pipeline-Specific Methods
    # These provide custom functionality not covered by standard CRUD
    # ========================================

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


class PipelineDefaultService(BaseCRUDService[PipelineDefault]):
    """
    Service class to handle pipeline_default-related operations.
    
    Extends BaseCRUDService to provide standard CRUD operations with RBAC.
    
    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "PipelineDefault"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class for PipelineDefault."""
        from app.datastore.pipeline import PipelineDefaultDataService

        return PipelineDefaultDataService

    @classmethod
    def serialize_entity(cls, entity: PipelineDefault) -> Dict[str, Any]:
        """
        Convert PipelineDefault entity to dictionary for API response.
        
        Args:
            entity: The PipelineDefault object to serialize
            
        Returns:
            Dictionary representation of the pipeline default
        """
        return {
            "id": entity.id,
            "pipeline_id": str(entity.pipeline_id),
            "pipeline_name": entity.pipeline.name if entity.pipeline else None,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
            "date_updated": entity.date_updated.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return PipelineDefault-specific NotFoundError exception class."""
        return PipelineDefaultNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return PipelineDefault-specific CreationError exception class."""
        return PipelineDefaultCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return PipelineDefault-specific UpdateError exception class."""
        return PipelineDefaultUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return PipelineDefault-specific DeletionError exception class."""
        return PipelineDefaultDeletionError


class PipelineModelService(BaseCRUDService[PipelineModel]):
    """
    Service class to handle pipeline_model-related operations.
    
    Extends BaseCRUDService to provide standard CRUD operations with RBAC.
    
    Access Control:
    - GET operations (get_all, get_by_id): Any authenticated user
    - CUD operations (create, update, delete): CFIA admin only
    """

    @classmethod
    def get_entity_name(cls) -> str:
        """Return the entity name for error messages."""
        return "PipelineModel"

    @classmethod
    def get_data_service_class(cls) -> Type:
        """Return the data service class for PipelineModel."""
        from app.datastore.pipeline import PipelineModelDataService

        return PipelineModelDataService

    @classmethod
    def serialize_entity(cls, entity: PipelineModel) -> Dict[str, Any]:
        """
        Convert PipelineModel entity to dictionary for API response.
        
        Args:
            entity: The PipelineModel object to serialize
            
        Returns:
            Dictionary representation of the pipeline model
        """
        return {
            "id": str(entity.id),
            "pipeline_id": str(entity.pipeline_id),
            "pipeline_name": entity.pipeline.name if entity.pipeline else None,
            "model_id": str(entity.model_id),
            "model_name": entity.model.name if entity.model else None,
            "step": entity.step,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        """Return PipelineModel-specific NotFoundError exception class."""
        return PipelineModelNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        """Return PipelineModel-specific CreationError exception class."""
        return PipelineModelCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        """Return PipelineModel-specific UpdateError exception class."""
        return PipelineModelUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        """Return PipelineModel-specific DeletionError exception class."""
        return PipelineModelDeletionError
