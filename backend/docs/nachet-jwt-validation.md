# Nachet JWT Validation Process

This document explains the step-by-step JWT validation process in the Nachet backend, with code references for both supported authentication paths.

## Overview

Nachet validates protected API requests with either Microsoft Entra or a provider-neutral OpenID Connect (OIDC) provider. Microsoft Entra remains the default, and the backend has no unauthenticated mode.

Protected routes continue to depend on `get_current_user`. Provider selection happens inside `app/service/auth/jwt_auth.py`, so route handlers do not contain provider-specific code.

| `AUTH_PROVIDER` | Backend path |
| --- | --- |
| `azure` | Existing Microsoft Entra validation |
| `oidc` | Provider-neutral OIDC discovery and validation |

## Microsoft Entra Validation Flow

The existing Entra path remains unchanged.

### 1. Token Extraction

**File**: `auth.py:265-269`

```python
async def extract_access_token(self, request: HTTPConnection) -> Optional[str]:
    return await self.oauth(request=request)
```

This uses FastAPI's `OAuth2AuthorizationCodeBearer` to extract the `Bearer` token from the `Authorization` header.

### 2. Initial Token Parsing

**File**: `auth.py:164-177`

```python
try:
    if access_token is None:
        raise InvalidRequest('No access token provided', request=request)
    # Extract header information of the token.
    header: dict[str, Any] = get_unverified_header(access_token)
    claims: dict[str, Any] = get_unverified_claims(access_token)
except Exception as error:
    log.warning('Malformed token received. %s. Error: %s', access_token, error, exc_info=True)
    raise Unauthorized(detail='Invalid token format', ...)
```

**File**: `utils.py:19-30`

```python
def get_unverified_header(access_token: str) -> Dict[str, Any]:
    return dict(jwt.get_unverified_header(access_token))

def get_unverified_claims(access_token: str) -> Dict[str, Any]:
    return dict(jwt.decode(access_token, options={'verify_signature': False}))
```

This extracts the JWT header (contains `kid` - key ID) and claims without verifying the signature yet.

### 3. Guest User Check

**File**: `auth.py:179-182`

```python
user_is_guest: bool = is_guest(claims=claims)
if not self.allow_guest_users and user_is_guest:
    log.info('User denied, is a guest user', claims)
    raise Forbidden(detail='Guest users not allowed', request=request)
```

**File**: `utils.py:6-16`

```python
def is_guest(claims: Dict[str, Any]) -> bool:
    if claims.get('acct') == 1:
        return True
    # formula: idp exist and idp != iss: guest user
    claims_iss: str = claims.get('iss', '')
    idp: str = claims.get('idp', claims_iss)
    return idp != claims_iss
```

Checks if the user is a guest (external user invited to the tenant).

### 4. Scope Validation

**File**: `auth.py:184-192`

```python
for scope in security_scopes.scopes:
    token_scope_string = claims.get('scp', '')
    log.debug('Scopes: %s', token_scope_string)
    if not isinstance(token_scope_string, str):
        raise Forbidden('Token contains invalid formatted scopes', request=request)

    token_scopes = token_scope_string.split(' ')
    if scope not in token_scopes:
        raise Forbidden('Required scope missing', request=request)
```

Validates that the token contains all required scopes for the endpoint.

### 5. OpenID Configuration Loading

**File**: `auth.py:193-194`

```python
await self.openid_config.load_config()
```

**File**: `openid_config.py:34-56`

```python
async def load_config(self) -> None:
    refresh_time = datetime.now() - timedelta(hours=24)
    if not self._config_timestamp or self._config_timestamp < refresh_time:
        try:
            log.debug('Loading Azure Entra ID OpenID configuration.')
            await self._load_openid_config()
            self._config_timestamp = datetime.now()
```

Fetches Azure AD's public keys and configuration (refreshed every 24 hours).

### 6. Issuer Determination

**File**: `auth.py:196-199`

```python
if self.multi_tenant and self.validate_iss and self.iss_callable:
    iss = await self.iss_callable(tid=claims.get('tid'))
else:
    iss = self.openid_config.issuer
```

Determines the expected issuer based on tenant configuration.

### 7. Signing Key Lookup

**File**: `auth.py:202-203`

```python
if key := self.openid_config.signing_keys.get(header.get('kid', '')):
```

