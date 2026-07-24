#!/bin/sh
set -eu

KEYCLOAK_HOST="keycloak.localhost"
SCRIPT_DIRECTORY=$(CDPATH='' cd "$(dirname "$0")" && pwd)
SERVER_CERT_DIRECTORY="$SCRIPT_DIRECTORY/local-certs/server"
CA_CERT_DIRECTORY="$SCRIPT_DIRECTORY/local-certs/ca"

if ! command -v mkcert >/dev/null 2>&1; then
    printf '%s\n' "mkcert is required. Install it, then run this script again." >&2
    exit 1
fi

mkdir -p "$SERVER_CERT_DIRECTORY" "$CA_CERT_DIRECTORY"

mkcert -install
mkcert \
    -cert-file "$SERVER_CERT_DIRECTORY/keycloak.pem" \
    -key-file "$SERVER_CERT_DIRECTORY/keycloak-key.pem" \
    "$KEYCLOAK_HOST"

CA_ROOT=$(mkcert -CAROOT)
if [ ! -f "$CA_ROOT/rootCA.pem" ]; then
    printf 'mkcert did not create %s/rootCA.pem\n' "$CA_ROOT" >&2
    exit 1
fi

# The backend needs the public CA certificate. The CA private key stays in
# mkcert's local store and must never be copied into the repository.
cp "$CA_ROOT/rootCA.pem" "$CA_CERT_DIRECTORY/rootCA.pem"
chmod 600 "$SERVER_CERT_DIRECTORY/keycloak-key.pem"

printf 'Created a trusted certificate for https://%s:8443\n' "$KEYCLOAK_HOST"
