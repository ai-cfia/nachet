"""Sanitization operations as DBOS steps.

IMPORTANT: DBOS decorators wrap async functions in a way that conflicts with
beartype's automatic type checking. Use @no_type_check to exclude these functions
from automatic beartype decoration applied by beartype_this_package().
"""

from uuid import UUID
from typing import no_type_check
# import aiohttp

from dbos import DBOS
from app.service.constants import Bucket, BlobAccount
from app.exceptions import SanitizationError


# @DBOS.step(retries_allowed=True, max_attempts=3, interval_seconds=2.0)
# async def trigger_sanitization_function(
#     image_id: UUID,
#     blob_url_original: str,
# ) -> None:
#     """
#     Trigger Azure Function for image sanitization.

#     The sanitizer will:
#     1. Download image from nachet-original
#     2. Extract RGB pixel data using Pillow
#     3. Create new sanitized image
#     4. Upload to nachet-sanitized with path: {genus}/{species}/{uuidv7}.png
#     5. Call backend callback endpoint
#     """
#     from app.api.config import get_settings

#     settings = get_settings()

#     # Determine sanitized container based on environment
#     sanitized_container = Bucket.get_sanitized_container(
#         is_test=settings.is_test_environment
#     )

#     # Get Azure Function URL and key from settings
#     azure_sanitization_function_url = settings.azure_sanitization_function_url
#     azure_sanitization_function_key = settings.azure_sanitization_function_key
#     backend_url = settings.backend_url

#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.post(
#                 azure_sanitization_function_url,
#                 json={
#                     "image_id": str(image_id),
#                     "blob_url_original": blob_url_original,
#                     "genus": genus,
#                     "species": species,
#                     "sanitized_container": sanitized_container,
#                     "callback_url": f"{backend_url}/api/v1/callbacks/sanitization-complete",
#                 },
#                 headers={
#                     "x-functions-key": azure_sanitization_function_key,
#                     "Content-Type": "application/json",
#                 },
#                 timeout=aiohttp.ClientTimeout(total=30),
#             ) as response:
#                 response.raise_for_status()
#                 result = await response.json()

#                 DBOS.logger.info(
#                     f"Sanitization triggered for {image_id}: {result.get('message')}"
#                 )

#         except Exception as e:
#             raise SanitizationError(f"Failed to trigger sanitization: {str(e)}") from e


# @DBOS.step(retries_allowed=True, max_attempts=1)
# async def wait_for_sanitization_callback(
#     image_id: UUID,
#     timeout_sec: int = 600,
# ) -> str:
#     """
#     Wait for sanitization completion callback using DBOS recv.

#     The sanitizer Azure Function will call the backend callback endpoint,
#     which will send a message to this workflow using DBOS.send().

#     Returns:
#         Sanitized blob URL
#     """
#     try:
#         # Wait for message from callback endpoint
#         # Topic format: "sanitization-{image_id}"
#         topic = f"sanitization-{image_id}"

#         DBOS.logger.info(f"Waiting for sanitization callback on topic: {topic}")

#         message = await DBOS.recv_async(topic=topic, timeout_seconds=timeout_sec)

#         if not message:
#             raise SanitizationError(f"Sanitization timed out after {timeout_sec}s")

#         if message.get("status") == "success":
#             sanitized_url = message["sanitized_blob_url"]
#             DBOS.logger.info(f"Sanitization complete: {sanitized_url}")
#             return sanitized_url
#         elif message.get("status") == "failed":
#             error = message.get("error", "Unknown error")
#             raise SanitizationError(f"Sanitization failed: {error}")
#         else:
#             raise SanitizationError(
#                 f"Invalid sanitization status: {message.get('status')}"
#             )

#     except Exception as e:
#         if isinstance(e, SanitizationError):
#             raise
#         raise SanitizationError(f"Error waiting for sanitization: {str(e)}") from e


