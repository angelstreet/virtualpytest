#!/bin/bash

# VirtualPyTest - Install Frontend
# This script installs frontend dependencies

set -e

echo "⚛️ Installing VirtualPyTest Frontend..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "frontend" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Install Node.js and npm if not present
# NOTE: This script requires Node.js 20+
# If you have Node.js 18 or older, update it by running:
#   sudo apt-get remove -y nodejs npm
#   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
#   sudo apt-get install -y nodejs
echo "📦 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "🔧 Installing Node.js 20..."
    # Install on Linux
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "✅ Node.js installed successfully"
else
    echo "✅ Node.js is already installed ($(node --version))"
fi

# Verify npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not available after Node.js installation"
    exit 1
fi

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install

# Create .env file if it doesn't exist
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

cd ..

# Configure firewall ports for frontend
echo "🔥 Configuring firewall for frontend..."

# Source port checking functions
source "$PROJECT_ROOT/setup/local/check_and_open_port.sh"

echo "🔧 Configuring firewall for frontend ports:"
echo "   - Frontend (prod): 5073"

# Configure UFW for frontend ports
check_and_open_port "5073" "frontend production" "tcp"

echo "✅ Frontend installation completed!"
echo "🚀 You can now run: ./setup/local/launch_frontend.sh" 