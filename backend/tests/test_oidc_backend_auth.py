from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from starlette.requests import Request

import app.api.config as config_module
from app.service.auth.config import AuthProvider, BackendAuthConfig
from app.service.auth.jwt_auth import JWTAuthenticator
from app.service.auth.oidc_discovery import OidcDiscoveryError
from app.service.auth.oidc_token_verifier import OidcTokenValidationError
from app.service.auth.user import User


ISSUER = "https://idp.example/realms/nachet"
AUDIENCE = "nachet-api"
ACCESS_TOKEN = "header.payload.signature"
REQUIRED_SCOPE = "access_as_user"


class FakeOidcDiscoveryClient:
    def __init__(
        self,
        claims: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.claims = claims or {}
        self.error = error
        self.verified_tokens: list[str] = []

    async def verify(self, access_token: str) -> dict[str, Any]:
        self.verified_tokens.append(access_token)
        if self.error is not None:
            raise self.error
        return self.claims


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "_settings", None)


def set_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> None:
    settings = config_module.Settings(**overrides)
    monkeypatch.setattr(config_module, "_settings", settings)


def set_oidc_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> None:
    oidc_settings: dict[str, Any] = {
        "auth_provider": "oidc",
        "oidc_issuer": ISSUER,
        "oidc_audience": AUDIENCE,
    }
    oidc_settings.update(overrides)
    set_settings(monkeypatch, **oidc_settings)


def create_auth_config(**overrides: Any) -> BackendAuthConfig:
    settings = config_module.Settings.model_validate(overrides)
    return BackendAuthConfig.from_settings(settings)


def no_security_scopes() -> SecurityScopes:
    return SecurityScopes(scopes=[])


def required_security_scopes() -> SecurityScopes:
    return SecurityScopes(scopes=[REQUIRED_SCOPE])


def create_request(authorization: str | None = f"Bearer {ACCESS_TOKEN}") -> Request:
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": headers,
        }
    )


def create_azure_user(oid: str | None = None) -> User:
    user_oid = oid or str(uuid4())
    claims: dict[str, Any] = {
        "aud": "azure-api-client-id",
        "iss": "https://login.microsoftonline.com/tenant/v2.0",
        "iat": 1,
        "nbf": 1,
        "exp": 4_102_444_800,
        "sub": "azure-subject",
        "oid": user_oid,
        "ver": "2.0",
        "scp": REQUIRED_SCOPE,
    }
    return User(**claims, claims=claims, access_token=ACCESS_TOKEN, is_guest=False)


def create_oidc_claims(**overrides: Any) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": 1,
        "nbf": 1,
        "exp": 4_102_444_800,
        "sub": str(uuid4()),
        "scp": REQUIRED_SCOPE,
        "preferred_username": "oidc.user@example.com",
        "email": "oidc.user@example.com",
        "name": "OIDC User",
    }
    claims.update(overrides)
    return claims


def create_oidc_claims_without_not_before(**overrides: Any) -> dict[str, Any]:
    claims = create_oidc_claims(**overrides)
    del claims["nbf"]
    return claims


def install_fake_oidc_client(
    monkeypatch: pytest.MonkeyPatch,
    authenticator: JWTAuthenticator,
    client: FakeOidcDiscoveryClient,
) -> None:
    monkeypatch.setattr(authenticator, "_get_oidc_discovery_client", lambda: client)


@pytest.mark.asyncio
async def test_default_provider_uses_azure_auth_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_settings(
        monkeypatch,
        azure_client_id="azure-api-client-id",
        azure_tenant_id="tenant-id",
    )
    authenticator = JWTAuthenticator()
    expected_user = create_azure_user()
    azure_called = False

    async def fake_azure_auth(
        request: Request,
        security_scopes: SecurityScopes,
    ) -> User:
        nonlocal azure_called
        azure_called = True
        return expected_user

    async def fail_if_oidc_is_called(
        request: Request,
        security_scopes: SecurityScopes,
    ) -> User:
        raise AssertionError("OIDC auth should not run for the default provider")

    monkeypatch.setattr(authenticator, "_authenticate_with_azure", fake_azure_auth)
    monkeypatch.setattr(
        authenticator, "_authenticate_with_oidc", fail_if_oidc_is_called
    )

    user = await authenticator(create_request(), no_security_scopes())

    assert user is expected_user
    assert azure_called
    assert user.ipaddr is None


@pytest.mark.parametrize(
    ("issuer", "audience", "missing_setting"),
    [
        (None, None, "OIDC issuer"),
        (" ", AUDIENCE, "OIDC issuer"),
        (ISSUER, " ", "OIDC audience"),
    ],
)
def test_oidc_provider_requires_non_blank_issuer_and_audience_config(
    issuer: str | None,
    audience: str | None,
    missing_setting: str,
) -> None:
    with pytest.raises(ValueError, match=f"{missing_setting} is required"):
        create_auth_config(
            auth_provider="oidc",
            oidc_issuer=issuer,
            oidc_audience=audience,
        )


