#!/usr/bin/env python3
"""
Script to upload frontend build files to Azure Blob Storage.

This script uploads the compiled frontend files from the dist/ folder
to Azure Blob Storage, preserving the directory structure and generating
a version file for cache invalidation.

Usage:
  # Basic usage (uses env vars from .env)
  cd backend
  uv run python -m app.scripts.push_frontend_to_blob

  # Custom source directory
  uv run python -m app.scripts.push_frontend_to_blob --source ../frontend/dist

  # Dry run (test without uploading)
  uv run python -m app.scripts.push_frontend_to_blob --dry-run

  # Custom container name (overrides env)
  uv run python -m app.scripts.push_frontend_to_blob --container my-frontend

  # Skip version file creation
  uv run python -m app.scripts.push_frontend_to_blob --skip-version

  # Custom source directory and container
  uv run python -m app.scripts.push_frontend_to_blob --source ../frontend/dist --container frontend
  
  # Clean and upload (delete everything first)
  uv run python -m app.scripts.push_frontend_to_blob --clean

  # Preview what would be deleted and uploaded
  uv run python -m app.scripts.push_frontend_to_blob --clean --dry-run

  # Clean upload with specific container
  uv run python -m app.scripts.push_frontend_to_blob --clean --container frontend
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
# import subprocess

# Add parent directory to path for imports
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.blob import create_blob_storage_client, BlobStorageInterface
from app.api.config import Settings
from app.service.logs import LogService


def extract_vite_hash_from_assets(source_dir: Path) -> Optional[str]:
    """
    Extract the Vite-generated content hash from the main JS file.

    Vite generates files like: index-BixMaUQK.js
    We extract the hash portion (BixMaUQK) to use as version.

    Args:
        source_dir: Frontend dist directory

    Returns:
        Hash string or None if not found
    """
    assets_dir = source_dir / "assets"
    if not assets_dir.exists():
        return None

    # Look for index-*.js files
    js_files = list(assets_dir.glob("index-*.js"))
    if not js_files:
        return None

    # Extract hash from first match (e.g., index-BixMaUQK.js -> BixMaUQK)
    filename = js_files[0].stem  # Gets "index-BixMaUQK"
    parts = filename.split("-")
    if len(parts) >= 2:
        return parts[-1]  # Return the last part (the hash)

    return None


def generate_version(source_dir: Path) -> str:
    """
    Generate a version string from Vite build hash.

    Uses the content hash from Vite's generated files (e.g., index-BixMaUQK.js -> BixMaUQK)
    Falls back to timestamp if hash cannot be extracted.

    Args:
        source_dir: Frontend dist directory

    Returns:
        Version string
    """
    vite_hash = extract_vite_hash_from_assets(source_dir)
    if vite_hash:
        return vite_hash
    else:
        # Fallback to timestamp if hash extraction fails
        return datetime.now().strftime("%Y%m%d-%H%M%S")


async def upload_file(
    storage_client: BlobStorageInterface,
    container_name: str,
    file_path: Path,
    blob_name: str,
    dry_run: bool = False,
    logger=None,
) -> bool:
    """
    Upload a single file to blob storage.

    Args:
        storage_client: Blob storage client
        container_name: Target container name
        file_path: Local file path
        blob_name: Blob name in storage (relative path)
        dry_run: If True, only simulate the upload
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        if logger:
            logger.info(
                "Would upload file (dry run)",
                blob_name=blob_name,
                file_size=file_path.stat().st_size,
            )
        return True

    try:
        with open(file_path, "rb") as file_data:
            await storage_client.upload_blob(
                container=container_name, name=blob_name, data=file_data, overwrite=True
            )
        if logger:
            logger.info(
                "Uploaded file", blob_name=blob_name, file_size=file_path.stat().st_size
            )
        return True
    except Exception as e:
        if logger:
            logger.error(
                "Failed to upload file",
                blob_name=blob_name,
                error=str(e),
                error_type=type(e).__name__,
            )
        return False


async def upload_directory(
    storage_client: BlobStorageInterface,
    source_dir: Path,
    container_name: str,
    dry_run: bool = False,
    logger=None,
) -> tuple[int, int]:
    """
    Recursively upload all files from a directory to blob storage.

    Args:
        storage_client: Blob storage client
        source_dir: Source directory path
        container_name: Target container name
        dry_run: If True, only simulate the upload
        logger: Logger instance

    Returns:
        Tuple of (successful_uploads, failed_uploads)
    """
    if not source_dir.exists():
        if logger:
            logger.error("Source directory does not exist", source_dir=str(source_dir))
        return 0, 0

    if not source_dir.is_dir():
        if logger:
            logger.error("Source path is not a directory", source_path=str(source_dir))
        return 0, 0

    # Get all files recursively
    files = list(source_dir.rglob("*"))
    files = [f for f in files if f.is_file()]

    if not files:
        if logger:
            logger.warning("No files found in source directory", source_dir=str(source_dir))
        return 0, 0

    if logger:
        logger.info(
            "Starting directory upload",
            file_count=len(files),
            source_dir=str(source_dir),
            container_name=container_name,
        )

    successful = 0
    failed = 0

    for file_path in files:
        # Get relative path from source_dir
        relative_path = file_path.relative_to(source_dir)
        # Convert to forward slashes for blob storage
        blob_name = str(relative_path).replace("\\", "/")

        success = await upload_file(
            storage_client, container_name, file_path, blob_name, dry_run, logger
        )

        if success:
            successful += 1
        else:
            failed += 1

    return successful, failed


