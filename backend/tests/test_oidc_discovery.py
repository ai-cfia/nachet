from __future__ import annotations

import asyncio
import json
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.service.auth.oidc_discovery import (
    OidcDiscoveryClient,
    OidcDiscoveryConfig,
    OidcDiscoveryError,
)
from app.service.auth.oidc_token_verifier import OidcTokenValidationError


ISSUER = "https://idp.example/realms/nachet"
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
JWKS_URI = f"{ISSUER}/protocol/openid-connect/certs"
AUDIENCE = "nachet-api"
KEY_ID = "test-signing-key"
ROTATED_KEY_ID = "rotated-signing-key"
SIGNING_ALGORITHM = "RS256"


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def advance(self, delta: timedelta) -> None:
        self.now += delta

    def __call__(self) -> datetime:
        return self.now


@dataclass
class MockOidcProvider:
    issuer: str = ISSUER
    discovery_url: str = DISCOVERY_URL
    jwks_uri: str = JWKS_URI
    jwks: dict[str, Any] = field(default_factory=lambda: {"keys": []})
    delay_seconds: float = 0
    discovery_status: int = 200
    jwks_status: int = 200
    include_jwks_uri: bool = True
    requests: list[str] = field(default_factory=list)

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)

        if str(request.url) == self.discovery_url:
            if self.discovery_status != 200:
                return httpx.Response(self.discovery_status)

            discovery_metadata = {"issuer": self.issuer}
            if self.include_jwks_uri:
                discovery_metadata["jwks_uri"] = self.jwks_uri

            return httpx.Response(200, json=discovery_metadata)

        if str(request.url) == self.jwks_uri:
            if self.jwks_status != 200:
                return httpx.Response(self.jwks_status)

            return httpx.Response(200, json=self.jwks)

        return httpx.Response(404, json={"error": "not found"})

    def count_requests(self, url: str) -> int:
        return self.requests.count(url)


def create_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def public_jwk_from_key(
    private_key: rsa.RSAPrivateKey,
    key_id: str = KEY_ID,
) -> dict[str, Any]:
    public_key = private_key.public_key()
    public_jwk_json = RSAAlgorithm.to_jwk(public_key)
    jwk = json.loads(public_jwk_json)
    jwk["kid"] = key_id
    jwk["use"] = "sig"
    jwk["alg"] = SIGNING_ALGORITHM
    return jwk


def jwks_from_key(
    private_key: rsa.RSAPrivateKey,
    key_id: str = KEY_ID,
) -> dict[str, Any]:
    return {"keys": [public_jwk_from_key(private_key, key_id=key_id)]}


def create_claims(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-subject",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "nbf": now - timedelta(seconds=5),
    }
    claims.update(overrides)
    return claims


def sign_token(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    key_id: str = KEY_ID,
) -> str:
    return jwt.encode(
        claims,
        private_key,
        algorithm=SIGNING_ALGORITHM,
        headers={"kid": key_id},
    )


def create_client(
    provider: MockOidcProvider,
    *,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    clock: MutableClock | None = None,
) -> OidcDiscoveryClient:
    transport = httpx.MockTransport(provider.handle_request)
    return OidcDiscoveryClient(
        config=OidcDiscoveryConfig(
            issuer=issuer,
            audience=audience,
        ),
        http_client_factory=lambda: httpx.AsyncClient(transport=transport),
        cache_clock=clock or MutableClock(datetime.now(timezone.utc)),
    )


@pytest.mark.asyncio
async def test_fetches_discovery_and_jwks_then_verifies_token() -> None:
    private_key = create_private_key()
    provider = MockOidcProvider(jwks=jwks_from_key(private_key))
    client = create_client(provider)
    token = sign_token(private_key, create_claims())

    verifier = await client.get_verifier()
    claims = verifier.verify(token)

    assert claims["sub"] == "user-subject"
    assert provider.count_requests(DISCOVERY_URL) == 1
    assert provider.count_requests(JWKS_URI) == 1


