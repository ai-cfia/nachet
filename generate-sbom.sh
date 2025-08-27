#!/bin/bash

# Check if directory argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    echo "Example: $0 /path/to/project"
    exit 1
fi

PROJECT_DIR="$(realpath "$1")"

# Check if directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Directory '$PROJECT_DIR' does not exist"
    exit 1
fi

# uv run cyclonedx-py environment --output-reproducible -v --sv 1.6 --pyproject pyproject.toml -o sbom.json

docker run --rm -v "$PROJECT_DIR":/app -w /app ubuntu:24.04 sh -c "\
  apt update && \
  apt install -y curl git build-essential python3-dev libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1-dev && \
  curl -LsSf https://astral.sh/uv/install.sh | sh && \
  /root/.local/bin/uv sync && \
  /root/.local/bin/uv lock && \
  /root/.local/bin/uv run cyclonedx-py environment --output-reproducible -v --sv 1.6 --pyproject pyproject.toml -o sbom.json && echo "" >> sbom.json"