@no_type_check
@DBOS.step(retries_allowed=True, max_attempts=3, interval_seconds=2.0)
async def trigger_sanitization_function_local(
    image_id: UUID,
    org_prefix: str,
) -> str:
    """
    Local image sanitization using blob client.

    The sanitizer will:
    1. Download image from nachet-original
    2. Extract RGB pixel data using Pillow
    3. Create new sanitized image
    4. Upload to nachet-sanitized with path: {org_prefix}/{image_id}.png

    Returns:
        URL of the sanitized blob
    """
    from app.api.config import get_settings
    from app.blob.manager import blob_storage_manager
    from PIL import Image
    from io import BytesIO
    from datetime import datetime

    settings = get_settings()
    sanitized_storage = blob_storage_manager.get_client(BlobAccount.ONPREM.value)
    external_storage = blob_storage_manager.get_client(BlobAccount.EXTERNAL.value)
    bucket_prefix = settings.blob_container_prefix

    # Determine containers based on environment
    sanitized_container = bucket_prefix + Bucket.get_sanitized_container(
        is_test=settings.is_test_environment
    )

    original_container = bucket_prefix + Bucket.get_original_container(
        is_test=settings.is_test_environment
    )

    try:
        # Step 1: Download original image from blob storage
        blob_name = f"{org_prefix}/{image_id}.png"

        DBOS.logger.info(
            f"Downloading original image: {original_container}/{blob_name}"
        )
        blob_bytes = await external_storage.download_blob(original_container, blob_name)

        # Step 2: Open image with PIL and extract RGB data
        DBOS.logger.info(f"Sanitizing image {image_id}")
        original_image = Image.open(BytesIO(blob_bytes))

        # Convert to RGB mode if needed (handles RGBA, grayscale, etc.)
        if original_image.mode != "RGB":
            original_image = original_image.convert("RGB")

        # Step 3: Create new sanitized image (creates a clean copy without metadata)
        sanitized_image = Image.new("RGB", original_image.size)
        # getdata() returns ImagingCore which is iterable but not typed as such
        # Using paste() instead for better type safety
        sanitized_image.paste(original_image, (0, 0))

        # Step 4: Convert sanitized image to bytes
        sanitized_buffer = BytesIO()
        sanitized_image.save(sanitized_buffer, format="PNG")
        sanitized_bytes = sanitized_buffer.getvalue()

        # Step 5: Upload to sanitized container
        sanitized_blob_name = f"{org_prefix}/{image_id}.png"

        DBOS.logger.info(
            f"Uploading sanitized image: {sanitized_container}/{sanitized_blob_name}"
        )
        _result = await sanitized_storage.upload_blob(
            container=sanitized_container,
            name=sanitized_blob_name,
            data=sanitized_bytes,
            metadata={
                "original_image_id": str(image_id),
                "date_sanitized": datetime.utcnow().isoformat(),
            },
        )
        DBOS.logger.info(f"Sanitized image uploaded: {_result['url']}")

        sanitized_url = f"{blob_name}"
        DBOS.logger.info(f"Sanitization complete: {sanitized_url}")

        return sanitized_url

    except Exception as e:
        raise SanitizationError(f"Failed to sanitize image locally: {str(e)}") from e


# @DBOS.step(retries_allowed=True, max_attempts=1)
# async def wait_for_sanitization_callback_local(
#     image_id: UUID,
#     timeout_sec: int = 600,
# ) -> str:
#     """
#     Wait for sanitization completion callback using DBOS recv.

#     The sanitizer Azure Function will call the backend callback endpoint,
#     which will send a message to this workflow using DBOS.send().

#     Returns:
#         Sanitized blob URL
#     """
#     try:
#         # Wait for message from callback endpoint
#         # Topic format: "sanitization-{image_id}"
#         topic = f"sanitization-{image_id}"

#         DBOS.logger.info(f"Waiting for sanitization callback on topic: {topic}")

#         message = await DBOS.recv_async(topic=topic, timeout_seconds=timeout_sec)

#         if not message:
#             raise SanitizationError(f"Sanitization timed out after {timeout_sec}s")

#         if message.get("status") == "success":
#             sanitized_url = message["sanitized_blob_url"]
#             DBOS.logger.info(f"Sanitization complete: {sanitized_url}")
#             return sanitized_url
#         elif message.get("status") == "failed":
#             error = message.get("error", "Unknown error")
#             raise SanitizationError(f"Sanitization failed: {error}")
#         else:
#             raise SanitizationError(
#                 f"Invalid sanitization status: {message.get('status')}"
#             )

#     except Exception as e:
#         if isinstance(e, SanitizationError):
#             raise
#         raise SanitizationError(f"Error waiting for sanitization: {str(e)}") from e
