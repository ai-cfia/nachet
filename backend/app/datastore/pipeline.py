"""
Database repository layer for pipeline and model operations.
"""

from typing import List, Optional, Dict, Any, Type
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload, selectinload

# Import BaseCRUDDataService directly to avoid circular import
from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import Pipeline, Model, PipelineModel, PipelineDefault


class PipelineDataService(BaseCRUDDataService[Pipeline]):
    """Repository class for pipeline and model database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Pipeline]:
        """Return the Pipeline model class."""
        return Pipeline

    def get_query_options(self) -> list:
        """
        Return query options for eager loading Pipeline relationships.
        
        Returns:
            List of SQLAlchemy query options for loading pipeline_models and related models
        """
        return [
            selectinload(Pipeline.pipeline_models).selectinload(PipelineModel.model)
        ]

    async def get_all_pipelines(self) -> List[Pipeline]:
        """
        Retrieve all active pipelines with their associated models.

        Returns:
            List of Pipeline objects with loaded models
        """
        stmt = (
            select(Pipeline)
            .where(Pipeline.active.is_(True))
            .options(
                selectinload(Pipeline.pipeline_models).selectinload(PipelineModel.model)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pipeline_by_name(self, name: str) -> Optional[Pipeline]:
        """
        Retrieve a pipeline by name with its associated models.

        Args:
            name: The pipeline name to search for

        Returns:
            Pipeline object with loaded models or None if not found
        """
        stmt = (
            select(Pipeline)
            .where(and_(Pipeline.name == name, Pipeline.active.is_(True)))
            .options(
                selectinload(Pipeline.pipeline_models).selectinload(PipelineModel.model)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_models(self) -> List[Model]:
        """
        Retrieve all active models with their task information.

        Returns:
            List of Model objects with loaded tasks
        """
        stmt = (
            select(Model)
            .where(Model.active.is_(True))
            .options(joinedload(Model.model_task))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_model_by_name(self, name: str) -> Optional[Model]:
        """
        Retrieve a model by name with task information.

        Args:
            name: The model name to search for

        Returns:
            Model object with loaded task or None if not found
        """
        stmt = (
            select(Model)
            .where(and_(Model.name == name, Model.active.is_(True)))
            .options(joinedload(Model.model_task))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_models_by_pipeline_id(self, pipeline_id: str) -> List[Model]:
        """
        Retrieve all models associated with a specific pipeline.

        Args:
            pipeline_id: UUID of the pipeline

        Returns:
            List of Model objects ordered by their association with the pipeline
        """
        stmt = (
            select(Model)
            .join(PipelineModel, Model.id == PipelineModel.model_id)
            .where(
                and_(
                    PipelineModel.pipeline_id == pipeline_id,
                    PipelineModel.active.is_(True),
                    Model.active.is_(True),
                )
            )
            .options(joinedload(Model.model_task))
            .order_by(PipelineModel.date_created)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pipeline_models_mapping(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a mapping of pipeline names to their associated model information.

        Returns:
            Dictionary with pipeline names as keys and list of model info as values
        """
        pipelines = await self.get_all_pipelines()
        mapping = {}

        for pipeline in pipelines:
            models_info = []
            for pipeline_model in pipeline.pipeline_models:
                if pipeline_model.active and pipeline_model.model.active:
                    model = pipeline_model.model
                    model_info = {
                        "id": str(model.id),
                        "name": model.name,
                        "version": model.version,
                        "endpoint_name": model.endpoint_name,
                        "api_url": model.api_url,
                        "api_key": model.api_key,
                        "content_type": model.content_type,
                        "deployment_platform": model.deployment_platform,
                        "task_name": model.model_task.name
                        if model.model_task
                        else None,
                        "date_model_training": model.date_model_training.isoformat()
                        if model.date_model_training
                        else None,
                    }
                    models_info.append(model_info)

            mapping[pipeline.name] = models_info

        return mapping

    # Legacy methods kept for backward compatibility
    # These provide specific functionality beyond standard CRUD operations


class PipelineDefaultDataService(BaseCRUDDataService[PipelineDefault]):
    """Repository class for pipeline_default database operations."""

    @classmethod
    def get_model_class(cls) -> Type[PipelineDefault]:
        """Return the PipelineDefault model class."""
        return PipelineDefault

    def get_query_options(self) -> list:
        """
        Return query options for eager loading PipelineDefault relationships.
        
        Returns:
            List of SQLAlchemy query options for loading the pipeline relationship
        """
        return [selectinload(PipelineDefault.pipeline)]


class PipelineModelDataService(BaseCRUDDataService[PipelineModel]):
    """Repository class for pipeline_model database operations."""

    @classmethod
    def get_model_class(cls) -> Type[PipelineModel]:
        """Return the PipelineModel model class."""
        return PipelineModel

    def get_query_options(self) -> list:
        """
        Return query options for eager loading PipelineModel relationships.
        
        Returns:
            List of SQLAlchemy query options for loading pipeline and model relationships
        """
        return [
            selectinload(PipelineModel.pipeline),
            selectinload(PipelineModel.model),
        ]
