#!/bin/bash

# VirtualPyTest - Install backend_server
# This script installs backend_server dependencies

set -e

echo "🖥️ Installing VirtualPyTest backend_server..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend_server" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Skip shared library installation - using direct imports instead
echo "📚 Shared library will be used via direct imports..."

# Skip backend_core installation - using direct imports instead
echo "⚙️ Backend_core will be used via direct imports..."

# Install backend_server dependencies
echo "📦 Installing backend_server dependencies..."
cd backend_server
pip install -r requirements.txt

# Create .env file in src/ directory if it doesn't exist
cd src
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env file from .env.example..."
        cp .env.example .env
        echo "✅ Created .env file - please configure it with your settings"
    else
        echo "⚠️ No .env.example found - please create .env manually"
    fi
else
    echo "✅ .env file already exists"
fi

cd ../..

echo "✅ backend_server installation completed!"
echo "🚀 You can now run: ./setup/local/launch_server.sh" 