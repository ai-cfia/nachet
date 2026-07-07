from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingRequiredClaimError,
)

from app.service.auth.openid_config import AllowedPublicKeys

DEFAULT_ALLOWED_ALGORITHMS = ("RS256",)
REQUIRED_ACCESS_TOKEN_CLAIMS = ("exp", "aud", "iat", "nbf", "iss", "sub")


class OidcTokenValidationError(ValueError):
    """Raised when an OIDC access token cannot be trusted by Nachet."""


@dataclass(frozen=True)
class OidcProviderConfig:
    issuer: str
    audience: str
    allowed_algorithms: tuple[str, ...] = DEFAULT_ALLOWED_ALGORITHMS
    required_claims: tuple[str, ...] = REQUIRED_ACCESS_TOKEN_CLAIMS
    leeway: int = 0


class OidcTokenVerifier:
    def __init__(self, config: OidcProviderConfig, jwks: dict[str, Any]) -> None:
        self.config = config
        self.signing_keys = self._load_signing_keys(jwks)

    # The JWKS is the provider's public key set. We keep the usable signing keys
    # and store them by `kid` so each token can name the key that should verify it.
    def _load_signing_keys(self, jwks: dict[str, Any]) -> dict[str, AllowedPublicKeys]:
        signing_keys: dict[str, AllowedPublicKeys] = {}
        jwks_keys = jwks.get("keys", [])
        for jwk in jwks_keys:
            loaded_key = self._load_signing_key(jwk)
            if loaded_key is None:
                continue

            key_id, key = loaded_key
            signing_keys[key_id] = key

        return signing_keys

    # A JWK is still just input data until it passes these checks. We ignore keys
    # that are not signing keys, have no `kid`, or use an algorithm we do not allow.
    def _load_signing_key(
        self,
        jwk: dict[str, Any],
    ) -> tuple[str, AllowedPublicKeys] | None:
        if jwk.get("use") not in (None, "sig"):
            return None

        key_id = jwk.get("kid")
        if not isinstance(key_id, str):
            return None

        algorithm = jwk.get("alg", self.config.allowed_algorithms[0])
        if not isinstance(algorithm, str):
            return None

        if algorithm not in self.config.allowed_algorithms:
            return None

        return key_id, jwt.PyJWK(jwk, algorithm).key

    # This is the verifier entry point. It chooses the key named by the token
    # header, then returns claims only after the signature and claim checks pass.
    def verify(self, access_token: str) -> dict[str, Any]:
        if not access_token:
            raise OidcTokenValidationError("Access token is empty")

        header = self._get_token_header(access_token)
        key = self._get_signing_key(header)
        return self._decode_claims(access_token, key)

    # We read the unverified header only to find metadata like `alg` and `kid`.
    # Claims stay untrusted until `_decode_claims` verifies the signed token.
    def _get_token_header(self, access_token: str) -> dict[str, Any]:
        try:
            return dict(jwt.get_unverified_header(access_token))
        except DecodeError as error:
            raise OidcTokenValidationError("Invalid token format") from error
        except InvalidTokenError as error:
            if "critical" in str(error).lower():
                raise OidcTokenValidationError(
                    "Unsupported critical token header"
                ) from error
            raise OidcTokenValidationError("Invalid token header") from error

    # The token header can request an algorithm and key, but Nachet still decides
    # whether that combination is allowed and available.
    def _get_signing_key(self, header: dict[str, Any]) -> AllowedPublicKeys:
        # `crit` marks required JWT header extensions. This verifier does not
        # support header extensions, so those tokens are not accepted.
        if header.get("crit"):
            raise OidcTokenValidationError("Unsupported critical token header")

        algorithm = header.get("alg")
        if algorithm not in self.config.allowed_algorithms:
            raise OidcTokenValidationError("Unsupported token algorithm")

        key_id = header.get("kid")
        if not isinstance(key_id, str):
            raise OidcTokenValidationError("Token is missing a signing key id")

        key = self.signing_keys.get(key_id)
        if not key:
            raise OidcTokenValidationError("No matching signing key found")

        return key

    # This is the trust check. PyJWT verifies the signature, issuer, audience,
    # time claims, and required claims before the verifier returns anything.
    def _decode_claims(
        self,
        access_token: str,
        key: AllowedPublicKeys,
    ) -> dict[str, Any]:
        try:
            return dict(
                jwt.decode(
                    access_token,
                    key=key,
                    algorithms=list(self.config.allowed_algorithms),
                    audience=self.config.audience,
                    issuer=self.config.issuer,
                    leeway=self.config.leeway,
                    options={
                        "verify_signature": True,
                        "verify_aud": True,
                        "verify_iat": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iss": True,
                        "require": list(self.config.required_claims),
                    },
                )
            )
        except ExpiredSignatureError as error:
            raise OidcTokenValidationError("Token expired") from error
        except ImmatureSignatureError as error:
            raise OidcTokenValidationError("Token is not valid yet") from error
        except InvalidAudienceError as error:
            raise OidcTokenValidationError("Invalid audience") from error
        except InvalidIssuerError as error:
            raise OidcTokenValidationError("Invalid issuer") from error
        except MissingRequiredClaimError as error:
            raise OidcTokenValidationError("Missing required claim") from error
        except InvalidSignatureError as error:
            raise OidcTokenValidationError("Invalid signature") from error
        except InvalidTokenError as error:
            raise OidcTokenValidationError("Invalid token") from error
