"""
CSP Nonce Manager for generating cryptographically secure nonces.

This module provides nonce generation for Content Security Policy (CSP) headers
to enable strict CSP without 'unsafe-inline' directives.
"""

import secrets
from beartype.typing import Optional
from starlette.requests import Request


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
    def build_csp_header(
        nonce: str,
        include_report_uri: bool = False,
        auth_provider_origin: str | None = None,
    ) -> str:
        """
        Build a Content Security Policy header with the given nonce.

        Args:
            nonce: The nonce value to include in the CSP header
            include_report_uri: Whether to include CSP violation reporting
            auth_provider_origin: Trusted origin used by browser authentication

        Returns:
            Complete CSP header string

        Example:
            >>> nonce = "abc123xyz"
            >>> header = CSPNonceManager.build_csp_header(nonce)
            >>> "nonce-abc123xyz" in header
            True
        """
        # OIDC uses direct requests and a hidden iframe for session checks. Both
        # browser paths are limited to the validated provider origin.
        provider_origin = f" {auth_provider_origin}" if auth_provider_origin else ""

        # Base CSP directives
        csp_parts = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://login.microsoftonline.com https://*.msauth.net https://*.msftauth.net https://*.msftauthimages.net https://*.msauthimages.net https://*.msidentity.com",
            f"style-src 'self' 'nonce-{nonce}'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "connect-src 'self' https://login.microsoftonline.com https://*.msauth.net https://*.msftauth.net https://*.msftauthimages.net https://*.msauthimages.net https://*.msidentity.com"
            f"{provider_origin}",
            "frame-src 'self' https://*.microsoftonline.com https://*.msauth.net https://*.msftauth.net https://*.msftauthimages.net https://*.msauthimages.net https://*.msidentity.com"
            f"{provider_origin}",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'self' https://login.microsoft.com https://login.microsoftonline.com",
            # "frame-ancestors 'none'",
        ]

        # Optional CSP reporting
        if include_report_uri:
            csp_parts.append("report-uri /api/csp-report")

        return "; ".join(csp_parts) + ";"

    @staticmethod
    def extract_nonce_from_request(request: Request) -> Optional[str]:
        """
        Extract CSP nonce from request state if it exists.

        Args:
            request: Starlette/FastAPI Request object

        Returns:
            Nonce string if found in request.state, None otherwise
        """
        return getattr(request.state, "csp_nonce", None)
