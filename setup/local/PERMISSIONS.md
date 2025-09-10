# VirtualPyTest Permission Setup

This document explains the permission requirements and setup for VirtualPyTest.

## Common Permission Errors

### Error: `PermissionError: [Errno 13] Permission denied: '/var/www'`

This error occurs when the ImageVerificationController tries to create directories in `/var/www/html/stream/` but doesn't have the necessary permissions.

**Root Cause:** The system needs to create capture directories for video/image processing, but the user doesn't have write access to `/var/www/`.

## Quick Fix

Run the permission fix script:

```bash
sudo ./setup/local/fix_permissions.sh --user $(whoami)
```

## Full Permission Setup

For a complete permission setup (recommended during installation):

```bash
sudo ./setup/local/setup_permissions.sh --user $(whoami)
```

## What Gets Fixed

### 1. Directory Structure
- `/var/www/html/stream/capture{1..4}/` - Video capture directories
- `/var/www/html/camera/captures/` - Camera capture directory  
- `/var/www/.config/pulse/` - PulseAudio configuration
- `/tmp/virtualpytest/` - Temporary files

### 2. User Groups
- Adds your user to: `video`, `audio`, `render`, `www-data`
- Adds `www-data` to: `video`, `audio`, `render`

### 3. Permissions
- Sets proper ownership: `www-data:www-data` for web directories
- Sets write permissions: `777` for capture directories
- Configures X11 access for `www-data` user

### 4. System Access
- PulseAudio permissions for audio capture
- Video device access for HDMI/camera capture
- Display server access for VNC/desktop capture

## Manual Permission Setup

If you prefer to set up permissions manually:

```bash
# Create directories
sudo mkdir -p /var/www/html/stream/capture{1..4}/captures
sudo mkdir -p /var/www/html/camera/captures
sudo mkdir -p /var/www/.config/pulse

# Set ownership
sudo chown -R www-data:www-data /var/www/html/stream
sudo chown -R www-data:www-data /var/www/.config/pulse

# Set permissions
sudo chmod -R 777 /var/www/html/stream
sudo chmod -R 777 /var/www/.config/pulse

# Add users to groups
sudo usermod -aG video,audio,render,www-data $(whoami)
sudo usermod -aG video,audio,render www-data

# Set X11 permissions (if using display)
xhost +local:www-data
```

## Verification

Test that permissions are working:

```bash
# Test write access
sudo -u www-data touch /var/www/html/stream/capture1/test.txt
ls -la /var/www/html/stream/capture1/test.txt
sudo rm /var/www/html/stream/capture1/test.txt

# Check group membership
groups $(whoami)
groups www-data
```

## Troubleshooting

### Permission changes not taking effect
- Log out and back in for group changes to take effect
- Or restart your session: `newgrp www-data`

### Still getting permission errors
- Check if directories exist: `ls -la /var/www/html/`
- Check ownership: `ls -la /var/www/html/stream/`
- Verify group membership: `groups $(whoami)`

### Docker/Container Issues
- Ensure proper volume mounts in Docker configuration
- Check that host directories have correct permissions
- Consider using bind mounts with proper user mapping

## Integration with Installation

The permission setup is automatically integrated into:

1. **install_all.sh** - Runs permission setup during installation
2. **launch_all.sh** - Checks for permission issues before starting
3. **fix_permissions.sh** - Standalone script for fixing issues

## Security Notes

- The `777` permissions on capture directories are intentional for multi-user access
- Only specific directories get elevated permissions, not the entire system
- The `www-data` user is added to hardware groups only for device access
- X11 permissions are scoped to local access only

## Platform Compatibility

This permission setup is designed for:
- Ubuntu/Debian systems with `www-data` user
- Raspberry Pi OS
- Other Linux distributions with standard web server setup

For other platforms, you may need to adapt the user/group names accordingly.
