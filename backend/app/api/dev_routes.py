from app.model.system import RateLimitTestResponse
from fastapi import APIRouter, Request, Depends, status
from app.api.config import get_limiter
from app.service.auth import User, get_current_user
from app.service.inference import InferenceService
from app.model.inference import ApiInferenceResponse, InferenceRequest
from uuid import UUID

router = APIRouter(prefix="", tags=["Debug"])
limiter = get_limiter()


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


# Rate limiter test route
@router.get(
    "/rate-limit-test",
    status_code=status.HTTP_200_OK,
    response_model=RateLimitTestResponse,
    name="Rate Limit Test [NO AUTH REQUIRED]",
)
@limiter.limit("6/hour")
async def rate_limit_test(request: Request):
    return {"message": "This is a rate-limited endpoint."}
