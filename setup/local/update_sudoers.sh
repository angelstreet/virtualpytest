#!/bin/bash

# Update VirtualPyTest sudoers configuration to allow passwordless sudo for systemctl and reboot
# This fixes the issue where HDMI stream controller requires password for systemctl commands

set -e

echo "=================================================="
echo "VirtualPyTest Sudoers Configuration Update"
echo "=================================================="
echo ""

# Check if running with appropriate permissions
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Please do not run this script as root"
    echo "   Run it as the user that runs the backend_host service"
    exit 1
fi

echo "🔐 Updating sudo permissions for VirtualPyTest..."
echo "   User: $USER"
echo ""
echo "This will configure passwordless sudo for:"
echo "  ✓ Running FFmpeg processes as www-data"
echo "  ✓ www-data user to manage FFmpeg processes (pkill, kill, fuser)"
echo "  ✓ Managing stream systemctl services"
echo "  ✓ System reboot command"
echo ""

# Create the sudoers configuration
sudo tee /etc/sudoers.d/virtualpytest > /dev/null << EOF
# VirtualPyTest - Allow backend_host user to run commands as www-data
# This enables dynamic stream quality changes via Python backend
$USER ALL=(www-data) NOPASSWD: ALL

# VirtualPyTest - Allow systemctl commands for stream service management (passwordless)
$USER ALL=(root) NOPASSWD: /bin/systemctl show stream *, /usr/bin/systemctl show stream *
$USER ALL=(root) NOPASSWD: /bin/systemctl status stream*, /usr/bin/systemctl status stream*
$USER ALL=(root) NOPASSWD: /bin/systemctl start stream*, /usr/bin/systemctl start stream*
$USER ALL=(root) NOPASSWD: /bin/systemctl stop stream*, /usr/bin/systemctl stop stream*
$USER ALL=(root) NOPASSWD: /bin/systemctl restart stream*, /usr/bin/systemctl restart stream*

# VirtualPyTest - Allow system reboot (passwordless)
$USER ALL=(root) NOPASSWD: /sbin/reboot, /usr/sbin/reboot
EOF

# Set proper permissions on sudoers file
sudo chmod 440 /etc/sudoers.d/virtualpytest

# Create www-data sudoers configuration for FFmpeg process management
sudo tee /etc/sudoers.d/ffmpeg-www-data > /dev/null << EOF
# Allow www-data to manage FFmpeg processes (used by stream.service ExecStartPre)
www-data ALL=(ALL) NOPASSWD: /usr/bin/fuser
www-data ALL=(ALL) NOPASSWD: /usr/bin/pkill
www-data ALL=(ALL) NOPASSWD: /usr/bin/kill
EOF

# Set proper permissions on www-data sudoers file
sudo chmod 0440 /etc/sudoers.d/ffmpeg-www-data

echo "✅ Sudoers configuration updated successfully!"
echo ""
echo "Testing sudo permissions..."

# Test systemctl command
if sudo systemctl show stream --property=ActiveState >/dev/null 2>&1; then
    echo "✅ systemctl command works without password"
else
    echo "⚠️  systemctl test failed, but configuration was applied"
fi

# Verify www-data sudoers syntax
if sudo visudo -c -f /etc/sudoers.d/ffmpeg-www-data >/dev/null 2>&1; then
    echo "✅ www-data sudoers configuration is valid"
else
    echo "⚠️  www-data sudoers syntax check failed"
fi

echo ""
echo "=================================================="
echo "✅ Configuration Complete!"
echo "=================================================="
echo ""
echo "Configured sudoers files:"
echo "  ✓ /etc/sudoers.d/virtualpytest       - User permissions for stream management"
echo "  ✓ /etc/sudoers.d/ffmpeg-www-data    - www-data permissions for process management"
echo ""
echo "The HDMI stream controller should now work without password prompts."
echo "Please restart the stream service to apply changes:"
echo ""
echo "  sudo systemctl restart stream"
echo ""