# Keycloak-style issuers often include a realm path. Discovery must preserve
# that path and append only the well-known suffix.
@pytest.mark.asyncio
async def test_builds_discovery_url_for_path_based_issuer() -> None:
    private_key = create_private_key()
    provider = MockOidcProvider(jwks=jwks_from_key(private_key))
    client = create_client(provider, issuer=ISSUER)

    await client.get_verifier()

    assert DISCOVERY_URL in provider.requests


@pytest.mark.asyncio
async def test_rejects_discovery_issuer_mismatch() -> None:
    private_key = create_private_key()
    provider = MockOidcProvider(
        issuer="https://wrong-idp.example/realms/nachet",
        jwks=jwks_from_key(private_key),
    )
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="issuer"):
        await client.get_verifier()


@pytest.mark.asyncio
async def test_rejects_missing_jwks_uri() -> None:
    provider = MockOidcProvider(include_jwks_uri=False)
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="jwks_uri"):
        await client.get_verifier()


@pytest.mark.asyncio
async def test_rejects_malformed_jwks_without_keys_array() -> None:
    provider = MockOidcProvider(jwks={"keys": "not-an-array"})
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="JWKS"):
        await client.get_verifier()


@pytest.mark.asyncio
async def test_rejects_malformed_jwks_with_non_object_key() -> None:
    provider = MockOidcProvider(jwks={"keys": ["not-a-jwk-object"]})
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="JWK objects"):
        await client.get_verifier()


@pytest.mark.asyncio
async def test_ignores_malformed_jwk_when_a_usable_signing_key_exists() -> None:
    private_key = create_private_key()
    malformed_jwk = {"kid": "malformed-key", "alg": SIGNING_ALGORITHM, "use": "sig"}
    provider = MockOidcProvider(
        jwks={"keys": [malformed_jwk, public_jwk_from_key(private_key)]}
    )
    client = create_client(provider)
    token = sign_token(private_key, create_claims())

    claims = await client.verify(token)

    assert claims["sub"] == "user-subject"


@pytest.mark.asyncio
async def test_rejects_jwks_without_a_usable_signing_key() -> None:
    malformed_jwk = {"kid": KEY_ID, "alg": SIGNING_ALGORITHM, "use": "sig"}
    provider = MockOidcProvider(jwks={"keys": [malformed_jwk]})
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="usable signing key"):
        await client.get_verifier()


@pytest.mark.asyncio
async def test_discovery_redirect_fails_closed_without_following_location() -> None:
    provider = MockOidcProvider(discovery_status=302)
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="Unable to load OIDC discovery"):
        await client.get_verifier()

    assert provider.requests == [DISCOVERY_URL]


# Fresh cache entries should be reused so normal API requests do not refetch
# provider metadata on every token validation.
@pytest.mark.asyncio
async def test_uses_cached_verifier_before_ttl_expires() -> None:
    private_key = create_private_key()
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    provider = MockOidcProvider(jwks=jwks_from_key(private_key))
    client = create_client(provider, clock=clock)

    first_verifier = await client.get_verifier()
    clock.advance(timedelta(hours=23, minutes=59))
    second_verifier = await client.get_verifier()

    assert second_verifier is first_verifier
    assert provider.count_requests(DISCOVERY_URL) == 1
    assert provider.count_requests(JWKS_URI) == 1


def test_rejects_http_issuer() -> None:
    with pytest.raises(ValueError, match="OIDC issuer must use HTTPS"):
        OidcDiscoveryClient(
            OidcDiscoveryConfig(
                issuer="http://idp.example/realms/nachet",
                audience=AUDIENCE,
            )
        )


@pytest.mark.asyncio
async def test_rejects_http_jwks() -> None:
    insecure_jwks_uri = "http://keys.example/realms/nachet/certs"
    provider = MockOidcProvider(jwks_uri=insecure_jwks_uri)
    client = create_client(provider)

    # Reject the JWKS URI before a second request leaves the backend.
    with pytest.raises(OidcDiscoveryError, match="JWKS URI must use HTTPS"):
        await client.get_verifier()

    assert provider.requests == [DISCOVERY_URL]


