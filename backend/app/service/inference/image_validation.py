"""
Image Validation and Preprocessing Module

This module handles image validation, preprocessing, and duplicate detection.
Validates image type, size, dimensions, and checks for duplicates in database.
"""

import base64
import magic
import hashlib
from dataclasses import dataclass
from uuid import UUID
from beartype.typing import Optional

from app.service.constants import MAX_BASE64_LENGTH
from app.exceptions import InvalidImageError, ImageProcessingError
from app.db.utils import sessionmanager
from app.datastore.image import ImageDataService


@dataclass
class PreprocessedImageData:
    """
    Dataclass containing validated image data and metadata from preprocessing.

    Attributes:
        image_bytes: Decoded binary image data
        width: Image width in pixels
        height: Image height in pixels
        mime_type: MIME type of the image (e.g., "image/png")
        size_bytes: Size of the image in bytes
        sha256_hash: SHA-256 hash of the image bytes
        duplicate_uuid: UUID of existing image with same hash, if found
    """

    image_bytes: bytes
    width: int
    height: int
    mime_type: str
    size_bytes: int
    sha256_hash: str
    duplicate_uuid: Optional[UUID] = None


async def preprocess_image(
    image_base64: str, user_role_id: UUID
) -> PreprocessedImageData:
    """
    Validate the uploaded image file. Decode from base64 and check type, size, dimensions.
    Issue #229 #231

    Args:
        image_base64: Base64-encoded image data
        user_role_id: User's organization role ID for duplicate checking

    Returns:
        PreprocessedImageData: Dataclass containing validated image data and metadata

    Raises:
        ValueError: If validation fails
        ImageProcessingError: If hash computation or duplicate check fails
    """
    from app.service.logs import LogService
    import time

    logger = LogService.get_logger()

    logger.debug(
        "Starting image preprocessing",
        user_role_id=str(user_role_id),
        image_size_base64=len(image_base64),
    )

    start_time = time.time()

    try:
        # validate size (max 10MB)
        if len(image_base64) > MAX_BASE64_LENGTH:
            raise InvalidImageError("Image size exceeds maximum limit of 10MB")

        # Strip data URL prefix if present before further validation
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]

        # Check minimum size (but be lenient - very small images will fail dimension check anyway)
        if len(image_base64.strip()) < 100:
            raise InvalidImageError("Image size is too small or empty")

        # Decode base64 to binary
        decode_start = time.time()
        image_bytes = base64.b64decode(image_base64)
        decode_ms = (time.time() - decode_start) * 1000

        logger.debug(
            "Image decoded from base64",
            size_bytes=len(image_bytes),
            decode_duration_ms=round(decode_ms, 2),
        )

        # Validate image type using magic bytes (more reliable than mimetypes on base64)
        mime_type = magic.from_buffer(image_bytes, mime=True)
        logger.debug("Image MIME type detected", mime_type=mime_type)

        if not mime_type.startswith("image/png"):
            raise InvalidImageError("Uploaded file is not a valid PNG image")

        # validate dimensions
        header = image_bytes[:24]
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")

        logger.debug(
            "Image dimensions extracted",
            width=width,
            height=height,
        )

        if width < 384 or height < 384:
            raise InvalidImageError(
                "Image dimensions are too small, minimum is 384x384 pixels"
            )
        if width > 1920 and height > 1080:
            raise InvalidImageError(
                "Image dimensions are too large, maximum is 1920x1080 pixels"
            )

        # Compute hash of the image
        hash_start = time.time()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        hash_ms = (time.time() - hash_start) * 1000

        logger.debug(
            "SHA256 hash computed",
            sha256=image_hash[:16] + "...",  # Log first 16 chars for privacy
            hash_duration_ms=round(hash_ms, 2),
        )

        # Check if image with this hash already exists in database
        duplicate_check_start = time.time()
        async with sessionmanager.get_session() as session:
            image_service = ImageDataService(session)
            duplicate_uuid_result = await image_service.check_sha256_exists(
                image_hash, user_role_id
            )
            # Cast to standard UUID type for compatibility
            duplicate_uuid: Optional[UUID] = (
                UUID(str(duplicate_uuid_result)) if duplicate_uuid_result else None
            )

        duplicate_check_ms = (time.time() - duplicate_check_start) * 1000

        if duplicate_uuid:
            logger.debug(
                "Duplicate image detected",
                duplicate_picture_id=str(duplicate_uuid),
                duplicate_check_duration_ms=round(duplicate_check_ms, 2),
            )
        else:
            logger.debug(
                "No duplicate found",
                duplicate_check_duration_ms=round(duplicate_check_ms, 2),
            )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.debug(
            "Image preprocessing completed",
            width=width,
            height=height,
            size_bytes=len(image_bytes),
            mime_type=mime_type,
            is_duplicate=duplicate_uuid is not None,
            total_duration_ms=round(elapsed_ms, 2),
        )

        return PreprocessedImageData(
            image_bytes=image_bytes,
            width=width,
            height=height,
            mime_type=mime_type,
            size_bytes=len(image_bytes),
            sha256_hash=image_hash,
            duplicate_uuid=duplicate_uuid,
        )

    except (InvalidImageError, ImageProcessingError):
        # Re-raise validation errors without logging (already handled by exception message)
        raise
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            "Image preprocessing failed",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(elapsed_ms, 2),
        )
        raise ImageProcessingError(f"Failed to preprocess image: {str(e)}") from e
