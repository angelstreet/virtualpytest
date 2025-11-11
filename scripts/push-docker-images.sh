#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat ../.env | grep -E '^(GITHUB_USERNAME|GITHUB_PAT)=' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if required variables are set
if [ -z "$GITHUB_USERNAME" ] || [ -z "$GITHUB_PAT" ]; then
    echo "Error: GITHUB_USERNAME or GITHUB_PAT not found in .env file"
    exit 1
fi

echo "🔐 Logging in to GitHub Container Registry..."
echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to GHCR"
    exit 1
fi

echo ""
echo "🏗️  Building virtualpytest-host for linux/amd64..."
docker buildx build \
  --platform linux/amd64 \
  --tag ghcr.io/$GITHUB_USERNAME/virtualpytest-host:latest \
  --file backend_host/Dockerfile \
  --push \
  .

if [ $? -ne 0 ]; then
    echo "❌ Failed to build virtualpytest-host"
    exit 1
fi

echo ""
echo "🏗️  Building virtualpytest-server for linux/amd64..."
docker buildx build \
  --platform linux/amd64 \
  --tag ghcr.io/$GITHUB_USERNAME/virtualpytest-server:latest \
  --file backend_server/Dockerfile \
  --push \
  .

if [ $? -ne 0 ]; then
    echo "❌ Failed to build virtualpytest-server"
    exit 1
fi

echo ""
echo "✅ Successfully pushed both images!"
echo ""
echo "Images available at:"
echo "  - ghcr.io/$GITHUB_USERNAME/virtualpytest-host:latest"
echo "  - ghcr.io/$GITHUB_USERNAME/virtualpytest-server:latest"
echo ""
echo "✅ Compatible with Render (linux/amd64)"

