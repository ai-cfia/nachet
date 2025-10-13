"""
Database repository layer for pipeline and model operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload, selectinload

from app.db.model import Pipeline, Model, PipelineModel


class PipelineDataService:
    """Repository class for pipeline and model database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

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

    async def get_by_id(self, pipeline_id: str) -> Optional[Pipeline]:
        """
        Retrieve a pipeline by ID.

        Args:
            pipeline_id: The pipeline UUID

        Returns:
            Pipeline object if found and active, None otherwise
        """
        stmt = (
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .where(Pipeline.active.is_(True))
            .options(
                selectinload(Pipeline.pipeline_models).selectinload(PipelineModel.model)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
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
    ) -> Pipeline:
        """
        Create a new pipeline.

        Args:
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
            The created Pipeline object
        """
        pipeline = Pipeline(
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
            active=True,
        )
        self.session.add(pipeline)
        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline

    async def update(
        self,
        pipeline_id: str,
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
    ) -> Optional[Pipeline]:
        """
        Update a pipeline.

        Args:
            pipeline_id: The pipeline UUID
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
            Updated Pipeline object if found, None otherwise
        """
        pipeline = await self.get_by_id(pipeline_id)
        if not pipeline:
            return None

        if name is not None:
            pipeline.name = name
        if data is not None:
            pipeline.data = data
        if created_by is not None:
            pipeline.created_by = created_by
        if creation_date is not None:
            pipeline.creation_date = creation_date
        if description is not None:
            pipeline.description = description
        if job_name is not None:
            pipeline.job_name = job_name
        if version is not None:
            pipeline.version = version
        if dataset is not None:
            pipeline.dataset = dataset
        if identifiable is not None:
            pipeline.identifiable = identifiable
        if metrics is not None:
            pipeline.metrics = metrics
        if default is not None:
            pipeline.default = default

        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline

    async def soft_delete(self, pipeline_id: str) -> Optional[Pipeline]:
        """
        Soft delete a pipeline by setting active to False.

        Args:
            pipeline_id: The pipeline UUID

        Returns:
            The soft-deleted Pipeline object if found, None otherwise
        """
        stmt = select(Pipeline).where(Pipeline.id == pipeline_id)
        result = await self.session.execute(stmt)
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            return None

        pipeline.active = False
        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline
