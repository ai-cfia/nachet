# Backend token validation

Nachet validates every protected backend request with either Microsoft Entra or
a provider-neutral OpenID Connect (OIDC) provider. Microsoft Entra remains the
default. The backend has no unauthenticated mode.

## Request flow

```text
Protected FastAPI route
  -> get_current_user
  -> select AUTH_PROVIDER
     -> azure: existing Entra validator
     -> oidc: OIDC discovery and token verifier
  -> normalize verified claims into User
  -> require a UUID-shaped User.oid
  -> continue to the route
```

Routes continue to depend on `get_current_user`. Provider selection happens in
`app/service/auth/jwt_auth.py`, so routes do not contain provider-specific code.

## Provider selection

`AUTH_PROVIDER` accepts two values:

| Value | Backend path |
| --- | --- |
| `azure` | Existing Microsoft Entra validation |
| `oidc` | Provider-neutral OIDC discovery and validation |

The default is `azure`. Any other value is rejected by the settings model.

## Microsoft Entra path

The Entra path continues to use `SingleTenantAzureAuthorizationCodeBearer` and
the existing Azure configuration:

```bash
AUTH_PROVIDER="azure"
AZURE_CLIENT_ID="<api-client-id>"
AZURE_TENANT_ID="<tenant-id>"
```

This path validates the Entra token and creates the same `User` model returned
by the OIDC path.

## OIDC path

The OIDC path is split into three small layers.

### Token verifier

`app/service/auth/oidc_token_verifier.py` validates a JWT access token with
PyJWT. It checks:

- the signature against a trusted public key;
- the configured issuer and audience;
- the allowed signing algorithm;
- the `exp`, `iat`, and `nbf` time claims;
- the required claims, including `iss`, `aud`, and `sub`;
- the `kid` used to select the signing key.

The identity provider sets the token lifetime in `exp`. Nachet does not create
or extend that lifetime. It rejects expired tokens and tokens whose `nbf` time
has not arrived.

### Discovery and JWKS

`app/service/auth/oidc_discovery.py` loads the provider metadata from:

```text
<OIDC_ISSUER>/.well-known/openid-configuration
```

The discovery response must return the exact configured issuer and a `jwks_uri`.
The JWKS response must be a JSON object with a `keys` array. The verifier keeps
only signing keys with a supported algorithm and a string `kid`.

The verifier is cached for 24 hours. If a token names an unknown `kid`, the
backend refreshes JWKS once so normal provider key rotation can succeed. A
cooldown limits repeated refreshes caused by invalid tokens.

`OIDC_ISSUER` is a trusted deployment setting. It must not come from an API
request or token claim. Staging and production providers must publish discovery
and JWKS over HTTPS. A compromised identity provider or deployment
configuration is outside the protection a JWT verifier can provide because that
provider is the source of the trusted keys.

### FastAPI auth boundary

`app/service/auth/jwt_auth.py` extracts the bearer token, calls the discovery
client, checks any scopes requested by FastAPI, and converts the verified claims
into `User`.

Providers commonly use either `scp` or `scope`. Nachet reads both. Scope checks
run only when a route declares FastAPI security scopes. Existing routes that use
`Depends(get_current_user)` without declared scopes still require a valid token,
but they do not add a route-specific scope requirement.

Authentication failures return a Bearer `WWW-Authenticate` header. Invalid
tokens return HTTP 401. A valid token without a required scope returns HTTP 403.

## User identity

The OIDC adapter reads the user ID from `OIDC_USER_ID_CLAIM`, which defaults to
`sub`. The selected value must currently be a UUID because existing routes and
database services use `UUID(current_user.oid)`.

This is a compatibility rule, not the final identity model. A later change will
map the provider, issuer, and subject to an internal Nachet user ID.

Do not enable the OIDC path against an existing Entra production database until
that mapping exists. A UUID proves only that the claim has the expected format.
It does not separate identities issued by different providers.

The adapter stores the normalized UUID in `User.oid`. Raw provider claims remain
available through `User.claims`, but unknown claims do not automatically become
normal `User` attributes. Nachet-owned fields such as `access_token` and
`is_guest` are written after provider claims, so a token cannot replace them.

OIDC does not define a common guest/member claim. OIDC users therefore use the
restricted guest posture until claim mapping is designed.

## OIDC settings

```bash
AUTH_PROVIDER="oidc"
OIDC_ISSUER="https://<provider-issuer>"
OIDC_AUDIENCE="<nachet-api-audience>"
OIDC_USER_ID_CLAIM="sub"
OIDC_USERNAME_CLAIM="preferred_username"
OIDC_EMAIL_CLAIM="email"
```

`OIDC_ISSUER` and `OIDC_AUDIENCE` are required in OIDC mode. Blank claim names
are rejected. Optional configuration values are trimmed when settings load.

## Tests

Run the focused backend auth tests from `backend/`:

```bash
uv run pytest tests/test_oidc_token_verifier.py tests/test_oidc_discovery.py tests/test_oidc_backend_auth.py -q
```

The test groups cover:

- signed token and claim validation;
- discovery, JWKS shape, caching, and key refresh;
- provider selection and Entra compatibility;
- bearer header parsing and failure responses;
- UUID identity normalization;
- `scp` and `scope` handling;
- protection of Nachet-owned user fields.

## Current limits

- Local Keycloak startup and realm configuration are not included yet.
- External OIDC subjects are not yet mapped to internal Nachet user IDs.
- The OIDC path must not use an existing Entra production database until that
  identity mapping is implemented.
- Production OIDC endpoints must use HTTPS. The local-provider work still needs
  to define and enforce any loopback-only HTTP exception used for development.
- Existing routes do not currently declare route-specific FastAPI scopes.
- Microsoft Entra remains the official production path.
