#!/bin/bash

# VirtualPyTest - VNC Cleanup Script
# This script removes conflicting VNC packages and installs only TigerVNC
# Usage: ./cleanup_vnc.sh

set -e

echo "🧹 VirtualPyTest VNC Cleanup & TigerVNC Installation"
echo "This will remove conflicting VNC packages and install only TigerVNC"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    echo "   Run as regular user - script will use sudo when needed"
    exit 1
fi

# Check if sudo is available
if ! command -v sudo >/dev/null 2>&1; then
    echo "❌ sudo is required but not available"
    exit 1
fi

echo "🔍 Checking current VNC installations..."

# List of conflicting VNC packages to remove
conflicting_packages=(
    "realvnc-vnc-server"
    "realvnc-vnc-viewer" 
    "vnc4server"
    "tightvncserver"
    "vncserver"
    "vnc-java"
)

# Check what's currently installed
installed_conflicting=()
for package in "${conflicting_packages[@]}"; do
    if dpkg -l 2>/dev/null | grep -q "^ii.*$package"; then
        installed_conflicting+=("$package")
        echo "  ⚠️ Found conflicting package: $package"
    fi
done

# Check if TigerVNC is already installed
if dpkg -l 2>/dev/null | grep -q "^ii.*tigervnc-standalone-server"; then
    echo "  ✅ TigerVNC already installed"
    TIGERVNC_INSTALLED=true
else
    echo "  📦 TigerVNC not installed"
    TIGERVNC_INSTALLED=false
fi

echo ""

# If no conflicts and TigerVNC is installed, nothing to do
if [ ${#installed_conflicting[@]} -eq 0 ] && [ "$TIGERVNC_INSTALLED" = true ]; then
    echo "✅ No conflicting VNC packages found and TigerVNC is already installed"
    echo "🎉 VNC setup is clean!"
    exit 0
fi

# Show what will be done
echo "📋 Cleanup Plan:"
if [ ${#installed_conflicting[@]} -gt 0 ]; then
    echo "  🗑️ Remove conflicting packages:"
    for package in "${installed_conflicting[@]}"; do
        echo "     - $package"
    done
fi

if [ "$TIGERVNC_INSTALLED" = false ]; then
    echo "  📦 Install TigerVNC packages:"
    echo "     - tigervnc-standalone-server"
    echo "     - xvfb (virtual display)"
    echo "     - fluxbox (window manager)"
    echo "     - novnc (web interface)"
    echo "     - websockify (web proxy)"
fi

echo ""

# Confirm with user
read -p "Continue with VNC cleanup? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "🚀 Starting VNC cleanup..."

# Stop any running VNC services
echo "🛑 Stopping VNC services and processes..."
sudo systemctl stop vncserver 2>/dev/null || true
sudo systemctl stop novnc 2>/dev/null || true
sudo pkill -f "Xvnc" 2>/dev/null || true
sudo pkill -f "vncserver" 2>/dev/null || true
sudo pkill -f "websockify" 2>/dev/null || true

# Clean up lock files
echo "🧹 Cleaning up VNC lock files..."
sudo rm -f /tmp/.X*-lock 2>/dev/null || true
sudo rm -f /tmp/.X11-unix/X* 2>/dev/null || true

# Remove conflicting packages
if [ ${#installed_conflicting[@]} -gt 0 ]; then
    echo "🗑️ Removing conflicting VNC packages..."
    for package in "${installed_conflicting[@]}"; do
        echo "  Removing $package..."
        sudo apt-get remove -y "$package" 2>/dev/null || true
    done
    
    # Clean up any remaining configuration
    echo "🧹 Cleaning up package configuration..."
    sudo apt-get autoremove -y 2>/dev/null || true
fi

# Install TigerVNC if not present
if [ "$TIGERVNC_INSTALLED" = false ]; then
    echo "📦 Installing TigerVNC and components..."
    sudo apt-get update
    sudo apt-get install -y tigervnc-standalone-server xvfb fluxbox novnc websockify
fi

# Verify installation
echo ""
echo "🔍 Verifying TigerVNC installation..."

if command -v vncserver >/dev/null 2>&1; then
    VNC_VERSION=$(vncserver -help 2>&1 | head -1 || echo "Unknown version")
    echo "✅ TigerVNC installed: $VNC_VERSION"
else
    echo "❌ TigerVNC installation failed"
    exit 1
fi

if [ -d "/usr/share/novnc" ]; then
    echo "✅ noVNC web interface available"
else
    echo "⚠️ noVNC not found - web interface may not work"
fi

echo ""
echo "🎉 VNC cleanup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Reinstall VirtualPyTest host services:"
echo "   ./setup/local/install_host_services.sh"
echo ""
echo "2. Or run complete fresh installation:"
echo "   ./setup/local/install_all.sh"
echo ""
echo "✅ TigerVNC-only installation is now ready!"
