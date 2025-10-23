"""
Image Processing Service

High-level service layer for managing image processing workflows.
Coordinates between DBOS workflows, blob storage, and database operations.

Handles base64-encoded images from frontend and converts to binary for Azure Blob Storage.
"""

import base64
from typing import Dict, Any, Optional
from uuid import UUID
import hashlib
import io
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dbos import DBOS
from app.db.model import Picture, Folder, ImageProcessingState
from app.service.constants import ProcessingStatus
from app.exceptions import (
    ImageProcessingError,
    InvalidImageError,
    FolderNotFoundError,
)
from app.service.image_pipeline import process_image_pipeline
from app.service.image_processing_queue import image_processing_queue


class ImageProcessingService:
    """Service for managing image processing pipeline."""

    @staticmethod
    async def submit_image_for_processing(
        session: AsyncSession,
        image_data: str,  # Base64 encoded string from frontend
        filename: str,
        genus: str,
        species: str,
        org_name: str,
        user_id: UUID,
        folder_id: UUID,
        org_user_role_id: UUID,
        org_admin_role_id: UUID,
        image_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit an image for async processing.

        Returns immediately with UUID v7 while processing continues in background.
        Accepts base64 encoded images from frontend and converts to binary.

        Args:
            session: Database session
            image_data: Base64 encoded image string from frontend
            filename: Original filename
            genus: Genus name (normalized: a-z, dashes only)
            species: Species name (normalized: a-z, dashes only)
            org_name: Organization name (normalized: a-z, 0-9, dashes, max 10 chars)
            user_id: Submitting user UUID
            folder_id: Target folder UUID
            org_user_role_id: Organization user role UUID
            org_admin_role_id: Organization admin role UUID
            image_metadata: Optional metadata (dimensions, format, etc.)

        Returns:
            Dict with image_id, status, and workflow_id

        Raises:
            InvalidImageError: If image validation fails
            FolderNotFoundError: If folder doesn't exist
            ImageProcessingError: If submission fails
        """
        try:
            # Generate UUIDv7 immediately
            from uuid_extensions import uuid7

            image_id = uuid7()

            # Validate folder exists
            folder = await session.get(Folder, folder_id)
            if not folder or not folder.active:
                raise FolderNotFoundError(f"Folder {folder_id} not found")

            # Decode base64 image to bytes
            try:
                # Handle data URL format: "data:image/png;base64,..."
                if image_data.startswith("data:"):
                    # Strip data URL prefix
                    image_data = image_data.split(",", 1)[1]

                file_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise InvalidImageError(f"Invalid base64 image data: {str(e)}") from e

            # Validate image (basic checks before workflow)
            ImageProcessingService._validate_image_basic(file_bytes, filename)

            # Extract or validate metadata
            if not image_metadata:
                image_metadata = await ImageProcessingService._extract_image_metadata(
                    file_bytes, filename
                )

            # Create minimal Picture record
            picture = Picture(
                id=image_id,
                active=True,
                folder_id=folder_id,
                user_id=user_id,
                org_user_role_id=org_user_role_id,
                org_admin_role_id=org_admin_role_id,
                name=filename,
                width=image_metadata.get("width", 0),
                height=image_metadata.get("height", 0),
                format=image_metadata.get("format", "unknown"),
                size_on_disk_original=len(file_bytes),
                sha256=image_metadata.get("sha256", ""),
                date_created=datetime.utcnow(),
            )

            session.add(picture)

            # Create separate processing state record
            processing_state = ImageProcessingState(
                picture_id=image_id,
                status=ProcessingStatus.PENDING,
                created_at=datetime.utcnow(),
                progress_percentage=5,
            )

            session.add(processing_state)
            await session.commit()

            # Start workflow in background using DBOS queue
            # Queue handles rate limiting and concurrency
            workflow_handle = await image_processing_queue.enqueue_async(
                process_image_pipeline,
                image_id=image_id,
                file_bytes=file_bytes,
                filename=filename,
                genus=genus,
                species=species,
                org_name=org_name,
                user_id=user_id,
            )
            workflow_id = workflow_handle.get_workflow_id()

            # Update processing state with workflow ID
            processing_state.workflow_id = workflow_id
            await session.commit()

            DBOS.logger.info(
                f"Image {image_id} submitted for processing. Workflow: {workflow_id}"
            )

            return {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": ProcessingStatus.PENDING,
                "message": "Image submitted for processing",
            }

        except (InvalidImageError, FolderNotFoundError):
            raise
        except Exception as e:
            raise ImageProcessingError(f"Failed to submit image: {str(e)}") from e

    @staticmethod
    async def get_processing_status(
        session: AsyncSession,
        image_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get current processing status of an image.

        Retrieves workflow status from DBOS and combines with database state
        from the ImageProcessingState table.

        Args:
            session: Database session
            image_id: Image UUID

        Returns:
            Dict with status, progress, events, and results if complete

        Raises:
            ImageProcessingError: If status retrieval fails
        """
        try:
            # Get processing state from database
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            workflow_id = processing_state.workflow_id

            # Retrieve workflow handle from DBOS if workflow exists
            if workflow_id:
                try:
                    workflow_handle = await DBOS.retrieve_workflow_async(workflow_id)
                    workflow_status = await workflow_handle.get_status()
                    # Get all events published by workflow
                    _events = await DBOS.get_all_events_async(workflow_id)

                    # Add workflow status to response if available
                    if workflow_status and workflow_status.status == "SUCCESS":
                        # Could add workflow results here if needed
                        pass
                except Exception:
                    # Workflow may not exist yet or already completed
                    pass

            response = {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": processing_state.status,
                "progress_percentage": processing_state.progress_percentage,
                "stages": {
                    "upload": processing_state.uploaded_at is not None,
                    "defender_scan": processing_state.defender_scan_completed_at
                    is not None,
                    "sanitization": processing_state.sanitization_completed_at
                    is not None,
                },
                "timestamps": {
                    "created": processing_state.created_at.isoformat()
                    if processing_state.created_at
                    else None,
                    "uploaded": processing_state.uploaded_at.isoformat()
                    if processing_state.uploaded_at
                    else None,
                    "defender_scan_started": processing_state.defender_scan_started_at.isoformat()
                    if processing_state.defender_scan_started_at
                    else None,
                    "defender_scan_completed": processing_state.defender_scan_completed_at.isoformat()
                    if processing_state.defender_scan_completed_at
                    else None,
                    "sanitization_started": processing_state.sanitization_started_at.isoformat()
                    if processing_state.sanitization_started_at
                    else None,
                    "sanitization_completed": processing_state.sanitization_completed_at.isoformat()
                    if processing_state.sanitization_completed_at
                    else None,
                    "completed": processing_state.completed_at.isoformat()
                    if processing_state.completed_at
                    else None,
                    "failed": processing_state.failed_at.isoformat()
                    if processing_state.failed_at
                    else None,
                },
                "blob_urls": {
                    "original": processing_state.blob_url_original,
                    "sanitized": processing_state.blob_url_sanitized,
                },
                "retry_count": processing_state.retry_count,
            }

            # Add malware detection info if available
            if processing_state.defender_scan_result:
                response["defender_scan"] = {
                    "malware_detected": processing_state.malware_detected,
                    "scan_result": processing_state.defender_scan_result,
                }

            # Add error details if failed
            if processing_state.status == ProcessingStatus.FAILED:
                response["error_message"] = processing_state.error_message
                response["error_details"] = processing_state.error_details

            return response

        except Exception as e:
            raise ImageProcessingError(f"Failed to get status: {str(e)}") from e

    @staticmethod
    async def cancel_processing(
        session: AsyncSession,
        image_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Cancel an in-progress image processing workflow.

        Args:
            session: Database session
            image_id: Image UUID
            user_id: Requesting user UUID (for authorization)

        Returns:
            Dict with cancellation status

        Raises:
            ImageProcessingError: If cancellation fails
        """
        try:
            # Get processing state
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            workflow_id = processing_state.workflow_id

            # Cancel the workflow in DBOS
            if workflow_id:
                DBOS.cancel_workflow(workflow_id)

            # Update processing state
            processing_state.status = ProcessingStatus.CANCELLED

            await session.commit()

            DBOS.logger.info(
                f"Image processing workflow {workflow_id} cancelled by user {user_id}"
            )

            return {
                "image_id": str(image_id),
                "status": ProcessingStatus.CANCELLED,
                "message": "Processing cancelled successfully",
            }

        except Exception as e:
            raise ImageProcessingError(f"Failed to cancel processing: {str(e)}") from e

    @staticmethod
    async def retry_failed_processing(
        session: AsyncSession,
        image_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Retry a failed image processing workflow.

        Args:
            session: Database session
            image_id: Image UUID
            user_id: Requesting user UUID (for authorization)

        Returns:
            Dict with retry status

        Raises:
            ImageProcessingError: If retry fails
        """
        try:
            # Get processing state
            result = await session.execute(
                select(ImageProcessingState).where(
                    ImageProcessingState.picture_id == image_id
                )
            )
            processing_state = result.scalar_one_or_none()

            if not processing_state:
                raise ImageProcessingError(
                    f"No processing state found for image {image_id}"
                )

            if processing_state.status != ProcessingStatus.FAILED:
                raise ImageProcessingError(
                    f"Cannot retry processing in status {processing_state.status}"
                )

            workflow_id = processing_state.workflow_id

            # Resume the workflow from last completed step
            DBOS.resume_workflow(workflow_id)

            # Update processing state
            processing_state.retry_count += 1
            processing_state.last_retry_at = datetime.utcnow()
            processing_state.error_message = None
            processing_state.error_details = None

            await session.commit()

            DBOS.logger.info(
                f"Image processing workflow {workflow_id} resumed by user {user_id}"
            )

            return {
                "image_id": str(image_id),
                "workflow_id": workflow_id,
                "status": "retrying",
                "message": "Processing resumed successfully",
            }

        except Exception as e:
            raise ImageProcessingError(f"Failed to retry processing: {str(e)}") from e

    @staticmethod
    def _validate_image_basic(file_bytes: bytes, filename: str) -> None:
        """Perform basic image validation before workflow submission."""
        # Size validation
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_bytes) > max_size:
            raise InvalidImageError(f"Image size exceeds {max_size} bytes")

        if len(file_bytes) < 100:
            raise InvalidImageError("Image file too small")

        # Format validation (basic magic number check)
        valid_formats = {
            b"\xff\xd8\xff": "jpeg",
            b"\x89PNG\r\n\x1a\n": "png",
            b"GIF87a": "gif",
            b"GIF89a": "gif",
        }

        is_valid = any(file_bytes.startswith(magic) for magic in valid_formats.keys())
        if not is_valid:
            raise InvalidImageError("Unsupported image format")

    @staticmethod
    async def _extract_image_metadata(
        file_bytes: bytes, filename: str
    ) -> Dict[str, Any]:
        """Extract metadata from image bytes."""
        # Calculate SHA256
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Extract dimensions and format
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(file_bytes))
            width, height = image.size
            format_type = image.format.lower() if image.format else "unknown"
        except Exception:
            width, height, format_type = 0, 0, "unknown"

        return {
            "width": width,
            "height": height,
            "format": format_type,
            "sha256": sha256,
            "size": len(file_bytes),
        }

    @staticmethod
    def calculate_progress_percentage(status: ProcessingStatus) -> int:
        """
        Calculate progress percentage from processing status (MVP scope only).

        Used when updating ImageProcessingState.progress_percentage field.

        Note: Progress is for upload � scan � sanitize pipeline only.
        Inference progress is tracked separately.
        """
        progress_map = {
            ProcessingStatus.PENDING: 5,
            ProcessingStatus.UPLOADED: 25,
            ProcessingStatus.DEFENDER_SCANNING: 40,
            ProcessingStatus.DEFENDER_SCANNED: 50,
            ProcessingStatus.SANITIZING: 75,
            ProcessingStatus.SANITIZED: 90,
            ProcessingStatus.COMPLETED: 100,
            ProcessingStatus.FAILED: 0,
            ProcessingStatus.CANCELLED: 0,
        }
        return progress_map.get(status, 0)

    @staticmethod
    async def handle_sanitization_callback(
        image_id: str,
        status: str,
        sanitized_blob_url: Optional[str],
        error: Optional[str],
        function_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle sanitization completion callback from Azure Function.

        Validates the function key, validates the request, and sends a DBOS message
        to the waiting workflow using the DBOS messaging system (recv/send pattern).

        Args:
            image_id: UUID string of the image
            status: "success" or "failed"
            sanitized_blob_url: URL to sanitized blob (if successful)
            error: Error message (if failed)
            function_key: Azure Function authentication key (optional)

        Returns:
            Dict with confirmation message

        Raises:
            ValueError: If image_id is invalid UUID or function key is invalid
            ImageProcessingError: If message send fails or config error
        """
        from app.api.config import get_settings

        try:
            # Validate function key if provided
            if function_key is not None:
                settings = get_settings()
                expected_key = settings.azure_sanitization_function_key

                if not expected_key:
                    raise ImageProcessingError(
                        "Sanitization function key not configured"
                    )

                if function_key != expected_key:
                    DBOS.logger.warning(
                        f"Invalid function key in sanitization callback for image {image_id}"
                    )
                    raise ValueError("Invalid function key")

            # Validate image_id is valid UUID
            try:
                _image_uuid = UUID(image_id)
            except ValueError as e:
                raise ValueError(f"Invalid image_id format: {image_id}") from e

            # Prepare message for workflow
            message = {
                "status": status,
                "sanitized_blob_url": sanitized_blob_url,
                "error": error,
            }

            # Send message to waiting workflow using DBOS messaging
            # Topic format matches what workflow is listening on: "sanitization-{image_id}"
            topic = f"sanitization-{image_id}"

            await DBOS.send_async(
                destination_id=topic,
                message=message,
                topic=topic,
            )

            DBOS.logger.info(
                f"Sanitization callback processed for image {image_id}: {status}"
            )

            return {
                "message": "Callback received and workflow notified",
                "image_id": image_id,
                "status": status,
            }

        except ValueError:
            raise
        except ImageProcessingError:
            raise
        except Exception as e:
            DBOS.logger.error(
                f"Failed to process sanitization callback: {str(e)}",
                exc_info=True,
            )
            raise ImageProcessingError(
                f"Failed to process sanitization callback: {str(e)}"
            ) from e
