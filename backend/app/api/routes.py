from fastapi import APIRouter, status
from app.service import PipelineService, SeedService, DirectoryService
from app.model import DirectoryRequest

router = APIRouter()


# no authentication needed
@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    name="Get Health Status [NO AUTH REQUIRED]",
)
async def get_health_status():
    return {"status": "ok"}


@router.get(
    "/version",
    status_code=status.HTTP_200_OK,
    name="Get API Version [NO AUTH REQUIRED]",
)
async def get_version():
    return {"version": "0.0.0"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    name="Get Readiness Status [NO AUTH REQUIRED]",
)
async def get_readiness_status():
    return {"status": "ready"}


@router.get(
    "/pipelines",
    status_code=status.HTTP_200_OK,
    name="Get Pipelines [NO AUTH REQUIRED]",
)
async def get_pipelines():
    pipelines = await PipelineService.get_pipelines()
    return {"pipelines": pipelines}


@router.get(
    "/model-endpoints-metadata",
    status_code=status.HTTP_200_OK,
    name="Get Model Endpoints Metadata [NO AUTH REQUIRED]",
)
async def get_model_endpoints_metadata():
    print("/model-endpoints-metadata")
    metadata = await PipelineService.get_model_endpoints_metadata()
    return metadata


@router.get(
    "/seeds",
    status_code=status.HTTP_200_OK,
    name="Get Seed Data [NO AUTH REQUIRED]",
)
async def get_seed_data():
    print("/seeds")
    seed_data = await SeedService.get_seed_data()
    return seed_data


@router.post(
    "/get-user-id",
    status_code=status.HTTP_200_OK,
    name="Get User ID from email [NO AUTH REQUIRED]",
)
async def get_user_id():
    print("/get-user-id")
    return {"user_id": "8ea46a6b-7d37-4fbb-a66f-775112376e16"}


@router.post(
    "/get-directories",
    status_code=status.HTTP_200_OK,
    name="Get Directories [NO AUTH REQUIRED]",
)
async def get_directories(req_body: DirectoryRequest):
    print("/get-directories")
    directories = await DirectoryService.get_user_directories(req_body.container_name)
    return directories
