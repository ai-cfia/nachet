from __future__ import annotations

import httpx


class OidcEndpointError(ValueError):
    """Raised when an OIDC endpoint does not meet Nachet's URL policy."""


def validate_oidc_issuer_url(issuer: str) -> str:
    """Validate an issuer URL without changing its exact configured value."""
    return _validate_oidc_endpoint(
        issuer,
        endpoint_name="OIDC issuer",
        allow_query=False,
    )


def validate_oidc_jwks_uri(jwks_uri: str) -> str:
    """Validate a provider-supplied JWKS URI before requesting it."""
    return _validate_oidc_endpoint(
        jwks_uri,
        endpoint_name="OIDC JWKS URI",
        allow_query=True,
    )


def _validate_oidc_endpoint(
    endpoint: str,
    *,
    endpoint_name: str,
    allow_query: bool,
) -> str:
    parsed_endpoint = _parse_oidc_endpoint(endpoint, endpoint_name)
    _validate_oidc_endpoint_shape(
        parsed_endpoint,
        endpoint_name=endpoint_name,
        allow_query=allow_query,
    )
    if parsed_endpoint.scheme != "https":
        raise OidcEndpointError(f"{endpoint_name} must use HTTPS")
    return endpoint


def _parse_oidc_endpoint(endpoint: str, endpoint_name: str) -> httpx.URL:
    try:
        return httpx.URL(endpoint)
    except (httpx.InvalidURL, TypeError) as error:
        raise OidcEndpointError(f"{endpoint_name} must be a valid URL") from error


def _validate_oidc_endpoint_shape(
    parsed_endpoint: httpx.URL,
    *,
    endpoint_name: str,
    allow_query: bool,
) -> None:
    is_absolute = parsed_endpoint.is_absolute_url
    uses_http = parsed_endpoint.scheme in {"http", "https"}
    has_host = bool(parsed_endpoint.host)
    if not all((is_absolute, uses_http, has_host)):
        raise OidcEndpointError(
            f"{endpoint_name} must be an absolute HTTP or HTTPS URL"
        )

    if parsed_endpoint.username or parsed_endpoint.password:
        raise OidcEndpointError(f"{endpoint_name} must not contain credentials")

    if parsed_endpoint.fragment:
        raise OidcEndpointError(f"{endpoint_name} must not contain a fragment")

    if not allow_query and parsed_endpoint.query:
        raise OidcEndpointError(f"{endpoint_name} must not contain a query string")
