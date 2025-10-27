import os
from uuid import UUID
from beartype.typing import Optional
from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from starlette.requests import HTTPConnection
from app.service.auth.auth import SingleTenantAzureAuthorizationCodeBearer
from app.service.auth.user import User
from app.api.config import get_settings


class JWTAuthenticator:
    """JWT Authentication handler for Nachet API"""

    def __init__(self):
        self._auth_scheme: Optional[SingleTenantAzureAuthorizationCodeBearer] = None

    def _get_auth_scheme(self) -> SingleTenantAzureAuthorizationCodeBearer:
        """Initialize and return the Azure AD auth scheme"""
        if self._auth_scheme is None:
            settings = get_settings()

            # Get Azure AD configuration from environment or settings
            client_id = settings.azure_client_id or os.getenv("AZURE_CLIENT_ID")
            tenant_id = settings.azure_tenant_id or os.getenv("AZURE_TENANT_ID")

            if not client_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Azure AD configuration missing. Please set AZURE_CLIENT_ID and AZURE_TENANT_ID "
                    "in environment variables or app settings.",
                )

            self._auth_scheme = SingleTenantAzureAuthorizationCodeBearer(
                app_client_id=client_id,
                tenant_id=tenant_id,
                auto_error=True,
                allow_guest_users=True,  # Allow guest users (external accounts)
            )

        return self._auth_scheme

    async def __call__(
        self, request: HTTPConnection, security_scopes: SecurityScopes
    ) -> User:
        """
        Make this callable as a FastAPI dependency.

        Validates the JWT token and ensures the user has a valid oid (object ID).

        Raises:
            HTTPException: If user oid is missing or invalid
        """
        auth_scheme = self._get_auth_scheme()
        user = await auth_scheme(request, security_scopes)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Validate that oid exists and is a valid UUID
        if not user.oid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID (oid) is missing from token",
            )

        try:
            # Validate that oid is a valid UUID format
            UUID(user.oid)
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid user ID format: {user.oid}",
            ) from e

        return user


# Global authenticator instance
jwt_authenticator = JWTAuthenticator()

# Dependency for protected routes - this is now callable as a FastAPI dependency
get_current_user = jwt_authenticator
