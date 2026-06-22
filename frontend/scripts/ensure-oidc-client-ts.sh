#!/bin/sh
set -eu

OIDC_CLIENT_DIR="submodules/oidc-client-ts"
OIDC_CLIENT_ENTRY="$OIDC_CLIENT_DIR/src/index.ts"
OIDC_CLIENT_REPO="https://github.com/ai-cfia/oidc-client-ts.git"
OIDC_CLIENT_COMMIT="50bf3745523a609f1448fd23fc772a56c43b4a57"

if [ -f "$OIDC_CLIENT_ENTRY" ]; then
  exit 0
fi

echo "Initializing oidc-client-ts frontend submodule..."

if git -C .. rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C .. submodule update --init --recursive frontend/submodules/oidc-client-ts || true
fi

if [ -f "$OIDC_CLIENT_ENTRY" ]; then
  exit 0
fi

echo "Submodule content is unavailable; cloning pinned oidc-client-ts fork..."
rm -rf "$OIDC_CLIENT_DIR"
git clone "$OIDC_CLIENT_REPO" "$OIDC_CLIENT_DIR"
git -C "$OIDC_CLIENT_DIR" checkout "$OIDC_CLIENT_COMMIT"

if [ ! -f "$OIDC_CLIENT_ENTRY" ]; then
  echo "oidc-client-ts source was not found at $OIDC_CLIENT_ENTRY" >&2
  exit 1
fi
