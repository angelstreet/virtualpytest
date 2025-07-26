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

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install shared library
echo "📦 Installing shared library..."
cd shared
pip install -e . --use-pep517

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📝 Creating .env file from env.example..."
        cp env.example .env
        echo "✅ Created .env file - please configure it with your settings"
    else
        echo "⚠️ No env.example found - please create .env manually"
    fi
else
    echo "✅ .env file already exists"
fi

cd ..

echo "✅ Shared library installation completed!" 