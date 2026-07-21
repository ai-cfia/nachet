#!/bin/sh
set -eu

SCRIPT_DIRECTORY=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH='' cd -- "$SCRIPT_DIRECTORY/.." && pwd)
CA_CERTIFICATE="$SCRIPT_DIRECTORY/local-certs/ca/rootCA.pem"
EXPECTED_ISSUER="https://keycloak.localhost:8443/realms/nachet"
DISCOVERY_URL="$EXPECTED_ISSUER/.well-known/openid-configuration"

if [ ! -f "$CA_CERTIFICATE" ]; then
    printf '%s\n' "Local CA certificate not found. Run keycloak/setup_local_tls.sh first." >&2
    exit 1
fi

docker compose --project-directory "$REPOSITORY_ROOT" --profile oidc config --quiet
DISCOVERY_DOCUMENT=$(
    curl --fail --silent --show-error --cacert "$CA_CERTIFICATE" "$DISCOVERY_URL"
)

if ! printf '%s' "$DISCOVERY_DOCUMENT" | grep -F "\"issuer\":\"$EXPECTED_ISSUER\"" >/dev/null; then
    printf 'Keycloak discovery did not return the expected issuer: %s\n' "$EXPECTED_ISSUER" >&2
    exit 1
fi

# Each local frontend URL must be accepted as both a login redirect and a
# browser origin for the token exchange.
for FRONTEND_ORIGIN in \
    "http://localhost:5173" \
    "http://localhost:5174" \
    "http://localhost:12435" \
    "http://localhost:12436"
do
    STATUS_CODE=$(
        curl --silent --show-error \
            --cacert "$CA_CERTIFICATE" \
            --output /dev/null \
            --write-out '%{http_code}' \
            --get "$EXPECTED_ISSUER/protocol/openid-connect/auth" \
            --data-urlencode 'client_id=nachet-frontend' \
            --data-urlencode "redirect_uri=$FRONTEND_ORIGIN" \
            --data-urlencode 'response_type=code' \
            --data-urlencode 'scope=openid' \
            --data-urlencode 'code_challenge=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
            --data-urlencode 'code_challenge_method=S256'
    )

    if [ "$STATUS_CODE" != "200" ]; then
        printf 'Keycloak rejected the frontend redirect URI %s with HTTP %s.\n' \
            "$FRONTEND_ORIGIN" "$STATUS_CODE" >&2
        exit 1
    fi

    CORS_HEADERS=$(
        curl --silent --show-error \
            --cacert "$CA_CERTIFICATE" \
            --dump-header - \
            --output /dev/null \
            --header "Origin: $FRONTEND_ORIGIN" \
            --header 'Content-Type: application/x-www-form-urlencoded' \
            --data-urlencode 'client_id=nachet-frontend' \
            --data-urlencode 'grant_type=authorization_code' \
            --data-urlencode 'code=not-a-real-code' \
            --data-urlencode "redirect_uri=$FRONTEND_ORIGIN" \
            "$EXPECTED_ISSUER/protocol/openid-connect/token"
    )

    if ! printf '%s' "$CORS_HEADERS" \
        | grep -i -F "access-control-allow-origin: $FRONTEND_ORIGIN" >/dev/null
    then
        printf 'Keycloak rejected the frontend web origin %s.\n' \
            "$FRONTEND_ORIGIN" >&2
        exit 1
    fi
done

UNTRUSTED_ORIGIN_STATUS=$(
    curl --silent --show-error \
        --cacert "$CA_CERTIFICATE" \
        --output /dev/null \
        --write-out '%{http_code}' \
        --header 'Origin: http://untrusted.example' \
        --header 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode 'client_id=nachet-frontend' \
        --data-urlencode 'grant_type=authorization_code' \
        --data-urlencode 'code=not-a-real-code' \
        --data-urlencode 'redirect_uri=http://localhost:5173' \
        "$EXPECTED_ISSUER/protocol/openid-connect/token"
)

if [ "$UNTRUSTED_ORIGIN_STATUS" != "403" ]; then
    printf 'Keycloak accepted an unlisted frontend origin with HTTP %s.\n' \
        "$UNTRUSTED_ORIGIN_STATUS" >&2
    exit 1
fi

printf '%s\n' "Local Keycloak HTTPS, redirects, and browser origins are working."
