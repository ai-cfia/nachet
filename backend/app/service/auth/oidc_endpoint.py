from __future__ import annotations

from ipaddress import ip_address

import httpx


class OidcEndpointError(ValueError):
    """Raised when an OIDC endpoint does not meet Nachet's URL policy."""


def validate_oidc_issuer_url(
    issuer: str,
    *,
    allow_insecure_http_for_local_development: bool = False,
) -> str:
    """Validate an issuer URL without changing its exact configured value."""
    allow_local_http = (
        allow_insecure_http_for_local_development and _has_loopback_host(issuer)
    )
    return _validate_oidc_endpoint(
        issuer,
        endpoint_name="OIDC issuer",
        allow_query=False,
        allow_insecure_http=allow_local_http,
    )


def validate_oidc_jwks_uri(
    jwks_uri: str,
    *,
    discovery_url: str,
) -> str:
    """Validate a provider-supplied JWKS URI before requesting it."""
    allow_local_http = _have_same_http_origin(jwks_uri, discovery_url)
    return _validate_oidc_endpoint(
        jwks_uri,
        endpoint_name="OIDC JWKS URI",
        allow_query=True,
        allow_insecure_http=allow_local_http,
    )


def _validate_oidc_endpoint(
    endpoint: str,
    *,
    endpoint_name: str,
    allow_query: bool,
    allow_insecure_http: bool,
) -> str:
    parsed_endpoint = _parse_oidc_endpoint(endpoint, endpoint_name)
    _validate_oidc_endpoint_shape(
        parsed_endpoint,
        endpoint_name=endpoint_name,
        allow_query=allow_query,
    )
    _validate_oidc_endpoint_transport(
        parsed_endpoint,
        endpoint_name=endpoint_name,
        allow_insecure_http=allow_insecure_http,
    )
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


def _validate_oidc_endpoint_transport(
    parsed_endpoint: httpx.URL,
    *,
    endpoint_name: str,
    allow_insecure_http: bool,
) -> None:
    if parsed_endpoint.scheme == "https":
        return

    if parsed_endpoint.scheme == "http" and allow_insecure_http:
        return

    raise OidcEndpointError(f"{endpoint_name} must use HTTPS")


def _has_loopback_host(endpoint: str) -> bool:
    host = _get_endpoint_host(endpoint)
    return _is_loopback_host(host)


def _is_loopback_host(host: str | None) -> bool:
    if host is None:
        return False

    normalized_host = host.lower()
    if normalized_host == "localhost" or normalized_host.endswith(".localhost"):
        return True

    try:
        return ip_address(normalized_host).is_loopback
    except ValueError:
        return False


def _get_endpoint_host(endpoint: str) -> str | None:
    try:
        return httpx.URL(endpoint).host
    except (httpx.InvalidURL, TypeError):
        return None


def _have_same_http_origin(first_url: str, second_url: str) -> bool:
    try:
        first = httpx.URL(first_url)
        second = httpx.URL(second_url)
    except (httpx.InvalidURL, TypeError):
        return False

    if first.scheme != "http" or second.scheme != "http":
        return False

    return first.host == second.host and first.port == second.port