async def upload_version_file(
    storage_client: BlobStorageInterface,
    container_name: str,
    version: str,
    version_filename: str = "version.txt",
    dry_run: bool = False,
    logger=None,
) -> bool:
    """
    Upload a version file to blob storage.

    Args:
        storage_client: Blob storage client
        container_name: Target container name
        version: Version string
        version_filename: Name of the version file
        dry_run: If True, only simulate the upload
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        if logger:
            logger.info(
                "Would create version file (dry run)",
                version_filename=version_filename,
                version=version,
            )
        return True

    try:
        await storage_client.upload_blob(
            container=container_name,
            name=version_filename,
            data=version.encode("utf-8"),
            overwrite=True,
        )
        if logger:
            logger.info(
                "Created version file", version_filename=version_filename, version=version
            )
        return True
    except Exception as e:
        if logger:
            logger.error(
                "Failed to create version file",
                error=str(e),
                error_type=type(e).__name__,
            )
        return False


async def ensure_container_exists(
    storage_client: BlobStorageInterface, container_name: str, dry_run: bool = False, logger=None
) -> bool:
    """
    Ensure the target container exists, create if it doesn't.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        dry_run: If True, only check existence
        logger: Logger instance

    Returns:
        True if container exists or was created, False otherwise
    """
    try:
        exists = await storage_client.container_exists(container_name)
        if exists:
            if logger:
                logger.info("Container exists", container_name=container_name)
            return True

        if dry_run:
            if logger:
                logger.warning(
                    "Container does not exist (would be created)",
                    container_name=container_name,
                )
            return True

        if logger:
            logger.info("Creating container", container_name=container_name)
        await storage_client.create_container(container_name)
        if logger:
            logger.info("Container created", container_name=container_name)
        return True
    except Exception as e:
        if logger:
            logger.error(
                "Failed to ensure container exists",
                container_name=container_name,
                error=str(e),
                error_type=type(e).__name__,
            )
        return False


async def get_current_version(
    storage_client: BlobStorageInterface, container_name: str, version_filename: str
) -> Optional[str]:
    """
    Get the current version from blob storage.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        version_filename: Name of the version file

    Returns:
        Current version string or None if not found
    """
    try:
        exists = await storage_client.blob_exists(container_name, version_filename)
        if not exists:
            return None

        content = await storage_client.download_blob(container_name, version_filename)
        return content.decode("utf-8").strip()
    except Exception:
        return None


async def clean_container(
    storage_client: BlobStorageInterface,
    container_name: str,
    dry_run: bool = False,
    logger=None,
) -> tuple[int, int]:
    """
    Delete all blobs in a container.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        dry_run: If True, only simulate the deletion
        logger: Logger instance

    Returns:
        Tuple of (successful_deletions, failed_deletions)
    """
    try:
        if logger:
            logger.info("Cleaning container", container_name=container_name)
        result = await storage_client.list_blobs(container_name)
        blobs = result.get("blobs", [])

        if not blobs:
            if logger:
                logger.info("Container is already empty", container_name=container_name)
            return 0, 0

        if logger:
            logger.info(
                "Found files to delete", blob_count=len(blobs), container_name=container_name
            )

        successful = 0
        failed = 0

        for blob in blobs:
            blob_name = blob.get("name")
            if not blob_name:
                continue

            if dry_run:
                if logger:
                    logger.info("Would delete blob (dry run)", blob_name=blob_name)
                successful += 1
            else:
                try:
                    await storage_client.delete_blob(container_name, blob_name)
                    if logger:
                        logger.info("Deleted blob", blob_name=blob_name)
                    successful += 1
                except Exception as e:
                    if logger:
                        logger.error(
                            "Failed to delete blob",
                            blob_name=blob_name,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                    failed += 1

        return successful, failed

    except Exception as e:
        if logger:
            logger.error(
                "Failed to clean container",
                container_name=container_name,
                error=str(e),
                error_type=type(e).__name__,
            )
        return 0, 0


async def verify_upload(
    storage_client: BlobStorageInterface,
    container_name: str,
    expected_count: int,
    logger=None,
) -> bool:
    """
    Verify that files were uploaded successfully.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        expected_count: Expected number of files
        logger: Logger instance

    Returns:
        True if verification passed, False otherwise
    """
    try:
        if logger:
            logger.info("Verifying upload", container_name=container_name)
        result = await storage_client.list_blobs(container_name)
        blobs = result.get("blobs", [])
        actual_count = len(blobs)

        if logger:
            logger.info(
                "Upload verification counts",
                expected_count=expected_count,
                actual_count=actual_count,
            )

        if actual_count >= expected_count:
            if logger:
                logger.info("Verification passed")
            return True
        else:
            if logger:
                logger.warning("File count mismatch during verification")
            return False
    except Exception as e:
        if logger:
            logger.error(
                "Verification failed", error=str(e), error_type=type(e).__name__
            )
        return False


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Upload frontend build files to Azure Blob Storage"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "frontend" / "dist",
        help="Source directory containing frontend build files (default: ../../frontend/dist)",
    )
    parser.add_argument(
        "--container",
        type=str,
        help="Target blob container name (default: from env FRONTEND_BLOB_CONTAINER)",
    )
    parser.add_argument(
        "--version-file",
        type=str,
        help="Version file name (default: from env FRONTEND_VERSION_FILE)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate upload without actually uploading files",
    )
    parser.add_argument(
        "--skip-version", action="store_true", help="Skip creating version file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force upload even if version hasn't changed",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete all existing files in the container before uploading",
    )

    args = parser.parse_args()

    # Setup console-only logging
    LogService.setup_console_only_logging("INFO")
    logger = LogService.get_logger()

    logger.info("Frontend to Blob Storage Upload Script started")

    # Load settings
    logger.info("Loading configuration")
    try:
        load_dotenv(".env.local")
        settings = Settings()
    except Exception as e:
        logger.error(
            "Failed to load settings",
            error=str(e),
            error_type=type(e).__name__,
            hint="Make sure environment variables are set (see .env.template)",
        )
        return 1

    # Determine container name
    container_name = args.container or settings.frontend_blob_container
    if not container_name:
        logger.error(
            "Container name not specified",
            hint="Use --container or set FRONTEND_BLOB_CONTAINER",
        )
        return 1

    # Determine version file name
    version_filename = (
        args.version_file or settings.frontend_version_file or "version.txt"
    )

    # Create blob storage client
    logger.info("Connecting to blob storage")
    try:
        blob_config = settings.blob_storage_config
        provider = blob_config.get("blob_storage_provider") or "azure"
        storage_client = create_blob_storage_client(provider, blob_config)
        logger.info("Connected to blob storage", provider=provider)
    except Exception as e:
        logger.error(
            "Failed to create storage client",
            error=str(e),
            error_type=type(e).__name__,
        )
        return 1

    # Ensure container exists
    if not await ensure_container_exists(storage_client, container_name, args.dry_run, logger):
        return 1

    # Generate version from Vite build hash
    version = generate_version(args.source)
    logger.info("Local build version generated", version=version)

    # Clean container if requested
    if args.clean:
        deleted_success, deleted_failed = await clean_container(
            storage_client, container_name, args.dry_run, logger
        )
        if deleted_failed > 0:
            logger.warning(
                "Some files failed to delete",
                failed_count=deleted_failed,
            )

    # Check current version in blob storage (unless forced or cleaning)
    if not args.force and not args.clean:
        current_version = await get_current_version(
            storage_client, container_name, version_filename
        )
        if current_version:
            logger.info("Remote version found", remote_version=current_version)

            if current_version == version:
                logger.info(
                    "Version already deployed - skipping upload",
                    version=version,
                    hint="No changes detected. Use --force to upload anyway.",
                )
                return 0
            else:
                logger.info(
                    "Version changed - uploading new version",
                    old_version=current_version,
                    new_version=version,
                )
        else:
            logger.info("No remote version found - performing initial upload")
    elif args.force:
        logger.warning("Force mode enabled - skipping version check")
    elif args.clean:
        logger.info("Clean mode enabled - uploading fresh files")

    # Upload directory
    successful, failed = await upload_directory(
        storage_client, args.source, container_name, args.dry_run, logger
    )

    # Upload version file
    if not args.skip_version:
        version_uploaded = await upload_version_file(
            storage_client, container_name, version, version_filename, args.dry_run, logger
        )
        if version_uploaded:
            successful += 1

    # Print summary
    logger.info(
        "Upload summary",
        successful_uploads=successful,
        failed_uploads=failed,
    )

    if not args.dry_run and failed == 0:
        # Verify upload
        await verify_upload(storage_client, container_name, successful, logger)

    if args.dry_run:
        logger.info("Dry run completed", hint="Use without --dry-run to actually upload")
        return 0

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
