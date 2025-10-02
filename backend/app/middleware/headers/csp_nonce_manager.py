"""
CSP Nonce Manager for generating cryptographically secure nonces.

This module provides nonce generation for Content Security Policy (CSP) headers
to enable strict CSP without 'unsafe-inline' directives.
"""

import secrets
from typing import Optional


class CSPNonceManager:
    """
    Manages Content Security Policy nonces for per-request CSP enforcement.

    Generates cryptographically secure random nonces that are unique per request
    to allow specific inline scripts and styles while blocking XSS attacks.
    """

    @staticmethod
    def generate_nonce(length: int = 32) -> str:
        """
        Generate a cryptographically secure random nonce.

        Args:
            length: Number of random bytes to generate (default: 32)
                   Result will be base64-encoded, so actual string length
                   will be ~1.33x this value

        Returns:
            Base64-encoded random string suitable for CSP nonce

        Example:
            >>> nonce = CSPNonceManager.generate_nonce()
            >>> len(nonce)
            43  # 32 bytes → 43 chars in base64
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def build_csp_header(nonce: str, include_report_uri: bool = False) -> str:
        """
        Build a Content Security Policy header with the given nonce.

        Args:
            nonce: The nonce value to include in the CSP header
            include_report_uri: Whether to include CSP violation reporting

        Returns:
            Complete CSP header string

        Example:
            >>> nonce = "abc123xyz"
            >>> header = CSPNonceManager.build_csp_header(nonce)
            >>> "nonce-abc123xyz" in header
            True
        """
        # Base CSP directives
        csp_parts = [
            f"default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            f"style-src 'self' 'nonce-{nonce}'",
            f"img-src 'self' data: blob:",
            f"font-src 'self' data:",
            f"connect-src 'self'",
            f"object-src 'none'",
            f"base-uri 'self'",
            f"form-action 'self'",
        ]

        # Optional CSP reporting
        if include_report_uri:
            csp_parts.append("report-uri /api/csp-report")

        return "; ".join(csp_parts) + ";"

    @staticmethod
    def extract_nonce_from_request(request) -> Optional[str]:
        """
        Extract CSP nonce from request state if it exists.

        Args:
            request: Starlette/FastAPI Request object

        Returns:
            Nonce string if found in request.state, None otherwise
        """
        return getattr(request.state, "csp_nonce", None)
