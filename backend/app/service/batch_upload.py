"""
Batch Upload Service

This service handles batch upload operations for the Nachet system.
It reuses existing DBOS workflows for security scanning and sanitization.

Key Features:
- Database-backed session management with 24-hour TTL
- Maximum 1000 files per session
- Reuses existing image_processing_workflow for Defender scanning
- Maintains blob path consistency: {org_prefix}/{image_id}.png
- Returns workflow_id for async status polling
- Duplicate detection via SHA256 hash tracking
"""

from uuid import UUID, uuid4
from datetime import datetime, timezone
from uuid6 import uuid7
from loguru import logger

from app.service.auth import User
from app.service.rbac import RbacService
from app.service import DirectoryService, ImageService, SeedService
from app.service.inference.image_validation import preprocess_image
from app.service.inference.workflows import image_processing_workflow
from app.service.inference.queues import image_processing_queue
from app.service.inference.state_management import create_processing_state
from app.service.constants import ProcessingStatus
from app.model.batch_upload import BatchUploadImageRequest
from app.exceptions import InvalidImageError, SeedNotFoundError
from app.datastore.batch_upload_session import BatchUploadSessionDataService
from app.db.utils import sessionmanager


class BatchUploadService:
    """
    Batch upload service - reuses DBOS workflows for security scanning.

    Session Management:
    - Database-backed storage with 24-hour TTL
    - Maximum 1000 files per session
    - Sessions store: user_id, folder_id, file_count, uploaded_count, duplicate_count
    - Automatic expiration after 24 hours

    Security:
    - All images go through Defender scan + sanitization
    - User authorization checked per session and per upload
    - Blob paths use consistent org_prefix pattern
    - Duplicate detection via SHA256 hash

    Workflow:
    1. initialize_batch_session() - Validate folder exists, create DB session, return session_id
    2. upload_picture_batch() - Upload image, enqueue DBOS workflow, return workflow_id
    3. Frontend polls /workflow/{workflow_id}/status for each image
    """

    @classmethod
    async def initialize_batch_session(
        cls,
        user_id: UUID,
        folder_id: UUID,
        file_count: int,
    ) -> dict:
        """
        Initialize batch session with existing folder.

        This method:
        1. Validates user has org roles
        2. Validates folder exists and belongs to user's organization (org_user_role_id)
        3. Validates file_count <= 1000
        4. Creates database session with 24-hour TTL
        5. Returns session_id

        Args:
            user_id: UUID of the requesting user
            folder_id: UUID of existing folder (must exist and belong to user's org)
            file_count: Expected number of images to upload (max 1000)

        Returns:
            {
                session_id: str (UUID)
            }

        Raises:
            ValueError: If folder doesn't exist, doesn't belong to user's organization, or file_count > 1000
            Exception: If database operation fails
        """
        try:
            # Get user org roles
            user_org_roles = await RbacService.get_user_org_roles(user_id)
            logger.info(
                f"Initializing batch session for user {user_id} with folder {folder_id}, file_count={file_count}"
            )

            # Validate file_count
            if file_count > 1000:
                raise ValueError("file_count cannot exceed 1000")

            # Validate folder exists and belongs to user's organization
            await DirectoryService.check_folder_exists(
                folder_id=folder_id,
                user_role_id=user_org_roles.org_user_role_id,
            )

            logger.info(
                f"Validated folder {folder_id} belongs to organization (org_user_role_id: {user_org_roles.org_user_role_id})"
            )

            # Create database session
            session_id = uuid4()
            async with sessionmanager.get_session() as db_session:
                session_data_service = BatchUploadSessionDataService(db_session)
                await session_data_service.create_session(
                    session_id=session_id,
                    user_id=user_id,
                    folder_id=folder_id,
                    file_count=file_count,
                    ttl_hours=24,
                )
                await db_session.commit()

            logger.info(
                f"Batch session {session_id} created for user {user_id}, folder {folder_id}, "
                f"file_count={file_count}, expires in 24 hours"
            )

            return {
                "session_id": str(session_id),
            }

        except Exception as e:
            logger.error(f"Failed to initialize batch session: {str(e)}")
            raise

    @classmethod
    async def upload_picture_batch(
        cls,
        request: BatchUploadImageRequest,
        user: User,
    ) -> dict:
        """
        Upload single picture in batch - REUSES EXISTING WORKFLOW.

        This function:
        1. Validates session (DB lookup, expiration check, active check)
        2. Validates seed exists
        3. Preprocesses image (reuse existing validation function)
        4. Checks for duplicates (SHA256 hash)
        5. On duplicate: Increment counters, return error
        6. Creates Picture record with seed_id and sample_id as name
        7. Enqueues image_processing_workflow (Defender + sanitization)
        8. Creates processing state
        9. Updates session counters
        10. Marks session inactive if complete
        11. Returns workflow_id for async tracking

        Workflow Steps (background):
        - Upload to EXTERNAL storage (nachet-original)
        - Azure Defender malware scan
        - Sanitization function
        - Store in INTERNAL storage (nachet-sanitized)

        Args:
            request: BatchUploadImageRequest with image and metadata
            user: Authenticated user from JWT token

        Returns:
            {
                success: bool,
                picture_id: str | None,
                workflow_id: str | None,  # For polling /workflow/{id}/status
                error: str | None
            }

        Note:
            Frontend must poll GET /workflow/{workflow_id}/status to track progress.
            When status is "completed", the image is ready for use.
        """
        try:
            # 1. Validate session (DB lookup)
            async with sessionmanager.get_session() as db_session:
                session_data_service = BatchUploadSessionDataService(db_session)
                session = await session_data_service.get_by_id(UUID(request.session_id))

                if not session:
                    logger.warning(f"Invalid session_id: {request.session_id}")
                    return {
                        "success": False,
                        "picture_id": None,
                        "workflow_id": None,
                        "error": "Invalid session_id",
                    }

                # Validate user owns session
                if session.user_id != UUID(user.oid):
                    logger.warning(
                        f"User {user.oid} attempted to upload to session owned by {session.user_id}"
                    )
                    return {
                        "success": False,
                        "picture_id": None,
                        "workflow_id": None,
                        "error": "User does not own this session",
                    }

                # Validate session is active
                if not session.active:
                    logger.warning(f"Session {request.session_id} is inactive")
                    return {
                        "success": False,
                        "picture_id": None,
                        "workflow_id": None,
                        "error": "Session is inactive (completed or cancelled)",
                    }

                # Validate session not expired (24-hour TTL)
                if datetime.now(timezone.utc) > session.expires_at:
                    logger.warning(
                        f"Session {request.session_id} expired at {session.expires_at}"
                    )
                    return {
                        "success": False,
                        "picture_id": None,
                        "workflow_id": None,
                        "error": "Session expired (24-hour limit exceeded)",
                    }

                folder_id = session.folder_id

            # 2. Validate seed exists
            try:
                seed = await SeedService.get_by_id(
                    requester_id=UUID(user.oid), entity_id=UUID(request.seed_id)
                )
                logger.debug(
                    f"Validated seed {request.seed_id}: {seed.get('name_code', 'unknown')}"
                )
            except SeedNotFoundError:
                logger.warning(f"Seed not found: {request.seed_id}")
                return {
                    "success": False,
                    "picture_id": None,
                    "workflow_id": None,
                    "error": f"Seed not found: {request.seed_id}",
                }

            # 3. Get user org roles
            user_org_roles = await RbacService.get_user_org_roles(UUID(user.oid))
            logger.debug(f"Retrieved org roles for user {user.oid}")

            # 4. Preprocess image (REUSE existing validation function)
            info = await preprocess_image(
                image_base64=request.image,
                user_role_id=user_org_roles.org_user_role_id,
            )
            logger.debug(
                f"Image preprocessed: {info.width}x{info.height}, {info.size_bytes} bytes, {info.mime_type}"
            )

            # 5. Check for duplicate (SHA256 collision)
            if info.duplicate_uuid:
                logger.info(
                    f"Duplicate image detected (SHA256 collision): {info.duplicate_uuid}"
                )

                # Increment both uploaded_count and duplicate_count
                async with sessionmanager.get_session() as db_session:
                    session_data_service = BatchUploadSessionDataService(db_session)
                    await session_data_service.update_counts(
                        session_id=UUID(request.session_id),
                        uploaded_delta=1,
                        duplicate_delta=1,
                    )

                    # Check if session is complete and mark inactive
                    if await session_data_service.is_complete(UUID(request.session_id)):
                        await session_data_service.mark_inactive(
                            UUID(request.session_id)
                        )
                        logger.info(
                            f"Session {request.session_id} marked inactive (reached file_count limit)"
                        )

                    await db_session.commit()

                return {
                    "success": False,
                    "picture_id": str(info.duplicate_uuid),
                    "workflow_id": None,
                    "error": f"Duplicate image detected: {info.duplicate_uuid}",
                }

            # 6. Generate image_id (uuid7 for chronological ordering)
            image_id = uuid7()
            logger.info(
                f"Generated image_id {image_id} for batch upload in session {request.session_id}"
            )

            # 7. Construct blob URL (consistent with app: {org_prefix}/{image_id}.png)
            blob_url_original = f"{user_org_roles.org_prefix}/{image_id}.png"
            logger.debug(f"Blob URL: {blob_url_original}")

            # 8. Build description with batch metadata
            description = (
                f"Batch upload: Seed {seed.get('name_code', 'unknown')} | "
                f"Tray: {request.tray_code} | Sample: {request.sample_id}"
            )

            # 9. Create Picture record (REUSE ImageService)
            # Note: sample_id becomes picture.name, seed_id links to single_species_image
            await ImageService.create(
                requester_id=UUID(user.oid),
                id=image_id,
                active=True,
                folder_id=folder_id,
                org_user_role_id=user_org_roles.org_user_role_id,
                org_admin_role_id=user_org_roles.org_admin_role_id,
                name=request.sample_id,  # sample_id becomes picture name
                width=info.width,
                height=info.height,
                format=info.mime_type,
                size_on_disk_original=info.size_bytes,
                sha256=info.sha256_hash,
                blob_url_original=blob_url_original,
                magnification=request.magnification,
                device_model_id=UUID(request.device_model_id),
                device_lens_id=UUID(request.device_lens_id),
                description=description,
                single_species_image=UUID(
                    request.seed_id
                ),  # Link to seed for training data
            )
            logger.info(
                f"Picture record created for image_id {image_id} with seed {request.seed_id}"
            )

            # 10. Enqueue DBOS workflow (PROCESSING ONLY - no inference)
            # This workflow does: Upload → Defender scan → Sanitization
            parent_workflow_id = str(uuid4())  # Generate parent for state tracking
            workflow_handle = await image_processing_queue.enqueue_async(
                image_processing_workflow,  # Existing workflow!
                image_id=image_id,
                file_bytes=info.image_bytes,
                user_id=UUID(user.oid),
                org_prefix=user_org_roles.org_prefix,
                parent_workflow_id=parent_workflow_id,
            )
            workflow_id = workflow_handle.get_workflow_id()
            logger.info(
                f"DBOS workflow {workflow_id} enqueued for image_id {image_id} (parent: {parent_workflow_id})"
            )

            # 11. Create processing state for tracking
            await create_processing_state(
                workflow_id=workflow_id,
                picture_id=image_id,
                user_id=UUID(user.oid),
                org_user_role_id=user_org_roles.org_user_role_id,
                org_admin_role_id=user_org_roles.org_admin_role_id,
                status=ProcessingStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                progress_percentage=5,
            )
            logger.debug(f"Processing state created for workflow {workflow_id}")

            # 12. Update session counter and check completion
            async with sessionmanager.get_session() as db_session:
                session_data_service = BatchUploadSessionDataService(db_session)
                await session_data_service.update_counts(
                    session_id=UUID(request.session_id),
                    uploaded_delta=1,
                )

                # Refresh session to get updated counts
                updated_session = await session_data_service.get_by_id(
                    UUID(request.session_id)
                )
                if updated_session:
                    logger.info(
                        f"Session {request.session_id} progress: {updated_session.uploaded_count}/"
                        f"{updated_session.file_count} files (duplicates: {updated_session.duplicate_count})"
                    )

                    # Mark session inactive if reached file_count limit
                    if updated_session.uploaded_count >= updated_session.file_count:
                        await session_data_service.mark_inactive(
                            UUID(request.session_id)
                        )
                        logger.info(
                            f"Session {request.session_id} marked inactive (completed)"
                        )

                await db_session.commit()

            return {
                "success": True,
                "picture_id": str(image_id),
                "workflow_id": workflow_id,  # Frontend polls this!
                "error": None,
            }

        except InvalidImageError as e:
            logger.warning(f"Image validation error in batch upload: {str(e)}")
            return {
                "success": False,
                "picture_id": None,
                "workflow_id": None,
                "error": f"Image validation error: {str(e)}",
            }
        except SeedNotFoundError as e:
            logger.warning(f"Seed validation error in batch upload: {str(e)}")
            return {
                "success": False,
                "picture_id": None,
                "workflow_id": None,
                "error": f"Seed validation error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Unexpected error in batch upload: {str(e)}", exc_info=True)
            return {
                "success": False,
                "picture_id": None,
                "workflow_id": None,
                "error": str(e),
            }
