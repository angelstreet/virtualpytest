#!/bin/bash

# VirtualPyTest - Install backend_host
# This script installs backend_host dependencies

set -e

echo "🔧 Installing VirtualPyTest backend_host..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend_host" ]; then
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

# Install backend_core (required by backend_host)
echo "⚙️ Installing backend_core (required dependency)..."
cd backend_core
pip install -r requirements.txt
cd ..

# Install backend_host dependencies
echo "📦 Installing backend_host dependencies..."
cd backend_host
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

echo "✅ backend_host installation completed!"
echo "🚀 You can now run: ./setup/local/launch_host.sh" 