def test_azure_provider_ignores_oidc_config() -> None:
    auth_config = create_auth_config(
        auth_provider="azure",
        oidc_issuer=None,
        oidc_audience=None,
        oidc_user_id_claim=" ",
        oidc_username_claim=" ",
        oidc_email_claim=" ",
    )

    assert auth_config.provider is AuthProvider.AZURE
    assert auth_config.azure is not None
    assert auth_config.oidc is None


def test_auth_config_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="AUTH_PROVIDER must be azure or oidc"):
        create_auth_config(auth_provider="unknown")


def test_oidc_provider_accepts_https_issuer() -> None:
    auth_config = create_auth_config(
        auth_provider="oidc",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
    )

    assert auth_config.azure is None
    assert auth_config.oidc is not None
    assert auth_config.oidc.discovery.issuer == ISSUER


def test_oidc_provider_rejects_http_issuer() -> None:
    with pytest.raises(ValueError, match="OIDC issuer must use HTTPS"):
        create_auth_config(
            auth_provider="oidc",
            oidc_issuer="http://localhost:8080/realms/nachet",
            oidc_audience=AUDIENCE,
        )


def test_oidc_provider_passes_ca_bundle_to_discovery_config() -> None:
    auth_config = create_auth_config(
        auth_provider="oidc",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_ca_bundle="/local-certs/ca/rootCA.pem",
    )

    assert auth_config.oidc is not None
    assert auth_config.oidc.discovery.ca_bundle == "/local-certs/ca/rootCA.pem"


@pytest.mark.parametrize("ca_contents", ["", "not a certificate"])
def test_oidc_authenticator_rejects_invalid_ca_bundle_during_initialization(
    tmp_path: Path,
    ca_contents: str,
) -> None:
    ca_bundle = tmp_path / "invalid-ca.pem"
    ca_bundle.write_text(ca_contents)
    settings = config_module.Settings(
        auth_provider="oidc",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_ca_bundle=str(ca_bundle),
    )

    with pytest.raises(OidcDiscoveryError, match="CA bundle"):
        JWTAuthenticator(settings)


def test_oidc_authenticator_rejects_missing_ca_bundle_during_initialization(
    tmp_path: Path,
) -> None:
    settings = config_module.Settings(
        auth_provider="oidc",
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_ca_bundle=str(tmp_path / "missing-ca.pem"),
    )

    with pytest.raises(OidcDiscoveryError, match="CA bundle"):
        JWTAuthenticator(settings)


@pytest.mark.parametrize(
    "issuer",
    [
        "https://user:password@idp.example/realms/nachet",
        "https://idp.example/realms/nachet?tenant=one",
        "https://idp.example/realms/nachet#keys",
    ],
)
def test_oidc_provider_rejects_unsafe_issuer_urls(issuer: str) -> None:
    with pytest.raises(ValueError, match="OIDC issuer"):
        create_auth_config(
            auth_provider="oidc",
            oidc_issuer=issuer,
            oidc_audience=AUDIENCE,
        )


@pytest.mark.parametrize(
    "claim_setting",
    ["oidc_user_id_claim", "oidc_username_claim", "oidc_email_claim"],
)
def test_oidc_claim_names_cannot_be_blank(claim_setting: str) -> None:
    with pytest.raises(ValueError, match="OIDC claim names cannot be blank"):
        create_auth_config(
            auth_provider="oidc",
            oidc_issuer=ISSUER,
            oidc_audience=AUDIENCE,
            **{claim_setting: " "},
        )


def test_oidc_settings_are_normalized_at_the_config_boundary() -> None:
    auth_config = create_auth_config(
        auth_provider=" OIDC ",
        oidc_issuer=f" {ISSUER} ",
        oidc_audience=f" {AUDIENCE} ",
        oidc_user_id_claim=" sub ",
    )

    assert auth_config.provider is AuthProvider.OIDC
    assert auth_config.oidc is not None
    assert auth_config.oidc.discovery.issuer == ISSUER
    assert auth_config.oidc.discovery.audience == AUDIENCE
    assert auth_config.oidc.user_id_claim == "sub"


