"""
Pipeline service module.
"""

from beartype.typing import List, Dict, Any, Optional, Type
from uuid import UUID
from fastapi import HTTPException
from app.db.utils import sessionmanager
from app.datastore import PipelineDataService
from app.service.base_crud import BaseCRUDService
from app.service.logs import LogService
from app.service.cache import CacheService
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

PIPELINE_CACHE_KEY = "pipelines"


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
                                "request_function": pipeline_model.request_function,
                                "step": pipeline_model.step,
                            }
                            pipeline_dict["models"].append(model_dict)

                    result.append(pipeline_dict)

                return result

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve pipelines: {str(e)}"
            )

    @classmethod
    async def initialize_cache(cls) -> Dict[str, Any]:
        """
        Initialize the pipeline cache with data from the database.

        Builds a cached structure for fast lookups:
        - by_id: UUID -> full pipeline config
        - by_name: name -> UUID

        Returns:
            Stats dict with initialization info
        """
        logger = cls._get_logger()
        logger.info("Initializing pipeline cache...")

        # Fetch pipelines from database
        pipelines = await cls.get_pipelines()

        # Build cache structure with domain logic
        cache_data = {
            "by_id": {},
            "by_name": {},
        }

        for pipeline in pipelines:
            try:
                pipeline_id = pipeline["pipeline_id"]
                pipeline_name = pipeline["pipeline_name"]

                # Build ordered steps from models
                steps = []
                for model in pipeline.get("models", []):
                    step = {
                        "step": model.get("step"),
                        "model_id": model.get("model_id"),
                        "model_name": model.get("model_name"),
                        "request_function": model.get("request_function"),
                        "endpoint": model.get("endpoint"),
                        "api_key": model.get("api_key"),
                        "content_type": model.get("content_type"),
                        "deployment_platform": model.get("deployment_platform"),
                        "version": model.get("version"),
                        "endpoint_name": model.get("endpoint_name"),
                    }
                    steps.append(step)

                # Sort steps by step number
                steps.sort(key=lambda x: x["step"])

                # Store pipeline config
                pipeline_config = {
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline_name,
                    "steps": steps,
                    "metadata": {
                        "created_by": pipeline.get("created_by"),
                        "creation_date": pipeline.get("creation_date"),
                        "description": pipeline.get("description"),
                        "job_name": pipeline.get("job_name"),
                        "version": pipeline.get("version"),
                        "dataset": pipeline.get("dataset"),
                        "identifiable": pipeline.get("identifiable", []),
                        "metrics": pipeline.get("metrics", []),
                    },
                }

                cache_data["by_id"][pipeline_id] = pipeline_config
                cache_data["by_name"][pipeline_name] = pipeline_id

                logger.debug(
                    f"Cached pipeline: {pipeline_name}",
                    pipeline_id=pipeline_id,
                    steps=len(steps),
                )

            except Exception as e:
                logger.error(
                    f"Failed to cache pipeline: {str(e)}",
                    pipeline=pipeline,
                    error_type=type(e).__name__,
                )

        # Store in cache
        CacheService.set(PIPELINE_CACHE_KEY, cache_data)

        stats = {
            "total_pipelines": len(cache_data["by_id"]),
            "total_steps": sum(
                len(p.get("steps", [])) for p in cache_data["by_id"].values()
            ),
            "pipeline_names": list(cache_data["by_name"].keys()),
        }

        logger.info(
            f"Pipeline cache initialized with {stats['total_pipelines']} pipelines",
            pipeline_names=stats["pipeline_names"],
        )
        return stats

    @classmethod
    async def get_pipeline_steps(
        cls, pipeline_identifier: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get ordered pipeline steps for inference execution from cache.

        Automatically initializes cache if not already initialized.

        Args:
            pipeline_identifier: Pipeline UUID or name

        Returns:
            List of step dictionaries or None if not found
        """
        cache_data = CacheService.get(PIPELINE_CACHE_KEY)
        if not cache_data:
            cls._get_logger().info(
                "Pipeline cache not initialized, initializing now...",
                pipeline_identifier=pipeline_identifier,
            )
            await cls.initialize_cache()
            cache_data = CacheService.get(PIPELINE_CACHE_KEY)

        # Type guard: cache_data should now be initialized
        if cache_data is None:
            cls._get_logger().error("Failed to initialize pipeline cache")
            return None

        # Try as UUID first
        pipeline = cache_data.get("by_id", {}).get(pipeline_identifier)

        # Try as name if not found by ID
        if not pipeline:
            pipeline_id = cache_data.get("by_name", {}).get(pipeline_identifier)
            if pipeline_id:
                pipeline = cache_data.get("by_id", {}).get(pipeline_id)

        if pipeline:
            return pipeline.get("steps", [])

        cls._get_logger().warning(
            f"Pipeline not found in cache: {pipeline_identifier}",
            available_pipelines=list(cache_data.get("by_name", {}).keys()),
        )
        return None

    @classmethod
    def get_cached_pipeline_names(cls) -> List[str]:
        """
        Get list of all cached pipeline names.

        Returns:
            List of pipeline names
        """
        cache_data = CacheService.get(PIPELINE_CACHE_KEY)
        if not cache_data:
            return []
        return list(cache_data.get("by_name", {}).keys())

    @classmethod
    async def pipeline_exists(cls, pipeline_id: str, requester_id: UUID) -> UUID:
        """
        Validate that a pipeline exists and is active, with RBAC authorization.

        Converts string pipeline_id to UUID and verifies the pipeline exists
        in the database using inherited get_by_id() method with RBAC checks.

        Args:
            pipeline_id: Pipeline UUID as string
            requester_id: UUID of requesting user (for RBAC authorization)

        Returns:
            UUID: Validated pipeline UUID

        Raises:
            ValueError: If pipeline_id is not a valid UUID format
            PipelineNotFoundError: If pipeline not found or not active
        """
        # Validate UUID format - raises ValueError if invalid
        try:
            pipeline_uuid = UUID(pipeline_id)
        except ValueError as e:
            cls._get_logger().warning(
                f"Invalid pipeline_id format: {pipeline_id}",
                requester_id=str(requester_id),
            )
            raise ValueError(f"Invalid pipeline_id format: {pipeline_id}") from e

        # Use inherited get_by_id() with RBAC to verify pipeline exists and is active
        # This raises PipelineNotFoundError if not found or inactive
        pipeline_data = await cls.get_by_id(
            entity_id=pipeline_uuid,
            requester_id=requester_id,
        )

        # Extract UUID from serialized data and return
        # The inherited get_by_id() returns serialized dict with "id" field as string
        return UUID(pipeline_data["id"])

    @classmethod
    async def refresh_cache(cls) -> Dict[str, Any]:
        """
        Refresh the pipeline cache with updated data from database.

        Returns:
            Stats dict with refresh info
        """
        cls._get_logger().info("Refreshing pipeline cache...")
        return await cls.initialize_cache()

    @classmethod
    async def get_model_endpoints_metadata(cls) -> List[Dict[str, Any]]:
        """
        Retrieves model endpoints metadata from the database in the format expected by the frontend.

        Lazy-loads the pipeline cache on first call.

        Returns:
            List of ModelMetadata objects matching the frontend interface.

        Raises:
            HTTPException: If database operation fails.
        """
        # Lazy initialize cache if not already initialized
        cache_data = CacheService.get(PIPELINE_CACHE_KEY)
        if cache_data is None:
            cls._get_logger().info(
                "Pipeline cache not initialized, initializing now..."
            )
            await cls.initialize_cache()
            cache_data = CacheService.get(PIPELINE_CACHE_KEY)

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
            "request_function": entity.request_function,
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
