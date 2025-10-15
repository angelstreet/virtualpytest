# Passwordless Sudo Configuration for VirtualPyTest

## Issue

When trying to take control of a device with HDMI streaming, you may encounter this error:

```json
{
  "error": "AV controller not available for device device1. Cannot stream video.",
  "errorType": "host_error",
  "host_result": {
    "error": "AV controller not available for device device1. Cannot stream video.",
    "success": false
  },
  "success": false
}
```

In the logs, you'll see:

```
sudo: a terminal is required to read the password; either use the -S option to read from standard input or configure an askpass helper
sudo: il est nécessaire de saisir un mot de passe
```

This happens because the HDMI stream controller needs to check the systemd service status using `sudo systemctl show stream`, but sudo is configured to require a password.

## Root Cause

The backend_host service needs to run these commands without password prompts:

1. `sudo systemctl show stream` - Check stream service status
2. `sudo systemctl start/stop/restart stream` - Manage stream service
3. `sudo reboot` - Reboot the system (for system management)
4. Commands as `www-data` user - For FFmpeg process management

## Solution

### For New Installations

The sudoers configuration is automatically set up when you run:

```bash
./setup/local/install_host_services.sh
```

### For Existing Installations

If you're experiencing this issue on an existing installation, run the sudoers update script:

```bash
cd /path/to/virtualpytest
./setup/local/update_sudoers.sh
```

This script will:
1. Update `/etc/sudoers.d/virtualpytest` with the correct permissions
2. Test that the configuration works
3. Provide instructions for restarting the service

After running the script, restart the backend_host service:

```bash
sudo systemctl restart host
```

### Manual Configuration

If you prefer to configure manually, edit `/etc/sudoers.d/virtualpytest`:

```bash
sudo visudo -f /etc/sudoers.d/virtualpytest
```

Add the following content (replace `$USER` with the actual username running the backend_host service):

```
# VirtualPyTest - Allow backend_host user to run commands as www-data
# This enables dynamic stream quality changes via Python backend
username ALL=(www-data) NOPASSWD: ALL

# VirtualPyTest - Allow systemctl commands for stream service management (passwordless)
username ALL=(root) NOPASSWD: /bin/systemctl show stream *, /usr/bin/systemctl show stream *
username ALL=(root) NOPASSWD: /bin/systemctl status stream*, /usr/bin/systemctl status stream*
username ALL=(root) NOPASSWD: /bin/systemctl start stream*, /usr/bin/systemctl start stream*
username ALL=(root) NOPASSWD: /bin/systemctl stop stream*, /usr/bin/systemctl stop stream*
username ALL=(root) NOPASSWD: /bin/systemctl restart stream*, /usr/bin/systemctl restart stream*

# VirtualPyTest - Allow system reboot (passwordless)
username ALL=(root) NOPASSWD: /sbin/reboot, /usr/sbin/reboot
```

Set proper permissions:

```bash
sudo chmod 440 /etc/sudoers.d/virtualpytest
```

## Verification

To verify the configuration is working:

1. Test systemctl without password:
   ```bash
   sudo systemctl show stream --property=ActiveState
   ```
   This should run without asking for a password.

2. Try to take control of a device through the UI or API
   - The HDMI stream controller should now work correctly
   - No password errors should appear in the logs

## Security Considerations

This configuration allows the backend_host user to:
- Manage stream services without password
- Reboot the system without password
- Run commands as www-data user without password

These permissions are limited to:
- Specific systemctl commands for the stream service only
- The reboot command only
- Commands run as www-data (restricted user)

This is necessary for the automated testing and streaming functionality to work properly.

## Troubleshooting

### Still Getting Password Prompts

1. Check which user is running the backend_host service:
   ```bash
   ps aux | grep backend_host
   ```

2. Verify the sudoers file has the correct username:
   ```bash
   sudo cat /etc/sudoers.d/virtualpytest
   ```

3. Check sudoers file syntax:
   ```bash
   sudo visudo -c -f /etc/sudoers.d/virtualpytest
   ```

4. Check file permissions:
   ```bash
   ls -la /etc/sudoers.d/virtualpytest
   ```
   Should show: `-r--r----- 1 root root` (permissions: 440)

### Different systemctl Paths

If your system uses different paths for systemctl, update the sudoers file with the correct paths:

```bash
which systemctl
```

Common paths:
- `/bin/systemctl`
- `/usr/bin/systemctl`
- `/usr/sbin/systemctl`

## Related Files

- Setup script: `setup/local/install_host_services.sh`
- Update script: `setup/local/update_sudoers.sh`
- HDMI controller: `backend_host/src/controllers/audiovideo/hdmi_stream.py`
- System utilities: `shared/src/lib/utils/system_utils.py`

