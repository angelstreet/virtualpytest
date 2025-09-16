#!/bin/bash

# VirtualPyTest - Install System Requirements (Ubuntu/Linux)
# This script installs system-level dependencies NOT covered by other install_*.sh scripts
# Usage: ./install_requirements.sh [--minimal]

set -e

# Parse command line arguments
INSTALL_MODE="full"
for arg in "$@"; do
    case $arg in
        --minimal)
            INSTALL_MODE="minimal"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--minimal]"
            echo "  --minimal     Install only essential build tools and basic dependencies"
            echo "  (default)     Install all dependencies including video, OCR, VNC"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🔧 Installing VirtualPyTest System Requirements for Ubuntu/Linux ($INSTALL_MODE mode)..."

# Check if running on Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    echo "❌ This script is designed for Ubuntu/Debian systems with apt-get"
    echo "For other Linux distributions, please install packages manually:"
    echo "See REQUIREMENTS.md for the complete package list"
    exit 1
fi

echo "🖥️ Detected Ubuntu/Debian system"

# Function to check if running as root (bad practice)
check_root() {
    if [ "$EUID" -eq 0 ]; then
        echo "⚠️ Warning: Running as root is not recommended"
        echo "Please run as a regular user (the script will use sudo when needed)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to install packages
install_packages() {
    local packages=("$@")
    
    echo "📦 Updating package list..."
    sudo apt-get update
    echo "📦 Installing packages: ${packages[*]}"
    sudo apt-get install -y "${packages[@]}"
}

# Function to install development tools
install_dev_tools() {
    echo "🔧 Installing development tools..."
    install_packages build-essential git curl wget software-properties-common
}

# Function to install system monitoring tools
install_system_tools() {
    echo "🔍 Installing system monitoring tools..."
    install_packages lsof net-tools psmisc inotify-tools
}

# Function to install multimedia tools (full mode only)
install_multimedia() {
    echo "🎥 Installing multimedia tools..."
    install_packages ffmpeg imagemagick
}

# Function to install OCR tools (full mode only)
install_ocr() {
    echo "🔤 Installing OCR tools..."
    install_packages tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-ita
}

# Function to install VNC tools (full mode only)
install_vnc() {
    echo "🖥️ Installing VNC and display tools..."
    
    # Clean removal of conflicting VNC packages first
    echo "🧹 Removing any conflicting VNC packages..."
    
    # List of conflicting VNC packages to remove
    conflicting_packages=(
        "realvnc-vnc-server"
        "realvnc-vnc-viewer" 
        "vnc4server"
        "tightvncserver"
        "vncserver"
        "vnc-java"
    )
    
    for package in "${conflicting_packages[@]}"; do
        if dpkg -l | grep -q "^ii.*$package"; then
            echo "  🗑️ Removing conflicting package: $package"
            sudo apt-get remove -y "$package" 2>/dev/null || true
        fi
    done
    
    # Clean up any remaining VNC configuration
    echo "🧹 Cleaning up VNC processes and locks..."
    sudo pkill -f "Xvnc" 2>/dev/null || true
    sudo pkill -f "vncserver" 2>/dev/null || true
    sudo rm -f /tmp/.X*-lock 2>/dev/null || true
    sudo rm -f /tmp/.X11-unix/X* 2>/dev/null || true
    
    # Install only TigerVNC and required components
    echo "📦 Installing TigerVNC-only packages..."
    install_packages tigervnc-standalone-server xvfb fluxbox novnc websockify
    
    # Verify TigerVNC installation
    if command -v vncserver >/dev/null 2>&1; then
        VNC_VERSION=$(vncserver -help 2>&1 | head -1 || echo "Unknown")
        echo "✅ TigerVNC installed: $VNC_VERSION"
    else
        echo "❌ TigerVNC installation failed"
    fi
    
    # Setup noVNC if not already present
    if [ -d "/usr/share/novnc" ]; then
        echo "✅ noVNC web interface installed"
    else
        echo "⚠️ noVNC may need manual setup if package installation failed"
    fi
    
    echo "✅ VNC installation completed (TigerVNC only)"
}

# Function to install browsers (full mode only)
install_browsers() {
    echo "🌐 Installing web browsers..."
    # Try to install browsers, but don't fail if they're not available
    install_packages chromium-browser || install_packages chromium || true
    install_packages epiphany-browser || true
}

# Function to verify installations
verify_installation() {
    echo "🔍 Verifying installations..."
    
    # Always check these
    echo -n "Git: "
    if command -v git &> /dev/null; then
        echo "✅ $(git --version)"
    else
        echo "❌ Not found"
    fi
    
    echo -n "Curl: "
    if command -v curl &> /dev/null; then
        echo "✅ Available"
    else
        echo "❌ Not found"
    fi
    
    if [ "$INSTALL_MODE" = "full" ]; then
        echo -n "FFmpeg: "
        if command -v ffmpeg &> /dev/null; then
            echo "✅ $(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f3)"
        else
            echo "❌ Not found"
        fi
        
        echo -n "Tesseract: "
        if command -v tesseract &> /dev/null; then
            echo "✅ $(tesseract --version 2>&1 | head -n1)"
        else
            echo "❌ Not found"
        fi
        
        echo -n "VNC Server: "
        if command -v vncserver &> /dev/null; then
            echo "✅ Available"
        else
            echo "❌ Not found"
        fi
    fi
}

# Main installation process
main() {
    check_root
    
    echo "📋 Installation plan:"
    echo "  - Development tools (git, curl, build tools)"
    echo "  - System monitoring tools"
    if [ "$INSTALL_MODE" = "full" ]; then
        echo "  - Multimedia tools (ffmpeg, imagemagick)"
        echo "  - OCR tools (tesseract)"
        echo "  - VNC tools (for remote desktop)"
        echo "  - Web browsers (for automation)"
    fi
    echo ""
    
    # Confirm installation
    if [ -t 0 ]; then  # Only prompt if running interactively
        read -p "Continue with installation? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    fi
    
    # Install components
    install_dev_tools
    install_system_tools
    
    if [ "$INSTALL_MODE" = "full" ]; then
        install_multimedia
        install_ocr
        install_vnc
        install_browsers
    fi
    
    echo ""
    echo "✅ System requirements installation completed!"
    echo ""
    
    verify_installation
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Run VirtualPyTest installation:"
    echo "   ./setup/local/install_all.sh"
    echo ""
    echo "2. Launch VirtualPyTest:"
    echo "   ./scripts/launch_virtualpytest.sh"
    echo ""
    echo "💡 Note: Some packages may require logging out and back in to work properly"
}

# Execute main function
main "$@"
