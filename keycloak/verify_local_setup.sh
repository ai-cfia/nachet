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

printf '%s\n' "Local Keycloak configuration and HTTPS discovery are working."
