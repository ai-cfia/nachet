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
) -> bool:
    """
    Upload a single file to blob storage.

    Args:
        storage_client: Blob storage client
        container_name: Target container name
        file_path: Local file path
        blob_name: Blob name in storage (relative path)
        dry_run: If True, only simulate the upload

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(
            f"  [DRY RUN] Would upload: {blob_name} ({file_path.stat().st_size} bytes)"
        )
        return True

    try:
        with open(file_path, "rb") as file_data:
            await storage_client.upload_blob(
                container=container_name, name=blob_name, data=file_data, overwrite=True
            )
        print(f"  [OK] Uploaded: {blob_name} ({file_path.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to upload {blob_name}: {e}")
        return False


async def upload_directory(
    storage_client: BlobStorageInterface,
    source_dir: Path,
    container_name: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Recursively upload all files from a directory to blob storage.

    Args:
        storage_client: Blob storage client
        source_dir: Source directory path
        container_name: Target container name
        dry_run: If True, only simulate the upload

    Returns:
        Tuple of (successful_uploads, failed_uploads)
    """
    if not source_dir.exists():
        print(f"ERROR: Source directory does not exist: {source_dir}")
        return 0, 0

    if not source_dir.is_dir():
        print(f"ERROR: Source path is not a directory: {source_dir}")
        return 0, 0

    # Get all files recursively
    files = list(source_dir.rglob("*"))
    files = [f for f in files if f.is_file()]

    if not files:
        print(f"WARNING: No files found in {source_dir}")
        return 0, 0

    print(f"\nFound {len(files)} files to upload from {source_dir}")
    print(f"Target container: {container_name}\n")

    successful = 0
    failed = 0

    for file_path in files:
        # Get relative path from source_dir
        relative_path = file_path.relative_to(source_dir)
        # Convert to forward slashes for blob storage
        blob_name = str(relative_path).replace("\\", "/")

        success = await upload_file(
            storage_client, container_name, file_path, blob_name, dry_run
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
) -> bool:
    """
    Upload a version file to blob storage.

    Args:
        storage_client: Blob storage client
        container_name: Target container name
        version: Version string
        version_filename: Name of the version file
        dry_run: If True, only simulate the upload

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(
            f"\n  [DRY RUN] Would create version file: {version_filename} with content: {version}"
        )
        return True

    try:
        await storage_client.upload_blob(
            container=container_name,
            name=version_filename,
            data=version.encode("utf-8"),
            overwrite=True,
        )
        print(f"\n  [OK] Created version file: {version_filename} -> {version}")
        return True
    except Exception as e:
        print(f"\n  [FAIL] Failed to create version file: {e}")
        return False


async def ensure_container_exists(
    storage_client: BlobStorageInterface, container_name: str, dry_run: bool = False
) -> bool:
    """
    Ensure the target container exists, create if it doesn't.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        dry_run: If True, only check existence

    Returns:
        True if container exists or was created, False otherwise
    """
    try:
        exists = await storage_client.container_exists(container_name)
        if exists:
            print(f"[OK] Container '{container_name}' exists")
            return True

        if dry_run:
            print(f"WARNING: Container '{container_name}' does not exist (would be created)")
            return True

        print(f"Creating container '{container_name}'...")
        await storage_client.create_container(container_name)
        print(f"[OK] Container '{container_name}' created")
        return True
    except Exception as e:
        print(f"ERROR: Failed to ensure container exists: {e}")
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
    dry_run: bool = False
) -> tuple[int, int]:
    """
    Delete all blobs in a container.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        dry_run: If True, only simulate the deletion

    Returns:
        Tuple of (successful_deletions, failed_deletions)
    """
    try:
        print("\nCleaning container...")
        result = await storage_client.list_blobs(container_name)
        blobs = result.get("blobs", [])

        if not blobs:
            print("  INFO: Container is already empty")
            return 0, 0

        print(f"  Found {len(blobs)} files to delete")

        successful = 0
        failed = 0

        for blob in blobs:
            blob_name = blob.get("name")
            if not blob_name:
                continue

            if dry_run:
                print(f"  [DRY RUN] Would delete: {blob_name}")
                successful += 1
            else:
                try:
                    await storage_client.delete_blob(container_name, blob_name)
                    print(f"  [OK] Deleted: {blob_name}")
                    successful += 1
                except Exception as e:
                    print(f"  [FAIL] Failed to delete {blob_name}: {e}")
                    failed += 1

        return successful, failed

    except Exception as e:
        print(f"  ERROR: Failed to clean container: {e}")
        return 0, 0


async def verify_upload(
    storage_client: BlobStorageInterface, container_name: str, expected_count: int
) -> bool:
    """
    Verify that files were uploaded successfully.

    Args:
        storage_client: Blob storage client
        container_name: Container name
        expected_count: Expected number of files

    Returns:
        True if verification passed, False otherwise
    """
    try:
        print("\nVerifying upload...")
        result = await storage_client.list_blobs(container_name)
        blobs = result.get("blobs", [])
        actual_count = len(blobs)

        print(f"  Expected files: {expected_count}")
        print(f"  Actual files: {actual_count}")

        if actual_count >= expected_count:
            print("  [OK] Verification passed")
            return True
        else:
            print("  WARNING: File count mismatch")
            return False
    except Exception as e:
        print(f"  [FAIL] Verification failed: {e}")
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

    print("=" * 60)
    print("Frontend to Blob Storage Upload Script")
    print("=" * 60)

    # Load settings
    print("\nLoading configuration...")
    try:
        load_dotenv(".env.local")
        settings = Settings()
    except Exception as e:
        print(f"ERROR: Failed to load settings: {e}")
        print("HINT: Make sure environment variables are set (see .env.template)")
        return 1

    # Determine container name
    container_name = args.container or settings.frontend_blob_container
    if not container_name:
        print(
            "ERROR: Container name not specified. Use --container or set FRONTEND_BLOB_CONTAINER"
        )
        return 1

    # Determine version file name
    version_filename = (
        args.version_file or settings.frontend_version_file or "version.txt"
    )

    # Create blob storage client
    print("Connecting to blob storage...")
    try:
        blob_config = settings.blob_storage_config
        provider = blob_config.get("blob_storage_provider") or "azure"
        storage_client = create_blob_storage_client(provider, blob_config)
        print(f"[OK] Connected to {provider} blob storage")
    except Exception as e:
        print(f"ERROR: Failed to create storage client: {e}")
        return 1

    # Ensure container exists
    if not await ensure_container_exists(storage_client, container_name, args.dry_run):
        return 1

    # Generate version from Vite build hash
    version = generate_version(args.source)
    print(f"Local build version: {version}")

    # Clean container if requested
    if args.clean:
        deleted_success, deleted_failed = await clean_container(
            storage_client, container_name, args.dry_run
        )
        if deleted_failed > 0:
            print(f"WARNING: {deleted_failed} files failed to delete")

    # Check current version in blob storage (unless forced or cleaning)
    if not args.force and not args.clean:
        current_version = await get_current_version(
            storage_client, container_name, version_filename
        )
        if current_version:
            print(f"Remote version: {current_version}")

            if current_version == version:
                print(
                    f"\n[OK] Version {version} already deployed - skipping upload to save costs"
                )
                print("HINT: No changes detected. Use --force to upload anyway.")
                return 0
            else:
                print(f"\nVersion changed: {current_version} -> {version}")
                print("Uploading new version...")
        else:
            print("No remote version found - performing initial upload")
    elif args.force:
        print("WARNING: Force mode enabled - skipping version check")
    elif args.clean:
        print("Clean mode enabled - uploading fresh files")

    # Upload directory
    successful, failed = await upload_directory(
        storage_client, args.source, container_name, args.dry_run
    )

    # Upload version file
    if not args.skip_version:
        version_uploaded = await upload_version_file(
            storage_client, container_name, version, version_filename, args.dry_run
        )
        if version_uploaded:
            successful += 1

    # Print summary
    print("\n" + "=" * 60)
    print("Upload Summary")
    print("=" * 60)
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if not args.dry_run and failed == 0:
        # Verify upload
        await verify_upload(storage_client, container_name, successful)

    print("=" * 60)

    if args.dry_run:
        print("\nHINT: This was a dry run. Use without --dry-run to actually upload.")
        return 0

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
