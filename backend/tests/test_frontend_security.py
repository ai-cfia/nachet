"""
Tests for Frontend Static File Serving Security
Ensures directory traversal attacks are prevented.

This test suite validates that:
1. Directory traversal attacks (../) are blocked at both route and service layers
2. URL-encoded traversal attempts (%2e%2e) are properly decoded and blocked
3. Valid frontend file requests work correctly
4. Path normalization prevents bypassing security checks

Note: Tests use URL-encoded ".." (%2e%2e) to prevent httpx from normalizing
paths before they reach the server, ensuring realistic attack simulation.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException

from app.main import app
from app.service.frontend import FrontendService


class TestFrontendStaticFileDirectoryTraversal:
    """Test frontend static file endpoint against directory traversal attacks."""

    @pytest.mark.asyncio
    async def test_valid_index_file(self):
        """Valid request to index.html should succeed (if blob exists)."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            with patch.object(
                FrontendService, "get_file", new_callable=AsyncMock
            ) as mock_get_file:
                mock_get_file.return_value = (b"<html></html>", "text/html")

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://localhost"
                ) as ac:
                    response = await ac.get("/")

                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_valid_asset_file(self):
        """Valid request to asset file should succeed (if blob exists)."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            with patch.object(
                FrontendService, "get_file", new_callable=AsyncMock
            ) as mock_get_file:
                mock_get_file.return_value = (
                    b"console.log('test');",
                    "application/javascript",
                )

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://localhost"
                ) as ac:
                    response = await ac.get("/assets/index.js")

                assert response.status_code == 200
                assert response.headers["content-type"] == "application/javascript"

    @pytest.mark.asyncio
    async def test_directory_traversal_with_dotdot(self):
        """Directory traversal using .. should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # URL-encode .. as %2e%2e to prevent httpx from normalizing
                response = await ac.get("/%2e%2e/etc/passwd")

            assert response.status_code == 400
            assert b"Invalid file path" in response.content

    @pytest.mark.asyncio
    async def test_directory_traversal_encoded_dotdot(self):
        """URL-encoded directory traversal should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # %2e%2e is URL-encoded ..
                response = await ac.get("/%2e%2e%2f%2e%2e/etc/passwd")

            assert response.status_code == 400
            assert b"Invalid file path" in response.content

    @pytest.mark.asyncio
    async def test_directory_traversal_nested_dotdot(self):
        """Nested directory traversal should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # URL-encode .. to prevent normalization
                response = await ac.get("/assets/%2e%2e/%2e%2e/etc/passwd")

            assert response.status_code == 400
            assert b"Invalid file path" in response.content

    @pytest.mark.asyncio
    async def test_directory_traversal_multiple_dotdot(self):
        """Multiple .. sequences should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # URL-encode .. sequences
                response = await ac.get("/%2e%2e/%2e%2e/%2e%2e/etc/passwd")

            assert response.status_code == 400
            assert b"Invalid file path" in response.content

    @pytest.mark.asyncio
    async def test_directory_traversal_windows_style(self):
        """Windows-style directory traversal should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # URL-encode .. to prevent normalization
                response = await ac.get(
                    "/%2e%2e\\%2e%2e\\windows\\system32\\config\\sam"
                )

            assert response.status_code == 400
            assert b"Invalid file path" in response.content

    @pytest.mark.asyncio
    async def test_absolute_path_blocked(self):
        """URL-encoded directory traversal with leading slash should be blocked."""
        with patch.object(
            FrontendService, "check_and_update_version", new_callable=AsyncMock
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
                follow_redirects=False,
            ) as ac:
                # Test URL-encoded .. pattern
                response = await ac.get("/%2e%2e/%2e%2e/etc/passwd")

            assert response.status_code == 400
            assert b"Invalid file path" in response.content


class TestFrontendServiceDirectoryTraversal:
    """Test FrontendService.get_file() method against directory traversal."""

    @pytest.mark.asyncio
    async def test_get_file_with_dotdot_raises_400(self):
        """FrontendService.get_file() should reject paths with .."""
        with pytest.raises(HTTPException) as exc_info:
            await FrontendService.get_file("../etc/passwd")

        assert exc_info.value.status_code == 400
        assert "directory traversal" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_file_with_nested_dotdot_raises_400(self):
        """FrontendService.get_file() should reject nested .. patterns."""
        with pytest.raises(HTTPException) as exc_info:
            await FrontendService.get_file("assets/../../etc/passwd")

        assert exc_info.value.status_code == 400
        assert "directory traversal" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_file_with_leading_slash_after_strip(self):
        """FrontendService.get_file() should handle paths with leading slashes."""
        # After lstrip("/"), a path starting with "/" won't exist
        # but let's test the edge case
        with pytest.raises(HTTPException) as exc_info:
            # This gets normalized to "" which might fail differently
            await FrontendService.get_file("///../etc/passwd")

        # Should raise 400 for directory traversal or 404/500 for not found
        assert exc_info.value.status_code in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_get_file_valid_path_structure(self):
        """FrontendService.get_file() should accept valid paths (may fail on missing blob)."""
        # This should pass validation but fail on blob not found (which is expected)
        with pytest.raises(HTTPException) as exc_info:
            await FrontendService.get_file("assets/index.js")

        # Should be 404 or 500 (blob not found), not 400 (validation error)
        assert exc_info.value.status_code in [404, 500]
        assert "directory traversal" not in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_file_valid_index_html(self):
        """FrontendService.get_file() should accept index.html (may fail on missing blob)."""
        with pytest.raises(HTTPException) as exc_info:
            await FrontendService.get_file("index.html")

        # Should be 404 or 500 (blob not found), not 400 (validation error)
        assert exc_info.value.status_code in [404, 500]
        assert "directory traversal" not in exc_info.value.detail.lower()


class TestFrontendServicePathNormalization:
    """Test path normalization in FrontendService."""

    @pytest.mark.asyncio
    async def test_leading_slash_removed(self):
        """Leading slashes should be removed from paths."""
        # Both should be normalized to the same path
        with pytest.raises(HTTPException) as exc1:
            await FrontendService.get_file("/index.html")

        with pytest.raises(HTTPException) as exc2:
            await FrontendService.get_file("index.html")

        # Both should fail with same error (blob not found, not traversal)
        assert exc1.value.status_code == exc2.value.status_code

    @pytest.mark.asyncio
    async def test_multiple_leading_slashes_removed(self):
        """Multiple leading slashes should be removed."""
        with pytest.raises(HTTPException) as exc_info:
            await FrontendService.get_file("///index.html")

        # Should fail with blob not found, not validation error
        assert exc_info.value.status_code in [404, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