Uses the `kid` (key ID) from the JWT header to find the matching public key from Azure AD.

### 8. Token Signature Validation

**File**: `auth.py:204-219`

```python
required_claims = ['exp', 'aud', 'iat', 'nbf', 'sub']
if self.validate_iss:
    required_claims.append('iss')

options = {
    'verify_signature': True,
    'verify_aud': True,      # Validates audience (your app's client ID)
    'verify_iat': True,      # Validates issued at time
    'verify_exp': True,      # Validates expiration
    'verify_nbf': True,      # Validates not before time
    'verify_iss': self.validate_iss,  # Validates issuer
    'require': required_claims,
}
token = self.validate(access_token=access_token, iss=iss, key=key, options=options)
```

**File**: `auth.py:271-288`

```python
def validate(self, access_token: str, key: 'AllowedPublicKeys', iss: str, options: Dict[str, Any]) -> Dict[str, Any]:
    alg = 'RS256'
    return dict(
        jwt.decode(
            access_token,
            key=key,
            algorithms=[alg],
            audience=self.app_client_id,
            issuer=iss,
            leeway=self.leeway,
            options=options,
        )
    )
```

This is the core validation that:

- Verifies the token signature using Azure AD's public key
- Validates the token hasn't expired (`exp`)
- Validates the audience matches your app (`aud`)
- Validates the issuer is Azure AD (`iss`)

### 9. User Object Creation

**File**: `auth.py:220-225`

```python
user: User = User(
    **{**token, 'claims': token, 'access_token': access_token, 'is_guest': user_is_guest}
)
request.state.user = user
return user
```

Creates a `User` object containing all the validated claims and attaches it to the request.

### 10. Error Handling

**File**: `auth.py:226-246`

```python
except (
    InvalidAudienceError,     # Wrong app/audience
    InvalidIssuerError,       # Wrong tenant/issuer
    InvalidIssuedAtError,     # Invalid timestamp
    ImmatureSignatureError,   # Token not yet valid (nbf)
    MissingRequiredClaimError # Missing required claims
) as error:
    raise Unauthorized(detail='Token contains invalid claims', request=request)
except ExpiredSignatureError as error:
    raise Unauthorized(detail='Token signature has expired', request=request)
except InvalidTokenError as error:
    raise Unauthorized(detail='Unable to validate token', request=request)
```

Handles various JWT validation failures with appropriate error messages.

## Implementation in Nachet

### Protected Route Example

**File**: `routes.py:59-67`

```python
@router.get(
    "/seeds",
    status_code=status.HTTP_200_OK,
    name="Get Seed Data [AUTH REQUIRED]",
)
async def get_seed_data(current_user: User = Depends(get_current_user)):
    print(f"/seeds - authenticated user: {current_user.oid}")
    seed_data = await SeedService.get_seed_data()
    return seed_data
```

### JWT Authenticator Setup

**File**: `jwt_auth.py:31-35`

```python
self._auth_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=client_id,
    tenant_id=tenant_id,
    auto_error=True,
)
```

## Flow Summary for `/seeds` Endpoint

1. **Request arrives** at `/seeds` with `Authorization: Bearer <jwt_token>`
2. **Dependency triggers** `get_current_user` dependency triggers JWT validation
3. **Token extraction** from Authorization header
4. **Claims parsing** (unverified) to extract header and payload
5. **Guest check** validates user is not a guest (if configured)
6. **Scope validation** ensures token has required permissions
7. **Config loading** fetches Azure AD public keys (cached for 24h)
8. **Key lookup** finds signing key using `kid` from JWT header
9. **Signature validation** verifies token signature and claims
10. **User creation** `User` object is created and returned
11. **Route execution** handler receives authenticated user: `current_user.oid`

## Required Environment Variables

```bash
AZURE_CLIENT_ID="your-azure-client-id"
AZURE_TENANT_ID="your-tenant-id"
```

## Security Features

- **Signature verification** using Azure AD's public keys
- **Token expiration** validation
- **Audience validation** ensures token is for this application
- **Issuer validation** ensures token comes from correct Azure AD tenant
- **Scope validation** for fine-grained permissions
- **Guest user filtering** (configurable)
- **Automatic key rotation** support through OpenID Connect discovery

## Provider-neutral OIDC validation flow

The OIDC path uses the same `get_current_user` route dependency but separates
configuration, provider metadata loading, token verification, and user
normalization.

