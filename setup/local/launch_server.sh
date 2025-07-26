#!/bin/bash

# VirtualPyTest - Launch Backend-Server Only
# This script starts only the backend-server service

set -e

echo "🖥️ Launching VirtualPyTest - Backend-Server Only"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend-server" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "backend-server/venv" ] && ! python -c "import flask" 2>/dev/null; then
    echo "❌ Dependencies not installed. Please run: ./setup/local/install_local.sh"
    exit 1
fi

# Navigate to backend-server directory
cd backend-server

echo "🚀 Starting Backend-Server on http://localhost:5109"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the server
python src/app.py 