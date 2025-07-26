#!/bin/bash

# VirtualPyTest - Install Shared Library
# This script installs the shared library dependencies

set -e

echo "📚 Installing VirtualPyTest Shared Library..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Install shared library
echo "📦 Installing shared library..."
cd shared
pip install -e . --use-pep517
cd ..

echo "✅ Shared library installation completed!" 