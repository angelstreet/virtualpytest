#!/bin/bash

# VirtualPyTest - Install Backend-Host
# This script installs backend-host dependencies

set -e

echo "🔧 Installing VirtualPyTest Backend-Host..."

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-host" ]; then
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

# Install backend-core (required by backend-host)
echo "⚙️ Installing backend-core (required dependency)..."
cd backend-core
pip install -e . --use-pep517
cd ..

# Install backend-host dependencies
echo "📦 Installing backend-host dependencies..."
cd backend-host
pip install -r requirements.txt

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

# Install systemd service
echo "🔧 Installing systemd service..."
SERVICE_NAME="virtualpytest-backend-host"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Create systemd service file
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=VirtualPyTest Backend-Host Service (Hardware Interface)
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)/backend-host
Environment=PATH=$(pwd)/venv/bin:/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$(pwd)/venv/lib/python*/site-packages:$(pwd)/shared/lib:$(pwd)/backend-core/src
ExecStart=$(pwd)/venv/bin/python src/app.py
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

echo "✅ Backend-Host installation completed!"
echo "✅ Systemd service '$SERVICE_NAME' created and enabled"
echo "🚀 You can now run: ./setup/local/launch_host.sh" 