#!/bin/sh

set -eu

output_path="${OUTPUT_PATH:-/tmp/dataset-name}"

if [ -z "$(printf '%s' "${DATASET_NAME:-}" | tr -d '[:space:]')" ]; then
  printf 'dataset-name must not be empty\n' >&2
  exit 1
fi

printf '%s' "$DATASET_NAME" > "$output_path"
printf 'stage=%s dataset=%s\n' "$STAGE" "$DATASET_NAME"
