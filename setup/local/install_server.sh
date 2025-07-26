#!/bin/bash

# VirtualPyTest - Install Backend-Server
# This script installs backend-server dependencies

set -e

echo "🖥️ Installing VirtualPyTest Backend-Server..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-server" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Install shared library first (dependency)
echo "📚 Installing shared library (required dependency)..."
cd shared
pip install -e . --use-pep517
cd ..

# Install backend-server dependencies
echo "📦 Installing backend-server dependencies..."
cd backend-server
pip install -r requirements.txt
cd ..

echo "✅ Backend-Server installation completed!"
echo "🚀 You can now run: ./setup/local/launch_server.sh" 