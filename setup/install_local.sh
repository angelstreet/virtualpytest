#!/bin/bash

# VirtualPyTest - Local Development Setup Script
# This script installs all dependencies for local development

set -e

echo "🔧 Setting up VirtualPyTest for local development..."

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Please run this script from the virtualpytest root directory"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."

# Install shared library
echo "📚 Installing shared library..."
cd shared
pip install -e . --use-pep517
cd ..

# Install backend-server dependencies
echo "🖥️ Installing backend-server dependencies..."
cd backend-server
pip install -r requirements.txt
cd ..

# Install backend-host dependencies
echo "🔧 Installing backend-host dependencies..."
cd backend-host
pip install -r requirements.txt
cd ..

# Install backend-core dependencies
echo "⚙️ Installing backend-core dependencies..."
cd backend-core
pip install -e . --use-pep517
cd ..

# Install Node.js dependencies for frontend
echo "⚛️ Installing frontend dependencies..."
cd frontend

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first:"
    echo "   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
    echo "   sudo apt-get install -y nodejs"
    exit 1
fi

npm install
cd ..

echo ""
echo "🎉 Local development setup completed!"
echo "🚀 You can now run individual services:"
echo "   ./setup/launch_server.sh    - Start backend-server only"
echo "   ./setup/launch_host.sh      - Start backend-host only"
echo "   ./setup/launch_frontend.sh  - Start frontend only"
echo "   ./setup/launch_all.sh       - Start all services with Docker" 