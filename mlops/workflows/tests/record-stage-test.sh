#!/bin/sh

set -eu

test_directory="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
script="$test_directory/../scripts/record-stage.sh"
temporary_directory="$(mktemp -d)"
trap 'rm -rf "$temporary_directory"' EXIT HUP INT TERM

valid_output="$temporary_directory/dataset-name"
valid_log="$temporary_directory/valid.log"
OUTPUT_PATH="$valid_output" \
  STAGE="input-validated" \
  DATASET_NAME="seed-lab-batch-1" \
  "$script" > "$valid_log"

test "$(cat "$valid_output")" = "seed-lab-batch-1"
grep -Fx \
  "stage=input-validated dataset=seed-lab-batch-1" \
  "$valid_log" > /dev/null

invalid_error="$temporary_directory/invalid.err"
if OUTPUT_PATH="$temporary_directory/invalid-output" \
  STAGE="input-validated" \
  DATASET_NAME="   " \
  "$script" 2> "$invalid_error"; then
  printf 'expected an empty dataset name to fail\n' >&2
  exit 1
fi

grep -Fx "dataset-name must not be empty" "$invalid_error" > /dev/null
test ! -e "$temporary_directory/invalid-output"
