#!/bin/bash
set -e

# Log the environment variables being used (without exposing sensitive values)
echo "Building application with runtime environment variables..."
echo "Using VITE_BACKEND_URL: ${VITE_BACKEND_URL:-/api}"
echo "Using PUBLIC_URL: ${PUBLIC_URL:-.}"

# Copy into writable folder
cp -r . /app/
cd /app

# Export the environment variables so they're available to the build process
export VITE_BACKEND_URL=${VITE_BACKEND_URL:-/api}
export PUBLIC_URL=${PUBLIC_URL:-.}

# Install dependencies if node_modules doesn't exist
echo "Installing dependencies..."
npm ci --include=dev

# Build the application with the current environment variables
echo "Building the application..."

# Directly run the build command without the prebuild hook
npx tsc && npx vite build

echo "Removing all files in node_modules..."

# Remove all files in node_modules
rm -rf node_modules/*

# Copy favicon if needed
if [ -f "./src/assets/CFIA_small_logo.ico" ]; then
  echo "Copying favicon..."
  cp ./src/assets/CFIA_small_logo.ico ./dist/favicon.ico
fi

# Serve the application
echo "Starting server on port 3000..."
npx serve -s dist
