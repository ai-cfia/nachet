from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from jwt.exceptions import InvalidTokenError

from app.service.auth.oidc_token_verifier import (
    DEFAULT_ALLOWED_ALGORITHMS,
    REQUIRED_ACCESS_TOKEN_CLAIMS,
    OidcProviderConfig,
    OidcTokenVerifier,
)


DEFAULT_DISCOVERY_CACHE_TTL = timedelta(hours=24)
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
# Unknown `kid` refreshes are rate-limited so invalid tokens cannot repeatedly
# force JWKS reloads. A short cooldown still allows normal key rotation recovery.
DEFAULT_UNKNOWN_KEY_REFRESH_COOLDOWN = timedelta(minutes=1)

AllowedAlgorithms = tuple[str, ...]
RequiredClaims = tuple[str, ...]
HttpClientFactory = Callable[[], httpx.AsyncClient]
CacheClock = Callable[[], datetime]


class OidcDiscoveryError(RuntimeError):
    """Raised when OIDC discovery or JWKS loading fails closed."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class OidcDiscoveryConfig:
    issuer: str
    audience: str
    allowed_algorithms: AllowedAlgorithms = DEFAULT_ALLOWED_ALGORITHMS
    required_claims: RequiredClaims = REQUIRED_ACCESS_TOKEN_CLAIMS
    leeway: int = 0
    cache_ttl: timedelta = DEFAULT_DISCOVERY_CACHE_TTL
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    unknown_key_refresh_cooldown: timedelta = DEFAULT_UNKNOWN_KEY_REFRESH_COOLDOWN


@dataclass(frozen=True)
class CachedOidcVerifier:
    verifier: OidcTokenVerifier
    loaded_at: datetime


class OidcDiscoveryClient:
    def __init__(
        self,
        config: OidcDiscoveryConfig,
        http_client_factory: HttpClientFactory | None = None,
        cache_clock: CacheClock | None = None,
    ) -> None:
        self.config = config
        self.discovery_url = self._build_discovery_url(self.config.issuer)
        self._http_client_factory = (
            http_client_factory
            if http_client_factory is not None
            else self._create_http_client
        )
        self._cache_clock = cache_clock if cache_clock is not None else _utc_now
        self._cached_verifier: CachedOidcVerifier | None = None
        self._last_unknown_key_refresh_at: datetime | None = None
        self._refresh_lock = asyncio.Lock()

    # Trim only for URL construction. The discovered issuer is still compared
    # exactly against the configured issuer before the metadata is accepted.
    def _build_discovery_url(self, issuer: str) -> str:
        issuer_without_trailing_slash = issuer.rstrip("/")
        return f"{issuer_without_trailing_slash}/.well-known/openid-configuration"

    # Keep provider calls bounded so auth does not hang on a slow identity provider.
    def _create_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.config.request_timeout)

    # Cache reads happen before and after taking the lock. That lets normal
    # requests avoid locking while concurrent refreshes still collapse to one load.
    async def get_verifier(self) -> OidcTokenVerifier:
        cached_verifier = self._get_fresh_cached_verifier()
        if cached_verifier is not None:
            return cached_verifier.verifier

        async with self._refresh_lock:
            cached_verifier = self._get_fresh_cached_verifier()
            if cached_verifier is not None:
                return cached_verifier.verifier

            return await self._refresh_verifier()

    # A valid token may reference a new `kid` after provider key rotation. Refresh
    # JWKS once, subject to the unknown-key cooldown, before the final validation.
    async def verify(self, access_token: str) -> dict[str, Any]:
        verifier = await self.get_verifier()
        key_id = self._get_token_key_id(access_token)
        if key_id is not None:
            token_uses_unknown_key = not verifier.has_signing_key(key_id)
            if token_uses_unknown_key:
                verifier = await self._refresh_verifier_for_unknown_key(
                    key_id,
                    verifier,
                )

        return verifier.verify(access_token)

    def _get_fresh_cached_verifier(self) -> CachedOidcVerifier | None:
        cached_verifier = self._cached_verifier
        if cached_verifier is None:
            return None

        if not self._is_cache_fresh(cached_verifier):
            return None

        return cached_verifier

    def _is_cache_fresh(self, cached_verifier: CachedOidcVerifier) -> bool:
        cache_age = self._cache_clock() - cached_verifier.loaded_at
        return cache_age < self.config.cache_ttl

    # Unknown-key refreshes share the main refresh lock. This preserves key
    # rotation recovery without allowing a burst of bad tokens to stampede JWKS.
    async def _refresh_verifier_for_unknown_key(
        self,
        key_id: str,
        current_verifier: OidcTokenVerifier,
    ) -> OidcTokenVerifier:
        async with self._refresh_lock:
            cached_verifier = self._cached_verifier
            if cached_verifier and cached_verifier.verifier.has_signing_key(key_id):
                return cached_verifier.verifier

            if not self._can_refresh_for_unknown_key():
                return current_verifier

            self._last_unknown_key_refresh_at = self._cache_clock()
            return await self._refresh_verifier()

    # The cooldown applies process-wide for this client. It limits provider
    # traffic caused by repeated unknown `kid` values.
    def _can_refresh_for_unknown_key(self) -> bool:
        cooldown = self.config.unknown_key_refresh_cooldown
        if cooldown <= timedelta(0):
            return True

        last_refresh = self._last_unknown_key_refresh_at
        if last_refresh is None:
            return True

        return self._cache_clock() - last_refresh >= cooldown

    # Cache only after discovery and JWKS both pass shape and issuer validation.
    async def _refresh_verifier(self) -> OidcTokenVerifier:
        async with self._http_client_factory() as client:
            discovery_metadata = await self._fetch_discovery_metadata(client)
            jwks_uri = discovery_metadata["jwks_uri"]
            jwks = await self._fetch_jwks(client, jwks_uri)

        verifier = self._build_verifier(jwks)
        self._cached_verifier = CachedOidcVerifier(
            verifier=verifier,
            loaded_at=self._cache_clock(),
        )
        return verifier

    # Discovery supplies keys. Nachet still supplies the expected issuer, audience,
    # algorithms, and required claims used by the verifier.
    def _build_verifier(self, jwks: dict[str, Any]) -> OidcTokenVerifier:
        verifier_config = OidcProviderConfig(
            issuer=self.config.issuer,
            audience=self.config.audience,
            allowed_algorithms=self.config.allowed_algorithms,
            required_claims=self.config.required_claims,
            leeway=self.config.leeway,
        )
        return OidcTokenVerifier(config=verifier_config, jwks=jwks)

    # Accept discovery metadata only from the configured issuer and only when it
    # provides a JWKS endpoint.
    async def _fetch_discovery_metadata(
        self,
        client: httpx.AsyncClient,
    ) -> dict[str, str]:
        metadata = await self._get_json(client, self.discovery_url, "discovery")
        issuer = metadata.get("issuer")
        if not isinstance(issuer, str) or issuer != self.config.issuer:
            raise OidcDiscoveryError("OIDC discovery issuer does not match config")

        jwks_uri = metadata.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise OidcDiscoveryError("OIDC discovery metadata is missing jwks_uri")

        return {"issuer": issuer, "jwks_uri": jwks_uri}

    # RFC 7517 defines a JWKS as a JSON object with a `keys` array.
    async def _fetch_jwks(
        self,
        client: httpx.AsyncClient,
        jwks_uri: str,
    ) -> dict[str, Any]:
        jwks = await self._get_json(client, jwks_uri, "JWKS")
        if not isinstance(jwks.get("keys"), list):
            raise OidcDiscoveryError("OIDC JWKS must contain a keys array")

        return jwks

    # Discovery and JWKS endpoints must return JSON objects. Transport failures,
    # invalid JSON, or other JSON shapes fail closed.
    async def _get_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        source_name: str,
    ) -> dict[str, Any]:
        try:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OidcDiscoveryError(f"Unable to load OIDC {source_name}") from error

        if not isinstance(payload, dict):
            raise OidcDiscoveryError(f"OIDC {source_name} response must be an object")

        return payload

    # The unverified header is used only to decide whether refreshing JWKS may
    # help. Claims and signatures are still validated by `OidcTokenVerifier`.
    def _get_token_key_id(self, access_token: str) -> str | None:
        try:
            header = jwt.get_unverified_header(access_token)
        except InvalidTokenError:
            return None

        key_id = header.get("kid")
        return key_id if isinstance(key_id, str) else None
