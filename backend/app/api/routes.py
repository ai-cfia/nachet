from fastapi import APIRouter, status, Depends, Request, HTTPException, Header
from fastapi.responses import Response
from typing import Optional
from uuid import UUID

from app.service import (
    PipelineService,
    SeedService,
    DirectoryService,
    FrontendService,
    LogService,
    DeviceService,
    UserService,
    ImageProcessingService,
)
from app.service.inference import InferenceService
from app.service.auth import User, get_current_user
from app.api.config import get_limiter
from app.model.inference import (
    InferenceRequest,
    ImageSubmissionResponse,
    SanitizationCallbackRequest,
    ApiInferenceResponse,
)
from app.exceptions import ImageProcessingError
# from app.api.test_dbos import router as test_dbos_router

router = APIRouter()
limiter = get_limiter()

# Include DBOS test router (no auth required for testing)
# router.include_router(test_dbos_router)

# Module-level logger
_logger = None


def _get_logger():
    """Lazy load logger to avoid circular imports"""
    global _logger
    if _logger is None:
        from app.service.logs import LogService

        _logger = LogService.get_logger()
    return _logger


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
        _get_logger().warning(
            "IP address mismatch", client_ip=client_ip, token_ip=token_ip
        )

    return current_user


# Image Processing Pipeline Endpoints
@router.post(
    "/inf",
    status_code=status.HTTP_200_OK,
    response_model=ImageSubmissionResponse,
    name="Submit Image for Processing [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def submit_image_for_processing(
    request: Request,
    req: InferenceRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Submit an image for async processing (MVP: upload → scan → sanitize).

    This is the new async version of the legacy /inf endpoint.
    Returns immediately with UUID while processing continues in background.

    Request body matches legacy API format:
    {
        "pipeline_id": "pipeline-name",
        "folder_name": "folder-identifier",
        "imageDims": [1920, 1080],
        "image": "data:image/png;base64,...",
        "area_ratio": 0.5,
        "color_format": "hex"
    }

    Response (new format):
    {
        "image_id": "uuid",
        "workflow_id": "workflow-uuid",
        "status": "pending",
        "message": "Image submitted for processing"
    }

    Frontend should poll GET /inf/{image_id}/status for progress.
    """
    # Delegate to InferenceService (handles session, logging, business logic)
    return await InferenceService.submit_inference_request(
        request=req,
        user_id=current_user.oid,
    )


@router.post(
    "/inf-direct",
    status_code=status.HTTP_200_OK,
    response_model=ApiInferenceResponse,
    name="Submit Image for Direct Processing [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def submit_image_for_simple_direct_processing(
    request: Request,
    req: InferenceRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Submit an image for direct processing (synchronous).
    Does not store anything.
    Direct to the model endpoint and returns the classification result.

    Returns ApiInferenceResponse with boxes and classifications.
    """
    # Delegate to InferenceService (handles session, logging, business logic)
    return await InferenceService.submit_direct_pipeline_inference_request_test(
        request=req,
        user_id=current_user.oid,
    )


@router.get(
    "/inf/{image_id}/status",
    status_code=status.HTTP_200_OK,
    name="Get Image Processing Status [AUTH REQUIRED]",
)
@limiter.limit("60/minute")
async def get_image_processing_status(
    request: Request,
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the current processing status of an image.

    Returns detailed status information including:
    - Current processing stage (upload, scan, sanitize)
    - Progress percentage (0-100)
    - Timestamps for each stage
    - Blob URLs when available
    - Error information if failed

    Frontend should poll this endpoint (with exponential backoff)
    until status is "completed" or "failed".
    """
    # Validate UUID format
    try:
        image_uuid = UUID(image_id)
    except ValueError:
        raise ValueError(f"Invalid image_id format: {image_id}")

    # Delegate to InferenceService (handles session, logging, business logic)
    return await InferenceService.get_inference_status(
        image_id=image_uuid,
        user_id=current_user.oid,
    )


# Sanitization Callback Endpoint
@router.post(
    "/callbacks/sanitization-complete",
    status_code=status.HTTP_200_OK,
    name="Sanitization Complete Callback [FUNCTION KEY AUTH]",
)
async def sanitization_complete_callback(
    request_data: SanitizationCallbackRequest,
    x_functions_key: Optional[str] = Header(None),
):
    """
    Callback endpoint for Azure sanitization function.

    The sanitizer calls this endpoint when image sanitization is complete.
    Uses DBOS messaging to notify the waiting workflow.

    Authentication: Validates x-functions-key header matches configured key.

    Request Body:
        {
            "image_id": "uuid",
            "status": "success|failed",
            "sanitized_blob_url": "https://...",  # optional, only on success
            "error": "error message"  # optional, only on failure
        }

    The workflow waits for this message using DBOS.recv_async() in
    wait_for_sanitization_callback() (app/service/sanitization.py).
    """
    try:
        # Delegate to ImageProcessingService (handles auth, validation, DBOS messaging)
        return await ImageProcessingService.handle_sanitization_callback(
            image_id=request_data.image_id,
            status=request_data.status,
            sanitized_blob_url=request_data.sanitized_blob_url,
            error=request_data.error,
            function_key=x_functions_key,
        )
    except ValueError as e:
        # ValueError indicates auth or validation failure
        if "Invalid function key" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    except ImageProcessingError as e:
        # ImageProcessingError indicates config or processing failure
        if "not configured" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process callback: {str(e)}",
            )


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
async def get_health_status(request: Request):
    return {"status": "ok"}


@router.get(
    "/version",
    status_code=status.HTTP_200_OK,
    name="Get API Version [NO AUTH REQUIRED]",
)
async def get_version(request: Request):
    return {"version": "0.0.0"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    name="Get Readiness Status [NO AUTH REQUIRED]",
)
async def get_readiness_status(request: Request):
    return {"status": "ready"}


@router.post(
    "/get-user-id",
    status_code=status.HTTP_200_OK,
    name="Get User ID from email [AUTH REQUIRED]",
)
async def get_user_id(request: Request, current_user: User = Depends(get_current_user)):
    _get_logger().debug("get_user_id endpoint called", user_id=current_user.oid)
    return {"user_id": current_user.oid}


@router.get(
    "/pipelines",
    status_code=status.HTTP_200_OK,
    name="Get Pipelines [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_pipelines(
    request: Request, current_user: User = Depends(get_current_user)
):
    pipelines = await PipelineService.get_pipelines()
    return {"pipelines": pipelines}


@router.get(
    "/model-endpoints-metadata",
    status_code=status.HTTP_200_OK,
    name="Get Model Endpoints Metadata [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_model_endpoints_metadata(
    request: Request, current_user: User = Depends(get_current_user)
):
    _get_logger().debug(
        "model_endpoints_metadata endpoint called", user_id=current_user.oid
    )
    metadata = await PipelineService.get_model_endpoints_metadata()
    return metadata


@router.get(
    "/seeds",
    status_code=status.HTTP_200_OK,
    name="Get Seed Data [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_seed_data(
    request: Request, current_user: User = Depends(get_current_user)
):
    # print(f"/seeds - authenticated user: {current_user.oid}")
    # print(f"/seeds - user: {current_user.__dict__}")
    seed_data = await SeedService.get_seed_data()
    return seed_data


@router.get(
    "/devices",
    status_code=status.HTTP_200_OK,
    name="Get All Devices [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_devices(request: Request, current_user: User = Depends(get_current_user)):
    """
    Get all device information organized by brand.

    Returns:
        Dictionary with "devices" key containing array of brand objects:
        {
            "devices": [
                {
                    "id": "uuid",
                    "name": "brand_name",
                    "description": "Brand description",
                    "models": [
                        {
                            "id": "uuid",
                            "name": "model1",
                            "description": "Model description"
                        }
                    ],
                    "lenses": [
                        {
                            "id": "uuid",
                            "name": "lens1",
                            "description": "Lens description"
                        }
                    ]
                }
            ]
        }
    """
    _get_logger().debug("get_devices endpoint called", user_id=current_user.oid)
    devices = await DeviceService.get_all_devices(current_user.oid)
    return devices


@router.get(
    "/get-directories",
    status_code=status.HTTP_200_OK,
    name="Get Directories [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def get_directories(
    request: Request, current_user: User = Depends(get_current_user)
):
    _get_logger().debug("get_directories endpoint called", user_id=current_user.oid)
    directories = await DirectoryService.get_user_directories(current_user.oid)
    return directories


@router.get(
    "/is-registered",
    status_code=status.HTTP_200_OK,
    name="Check if User is Registered [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def check_user_registration(
    request: Request, current_user: User = Depends(get_current_user)
):
    _get_logger().debug(
        "check_user_registration endpoint called", user_id=current_user.oid
    )
    is_registered = await UserService.check_user_registration(current_user)
    return {"is_registered": is_registered}


@router.get(
    "/logout",
    status_code=status.HTTP_200_OK,
    name="Logout User [NO AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def logout_user(request: Request):
    # Return html with clear site data header to clear cookies and cache
    html_content = """
    <html>
        <head>
            <title>Logged Out</title>
        </head>
        <body>
            <h1>You have been logged out.</h1>
            <p>You can close this window.</p>
        </body>
    </html>
    """
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Clear-Site-Data": '"cache","cookies","storage"',
            "Cache-Control": "no-store, max-age=0",
        },
    )


# Frontend Log endpoint
@router.post(
    "/logs",
    status_code=status.HTTP_200_OK,
    name="Frontend Log Endpoint [AUTH REQUIRED]",
)
async def frontend_log_endpoint(
    request: Request, current_user: User = Depends(get_current_user)
):
    log_data = await request.json()
    log_data["user_id"] = current_user.oid
    log_data["user_agent"] = request.headers.get("user-agent", "")
    response = await LogService.process_frontend_log(log_data)
    return response


# Frontend static file serving routes
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    name="Serve Frontend Root [NO AUTH REQUIRED]",
    include_in_schema=False,
)
@limiter.limit("60/minute")
async def serve_frontend_root(request: Request):
    """Serve the main index.html file."""
    await FrontendService.check_and_update_version()
    # Get CSP nonce from request state (set by HeadersMiddleware)
    csp_nonce = getattr(request.state, "csp_nonce", None)
    content, content_type = await FrontendService.get_file("index.html", csp_nonce)
    return Response(content=content, media_type=content_type)


# This is placed at the end to avoid catching other routes
@router.get(
    "/{path:path}",
    status_code=status.HTTP_200_OK,
    name="Serve Frontend Static Files [NO AUTH REQUIRED]",
    include_in_schema=False,
)
@limiter.limit("60/minute")
async def serve_frontend_static(request: Request, path: str):
    """
    Serve static frontend files (assets, favicon, etc.).
    Falls back to index.html for SPA client-side routing.

    Security: Only serves files from the frontend/dist/ directory.
    Validates paths to prevent directory traversal attacks.
    """
    await FrontendService.check_and_update_version()

    # Validate path to prevent directory traversal attacks
    # Normalize and check for dangerous patterns
    normalized_path = path.lstrip("/")

    # Block directory traversal attempts
    if ".." in normalized_path or normalized_path.startswith("/"):
        return Response(
            content="Invalid file path",
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="text/plain",
        )

    # Get CSP nonce from request state (set by HeadersMiddleware)
    csp_nonce = getattr(request.state, "csp_nonce", None)
    try:
        # Try to serve the requested file
        content, content_type = await FrontendService.get_file(
            normalized_path, csp_nonce
        )
        return Response(content=content, media_type=content_type)
    except Exception:
        # Fallback to index.html for client-side routing (SPA)
        # This allows React Router to handle the route
        try:
            content, content_type = await FrontendService.get_file(
                "index.html", csp_nonce
            )
            return Response(content=content, media_type=content_type)
        except Exception as e:
            # If even index.html fails, return 500
            _get_logger().error(
                "Error serving frontend file", error=str(e), error_type=type(e).__name__
            )
            return Response(
                content="Failed to load frontend file",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="text/plain",
            )
