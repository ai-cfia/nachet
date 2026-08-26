#!/usr/bin/env bash

set -euo pipefail

version="${1:?usage: install-argo-cli.sh VERSION DESTINATION}"
destination="${2:?usage: install-argo-cli.sh VERSION DESTINATION}"

if [[ "$(uname -s)" != "Linux" ]]; then
  printf 'unsupported runner operating system: %s\n' "$(uname -s)" >&2
  exit 1
fi

case "${version}:$(uname -m)" in
  v4.1.1:x86_64)
    architecture=amd64
    checksum=1d8c374916a2f172f1019c8c38653a1678abcbdc03f53df1e27fae391b250b3b
    ;;
  v4.1.1:aarch64|v4.1.1:arm64)
    architecture=arm64
    checksum=3d395d46449cfbd153e459f61c52f87c666a2b207f2a1bbf17856d5b0384df3f
    ;;
  *)
    printf 'unsupported Argo version or runner architecture: %s / %s\n' \
      "$version" "$(uname -m)" >&2
    exit 1
    ;;
esac

archive="${destination}.gz"
trap 'rm -f "$archive"' EXIT

curl --fail --location --silent --show-error \
  --output "$archive" \
  "https://github.com/argoproj/argo-workflows/releases/download/${version}/argo-linux-${architecture}.gz"
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status
gzip --decompress --stdout "$archive" > "$destination"
chmod +x "$destination"
