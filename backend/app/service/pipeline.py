"""
Pipeline service module.
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.db.utils import sessionmanager
from app.datastore.pipeline import PipelineDataService


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
                        "data": pipeline.data,
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
                        if pipeline_model.active and pipeline_model.model.active:
                            pipeline_models.append(pipeline_model.model.name)

                    # Create a ModelMetadata entry for this pipeline
                    if pipeline_models:  # Only include pipelines that have models
                        metadata = {
                            "created_by": pipeline_models[0] if pipeline_models else "unknown",  # Use first model's creator as placeholder
                            "creation_date": pipeline.date_created.isoformat(),
                            "dataset": pipeline.data.get("dataset", "") if isinstance(pipeline.data, dict) else "",
                            "description": pipeline.data.get("description", "") if isinstance(pipeline.data, dict) else "",
                            "identifiable": pipeline.data.get("identifiable", []) if isinstance(pipeline.data, dict) else [],
                            "job_name": pipeline.data.get("job_name", "") if isinstance(pipeline.data, dict) else "",
                            "metrics": pipeline.data.get("metrics", []) if isinstance(pipeline.data, dict) else [],
                            "model_name": pipeline.name,
                            "models": pipeline_models,
                            "pipeline_name": pipeline.name,
                        }

                        # Check if this is the default pipeline (you may need to adjust this logic)
                        # For now, we'll mark the first pipeline as default or check pipeline.data
                        metadata["default"] = pipeline.data.get("default", False) if isinstance(pipeline.data, dict) else False

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
                    "data": pipeline.data,
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
