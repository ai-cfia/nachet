from fastapi import APIRouter, status, Depends, Request, HTTPException  # , Header
from fastapi.responses import Response

# from beartype.typing import Optional
from uuid import UUID

from app.service import (
    PipelineService,
    SeedService,
    DirectoryService,
    FrontendService,
    LogService,
    DeviceService,
    UserService,
)
from app.service.inference import InferenceService
from app.service.auth import User, get_current_user
from app.api.config import get_limiter
from app.model.inference import (
    InferenceRequest,
    ImageSubmissionResponse,
    # SanitizationCallbackRequest,
    ApiInferenceResponse,
)
from app.model.batch_upload import (
    BatchUploadInitRequest,
    BatchUploadInitResponse,
    BatchUploadImageRequest,
)
from app.service.batch_upload import BatchUploadService
# from app.exceptions import ImageProcessingError
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


def get_client_ip(request: Request) -> str | None:
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
    # Delegate to InferenceService (handles session, logging, business logic)
    # user.oid is validated by get_current_user to be a valid UUID string
    return await InferenceService.submit_inference_request(
        request=req,
        user_id=UUID(current_user.oid),  # type: ignore[arg-type]
    )


@router.post(
    "/inf-direct",
    status_code=status.HTTP_200_OK,
    response_model=ApiInferenceResponse,
    name="Submit Image for Direct Processing [CFIA ADMIN ONLY]",
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

    Access: CFIA admin only
    """

    # Delegate to InferenceService (handles session, logging, business logic)
    # user.oid is validated by get_current_user to be a valid UUID string
    return await InferenceService.submit_direct_pipeline_inference_request_test(
        request=req,
        user_id=UUID(current_user.oid),  # type: ignore[arg-type]
    )


@router.get(
    "/workflow/{workflow_id}/status",
    status_code=status.HTTP_200_OK,
    name="Get Workflow Status [AUTH REQUIRED]",
)
@limiter.limit("60/minute")
async def get_workflow_status(
    request: Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive workflow status by workflow ID.

    Accepts any workflow_id (parent, processing, or inference child)
    and returns status for all related workflows.

    Authorization: User must own the workflow OR be a CFIA admin.

    Returns detailed status information including:
    - Workflow type (parent/processing/inference)
    - Associated image ID
    - Overall status (pending/in_progress/completed/failed)
    - Parent workflow status and progress
    - Processing workflow stages and timestamps
    - Inference workflow status and details
    - Authorization metadata

    Use cases:
    - Frontend receives workflow_id from POST /inf submission
    - Frontend polls this endpoint to check progress
    - Can query by any related workflow ID (parent or child)

    Returns:
        Dict with comprehensive workflow status across all related workflows
    """
    # Validate workflow_id is not empty
    if not workflow_id or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty")

    # Delegate to InferenceService (handles DB queries, authorization, DBOS status)
    return await InferenceService.get_workflow_status(
        workflow_id=workflow_id.strip(),
        user_id=UUID(current_user.oid),  # type: ignore[arg-type]
    )


@router.get(
    "/workflow/{workflow_id}/results",
    status_code=status.HTTP_200_OK,
    response_model=ApiInferenceResponse,
    name="Get Workflow Results [AUTH REQUIRED]",
)
@limiter.limit("60/minute")
async def get_workflow_results(
    request: Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get inference results for a completed workflow.

    Returns formatted inference results including bounding boxes, classifications,
    and model metadata when the workflow has completed successfully.

    Authorization: User must own the workflow OR be a CFIA admin.

    Args:
        workflow_id: Parent workflow ID returned by POST /inf

    Returns:
        ApiInferenceResponse with:
        - filename: Image filename
        - imageId: Image UUID
        - inference_id: Annotation UUID (equals workflow_id)
        - boxes: List of detected objects with classifications
        - labelOccurrence: Count of each label
        - totalBoxes: Total number of detected boxes
        - models: Model metadata used for inference

    Raises:
        404: If workflow not found or results not ready
        403: If user not authorized to access workflow
        500: If results retrieval fails

    Use cases:
    - Frontend polls /workflow/{id}/status until overall_status == "completed"
    - Frontend then calls this endpoint to get formatted results
    - Results are stored in Annotation table with id == parent workflow_id
    """
    # Validate workflow_id is not empty
    if not workflow_id or not workflow_id.strip():
        raise ValueError("workflow_id cannot be empty")

    # Delegate to InferenceService (handles DB queries, authorization, result formatting)
    return await InferenceService.get_workflow_results(
        workflow_id=workflow_id.strip(),
        user_id=UUID(current_user.oid),  # type: ignore[arg-type]
    )


# Sanitization Callback Endpoint
# @router.post(
#     "/callbacks/sanitization-complete",
#     status_code=status.HTTP_200_OK,
#     name="Sanitization Complete Callback [FUNCTION KEY AUTH]",
# )
# async def sanitization_complete_callback(
#     request_data: SanitizationCallbackRequest,
#     x_functions_key: Optional[str] = Header(None),
# ):
#     """
#     Callback endpoint for Azure sanitization function.

#     The sanitizer calls this endpoint when image sanitization is complete.
#     Uses DBOS messaging to notify the waiting workflow.

#     Authentication: Validates x-functions-key header matches configured key.

#     Request Body:
#         {
#             "image_id": "uuid",
#             "status": "success|failed",
#             "sanitized_blob_url": "https://...",  # optional, only on success
#             "error": "error message"  # optional, only on failure
#         }

#     The workflow waits for this message using DBOS.recv_async() in
#     wait_for_sanitization_callback() (app/service/sanitization.py).
#     """
#     try:
#         # Delegate to InferenceService (handles auth, validation, DBOS messaging)
#         return await InferenceService.handle_sanitization_callback(
#             image_id=request_data.image_id,
#             status=request_data.status,
#             sanitized_blob_url=request_data.sanitized_blob_url,
#             error=request_data.error,
#             function_key=x_functions_key,
#         )
#     except ValueError as e:
#         # ValueError indicates auth or validation failure
#         if "Invalid function key" in str(e):
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail=str(e),
#             )
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=str(e),
#             )
#     except ImageProcessingError as e:
#         # ImageProcessingError indicates config or processing failure
#         if "not configured" in str(e):
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=str(e),
#             )
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"Failed to process callback: {str(e)}",
#             )


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
    # user.oid is validated by get_current_user to be a valid UUID string
    user_id = UUID(current_user.oid)  # type: ignore[arg-type]
    _get_logger().debug("get_devices endpoint called", user_id=str(user_id))
    devices = await DeviceService.get_all_devices(user_id)
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
    # user.oid is validated by get_current_user to be a valid UUID string
    user_id = UUID(current_user.oid)  # type: ignore[arg-type]
    _get_logger().debug("get_directories endpoint called", user_id=str(user_id))
    directories = await DirectoryService.get_user_directories(user_id)
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


# Batch Upload Endpoints
@router.post(
    "/new-batch-import",
    status_code=status.HTTP_200_OK,
    response_model=BatchUploadInitResponse,
    name="Initialize Batch Upload [AUTH REQUIRED]",
)
@limiter.limit("10/minute")
async def initialize_batch_upload(
    request: Request,
    req: BatchUploadInitRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Initialize batch upload session.

    Creates a database-backed session for batch uploading images to an existing folder.
    Sessions expire after 24 hours and support up to 1000 files.

    Security:
    - Requires authentication (Bearer token)
    - Rate limited to 10 requests/minute
    - Validates folder exists and belongs to user

    Request:
        - folder_id: UUID of existing folder (MUST exist before batch upload)
        - file_count: Number of images to upload (max 1000)

    Response:
        - session_id: UUID for subsequent uploads (valid for 24 hours)

    Workflow:
    1. Validate user has org roles
    2. Validate folder exists and belongs to user
    3. Validate file_count <= 1000
    4. Create database session with 24-hour TTL
    5. Return session_id

    Constraints:
    - Maximum 1000 files per session
    - Session expires after 24 hours
    - Folder must exist before session creation
    - Folder must belong to authenticated user
    """
    result = await BatchUploadService.initialize_batch_session(
        user_id=UUID(current_user.oid),
        folder_id=UUID(req.folder_id),
        file_count=req.file_count,
    )
    return BatchUploadInitResponse(**result)


@router.post(
    "/upload-picture",
    status_code=status.HTTP_200_OK,
    name="Upload Picture in Batch [AUTH REQUIRED]",
)
@limiter.limit("60/minute")
async def upload_picture_in_batch(
    request: Request,
    req: BatchUploadImageRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Upload single picture in batch - ASYNC WORKFLOW with duplicate detection.

    Returns immediately with workflow_id. Frontend must poll
    GET /workflow/{workflow_id}/status for completion.

    Workflow steps (background):
    1. Upload to EXTERNAL storage (nachet-original)
    2. Azure Defender malware scan
    3. Sanitization function
    4. Store in INTERNAL storage (nachet-sanitized)

    Security:
    - Requires authentication (Bearer token)
    - Rate limited to 60 requests/minute
    - Validates session ownership, expiration, and active status
    - Validates seed exists
    - Reuses existing DBOS workflow (Defender + sanitization)

    Request:
        - session_id: From /new-batch-import (must be active and not expired)
        - seed_id: UUID of existing seed record (validated before upload)
        - tray_code: Sample tray identifier (A-E)
        - sample_id: Becomes picture.name field
        - device_*_id, magnification: Device metadata
        - image: Base64 data URL

    Response (Success):
        - workflow_id: Poll /workflow/{id}/status
        - picture_id: Image UUID

    Response (Duplicate):
        - 400 BAD_REQUEST with existing picture_id
        - Both uploaded_count and duplicate_count incremented
        - No workflow enqueued

    Response (Session Expired):
        - 400 BAD_REQUEST "Session expired (24-hour limit exceeded)"

    Response (Invalid Seed):
        - 400 BAD_REQUEST "Seed not found: {seed_id}"

    Duplicate Handling:
    - Detects duplicates via SHA256 hash collision
    - Increments session uploaded_count and duplicate_count
    - Returns error with existing picture_id
    - Does NOT create new picture or enqueue workflow

    Session Completion:
    - When uploaded_count >= file_count, session marked inactive
    - Both successful uploads and duplicates count toward file_count

    Note: FRONTEND MODIFICATION REQUIRED for async polling.
    See BATCH_UPLOAD_IMPLEMENTATION_PLAN.md for details.
    """
    result = await BatchUploadService.upload_picture_batch(
        request=req,
        user=current_user,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    # Return workflow_id for async tracking
    # Frontend will need to be updated to handle this
    return {
        "workflow_id": result["workflow_id"],
        "picture_id": result["picture_id"],
    }


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

    # Get CSP nonce from request state (set by HeadersMiddleware)
    csp_nonce = getattr(request.state, "csp_nonce", None)

    # Delegate to FrontendService for file processing and security validation
    return await FrontendService.process_file_request(path, csp_nonce)
