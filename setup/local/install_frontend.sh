#!/bin/bash

# VirtualPyTest - Install Frontend
# This script installs frontend dependencies

set -e

echo "⚛️ Installing VirtualPyTest Frontend..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
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

echo "✅ Frontend installation completed!"
echo "🚀 You can now run: ./setup/local/launch_frontend.sh" 