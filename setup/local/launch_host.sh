#!/bin/bash

# VirtualPyTest - Launch Backend-Host Only
# This script starts only the backend-host service

set -e

echo "🔧 Launching VirtualPyTest - Backend-Host Only"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-host" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "backend-host/venv" ] && ! python -c "import flask" 2>/dev/null; then
    echo "❌ Dependencies not installed. Please run: ./setup/local/install_local.sh"
    exit 1
fi

# Navigate to backend-host directory
cd backend-host

echo "🚀 Starting Backend-Host on http://localhost:6109"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the host service
python src/app.py 