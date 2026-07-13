from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.api.config import Settings
from app.service.auth.oidc_discovery import OidcDiscoveryConfig


class AuthProvider(str, Enum):
    AZURE = "azure"
    OIDC = "oidc"


@dataclass(frozen=True)
class BackendAuthConfig:
    provider: AuthProvider
    azure_client_id: str | None
    azure_tenant_id: str | None
    oidc_discovery: OidcDiscoveryConfig | None
    oidc_user_id_claim: str
    oidc_username_claim: str
    oidc_email_claim: str

    @classmethod
    def from_settings(cls, settings: Settings) -> BackendAuthConfig:
        provider = _parse_auth_provider(settings.auth_provider)
        oidc_user_id_claim = _parse_claim_name(settings.oidc_user_id_claim)
        oidc_username_claim = _parse_claim_name(settings.oidc_username_claim)
        oidc_email_claim = _parse_claim_name(settings.oidc_email_claim)

        oidc_discovery = None
        if provider is AuthProvider.OIDC:
            issuer = _parse_required_setting(settings.oidc_issuer, "OIDC issuer")
            audience = _parse_required_setting(
                settings.oidc_audience,
                "OIDC audience",
            )

            oidc_discovery = OidcDiscoveryConfig(
                issuer=issuer,
                audience=audience,
            )

        return cls(
            provider=provider,
            azure_client_id=settings.azure_client_id,
            azure_tenant_id=settings.azure_tenant_id,
            oidc_discovery=oidc_discovery,
            oidc_user_id_claim=oidc_user_id_claim,
            oidc_username_claim=oidc_username_claim,
            oidc_email_claim=oidc_email_claim,
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


def _parse_claim_name(value: str) -> str:
    claim_name = value.strip()
    if not claim_name:
        raise ValueError("OIDC claim names cannot be blank")
    return claim_name
