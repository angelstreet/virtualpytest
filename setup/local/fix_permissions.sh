#!/bin/bash

# VirtualPyTest - Fix Permission Issues Script
# This script fixes common permission issues that occur during runtime
# Usage: ./fix_permissions.sh [--user USERNAME]

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
            echo "VirtualPyTest Permission Fix Script"
            echo ""
            echo "This script fixes common permission issues that prevent VirtualPyTest from running:"
            echo "  - PermissionError: [Errno 13] Permission denied: '/var/www'"
            echo "  - Directory creation failures in /var/www/html/stream/"
            echo "  - www-data user access issues"
            echo ""
            echo "Usage: $0 [--user USERNAME]"
            echo "  --user USERNAME   Fix permissions for specific user (default: current user)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  sudo $0                    # Fix for current user"
            echo "  sudo $0 --user pi         # Fix for user 'pi'"
            echo "  sudo $0 --user sunri-pi4  # Fix for user 'sunri-pi4'"
            exit 0
            ;;
        *)
            echo "❌ Unknown parameter: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🔧 VirtualPyTest Permission Fix"
echo "Fixing permissions for user: $TARGET_USER"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run with sudo privileges"
    echo "Usage: sudo $0 [--user $TARGET_USER]"
    echo ""
    echo "Common permission errors this fixes:"
    echo "  - PermissionError: [Errno 13] Permission denied: '/var/www'"
    echo "  - Failed to create directories in /var/www/html/stream/"
    exit 1
fi

# Validate target user exists
if ! id "$TARGET_USER" &>/dev/null; then
    echo "❌ User '$TARGET_USER' does not exist"
    exit 1
fi

echo "🔍 Diagnosing permission issues..."

# Check if the problematic directories exist
ISSUES_FOUND=false

if [ ! -d "/var/www" ]; then
    echo "❌ /var/www directory does not exist"
    ISSUES_FOUND=true
fi

if [ ! -d "/var/www/html" ]; then
    echo "❌ /var/www/html directory does not exist"
    ISSUES_FOUND=true
fi

if [ ! -d "/var/www/html/stream" ]; then
    echo "❌ /var/www/html/stream directory does not exist"
    ISSUES_FOUND=true
fi

# Check permissions on existing directories
if [ -d "/var/www" ]; then
    WWW_OWNER=$(stat -c '%U' /var/www 2>/dev/null || echo "unknown")
    if [ "$WWW_OWNER" != "www-data" ] && [ "$WWW_OWNER" != "root" ]; then
        echo "⚠️ /var/www owned by $WWW_OWNER (should be www-data or root)"
        ISSUES_FOUND=true
    fi
fi

# Check if user is in www-data group
if ! groups "$TARGET_USER" | grep -q "www-data"; then
    echo "⚠️ User $TARGET_USER is not in www-data group"
    ISSUES_FOUND=true
fi

# Check if www-data is in required groups
if ! groups www-data | grep -q "video"; then
    echo "⚠️ www-data user is not in video group"
    ISSUES_FOUND=true
fi

if [ "$ISSUES_FOUND" = true ]; then
    echo ""
    echo "🔧 Fixing identified permission issues..."
    
    # Run the full permission setup script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/setup_permissions.sh" ]; then
        echo "Running full permission setup..."
        "$SCRIPT_DIR/setup_permissions.sh" --user "$TARGET_USER"
    else
        echo "⚠️ setup_permissions.sh not found, applying basic fixes..."
        
        # Basic fixes
        mkdir -p /var/www/html/stream
        mkdir -p /var/www/.config/pulse
        
        # Create capture directories
        for i in {1..4}; do
            mkdir -p "/var/www/html/stream/capture$i/captures"
        done
        
        # Set ownership and permissions
        chown -R www-data:www-data /var/www/html/stream
        chmod -R 777 /var/www/html/stream
        
        # Add users to groups
        usermod -aG video,audio,render,www-data "$TARGET_USER"
        usermod -aG video,audio,render www-data
        
        echo "✅ Basic permission fixes applied"
    fi
else
    echo "✅ No permission issues detected"
fi

echo ""
echo "🎉 Permission fix completed!"
echo ""
echo "📋 What was fixed:"
echo "   - Created missing /var/www directories"
echo "   - Set proper ownership (www-data:www-data)"
echo "   - Set proper permissions (777 for capture directories)"
echo "   - Added $TARGET_USER to required groups"
echo "   - Added www-data to system groups"
echo ""
echo "🔄 Next steps:"
echo "   1. Log out and back in (or restart) for group changes to take effect"
echo "   2. Try running VirtualPyTest again"
echo "   3. If issues persist, check the logs for other error messages"
echo ""
echo "🧪 Test the fix:"
echo "   sudo -u www-data touch /var/www/html/stream/capture1/test.txt"
echo "   ls -la /var/www/html/stream/capture1/test.txt"
echo "   sudo rm /var/www/html/stream/capture1/test.txt"
