from typing import Any
from uuid import UUID

from beartype.typing import Optional
from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from starlette.requests import HTTPConnection
from app.api.config import Settings, get_settings
from app.service.auth.auth import SingleTenantAzureAuthorizationCodeBearer
from app.service.auth.config import (
    AuthProvider,
    AzureAuthConfig,
    BackendAuthConfig,
    OidcAuthConfig,
)
from app.service.auth.exceptions import bearer_authenticate_headers
from app.service.auth.oidc_discovery import (
    OidcDiscoveryClient,
    OidcDiscoveryError,
)
from app.service.auth.oidc_token_verifier import OidcTokenValidationError
from app.service.auth.user import User

class JWTAuthenticator:
    """JWT Authentication handler for Nachet API"""

    def __init__(self, settings: Settings | None = None):
        app_settings = settings if settings is not None else get_settings()
        self._config = BackendAuthConfig.from_settings(app_settings)
        self._azure_auth_scheme: Optional[SingleTenantAzureAuthorizationCodeBearer] = (
            None
        )
        self._oidc_discovery_client: OidcDiscoveryClient | None = None

    def _get_azure_auth_scheme(self) -> SingleTenantAzureAuthorizationCodeBearer:
        """Initialize and return the Azure AD auth scheme"""
        if self._azure_auth_scheme is None:
            azure_config = self._get_azure_config()
            client_id = azure_config.client_id
            tenant_id = azure_config.tenant_id

            if not client_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Azure AD configuration missing. Please set AZURE_CLIENT_ID and AZURE_TENANT_ID "
                    "in environment variables or app settings.",
                )

            self._azure_auth_scheme = SingleTenantAzureAuthorizationCodeBearer(
                app_client_id=client_id,
                tenant_id=tenant_id,
                auto_error=True,
                allow_guest_users=True,  # Allow guest users (external accounts)
            )

        return self._azure_auth_scheme

    def _get_azure_config(self) -> AzureAuthConfig:
        azure_config = self._config.azure
        if azure_config is None:
            raise RuntimeError("Azure authentication is not configured")
        return azure_config

    def _get_oidc_discovery_client(self) -> OidcDiscoveryClient:
        if self._oidc_discovery_client is None:
            self._oidc_discovery_client = OidcDiscoveryClient(
                self._get_oidc_config().discovery
            )

        return self._oidc_discovery_client

    def _get_oidc_config(self) -> OidcAuthConfig:
        oidc_config = self._config.oidc
        if oidc_config is None:
            raise RuntimeError("OIDC authentication is not configured")
        return oidc_config

    async def __call__(
        self, request: HTTPConnection, security_scopes: SecurityScopes
    ) -> User:
        """
        Make this callable as a FastAPI dependency.

        Validates the JWT token and ensures the user has a valid oid (object ID).

        Raises:
            HTTPException: If user oid is missing or invalid
        """
        # Protected routes share this provider-selection point.
        match self._config.provider:
            case AuthProvider.AZURE:
                user = await self._authenticate_with_azure(request, security_scopes)
            case AuthProvider.OIDC:
                user = await self._authenticate_with_oidc(request, security_scopes)
            case _:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unsupported auth provider configured",
                )

        return self._validate_current_user(user)

    async def _authenticate_with_azure(
        self,
        request: HTTPConnection,
        security_scopes: SecurityScopes,
    ) -> User | None:
        auth_scheme = self._get_azure_auth_scheme()
        return await auth_scheme(request, security_scopes)

    async def _authenticate_with_oidc(
        self,
        request: HTTPConnection,
        security_scopes: SecurityScopes,
    ) -> User:
        access_token = self._extract_bearer_token(request)
        claims = await self._verify_oidc_access_token(access_token)

        self._validate_oidc_scopes(claims, security_scopes)
        user = self._build_oidc_user(claims, access_token)
        request.state.user = user
        return user

    async def _verify_oidc_access_token(self, access_token: str) -> dict[str, Any]:
        oidc_client = self._get_oidc_discovery_client()
        try:
            return await oidc_client.verify(access_token)
        except OidcTokenValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to validate token",
                headers=bearer_authenticate_headers("invalid_token"),
            ) from error
        except OidcDiscoveryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC provider is unavailable",
            ) from error

    def _validate_current_user(self, user: User | None) -> User:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers=bearer_authenticate_headers(),
            )

        self._validate_user_id(user.oid)
        return user

    def _validate_user_id(self, user_id: str | None) -> None:
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID (oid) is missing from token",
                headers=bearer_authenticate_headers("invalid_token"),
            )

        try:
            UUID(user_id)
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format",
                headers=bearer_authenticate_headers("invalid_token"),
            ) from e

    def _extract_bearer_token(self, request: HTTPConnection) -> str:
        authorization = request.headers.get("Authorization")
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token is required",
                headers=bearer_authenticate_headers(),
            )

        # Authorization must contain a Bearer scheme followed by one token.
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token is required",
                headers=bearer_authenticate_headers(),
            )

        return parts[1]

    def _validate_oidc_scopes(
        self,
        claims: dict[str, Any],
        security_scopes: SecurityScopes,
    ) -> None:
        required_scopes = security_scopes.scopes
        if not required_scopes:
            return

        token_scopes = self._extract_token_scopes(claims)
        missing_scopes = self._get_missing_required_scopes(
            required_scopes,
            token_scopes,
        )
        if not missing_scopes:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required scope missing",
            headers=bearer_authenticate_headers(
                "insufficient_scope",
                scopes=missing_scopes,
            ),
        )

    def _get_missing_required_scopes(
        self,
        required_scopes: list[str],
        token_scopes: set[str],
    ) -> list[str]:
        return [scope for scope in required_scopes if scope not in token_scopes]

    def _extract_token_scopes(self, claims: dict[str, Any]) -> set[str]:
        scp_scopes = self._scopes_from_claim_value(claims.get("scp"))
        scope_scopes = self._scopes_from_claim_value(claims.get("scope"))
        return scp_scopes | scope_scopes

    def _scopes_from_claim_value(self, raw_scope_claim: object) -> set[str]:
        if isinstance(raw_scope_claim, str):
            return set(raw_scope_claim.split())

        if not isinstance(raw_scope_claim, list):
            return set()

        scopes: set[str] = set()
        for scope in raw_scope_claim:
            if isinstance(scope, str):
                scopes.add(scope)

        return scopes

    def _build_oidc_user(self, claims: dict[str, Any], access_token: str) -> User:
        oidc_config = self._get_oidc_config()
        identity_claim_name = oidc_config.user_id_claim
        user_id = self._get_string_claim(claims, identity_claim_name)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"OIDC identity claim '{identity_claim_name}' is missing from token",
                headers=bearer_authenticate_headers("invalid_token"),
            )

        self._validate_user_id(user_id)
        preferred_username = self._get_oidc_display_username(claims)
        email = self._get_string_claim(claims, oidc_config.email_claim)
        user_data = dict(claims)
        user_data["oid"] = user_id
        if preferred_username is not None:
            user_data["preferred_username"] = preferred_username
        if email is not None:
            user_data["email"] = email

        # Nachet owns these runtime fields, so provider claims cannot override
        # them. OIDC has no common guest claim, so generic users get a guest marker.
        user_data.update(
            claims=claims,
            access_token=access_token,
            is_guest=True,
        )

        return User(**user_data)

    def _get_oidc_display_username(self, claims: dict[str, Any]) -> str | None:
        oidc_config = self._get_oidc_config()
        username_claim_candidates = (
            oidc_config.username_claim,
            "preferred_username",
            "email",
            "sub",
        )
        for claim_name in username_claim_candidates:
            username = self._get_string_claim(claims, claim_name)
            if username is not None:
                return username

        return None

    def _get_string_claim(self, claims: dict[str, Any], claim_name: str) -> str | None:
        claim_value = claims.get(claim_name)
        if not isinstance(claim_value, str):
            return None

        stripped_claim_value = claim_value.strip()
        return stripped_claim_value or None


# Global authenticator instance
jwt_authenticator = JWTAuthenticator()

# Dependency for protected routes - this is now callable as a FastAPI dependency
get_current_user = jwt_authenticator