@pytest.mark.asyncio
async def test_missing_bearer_token_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()

    with pytest.raises(HTTPException) as error:
        await authenticator(create_request(authorization=None), no_security_scopes())

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Bearer token is required" in error.value.detail
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "authorization",
    ["Basic abc", "Bearer", "Bearer one two"],
)
async def test_malformed_bearer_header_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    authorization: str,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()

    with pytest.raises(HTTPException) as error:
        await authenticator(
            create_request(authorization=authorization),
            no_security_scopes(),
        )

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Bearer token is required" in error.value.detail
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_invalid_oidc_token_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(error=OidcTokenValidationError("invalid token")),
    )

    with pytest.raises(HTTPException) as error:
        await authenticator(create_request(), no_security_scopes())

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Unable to validate token" in error.value.detail
    assert error.value.headers == {"WWW-Authenticate": 'Bearer error="invalid_token"'}


@pytest.mark.asyncio
async def test_oidc_provider_outage_returns_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(
            error=OidcDiscoveryError("unable to load discovery")
        ),
    )

    # An identity-provider outage is retryable and does not make the token invalid.
    with pytest.raises(HTTPException) as error:
        await authenticator(create_request(), no_security_scopes())

    assert error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert error.value.detail == "OIDC provider is unavailable"
    assert error.value.headers is None


@pytest.mark.asyncio
async def test_valid_oidc_token_returns_user_without_azure_version_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims()
    oidc_client = FakeOidcDiscoveryClient(claims=claims)
    install_fake_oidc_client(monkeypatch, authenticator, oidc_client)
    request = create_request()

    user = await authenticator(request, no_security_scopes())

    assert user.oid == claims["sub"]
    assert user.preferred_username == "oidc.user@example.com"
    assert user.email == "oidc.user@example.com"
    assert user.claims == claims
    assert user.access_token == ACCESS_TOKEN
    assert user.is_guest
    assert user.ipaddr is None
    assert user.ver is None
    assert "ver" not in claims
    assert request.state.user is user
    assert oidc_client.verified_tokens == [ACCESS_TOKEN]


@pytest.mark.asyncio
async def test_oidc_user_allows_optional_not_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims_without_not_before()
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    user = await authenticator(create_request(), no_security_scopes())

    assert user.oid == claims["sub"]
    assert user.nbf is None


@pytest.mark.asyncio
async def test_token_claims_cannot_replace_nachet_auth_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims(
        claims="provider-value",
        access_token="provider-value",
        is_guest=False,
        provider_private_claim="provider-value",
    )
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    user = await authenticator(create_request(), no_security_scopes())

    assert user.claims == claims
    assert user.access_token == ACCESS_TOKEN
    assert user.is_guest
    assert not hasattr(user, "provider_private_claim")


@pytest.mark.asyncio
async def test_configured_oidc_identity_claim_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(
        monkeypatch,
        oidc_user_id_claim="nachet_user_id",
    )
    authenticator = JWTAuthenticator()
    nachet_user_id = str(uuid4())
    claims = create_oidc_claims(
        sub="not-the-backend-user-id", nachet_user_id=nachet_user_id
    )
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    user = await authenticator(create_request(), no_security_scopes())

    assert user.oid == nachet_user_id


@pytest.mark.asyncio
async def test_missing_oidc_identity_claim_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims()
    del claims["sub"]
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    with pytest.raises(HTTPException) as error:
        await authenticator(create_request(), no_security_scopes())

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "identity claim" in error.value.detail
    assert error.value.headers == {"WWW-Authenticate": 'Bearer error="invalid_token"'}


@pytest.mark.asyncio
async def test_non_uuid_oidc_identity_claim_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=create_oidc_claims(sub="not-a-uuid")),
    )

    with pytest.raises(HTTPException) as error:
        await authenticator(create_request(), no_security_scopes())

    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid user ID format" in error.value.detail
    assert error.value.headers == {"WWW-Authenticate": 'Bearer error="invalid_token"'}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope_claims",
    [
        {"scp": f"openid profile {REQUIRED_SCOPE}"},
        {"scp": "", "scope": f"openid profile {REQUIRED_SCOPE}"},
    ],
)
async def test_required_scope_passes_from_supported_scope_claims(
    monkeypatch: pytest.MonkeyPatch,
    scope_claims: dict[str, str],
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims(**scope_claims)
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    user = await authenticator(create_request(), required_security_scopes())

    assert user.oid == claims["sub"]


@pytest.mark.asyncio
async def test_missing_required_scope_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_oidc_settings(monkeypatch)
    authenticator = JWTAuthenticator()
    claims = create_oidc_claims(scp="read")
    install_fake_oidc_client(
        monkeypatch,
        authenticator,
        FakeOidcDiscoveryClient(claims=claims),
    )

    with pytest.raises(HTTPException) as error:
        await authenticator(
            create_request(),
            SecurityScopes(scopes=["read", "write", "delete"]),
        )

    assert error.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Required scope missing" in error.value.detail
    assert error.value.headers == {
        "WWW-Authenticate": (
            'Bearer error="insufficient_scope", scope="write delete"'
        )
    }
