#!/bin/bash

# VirtualPyTest - Install Backend-Host
# This script installs backend-host dependencies

set -e

echo "🔧 Installing VirtualPyTest Backend-Host..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-host" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Install shared library first (dependency)
echo "📚 Installing shared library (required dependency)..."
cd shared
pip install -e . --use-pep517
cd ..

# Install backend-core (required by backend-host)
echo "⚙️ Installing backend-core (required dependency)..."
cd backend-core
pip install -e . --use-pep517
cd ..

# Install backend-host dependencies
echo "📦 Installing backend-host dependencies..."
cd backend-host
pip install -r requirements.txt
cd ..

echo "✅ Backend-Host installation completed!"
echo "🚀 You can now run: ./setup/local/launch_host.sh" 