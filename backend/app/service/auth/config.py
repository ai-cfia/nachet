from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.api.config import Settings
from app.service.auth.oidc_discovery import OidcDiscoveryConfig


class AuthProvider(str, Enum):
    AZURE = "azure"
    OIDC = "oidc"


@dataclass(frozen=True)
class OidcAuthConfig:
    discovery: OidcDiscoveryConfig
    user_id_claim: str
    username_claim: str
    email_claim: str


@dataclass(frozen=True)
class AzureAuthConfig:
    client_id: str | None
    tenant_id: str | None


@dataclass(frozen=True)
class BackendAuthConfig:
    provider: AuthProvider
    azure: AzureAuthConfig | None
    oidc: OidcAuthConfig | None

    @classmethod
    def from_settings(cls, settings: Settings) -> BackendAuthConfig:
        provider = _parse_auth_provider(settings.auth_provider)

        azure = None
        oidc = None
        if provider is AuthProvider.AZURE:
            azure = AzureAuthConfig(
                client_id=settings.azure_client_id,
                tenant_id=settings.azure_tenant_id,
            )
        else:
            issuer = _parse_required_setting(settings.oidc_issuer, "OIDC issuer")
            audience = _parse_required_setting(
                settings.oidc_audience,
                "OIDC audience",
            )
            discovery = _build_oidc_discovery_config(settings, issuer, audience)

            oidc = OidcAuthConfig(
                discovery=discovery,
                user_id_claim=_parse_claim_name(settings.oidc_user_id_claim),
                username_claim=_parse_claim_name(settings.oidc_username_claim),
                email_claim=_parse_claim_name(settings.oidc_email_claim),
            )

        return cls(
            provider=provider,
            azure=azure,
            oidc=oidc,
        )


def _parse_auth_provider(value: str) -> AuthProvider:
    normalized_value = value.strip().lower()
    try:
        return AuthProvider(normalized_value)
    except ValueError as error:
        raise ValueError("AUTH_PROVIDER must be azure or oidc") from error


def _parse_required_setting(value: str | None, setting_name: str) -> str:
    normalized_value = value.strip() if value is not None else ""
    if not normalized_value:
        raise ValueError(f"{setting_name} is required when AUTH_PROVIDER is oidc")
    return normalized_value


def _build_oidc_discovery_config(
    settings: Settings,
    issuer: str,
    audience: str,
) -> OidcDiscoveryConfig:
    allow_local_http = settings.oidc_allow_insecure_http_for_local_development
    if allow_local_http and settings.nachet_env.strip().lower() not in {
        "development",
        "local",
    }:
        raise ValueError(
            "Insecure OIDC HTTP is only available in local or development environments"
        )

    return OidcDiscoveryConfig(
        issuer=issuer,
        audience=audience,
        allow_insecure_http_for_local_development=allow_local_http,
    )


def _parse_claim_name(value: str) -> str:
    claim_name = value.strip()
    if not claim_name:
        raise ValueError("OIDC claim names cannot be blank")
    return claim_name
