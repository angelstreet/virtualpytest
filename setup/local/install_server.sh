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

# Install systemd service
echo "🔧 Installing systemd service..."
SERVICE_NAME="virtualpytest-backend-server"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Create systemd service file
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=VirtualPyTest Backend-Server Service (API Server)
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/backend-server
Environment=PATH=/usr/bin:/usr/local/bin:$(pwd)/venv/bin
ExecStart=$(which python) src/app.py
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

echo "✅ Backend-Server installation completed!"
echo "✅ Systemd service '$SERVICE_NAME' created and enabled"
echo "🚀 You can now run: ./setup/local/launch_server.sh" 