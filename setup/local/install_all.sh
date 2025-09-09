#!/bin/bash

# VirtualPyTest - Install All Local Dependencies
# This script installs all dependencies for local development
# Usage: ./install_all.sh [--with-grafana]

set -e

# Parse command line arguments
INSTALL_GRAFANA=false
for arg in "$@"; do
    case $arg in
        --with-grafana)
            INSTALL_GRAFANA=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--with-grafana]"
            echo "  --with-grafana    Also install Grafana for local monitoring"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$INSTALL_GRAFANA" = true ]; then
    echo "🔧 Setting up VirtualPyTest for local development (with Grafana)..."
else
    echo "🔧 Setting up VirtualPyTest for local development..."
fi

# Get to project root directory (from setup/local to project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "shared" ]; then
    echo "❌ Could not find virtualpytest project root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Make all install scripts executable
chmod +x setup/local/install_*.sh

echo "🚀 Installing all components..."

# Install individual components
echo "1️⃣ Installing shared library..."
./setup/local/install_shared.sh

echo ""
echo "2️⃣ Installing backend_server..."
./setup/local/install_server.sh

echo ""
echo "3️⃣ Installing backend_host..."
./setup/local/install_host.sh

echo ""
echo "4️⃣ Installing frontend..."
./setup/local/install_frontend.sh

if [ "$INSTALL_GRAFANA" = true ]; then
    echo ""
    echo "5️⃣ Installing Grafana for monitoring..."
    ./setup/local/install_grafana.sh
fi

echo ""
echo "🎉 All components installed successfully!"
echo "🐍 Virtual environment created at: $(pwd)/venv"
echo "🔌 To activate manually: source venv/bin/activate"
echo ""
echo "📝 IMPORTANT: Configure your .env files before launching:"
echo "   backend_host/src/.env - Hardware interface settings"
echo "   backend_server/src/.env - API server settings"
echo "   frontend/.env - Frontend settings"
echo "   shared/.env - Shared library settings"
echo ""
echo "🚀 You can now run services locally:"
echo "   ./setup/local/launch_all.sh - Start all services locally (recommended)"
echo "   ./setup/local/launch_server.sh    - Start backend_server only"
echo "   ./setup/local/launch_host.sh      - Start backend_host only"  
echo "   ./setup/local/launch_frontend.sh  - Start frontend only"
if [ "$INSTALL_GRAFANA" = true ]; then
    echo "   ./setup/local/launch_grafana.sh   - Start Grafana monitoring only"
fi
echo ""
echo "🔧 Individual component installation:"
echo "   ./setup/local/install_shared.sh      - Install shared library only"
echo "   ./setup/local/install_server.sh      - Install backend_server only"
echo "   ./setup/local/install_host.sh        - Install backend_host only"
echo "   ./setup/local/install_frontend.sh    - Install frontend only"
echo "   ./setup/local/install_grafana.sh     - Install Grafana monitoring only"
echo ""
echo "🏠 Host services setup (for Raspberry Pi):"
echo "   ./setup/local/install_host_services.sh - Full host services setup"
echo ""
echo "🐳 Or use Docker deployment:"
echo "   ./setup/docker/launch_all.sh      - Start all services with Docker" 