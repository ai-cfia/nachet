"""
Frontend service module for serving SPA static files from Azure Blob Storage.
"""

import re
import mimetypes
from typing import Dict, Optional, Tuple
from fastapi import HTTPException
from app.blob.manager import blob_storage_manager
from app.blob.exceptions import BlobNotFoundError


class FrontendService:
    """
    Service class to handle frontend static file serving from blob storage.

    Implements in-memory caching with version-based invalidation.
    """

    # In-memory cache: {file_path: (content_bytes, content_type)}
    _cache: Dict[str, Tuple[bytes, str]] = {}
    _current_version: Optional[str] = None
    _container_name: str = "frontend"
    _version_file: str = "version.txt"

    @classmethod
    def configure(cls, container_name: str, version_file: str):
        """
        Configure the frontend service with container and version file names.

        Args:
            container_name: Blob storage container name for frontend files
            version_file: Path to version file in blob storage
        """
        cls._container_name = container_name
        cls._version_file = version_file

    @classmethod
    async def get_version(cls) -> str:
        """
        Retrieve the current frontend version from blob storage.

        Returns:
            Version string

        Raises:
            HTTPException: If version file cannot be read
        """
        try:
            storage = blob_storage_manager.get_client()
            content = await storage.download_blob(
                cls._container_name, cls._version_file
            )
            return content.decode("utf-8").strip()
        except BlobNotFoundError:
            # Version file doesn't exist yet, return default
            return "unknown"
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve frontend version: {str(e)}"
            )

    @classmethod
    async def check_and_update_version(cls) -> bool:
        """
        Check if version has changed and invalidate cache if needed.

        Returns:
            True if cache was invalidated, False otherwise
        """
        try:
            new_version = await cls.get_version()

            if cls._current_version is None:
                # First time initialization
                cls._current_version = new_version
                return False

            if new_version != cls._current_version:
                print(
                    f"🔄 Frontend version changed: {cls._current_version} → {new_version}"
                )
                cls.invalidate_cache()
                cls._current_version = new_version
                return True

            return False
        except Exception as e:
            print(f"⚠️  Failed to check frontend version: {e}")
            return False

    @classmethod
    def invalidate_cache(cls):
        """Clear the entire cache."""
        cls._cache.clear()
        print("🗑️  Frontend cache invalidated")

    @classmethod
    async def get_file(
        cls, file_path: str, csp_nonce: Optional[str] = None
    ) -> Tuple[bytes, str]:
        """
        Retrieve a file from blob storage with caching.

        Args:
            file_path: Path to file in blob storage (e.g., "index.html", "assets/index.js")
            csp_nonce: Optional CSP nonce to inject into HTML files

        Returns:
            Tuple of (file_content_bytes, content_type)

        Raises:
            HTTPException: If file cannot be retrieved or path is invalid
        """
        # Normalize path (remove leading slash if present)
        normalized_path = file_path.lstrip("/")

        # Security: Validate path to prevent directory traversal
        # Only allow files from the frontend/dist/ directory (blob container)
        if ".." in normalized_path or normalized_path.startswith("/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path: directory traversal not allowed",
            )

        # Check cache
        if normalized_path in cls._cache:
            content, content_type = cls._cache[normalized_path]

            # For HTML files, inject nonce if provided (don't cache nonce-injected version)
            if csp_nonce and content_type == "text/html":
                content = cls._inject_nonce_into_html(content, csp_nonce)

            return content, content_type

        try:
            # Fetch from blob storage
            storage = blob_storage_manager.get_client()
            content = await storage.download_blob(cls._container_name, normalized_path)

            # Determine content type
            content_type = cls._get_content_type(normalized_path)

            # Cache the result (without nonce)
            cls._cache[normalized_path] = (content, content_type)

            # For HTML files, inject nonce if provided
            if csp_nonce and content_type == "text/html":
                content = cls._inject_nonce_into_html(content, csp_nonce)

            return content, content_type

        except BlobNotFoundError:
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve file {file_path}: {str(e)}"
            )

    @staticmethod
    def _get_content_type(file_path: str) -> str:
        """
        Determine MIME type based on file extension.

        Args:
            file_path: File path

        Returns:
            MIME type string
        """
        content_type, _ = mimetypes.guess_type(file_path)

        if content_type is None:
            # Default fallback
            if file_path.endswith(".js"):
                return "application/javascript"
            elif file_path.endswith(".css"):
                return "text/css"
            elif file_path.endswith(".html"):
                return "text/html"
            elif file_path.endswith(".json"):
                return "application/json"
            elif file_path.endswith(".svg"):
                return "image/svg+xml"
            else:
                return "application/octet-stream"

        return content_type

    @staticmethod
    def _inject_nonce_into_html(content: bytes, nonce: str) -> bytes:
        """
        Inject CSP nonce into HTML content.

        Replaces __CSP_NONCE__ placeholder with actual nonce value and
        adds a meta tag + inline script for client-side nonce access.

        Args:
            content: HTML content as bytes
            nonce: CSP nonce value to inject

        Returns:
            Modified HTML content with nonce injected
        """
        html = content.decode("utf-8")

        # Replace Vite's CSP nonce placeholder with actual nonce
        html = html.replace("__CSP_NONCE__", nonce)

        # Remove Vite's incorrectly formatted meta tag (uses 'nonce=' instead of 'content=')
        # Vite generates: <meta property="csp-nonce" nonce="...">
        # We need: <meta property="csp-nonce" content="...">
        html = re.sub(r'<meta property="csp-nonce" nonce="[^"]*">', "", html)

        # CRITICAL: Meta tag must use 'content' attribute, not 'nonce'
        # styled-components/Emotion looks for: meta[property="csp-nonce"]
        meta_tag = f'<meta property="csp-nonce" content="{nonce}">'

        # Inline script to set __webpack_nonce__ for styled-components v6
        webpack_nonce_script = (
            f'<script nonce="{nonce}">window.__webpack_nonce__ = "{nonce}";</script>'
        )

        # Inject BEFORE first <script> tag to ensure availability
        if "<script" in html:
            first_script_pos = html.find("<script")
            injection = f"{meta_tag}\n  {webpack_nonce_script}\n  "
            html = html[:first_script_pos] + injection + html[first_script_pos:]
        elif "</head>" in html:
            injection = f"  {meta_tag}\n  {webpack_nonce_script}\n"
            html = html.replace("</head>", injection + "</head>")
        elif "</body>" in html:
            injection = f"{meta_tag}\n{webpack_nonce_script}\n"
            html = html.replace("</body>", injection + "</body>")
        else:
            html = html + meta_tag + webpack_nonce_script

        return html.encode("utf-8")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache stats
        """
        total_size = sum(len(content) for content, _ in cls._cache.values())
        return {
            "cached_files": len(cls._cache),
            "total_size_bytes": total_size,
            "current_version": cls._current_version,
        }
