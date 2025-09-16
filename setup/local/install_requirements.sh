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
    install_packages lsof net-tools psmisc inotify-tools ufw
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
    install_packages tigervnc-standalone-server xvfb xfce4 xfce4-goodies novnc websockify
    
    # Setup noVNC if not already present
    if [ -d "/usr/share/novnc" ]; then
        echo "✅ noVNC web interface installed"
    else
        echo "⚠️ noVNC may need manual setup if package installation failed"
    fi
}

# Function to install browsers (full mode only)
install_browsers() {
    echo "🌐 Installing web browsers..."
    # Try to install browsers, but don't fail if they're not available
    install_packages chromium-browser || install_packages chromium || true
    install_packages epiphany-browser || true
}

# Function to install Android development tools
install_android_tools() {
    echo "📱 Installing Android development tools (ADB)..."
    
    # Check if ADB is already available
    if command -v adb &> /dev/null; then
        echo "ℹ️ ADB already installed: $(adb version 2>&1 | head -n1)"
        return 0
    fi
    
    # Try installing from Ubuntu repository first (easiest method)
    echo "📦 Attempting to install ADB from Ubuntu repository..."
    if sudo apt-get install -y android-tools-adb android-tools-fastboot 2>/dev/null; then
        echo "✅ ADB installed from Ubuntu repository"
        return 0
    fi
    
    echo "⚠️ Ubuntu repository installation failed, installing Android SDK Platform Tools..."
    
    # Create Android SDK directory
    local android_home="$HOME/android-sdk"
    local platform_tools_dir="$android_home/platform-tools"
    
    mkdir -p "$android_home"
    
    # Download Android SDK Platform Tools
    echo "📥 Downloading Android SDK Platform Tools..."
    local platform_tools_url="https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
    local temp_zip="/tmp/platform-tools.zip"
    
    if ! wget -O "$temp_zip" "$platform_tools_url"; then
        echo "❌ Failed to download Android SDK Platform Tools"
        return 1
    fi
    
    # Extract platform tools
    echo "📂 Extracting Android SDK Platform Tools..."
    if ! unzip -q "$temp_zip" -d "$android_home"; then
        echo "❌ Failed to extract Android SDK Platform Tools"
        rm -f "$temp_zip"
        return 1
    fi
    
    rm -f "$temp_zip"
    
    # Add to PATH in multiple shell profiles
    echo "🔧 Configuring PATH for ADB..."
    
    local path_export="export PATH=\"$platform_tools_dir:\$PATH\""
    local android_home_export="export ANDROID_HOME=\"$android_home\""
    
    # Add to .bashrc
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "android-sdk/platform-tools" "$HOME/.bashrc"; then
            echo "" >> "$HOME/.bashrc"
            echo "# Android SDK Platform Tools" >> "$HOME/.bashrc"
            echo "$android_home_export" >> "$HOME/.bashrc"
            echo "$path_export" >> "$HOME/.bashrc"
        fi
    fi
    
    # Add to .profile (for login shells)
    if [ -f "$HOME/.profile" ]; then
        if ! grep -q "android-sdk/platform-tools" "$HOME/.profile"; then
            echo "" >> "$HOME/.profile"
            echo "# Android SDK Platform Tools" >> "$HOME/.profile"
            echo "$android_home_export" >> "$HOME/.profile"
            echo "$path_export" >> "$HOME/.profile"
        fi
    fi
    
    # Add to .zshrc if it exists (for zsh users)
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "android-sdk/platform-tools" "$HOME/.zshrc"; then
            echo "" >> "$HOME/.zshrc"
            echo "# Android SDK Platform Tools" >> "$HOME/.zshrc"
            echo "$android_home_export" >> "$HOME/.zshrc"
            echo "$path_export" >> "$HOME/.zshrc"
        fi
    fi
    
    # Export for current session
    export ANDROID_HOME="$android_home"
    export PATH="$platform_tools_dir:$PATH"
    
    # Verify installation
    if command -v adb &> /dev/null; then
        echo "✅ ADB installed successfully: $(adb version 2>&1 | head -n1)"
        echo "📍 Location: $platform_tools_dir/adb"
        echo "🔄 Note: You may need to restart your terminal or run 'source ~/.bashrc' to use ADB"
        return 0
    else
        echo "❌ ADB installation verification failed"
        return 1
    fi
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
    
    echo -n "UFW (Firewall): "
    if command -v ufw &> /dev/null; then
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
        
        echo -n "ADB (Android Debug Bridge): "
        if command -v adb &> /dev/null; then
            echo "✅ $(adb version 2>&1 | head -n1)"
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
        echo "  - Android tools (ADB for device control)"
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
        install_android_tools
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
