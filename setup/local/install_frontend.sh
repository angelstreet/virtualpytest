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
echo "📦 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "🔧 Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
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
cd ..

# Install systemd service for frontend (optional, since it's typically for development)
echo "🔧 Installing systemd service..."
SERVICE_NAME="virtualpytest-frontend"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Create systemd service file
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=VirtualPyTest Frontend Service (React Development Server)
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/frontend
Environment=PATH=/usr/bin:/usr/local/bin:/usr/local/lib/nodejs/node-v18.x.x-linux-x64/bin
ExecStart=$(which npm) run dev
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "✅ Frontend installation completed!"
echo "✅ Systemd service '$SERVICE_NAME' created and enabled"
echo "🚀 You can now run: ./setup/local/launch_frontend.sh" 