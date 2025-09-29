from fastapi import APIRouter, status, Depends
from app.service import PipelineService, SeedService, DirectoryService
from app.middleware.auth.jwt_auth import get_current_user
from app.middleware.auth.user import User

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
    name="Get Pipelines [AUTH REQUIRED]",
)
async def get_pipelines(current_user: User = Depends(get_current_user)):
    pipelines = await PipelineService.get_pipelines()
    return {"pipelines": pipelines}


@router.get(
    "/model-endpoints-metadata",
    status_code=status.HTTP_200_OK,
    name="Get Model Endpoints Metadata [AUTH REQUIRED]",
)
async def get_model_endpoints_metadata(current_user: User = Depends(get_current_user)):
    print("/model-endpoints-metadata")
    metadata = await PipelineService.get_model_endpoints_metadata()
    return metadata


@router.get(
    "/seeds",
    status_code=status.HTTP_200_OK,
    name="Get Seed Data [AUTH REQUIRED]",
)
async def get_seed_data(current_user: User = Depends(get_current_user)):
    # print(f"/seeds - authenticated user: {current_user.oid}")
    # print(f"/seeds - user: {current_user.__dict__}")
    seed_data = await SeedService.get_seed_data()
    return seed_data


@router.post(
    "/get-user-id",
    status_code=status.HTTP_200_OK,
    name="Get User ID from email [AUTH REQUIRED]",
)
async def get_user_id(current_user: User = Depends(get_current_user)):
    print("/get-user-id")
    return {"user_id": current_user.oid}


@router.get(
    "/get-directories",
    status_code=status.HTTP_200_OK,
    name="Get Directories [NO AUTH REQUIRED]",
)
async def get_directories(current_user: User = Depends(get_current_user)):
    print("/get-directories")
    directories = await DirectoryService.get_user_directories(current_user.oid)
    return directories