def test_custom_ca_bundle_is_added_to_default_httpx_trust(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ca_bundle = tmp_path / "local-ca.pem"
    ca_bundle.write_text("test certificate")
    loaded_ca_files: list[str] = []

    class RecordingSslContext(ssl.SSLContext):
        def __new__(cls) -> RecordingSslContext:
            return super().__new__(cls, ssl.PROTOCOL_TLS_CLIENT)

        def load_verify_locations(
            self,
            cafile: Any = None,
            capath: Any = None,
            cadata: Any = None,
        ) -> None:
            if cafile is not None:
                loaded_ca_files.append(cafile)

    monkeypatch.setattr(httpx, "create_ssl_context", RecordingSslContext)

    client = OidcDiscoveryClient(
        OidcDiscoveryConfig(
            issuer=ISSUER,
            audience=AUDIENCE,
            ca_bundle=str(ca_bundle),
        )
    )

    assert client.config.ca_bundle == str(ca_bundle)
    assert loaded_ca_files == [str(ca_bundle)]


def test_default_httpx_trust_is_unchanged_without_custom_ca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_called = False

    class RecordingSslContext(ssl.SSLContext):
        def __new__(cls) -> RecordingSslContext:
            return super().__new__(cls, ssl.PROTOCOL_TLS_CLIENT)

        def load_verify_locations(
            self,
            cafile: Any = None,
            capath: Any = None,
            cadata: Any = None,
        ) -> None:
            nonlocal load_called
            load_called = True

    monkeypatch.setattr(httpx, "create_ssl_context", RecordingSslContext)

    OidcDiscoveryClient(
        OidcDiscoveryConfig(
            issuer=ISSUER,
            audience=AUDIENCE,
        )
    )

    assert load_called is False


@pytest.mark.parametrize("ca_contents", ["", "not a certificate"])
def test_invalid_ca_bundle_fails_during_client_initialization(
    tmp_path: Path,
    ca_contents: str,
) -> None:
    ca_bundle = tmp_path / "invalid-ca.pem"
    ca_bundle.write_text(ca_contents)

    with pytest.raises(OidcDiscoveryError, match="CA bundle"):
        OidcDiscoveryClient(
            OidcDiscoveryConfig(
                issuer=ISSUER,
                audience=AUDIENCE,
                ca_bundle=str(ca_bundle),
            )
        )


def test_missing_ca_bundle_fails_during_client_initialization(
    tmp_path: Path,
) -> None:
    missing_ca_bundle = tmp_path / "missing-ca.pem"

    with pytest.raises(OidcDiscoveryError, match="CA bundle"):
        OidcDiscoveryClient(
            OidcDiscoveryConfig(
                issuer=ISSUER,
                audience=AUDIENCE,
                ca_bundle=str(missing_ca_bundle),
            )
        )


@pytest.mark.asyncio
async def test_rejects_malformed_jwks_uri_with_discovery_error() -> None:
    provider = MockOidcProvider(jwks_uri="http://[::1/keys")
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="valid URL"):
        await client.get_verifier()

    assert provider.requests == [DISCOVERY_URL]


# Expired cache entries are replaced with fresh discovery and JWKS data.
@pytest.mark.asyncio
async def test_refreshes_verifier_after_ttl_expires() -> None:
    first_private_key = create_private_key()
    second_private_key = create_private_key()
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    provider = MockOidcProvider(jwks=jwks_from_key(first_private_key))
    client = create_client(provider, clock=clock)

    first_verifier = await client.get_verifier()
    provider.jwks = jwks_from_key(second_private_key)
    clock.advance(timedelta(hours=24, seconds=1))
    second_verifier = await client.get_verifier()

    assert second_verifier is not first_verifier
    assert provider.count_requests(DISCOVERY_URL) == 2
    assert provider.count_requests(JWKS_URI) == 2


