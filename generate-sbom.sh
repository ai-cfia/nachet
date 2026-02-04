#!/bin/bash

# Generate SBOM (Software Bill of Materials) for a Python project using uv
# Usage: ./generate-sbom.sh <directory>
# Example: ./generate-sbom.sh backend
# Example: ./generate-sbom.sh datastore
# Example: ./generate-sbom.sh frontend
# Example: ./generate-sbom.sh /path/to/project
# 
# This script creates a reproducible environment using Docker with Ubuntu 24.04
# and generates an SBOM in CycloneDX format (sbom.json) in the target directory.
# Run this whenever project version or dependencies change in pyproject.toml.

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

# Determine project type and run appropriate SBOM generation
if [[ "$(basename "$PROJECT_DIR")" == "frontend" ]]; then
    echo "Detected Node.js/npm project"
    
    # Extract Node.js and npm versions from package.json
    if [[ -f "$PROJECT_DIR/package.json" ]]; then
        NODE_VERSION=$(grep -o '"node": "[^"]*"' "$PROJECT_DIR/package.json" | sed 's/"node": "//; s/"//; s/\^//; s/~//; s/>=//')
        NPM_VERSION=$(grep -o '"npm": "[^"]*"' "$PROJECT_DIR/package.json" | sed 's/"npm": "//; s/"//; s/\^//; s/~//; s/>=//')
        
        # Default versions if not found
        NODE_VERSION=${NODE_VERSION:-"20"}
        NPM_VERSION=${NPM_VERSION:-"10"}
        
        echo "Using Node.js version: $NODE_VERSION"
        echo "Using npm version: $NPM_VERSION"
    else
        echo "package.json not found, using default versions"
        exit 1
    fi

    # delete existing node_modules to ensure clean install
    sudo rm -rf "$PROJECT_DIR/node_modules"
    
    # Generate SBOM for npm/Node.js project using versions from package.json engines
    docker run --rm -v "$PROJECT_DIR":/app -w /app ubuntu:24.04 sh -c "\
      apt update && \
      apt install -y curl git && \
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash && \
      export NVM_DIR=\"\$HOME/.nvm\" && \
      [ -s \"\$NVM_DIR/nvm.sh\" ] && \. \"\$NVM_DIR/nvm.sh\" && \
      nvm install $NODE_VERSION && \
      nvm use $NODE_VERSION && \
      npm install -g npm@$NPM_VERSION && \
      npm install && npm update &&\
      npx cyclonedx-npm package-lock.json --output-reproducible --package-lock-only -v --sv 1.6 -o sbom.json && echo '' >> sbom.json"
    
    # chown node_modules to avoid permission issues
    sudo chown -R 1000:1000 "$PROJECT_DIR/"
else
    echo "Detected Python/uv project"
    # Generate SBOM for Python/uv project
    docker run --rm -v "$PROJECT_DIR":/app -w /app ubuntu:24.04 sh -c "\
      apt update && \
      apt install -y curl git build-essential python3-dev libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1-dev && \
      curl -LsSf https://astral.sh/uv/install.sh | sh && \
      /root/.local/bin/uv sync --group dev --group sbom && \
      /root/.local/bin/uv lock && \
      /root/.local/bin/uv run cyclonedx-py environment --output-reproducible -v --sv 1.6 --pyproject pyproject.toml -o sbom.json && \
      echo "" >> sbom.json"
    
    sudo chown -R 1000:1000 "$PROJECT_DIR/.venv"
fi
