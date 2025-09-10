#!/bin/bash

# VirtualPyTest - Permission Setup Script
# This script sets up proper permissions for www-data, directories, and system access
# Usage: ./setup_permissions.sh [--user USERNAME]

set -e

# Parse command line arguments
CURRENT_USER=$(whoami)
TARGET_USER="$CURRENT_USER"

for arg in "$@"; do
    case $arg in
        --user=*)
            TARGET_USER="${arg#*=}"
            shift
            ;;
        --user)
            TARGET_USER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--user USERNAME]"
            echo "  --user USERNAME   Set up permissions for specific user (default: current user)"
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

echo "🔐 Setting up VirtualPyTest permissions for user: $TARGET_USER"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run with sudo privileges"
    echo "Usage: sudo $0 [--user $TARGET_USER]"
    exit 1
fi

# Validate target user exists
if ! id "$TARGET_USER" &>/dev/null; then
    echo "❌ User '$TARGET_USER' does not exist"
    exit 1
fi

echo "👤 Setting up permissions for user: $TARGET_USER"

# =============================================================================
# SYSTEM USER GROUPS AND PERMISSIONS
# =============================================================================

echo "📝 Adding user to required system groups..."

# Add user to video, audio, and render groups for hardware access
usermod -aG video,audio,render "$TARGET_USER"
echo "✅ Added $TARGET_USER to video, audio, render groups"

# Add www-data to required groups for web server access
usermod -aG video,audio,render www-data
echo "✅ Added www-data to video, audio, render groups"

# Add user to www-data group for file sharing
usermod -aG www-data "$TARGET_USER"
echo "✅ Added $TARGET_USER to www-data group"

# =============================================================================
# DISPLAY AND X11 PERMISSIONS
# =============================================================================

echo "🖥️ Setting up display permissions..."

# Set up X11 permissions for www-data (if DISPLAY is set)
if [ -n "$DISPLAY" ]; then
    echo "Setting X11 permissions for display: $DISPLAY"
    sudo -u "$TARGET_USER" DISPLAY="$DISPLAY" xhost +local:www-data 2>/dev/null || echo "⚠️ Warning: Could not set X11 permissions (display may not be available)"
    echo "✅ X11 permissions configured for www-data"
else
    echo "⚠️ No DISPLAY variable set, skipping X11 permissions"
fi

# =============================================================================
# DIRECTORY STRUCTURE CREATION
# =============================================================================

echo "📁 Creating directory structure..."

# Create main www directories
mkdir -p /var/www/html/stream
mkdir -p /var/www/.config/pulse
mkdir -p /tmp/virtualpytest

# Create capture directories for multiple devices
for i in {1..4}; do
    mkdir -p "/var/www/html/stream/capture$i"
    mkdir -p "/var/www/html/stream/capture$i/captures"
done

# Create additional directories
mkdir -p /var/www/html/camera/captures
mkdir -p /var/www/html/vnc/stream

echo "✅ Directory structure created"

# =============================================================================
# OWNERSHIP AND PERMISSIONS
# =============================================================================

echo "🔐 Setting ownership and permissions..."

# Set ownership of www directories
chown -R www-data:www-data /var/www/html/stream
chown -R www-data:www-data /var/www/.config/pulse
chown -R "$TARGET_USER:$TARGET_USER" /tmp/virtualpytest

# Set permissions for www directories (755 for directories, 644 for files)
chmod -R 755 /var/www/html/stream
chmod -R 755 /var/www/.config/pulse
chmod -R 777 /tmp/virtualpytest

# Set specific permissions for capture directories (need write access)
for i in {1..4}; do
    chown -R www-data:www-data "/var/www/html/stream/capture$i"
    chmod -R 777 "/var/www/html/stream/capture$i"
done

# Set permissions for camera and vnc directories
chown -R www-data:www-data /var/www/html/camera
chmod -R 777 /var/www/html/camera

if [ -d "/var/www/html/vnc" ]; then
    chown -R www-data:www-data /var/www/html/vnc
    chmod -R 777 /var/www/html/vnc
fi

echo "✅ Ownership and permissions set"

# =============================================================================
# BINARY PERMISSIONS (if they exist)
# =============================================================================

echo "🔧 Setting binary permissions..."

# Set permissions for analysis scripts if they exist
if [ -f "/usr/local/bin/analyze_frame.py" ]; then
    chown -R "$TARGET_USER:$TARGET_USER" /usr/local/bin/analyze_frame.py
    chmod +x /usr/local/bin/analyze_frame.py
    echo "✅ analyze_frame.py permissions set"
fi

if [ -f "/usr/local/bin/analyze_audio.py" ]; then
    chown -R "$TARGET_USER:$TARGET_USER" /usr/local/bin/analyze_audio.py
    chmod +x /usr/local/bin/analyze_audio.py
    echo "✅ analyze_audio.py permissions set"
fi

# =============================================================================
# PULSE AUDIO CONFIGURATION
# =============================================================================

echo "🔊 Setting up PulseAudio permissions..."

# Create PulseAudio config directory for www-data
mkdir -p /var/www/.config/pulse
chown -R www-data:www-data /var/www/.config/pulse
chmod -R 777 /var/www/.config/pulse

echo "✅ PulseAudio permissions configured"

# =============================================================================
# VERIFICATION AND SUMMARY
# =============================================================================

echo ""
echo "🎉 Permission setup completed successfully!"
echo ""
echo "📋 Summary of changes:"
echo "   👤 User groups:"
echo "      - $TARGET_USER: added to video, audio, render, www-data"
echo "      - www-data: added to video, audio, render"
echo ""
echo "   📁 Directories created:"
echo "      - /var/www/html/stream/capture{1..4}/"
echo "      - /var/www/html/camera/captures/"
echo "      - /var/www/.config/pulse/"
echo "      - /tmp/virtualpytest/"
echo ""
echo "   🔐 Permissions set:"
echo "      - /var/www/html/stream/: www-data:www-data, 755/777"
echo "      - /var/www/.config/pulse/: www-data:www-data, 777"
echo "      - /tmp/virtualpytest/: $TARGET_USER:$TARGET_USER, 777"
echo ""
echo "   🖥️ Display access:"
echo "      - X11 permissions granted to www-data (if display available)"
echo ""
echo "⚠️ IMPORTANT NOTES:"
echo "   - You may need to log out and back in for group changes to take effect"
echo "   - If using systemd services, restart them after permission changes"
echo "   - For Docker deployments, ensure proper volume mounts are configured"
echo ""
echo "🔄 To verify permissions are working:"
echo "   sudo -u www-data touch /var/www/html/stream/capture1/test.txt"
echo "   ls -la /var/www/html/stream/capture1/test.txt"
echo "   sudo rm /var/www/html/stream/capture1/test.txt"
