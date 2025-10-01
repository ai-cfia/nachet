from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import Response
from app.service import PipelineService, SeedService, DirectoryService, FrontendService
from app.middleware.auth.jwt_auth import get_current_user
from app.middleware.auth.user import User
from app.api.config import get_limiter

router = APIRouter()
limiter = get_limiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP address, handling reverse proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def validate_ip_address(
    request: Request, current_user: User = Depends(get_current_user)
) -> User:
    """Validate that request IP matches token IP claim."""
    client_ip = get_client_ip(request)
    token_ip = current_user.ipaddr

    if token_ip and client_ip != token_ip:
        # raise HTTPException(
        #     status_code=status.HTTP_403_FORBIDDEN,
        #     detail="IP address mismatch"
        # )
        print(f"Warning: IP address mismatch (client: {client_ip}, token: {token_ip})")

    return current_user


# Rate limiter test route
@router.get(
    "/rate-limit-test",
    status_code=status.HTTP_200_OK,
    name="Rate Limit Test [NO AUTH REQUIRED]",
)
@limiter.limit("2/minute")
async def rate_limit_test(request: Request):
    return {"message": "This is a rate-limited endpoint."}


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


@router.post(
    "/get-user-id",
    status_code=status.HTTP_200_OK,
    name="Get User ID from email [AUTH REQUIRED]",
)
async def get_user_id(current_user: User = Depends(get_current_user)):
    print("/get-user-id")
    return {"user_id": current_user.oid}


@router.get(
    "/pipelines",
    status_code=status.HTTP_200_OK,
    name="Get Pipelines [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_pipelines(current_user: User = Depends(get_current_user)):
    pipelines = await PipelineService.get_pipelines()
    return {"pipelines": pipelines}


@router.get(
    "/model-endpoints-metadata",
    status_code=status.HTTP_200_OK,
    name="Get Model Endpoints Metadata [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_model_endpoints_metadata(current_user: User = Depends(get_current_user)):
    print("/model-endpoints-metadata")
    metadata = await PipelineService.get_model_endpoints_metadata()
    return metadata


@router.get(
    "/seeds",
    status_code=status.HTTP_200_OK,
    name="Get Seed Data [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_seed_data(current_user: User = Depends(get_current_user)):
    # print(f"/seeds - authenticated user: {current_user.oid}")
    # print(f"/seeds - user: {current_user.__dict__}")
    seed_data = await SeedService.get_seed_data()
    return seed_data


@router.get(
    "/get-directories",
    status_code=status.HTTP_200_OK,
    name="Get Directories [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_directories(current_user: User = Depends(get_current_user)):
    print("/get-directories")
    directories = await DirectoryService.get_user_directories(current_user.oid)
    return directories


# Frontend static file serving routes
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    name="Serve Frontend Root [NO AUTH REQUIRED]",
    include_in_schema=False,
)
@limiter.limit("60/minute")
async def serve_frontend_root():
    """Serve the main index.html file."""
    content, content_type = await FrontendService.get_file("index.html")
    return Response(content=content, media_type=content_type)


# This is placed at the end to avoid catching other routes
@router.get(
    "/{path:path}",
    status_code=status.HTTP_200_OK,
    name="Serve Frontend Static Files [NO AUTH REQUIRED]",
    include_in_schema=False,
)
@limiter.limit("60/minute")
async def serve_frontend_static(path: str):
    """
    Serve static frontend files (assets, favicon, etc.).
    Falls back to index.html for SPA client-side routing.
    """
    try:
        # Try to serve the requested file
        content, content_type = await FrontendService.get_file(path)
        return Response(content=content, media_type=content_type)
    except Exception:
        # Fallback to index.html for client-side routing (SPA)
        # This allows React Router to handle the route
        try:
            content, content_type = await FrontendService.get_file("index.html")
            return Response(content=content, media_type=content_type)
        except Exception as e:
            # If even index.html fails, return 500
            print(f"Error serving frontend file: {e}")
            return Response(
                content="Failed to load frontend file",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="text/plain",
            )
