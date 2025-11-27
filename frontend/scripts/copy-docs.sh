#!/bin/bash

# Script to copy only necessary documentation files to frontend/public/docs
# - OpenAPI HTML docs (original)
# - New markdown READMEs only (for documentation wrapper)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Copying documentation files...${NC}"

# Clean and create target directory
rm -rf public/docs
mkdir -p public/docs

# 1. Copy OpenAPI HTML docs (original - what you had before)
echo -e "${GREEN}✓${NC} Copying OpenAPI HTML docs"
mkdir -p public/docs/api/openapi
cp -r ../docs/api/openapi/docs/* public/docs/api/openapi/

# 2. Copy only README.md files (new documentation wrapper)
echo -e "${GREEN}✓${NC} Copying documentation READMEs"

# Main docs README
cp ../docs/README.md public/docs/

# Section READMEs
mkdir -p public/docs/get-started
cp ../docs/get-started/README.md public/docs/get-started/ 2>/dev/null || true

mkdir -p public/docs/features
cp ../docs/features/README.md public/docs/features/ 2>/dev/null || true

mkdir -p public/docs/user-guide
cp ../docs/user-guide/README.md public/docs/user-guide/ 2>/dev/null || true

mkdir -p public/docs/technical
cp ../docs/technical/README.md public/docs/technical/ 2>/dev/null || true

mkdir -p public/docs/api
cp ../docs/api/README.md public/docs/api/ 2>/dev/null || true

mkdir -p public/docs/examples
cp ../docs/examples/README.md public/docs/examples/ 2>/dev/null || true

mkdir -p public/docs/integrations
cp ../docs/integrations/README.md public/docs/integrations/ 2>/dev/null || true

echo -e "${GREEN}✓ Documentation copied successfully!${NC}"
echo -e "${BLUE}Copied: OpenAPI HTML docs (15 files) + Section READMEs (8 files)${NC}"

