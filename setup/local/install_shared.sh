#!/bin/bash

# VirtualPyTest - Install Shared Library
# This script installs the shared library dependencies

set -e

echo "📚 Installing VirtualPyTest Shared Library..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Install shared library
echo "📦 Installing shared library..."
cd shared
pip install -e . --use-pep517
cd ..

echo "✅ Shared library installation completed!" 