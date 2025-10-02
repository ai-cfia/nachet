"""
Pipeline service module.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.db.utils import sessionmanager
from app.datastore import PipelineDataService


class PipelineService:
    """
    Service class to handle pipeline-related operations.
    """

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
