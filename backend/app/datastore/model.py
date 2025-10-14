"""
Model data service using generic BaseCRUDDataService.

Provides data access layer for Model operations with minimal code duplication.
"""

from typing import List, Optional, Type
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import Model, ModelTask
from app.service.base_crud import BaseCRUDDataService


class ModelDataService(BaseCRUDDataService[Model]):
    """Data access layer for Model database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Model]:
        """Return the Model ORM class."""
        return Model

    def get_query_options(self) -> list:
        """Load the model_task relationship for all queries."""
        return [selectinload(Model.model_task)]

    async def get_by_task_id(self, task_id: int) -> List[Model]:
        """
        Retrieve all active models for a specific task.

        This is a custom method specific to Model entity.

        Args:
            task_id: The model task ID

        Returns:
            List of Model objects for the given task
        """
        query = (
            select(Model)
            .where(Model.task_id == task_id)
            .where(Model.active.is_(True))
            .options(*self.get_query_options())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
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
    ) -> Model:
        """
        Create a new model.

        Override to provide type hints for Model-specific fields.
        Uses the base class implementation via super().

        Args:
            task_id: Model task ID (foreign key)
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
            The created Model object
        """
        return await super().create(
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


class ModelTaskDataService(BaseCRUDDataService[ModelTask]):
    """Data access layer for ModelTask database operations."""

    @classmethod
    def get_model_class(cls) -> Type[ModelTask]:
        """Return the ModelTask ORM class."""
        return ModelTask

    def get_query_options(self) -> list:
        """
        Return query options for eager loading ModelTask relationships.
        
        Returns:
            List of SQLAlchemy query options for loading the models relationship
        """
        return [selectinload(ModelTask.models)]
