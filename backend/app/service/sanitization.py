"""Sanitization operations as DBOS steps."""

from uuid import UUID
import aiohttp

from dbos import DBOS
from app.service.constants import Bucket
from app.exceptions import SanitizationError


@DBOS.step(retries_allowed=True, max_attempts=3, interval_seconds=2.0)
async def trigger_sanitization_function(
    image_id: UUID,
    genus: str,
    species: str,
    blob_url_original: str,
) -> None:
    """
    Trigger Azure Function for image sanitization.

    The sanitizer will:
    1. Download image from nachet-original
    2. Extract RGB pixel data using Pillow
    3. Create new sanitized image
    4. Upload to nachet-sanitized with path: {genus}/{species}/{uuidv7}.png
    5. Call backend callback endpoint
    """
    from app.api.config import get_settings

    settings = get_settings()

    # Determine sanitized container based on environment
    sanitized_container = Bucket.get_sanitized_container(
        is_test=settings.is_test_environment
    )

    # Get Azure Function URL and key from settings
    azure_sanitization_function_url = settings.azure_sanitization_function_url
    azure_sanitization_function_key = settings.azure_sanitization_function_key
    backend_url = settings.backend_url

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                azure_sanitization_function_url,
                json={
                    "image_id": str(image_id),
                    "blob_url_original": blob_url_original,
                    "genus": genus,
                    "species": species,
                    "sanitized_container": sanitized_container,
                    "callback_url": f"{backend_url}/api/v1/callbacks/sanitization-complete",
                },
                headers={
                    "x-functions-key": azure_sanitization_function_key,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                result = await response.json()

                DBOS.logger.info(
                    f"Sanitization triggered for {image_id}: {result.get('message')}"
                )

        except Exception as e:
            raise SanitizationError(f"Failed to trigger sanitization: {str(e)}") from e


@DBOS.step(retries_allowed=True, max_attempts=1)
async def wait_for_sanitization_callback(
    image_id: UUID,
    timeout_sec: int = 600,
) -> str:
    """
    Wait for sanitization completion callback using DBOS recv.

    The sanitizer Azure Function will call the backend callback endpoint,
    which will send a message to this workflow using DBOS.send().

    Returns:
        Sanitized blob URL
    """
    try:
        # Wait for message from callback endpoint
        # Topic format: "sanitization-{image_id}"
        topic = f"sanitization-{image_id}"

        DBOS.logger.info(f"Waiting for sanitization callback on topic: {topic}")

        message = await DBOS.recv_async(topic=topic, timeout_seconds=timeout_sec)

        if not message:
            raise SanitizationError(f"Sanitization timed out after {timeout_sec}s")

        if message.get("status") == "success":
            sanitized_url = message["sanitized_blob_url"]
            DBOS.logger.info(f"Sanitization complete: {sanitized_url}")
            return sanitized_url
        elif message.get("status") == "failed":
            error = message.get("error", "Unknown error")
            raise SanitizationError(f"Sanitization failed: {error}")
        else:
            raise SanitizationError(
                f"Invalid sanitization status: {message.get('status')}"
            )

    except Exception as e:
        if isinstance(e, SanitizationError):
            raise
        raise SanitizationError(f"Error waiting for sanitization: {str(e)}") from e