# Key rotation can happen before the cache TTL expires. An unknown `kid` gets
# one refresh attempt before final token validation.
@pytest.mark.asyncio
async def test_refreshes_jwks_once_when_token_kid_is_unknown() -> None:
    old_private_key = create_private_key()
    rotated_private_key = create_private_key()
    provider = MockOidcProvider(jwks=jwks_from_key(old_private_key))
    client = create_client(provider)
    await client.get_verifier()
    provider.jwks = jwks_from_key(rotated_private_key, key_id=ROTATED_KEY_ID)
    token = sign_token(
        rotated_private_key,
        create_claims(),
        key_id=ROTATED_KEY_ID,
    )

    claims = await client.verify(token)

    assert claims["sub"] == "user-subject"
    assert provider.count_requests(DISCOVERY_URL) == 2
    assert provider.count_requests(JWKS_URI) == 2


# Unknown `kid` values come from untrusted tokens. The cooldown keeps invalid
# tokens from forcing repeated discovery/JWKS reloads.
@pytest.mark.asyncio
async def test_unknown_kid_refresh_is_rate_limited() -> None:
    trusted_private_key = create_private_key()
    first_attacker_private_key = create_private_key()
    second_attacker_private_key = create_private_key()
    third_attacker_private_key = create_private_key()
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    provider = MockOidcProvider(jwks=jwks_from_key(trusted_private_key))
    client = create_client(provider, clock=clock)
    await client.get_verifier()

    first_fake_token = sign_token(
        first_attacker_private_key,
        create_claims(),
        key_id="fake-key-1",
    )
    second_fake_token = sign_token(
        second_attacker_private_key,
        create_claims(),
        key_id="fake-key-2",
    )
    third_fake_token = sign_token(
        third_attacker_private_key,
        create_claims(),
        key_id="fake-key-3",
    )

    with pytest.raises(OidcTokenValidationError, match="signing key"):
        await client.verify(first_fake_token)
    with pytest.raises(OidcTokenValidationError, match="signing key"):
        await client.verify(second_fake_token)

    assert provider.count_requests(DISCOVERY_URL) == 2
    assert provider.count_requests(JWKS_URI) == 2

    clock.advance(timedelta(minutes=1, seconds=1))
    with pytest.raises(OidcTokenValidationError, match="signing key"):
        await client.verify(third_fake_token)

    assert provider.count_requests(DISCOVERY_URL) == 3
    assert provider.count_requests(JWKS_URI) == 3


# ID tokens are meant for the frontend client, not the backend API. The audience
# check rejects them before they can be used as API credentials.
@pytest.mark.asyncio
async def test_frontend_id_token_audience_fails_closed() -> None:
    private_key = create_private_key()
    provider = MockOidcProvider(jwks=jwks_from_key(private_key))
    client = create_client(provider)
    token_for_frontend = sign_token(
        private_key,
        create_claims(aud="nachet-frontend-client"),
    )

    with pytest.raises(OidcTokenValidationError, match="audience"):
        await client.verify(token_for_frontend)


@pytest.mark.asyncio
async def test_fails_closed_when_discovery_fetch_fails_without_cache() -> None:
    provider = MockOidcProvider(discovery_status=503)
    client = create_client(provider)

    with pytest.raises(OidcDiscoveryError, match="discovery"):
        await client.get_verifier()


# If the cache is expired and refresh fails, the client does not continue using
# stale provider metadata.
@pytest.mark.asyncio
async def test_expired_cache_is_not_used_when_refresh_fails() -> None:
    private_key = create_private_key()
    clock = MutableClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    provider = MockOidcProvider(jwks=jwks_from_key(private_key))
    client = create_client(provider, clock=clock)
    await client.get_verifier()

    provider.discovery_status = 503
    clock.advance(timedelta(hours=24, seconds=1))

    with pytest.raises(OidcDiscoveryError, match="discovery"):
        await client.get_verifier()


# Concurrent startup checks should share one provider refresh.
@pytest.mark.asyncio
async def test_concurrent_get_verifier_calls_share_one_refresh() -> None:
    private_key = create_private_key()
    provider = MockOidcProvider(
        jwks=jwks_from_key(private_key),
        delay_seconds=0.01,
    )
    client = create_client(provider)

    first_verifier, second_verifier = await asyncio.gather(
        client.get_verifier(),
        client.get_verifier(),
    )

    assert second_verifier is first_verifier
    assert provider.count_requests(DISCOVERY_URL) == 1
    assert provider.count_requests(JWKS_URI) == 1
