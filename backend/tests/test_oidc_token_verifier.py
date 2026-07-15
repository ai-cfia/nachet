from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.service.auth.oidc_token_verifier import (
    OidcProviderConfig,
    OidcTokenValidationError,
    OidcTokenVerifier,
)


ISSUER = "https://idp.example/realms/nachet"
AUDIENCE = "nachet-api"
KEY_ID = "test-signing-key"
SIGNING_ALGORITHM = "RS256"


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


def create_verifier(
    jwk: dict[str, Any],
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
) -> OidcTokenVerifier:
    return OidcTokenVerifier(
        config=OidcProviderConfig(
            issuer=issuer,
            audience=audience,
        ),
        jwks={"keys": [jwk]},
    )


def create_claims(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-subject",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "nbf": now - timedelta(seconds=5),
        "preferred_username": "seed.user@example.com",
    }
    claims.update(overrides)
    return claims


def sign_token(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    key_id: str = KEY_ID,
    headers: dict[str, Any] | None = None,
) -> str:
    token_headers = {"kid": key_id}
    token_headers.update(headers or {})

    return jwt.encode(
        claims,
        private_key,
        algorithm=SIGNING_ALGORITHM,
        headers=token_headers,
    )


# Creates a token with no `kid` header for the missing-key-id negative test.
def sign_token_without_key_id(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
) -> str:
    return jwt.encode(
        claims,
        private_key,
        algorithm=SIGNING_ALGORITHM,
        headers={},
    )


def test_valid_token_returns_claims() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    token = sign_token(private_key, create_claims())

    claims = verifier.verify(token)

    assert claims["iss"] == ISSUER
    assert claims["aud"] == AUDIENCE
    assert claims["sub"] == "user-subject"


# `aud` can be a string or a list. The verifier accepts the token when Nachet's
# API audience is one of the listed audiences.
def test_audience_list_containing_expected_audience_returns_claims() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    claims_with_audience_list = create_claims(aud=["other-api", AUDIENCE])
    token = sign_token(private_key, claims_with_audience_list)

    claims = verifier.verify(token)

    assert claims["aud"] == ["other-api", AUDIENCE]


@pytest.mark.parametrize(
    ("claim_override", "expected_message"),
    [
        ({"iss": "https://wrong-issuer.example"}, "issuer"),
        ({"aud": "wrong-audience"}, "audience"),
        ({"exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, "expired"),
    ],
)
def test_invalid_standard_claims_fail_closed(
    claim_override: dict[str, Any],
    expected_message: str,
) -> None:
    private_key = create_private_key()
    public_jwk = public_jwk_from_key(private_key)
    verifier = create_verifier(public_jwk)
    claims = create_claims(**claim_override)
    token = sign_token(private_key, claims)

    with pytest.raises(OidcTokenValidationError, match=expected_message):
        verifier.verify(token)


# `nbf` means "not before." A token can be properly signed and still be invalid
# if its valid-from time is in the future.
def test_not_before_in_future_fails_closed() -> None:
    private_key = create_private_key()
    public_jwk = public_jwk_from_key(private_key)
    verifier = create_verifier(public_jwk)
    future_not_before = datetime.now(timezone.utc) + timedelta(days=1)
    claims = create_claims(nbf=future_not_before)
    token = sign_token(private_key, claims)

    with pytest.raises(OidcTokenValidationError, match="not valid yet"):
        verifier.verify(token)


def test_token_without_optional_not_before_claim_returns_claims() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    claims = create_claims()
    del claims["nbf"]
    token = sign_token(private_key, claims)

    verified_claims = verifier.verify(token)

    assert verified_claims["sub"] == "user-subject"


# `alg: none` asks the backend to trust unsigned claims. The verifier treats it
# as an unsupported algorithm.
def test_unsigned_alg_none_token_fails_closed() -> None:
    private_key = create_private_key()
    public_jwk = public_jwk_from_key(private_key)
    verifier = create_verifier(public_jwk)
    unsigned_claims = create_claims()
    unsigned_header = {"kid": KEY_ID}
    token = jwt.encode(
        unsigned_claims,
        key="",
        algorithm="none",
        headers=unsigned_header,
    )

    token_header = jwt.get_unverified_header(token)
    assert token_header["alg"] == "none"
    with pytest.raises(OidcTokenValidationError, match="algorithm"):
        verifier.verify(token)


def test_bad_signature_fails_closed() -> None:
    trusted_private_key = create_private_key()
    attacker_private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(trusted_private_key))
    token = sign_token(attacker_private_key, create_claims())

    with pytest.raises(OidcTokenValidationError, match="signature"):
        verifier.verify(token)


def test_missing_signing_key_fails_closed() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key, key_id="other-key"))
    token = sign_token(private_key, create_claims(), key_id=KEY_ID)

    with pytest.raises(OidcTokenValidationError, match="signing key"):
        verifier.verify(token)


# Without a `kid`, the verifier has no trusted key identifier to use.
def test_missing_key_id_fails_closed() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    token = sign_token_without_key_id(private_key, create_claims())

    with pytest.raises(OidcTokenValidationError, match="signing key id"):
        verifier.verify(token)


# `crit` announces required JWT header extensions. This verifier supports no
# header extensions, so tokens with `crit` are not accepted.
def test_unsupported_critical_header_fails_closed() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    token = sign_token(
        private_key,
        create_claims(),
        headers={"crit": ["unknown-extension"], "unknown-extension": True},
    )

    with pytest.raises(OidcTokenValidationError, match="critical"):
        verifier.verify(token)


def test_missing_required_identity_claim_fails_closed() -> None:
    private_key = create_private_key()
    verifier = create_verifier(public_jwk_from_key(private_key))
    claims = create_claims()
    del claims["sub"]
    token = sign_token(private_key, claims)

    with pytest.raises(OidcTokenValidationError, match="required claim"):
        verifier.verify(token)
