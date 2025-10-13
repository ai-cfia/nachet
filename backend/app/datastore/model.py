from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.model import Model


class ModelDataService:
    """Data access layer for Model database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Model]:
        """
        Retrieve all active models with their task relationships.

        Returns:
            List of Model objects
        """
        query = (
            select(Model)
            .where(Model.active.is_(True))
            .options(selectinload(Model.model_task))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, model_id: UUID) -> Optional[Model]:
        """
        Retrieve a model by ID.

        Args:
            model_id: The model UUID

        Returns:
            Model object if found and active, None otherwise
        """
        query = (
            select(Model)
            .where(Model.id == model_id)
            .where(Model.active.is_(True))
            .options(selectinload(Model.model_task))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_task_id(self, task_id: int) -> List[Model]:
        """
        Retrieve all active models for a specific task.

        Args:
            task_id: The model task ID

        Returns:
            List of Model objects for the given task
        """
        query = (
            select(Model)
            .where(Model.task_id == task_id)
            .where(Model.active.is_(True))
            .options(selectinload(Model.model_task))
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
        model = Model(
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
            active=True,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model, ["model_task"])
        return model

    async def update(
        self,
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
    ) -> Optional[Model]:
        """
        Update a model.

        Args:
            model_id: The model UUID
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
            Updated Model object if found, None otherwise
        """
        model = await self.get_by_id(model_id)
        if not model:
            return None

        if task_id is not None:
            model.task_id = task_id
        if name is not None:
            model.name = name
        if endpoint_name is not None:
            model.endpoint_name = endpoint_name
        if api_url is not None:
            model.api_url = api_url
        if api_key is not None:
            model.api_key = api_key
        if created_by is not None:
            model.created_by = created_by
        if date_model_training is not None:
            model.date_model_training = date_model_training
        if content_type is not None:
            model.content_type = content_type
        if deployment_platform is not None:
            model.deployment_platform = deployment_platform
        if version is not None:
            model.version = version
        if description is not None:
            model.description = description
        if job_name is not None:
            model.job_name = job_name
        if dataset is not None:
            model.dataset = dataset
        if artifacts_url is not None:
            model.artifacts_url = artifacts_url
        if sha256 is not None:
            model.sha256 = sha256

        await self.session.flush()
        await self.session.refresh(model, ["model_task"])
        return model

    async def soft_delete(self, model_id: UUID) -> Optional[Model]:
        """
        Soft delete a model by setting active to False.

        Args:
            model_id: The model UUID

        Returns:
            The soft-deleted Model object if found, None otherwise
        """
        query = select(Model).where(Model.id == model_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return None

        model.active = False
        await self.session.flush()
        await self.session.refresh(model, ["model_task"])
        return model