### Startup configuration

OIDC mode requires a nonblank issuer and audience:

```bash
AUTH_PROVIDER="oidc"
OIDC_ISSUER="https://<provider-issuer>"
OIDC_AUDIENCE="<nachet-api-audience>"
OIDC_USER_ID_CLAIM="sub"
OIDC_USERNAME_CLAIM="preferred_username"
OIDC_EMAIL_CLAIM="email"
```

The backend auth configuration validates this contract when the authenticator
is created during application startup. Azure mode does not require OIDC
settings.

### Endpoint policy

`app/service/auth/oidc_endpoint.py` validates the configured issuer and the
discovered `jwks_uri` with `httpx.URL`, the same URL parser used for the network
requests.

OIDC endpoints must use HTTPS. The issuer cannot contain credentials,
a query string, or a fragment. Normal HTTPX certificate verification remains
enabled for HTTPS requests.

### Discovery and JWKS loading

`app/service/auth/oidc_discovery.py` loads metadata from:

```text
<OIDC_ISSUER>/.well-known/openid-configuration
```

The discovery response must return the exact configured issuer and a valid
`jwks_uri`. The JWKS response must be a JSON object with a `keys` array as
defined by RFC 7517.

The client caches the verifier for 24 hours. If a token names an unknown `kid`,
the client refreshes JWKS once so provider key rotation can succeed. A cooldown
limits refresh traffic caused by repeated invalid key IDs. Concurrent refreshes
share one lock.

The configured issuer is trusted deployment input. It never comes from a token
or API request. If the provider or deployment configuration is compromised, an
application-side JWT verifier cannot restore that trust boundary.

### Access-token verification

`app/service/auth/oidc_token_verifier.py` uses PyJWT and the trusted public key
selected by `kid`. It verifies:

- the token signature;
- the configured issuer and audience;
- the allowed signing algorithm;
- the `exp`, `iat`, and `nbf` time claims;
- required claims, including `iss`, `aud`, and `sub`.

The identity provider controls token lifetime through `exp`. Nachet does not
create or extend that lifetime.

### Scope checks

OIDC providers commonly use either `scp` or `scope`. Nachet reads both. A route
that declares FastAPI security scopes requires every declared scope. Existing
routes that use `Depends(get_current_user)` still require authentication but do
not add a route-specific scope requirement.

### User normalization

The OIDC adapter reads the user ID from `OIDC_USER_ID_CLAIM`, which defaults to
`sub`. The value must currently be a UUID because existing routes and database
services call `UUID(current_user.oid)`.

This is a temporary compatibility rule. A later schema change will map the
provider issuer and subject to an internal Nachet user ID. Until then, do not
enable OIDC against an existing Entra production database.

Raw provider claims remain available through `User.claims`, but unknown claims
do not become normal `User` attributes. Nachet writes `access_token` and
`is_guest` after provider claims so token content cannot replace those fields.

OIDC does not define one guest/member claim. Generic OIDC users therefore use
the restricted guest posture until claim mapping is designed.

### HTTP failure responses

The OIDC auth boundary separates failures by meaning:

| Status | Meaning |
| --- | --- |
| `401 Unauthorized` | The request has no usable bearer token or the token is invalid. |
| `403 Forbidden` | The token is valid but lacks a required scope. |
| `503 Service Unavailable` | Discovery or JWKS could not be loaded or trusted. |

Invalid tokens return `WWW-Authenticate: Bearer error="invalid_token"`. Missing
scopes return `Bearer error="insufficient_scope"` with the missing scope names.
A provider outage does not claim that the user's token is invalid.

## OIDC tests

Run the focused backend auth tests from `backend/`:

```bash
uv run pytest tests/test_oidc_token_verifier.py tests/test_oidc_discovery.py tests/test_oidc_backend_auth.py -q
```

The tests cover token validation, discovery and JWKS shape, cache refresh,
provider selection, endpoint policy, bearer parsing, scope handling, UUID
identity compatibility, and protection of Nachet-owned user fields.

## Current limits

- Local Keycloak startup and realm configuration belong to Backend D.
- External OIDC subjects are not yet mapped to internal Nachet user IDs.
- OIDC must not use an existing Entra production database until that identity
  mapping exists.
- Existing routes do not currently declare route-specific FastAPI scopes.
- Microsoft Entra remains the official production path.
