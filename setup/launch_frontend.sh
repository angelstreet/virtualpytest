#!/bin/bash

# VirtualPyTest - Launch Frontend Only
# This script starts only the frontend service

set -e

echo "⚛️ Launching VirtualPyTest - Frontend Only"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please run: ./setup/install_local.sh"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Dependencies not installed. Please run: ./setup/install_local.sh"
    exit 1
fi

# Navigate to frontend directory
cd frontend

echo "🚀 Starting Frontend on http://localhost:3000"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the frontend development server
npm run dev 