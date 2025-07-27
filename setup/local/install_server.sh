#!/bin/bash

# VirtualPyTest - Install Backend-Server
# This script installs backend-server dependencies

set -e

echo "🖥️ Installing VirtualPyTest Backend-Server..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-server" ]; then
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

# Install shared library first (dependency)
echo "📚 Installing shared library (required dependency)..."
cd shared
pip install -e . --use-pep517
cd ..

# Install backend-core (required by backend-server for controller imports)
echo "⚙️ Installing backend-core (required dependency)..."
cd backend-core
pip install -r requirements.txt
cd ..

# Install backend-server dependencies
echo "📦 Installing backend-server dependencies..."
cd backend-server
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

echo "✅ Backend-Server installation completed!"
echo "🚀 You can now run: ./setup/local/launch_server.sh" 