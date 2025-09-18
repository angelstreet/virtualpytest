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

# Skip shared library installation - using direct imports instead
echo "📚 Shared library will be used via direct imports..."

# Skip backend_core installation - using direct imports instead
echo "⚙️ Backend_core will be used via direct imports..."

# Install system dependencies for IR remote control
echo "🔧 Installing IR remote control tools..."
sudo apt-get update
sudo apt-get install -y lirc v4l-utils ir-keytable
echo "✅ IR tools installed - ir-ctl and lircd commands available"
echo "💡 Commands: ir-ctl --send <file>, ir-ctl --read, and lircd"

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

# Configure firewall ports for backend_host
echo "🔥 Configuring firewall for backend_host..."

# Source port checking functions
source "$PROJECT_ROOT/setup/local/check_and_open_port.sh"

# Get HOST_PORT from backend_host .env file (default 6109)
HOST_ENV_FILE="$PROJECT_ROOT/backend_host/src/.env"
HOST_PORT=$(get_port_from_env "$HOST_ENV_FILE" "HOST_PORT" "6109")

echo "🔧 Configuring firewall for backend_host ports:"
echo "   - Backend Host API: $HOST_PORT"

# Configure UFW for backend_host ports
check_and_open_port "$HOST_PORT" "backend_host API" "tcp"

echo "✅ backend_host installation completed!"
echo "🚀 You can now run: ./setup/local/launch_host.sh" 