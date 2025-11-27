# Troubleshooting VirtualPyTest

**Common issues and solutions for QA teams.**

---

## 🚀 **Quick Fixes**

### System Won't Start
**Problem**: Docker compose fails to start
```bash
# Check if Docker is running
docker --version

# Restart Docker service
sudo systemctl restart docker

# Try starting again
docker compose up
```

### Web Interface Not Loading
**Problem**: Can't access http://localhost:3000
```bash
# Check if frontend is running
docker ps | grep frontend

# Restart frontend service
docker compose restart frontend
```

### Tests Not Running
**Problem**: Python scripts fail to execute
```bash
# Check if you're in the right directory
cd virtualpytest

# Verify Python environment
python --version

# Run with verbose output
python test_scripts/goto.py --node home -v
```

---

## 🔧 **Installation Issues**

### Docker Compose Fails
**Symptoms**: Services won't start, port conflicts
```bash
# Check for port conflicts
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :5109

# Kill conflicting processes
sudo kill -9 <PID>

# Clean Docker state
docker compose down
docker system prune -f
docker compose up
```

### Permission Errors
**Symptoms**: "Permission denied" when running scripts
```bash
# Fix script permissions
chmod +x test_scripts/*.py

# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### Missing Dependencies
**Symptoms**: Import errors, module not found
```bash
# Rebuild containers with fresh dependencies
docker compose build --no-cache
docker compose up
```

---

## 📱 **Device Connection Issues**

### Android Device Not Found
**Problem**: ADB can't see your device

**Solution**:
1. Enable **Developer Options** on Android device
2. Enable **USB Debugging**
3. Connect via USB and accept debugging prompt
4. Verify connection:
```bash
# Check ADB connection
adb devices

# If empty, restart ADB
adb kill-server
adb start-server
adb devices
```

### iOS Device Not Responding
**Problem**: Appium can't control iOS device

**Solution**:
1. Install **Xcode** and **iOS developer tools**
2. Trust the computer on iOS device
3. Verify **WebDriverAgent** is installed
4. Check device connection:
```bash
# List connected iOS devices
idevice_id -l

# Check if device is accessible
ideviceinfo
```

### STB/TV Remote Not Working
**Problem**: IR commands not reaching device

**Solution**:
1. **Check IR Hardware**: Ensure IR transmitter is connected
2. **Verify Line of Sight**: Clear path between transmitter and device
3. **Test IR Codes**: Use correct codes for your device model
4. **Check Configuration**: Verify device model in settings

---

## 🧪 **Test Execution Problems**

### Tests Fail Immediately
**Symptoms**: Tests stop at first step

**Common causes**:
1. **Device not ready**: Wait for device to fully boot
2. **Wrong device model**: Check userinterface_name parameter
3. **Navigation tree missing**: Verify navigation configuration

**Solution**:
```bash
# Run with debug mode to see details
python test_scripts/goto.py --node home --debug

# Check device status first
python test_scripts/validation.py --quick_check
```

### Screenshots Not Captured
**Problem**: No images saved in /captures folder

**Solution**:
1. **Check Permissions**: Ensure write access to captures directory
```bash
mkdir -p captures
chmod 755 captures
```

2. **Verify HDMI Capture**: Check video device connection
```bash
# List video devices
ls -la /dev/video*

# Test video capture
ffmpeg -f v4l2 -i /dev/video0 -t 5 test.mp4
```

### Navigation Fails
**Problem**: "No path found" or "Navigation failed"

**Solution**:
1. **Check Navigation Tree**: Verify target node exists
2. **Device State**: Ensure device is on correct screen
3. **Update Tree**: Navigation may have changed

```bash
# List available nodes
python test_scripts/goto.py --list_nodes

# Test basic navigation first
python test_scripts/goto.py --node home
```

---

## 📊 **Monitoring Issues**

### Grafana Dashboard Empty
**Problem**: No data showing in charts

**Solution**:
1. **Check Database Connection**:
```bash
# Test database connectivity
curl http://localhost:5109/api/health
```

2. **Verify Data Source**: Go to Grafana → Configuration → Data Sources
3. **Check Time Range**: Ensure time range includes test data
4. **Run Some Tests**: Generate data first

### Alerts Not Firing
**Problem**: No notifications despite issues

**Solution**:
1. **Test Notification Channel**: Send test alert
2. **Check Alert Rules**: Verify conditions are correct
3. **Review Logs**: Check Grafana logs for errors
4. **Verify Thresholds**: Ensure alert conditions can be met

---

## 🔌 **Hardware Problems**

### HDMI Capture Not Working
**Problem**: No video feed from device

**Solution**:
1. **Check Connections**: Ensure HDMI cables are secure
2. **Verify Capture Card**: Test with different video source
3. **Check Drivers**: Ensure capture card drivers installed
```bash
# Check if capture device is detected
lsusb | grep -i capture
dmesg | grep -i video
```

### Power Control Not Working
**Problem**: Smart plugs not responding

**Solution**:
1. **Check Network**: Ensure plugs are on same network
2. **Verify Credentials**: Check Tapo account settings
3. **Test Manually**: Use Tapo app to control plugs
4. **Check Configuration**: Verify plug IP addresses

---

## 🌐 **Network Issues**

### Services Can't Communicate
**Problem**: Frontend can't reach backend

**Solution**:
1. **Check Docker Network**:
```bash
# List Docker networks
docker network ls

# Inspect network configuration
docker network inspect virtualpytest-network
```

2. **Verify Service URLs**: Check environment variables
3. **Test Connectivity**: Ping between containers

### Remote Access Problems
**Problem**: Can't access from other computers

**Solution**:
1. **Check Firewall**: Open required ports
```bash
# Open ports on Linux
sudo ufw allow 3000
sudo ufw allow 5109
sudo ufw allow 6109
```

2. **Bind to All Interfaces**: Update Docker configuration
3. **Use Correct IP**: Access via machine's IP, not localhost

---

## 📝 **Log Analysis**

### Finding Useful Logs
```bash
# Docker container logs
docker logs virtualpytest-frontend-1
docker logs virtualpytest-backend_server-1
docker logs virtualpytest-backend_host-1

# Test execution logs
tail -f test_scripts/logs/latest.log

# System logs (Linux)
journalctl -u docker -f
```

### Understanding Error Messages

**"Device not found"**:
- Check device connection
- Verify device ID in configuration
- Ensure device is powered on

**"Navigation path not found"**:
- Update navigation tree
- Check if target node exists
- Verify device is on correct starting screen

**"Screenshot capture failed"**:
- Check video device permissions
- Verify HDMI connection
- Test video capture manually

---

## 🔄 **Recovery Procedures**

### Complete System Reset
```bash
# Stop all services
docker compose down

# Remove containers and volumes
docker compose down -v

# Clean Docker system
docker system prune -a -f

# Rebuild and restart
docker compose build --no-cache
docker compose up
```

### Reset Configuration
```bash
# Backup current config
cp -r config config.backup

# Reset to defaults
git checkout config/

# Restart services
docker compose restart
```

### Database Reset
```bash
# Connect to database and reset tables
# (Only if you have database access and backups)

# Alternative: Start fresh
docker volume rm virtualpytest_grafana-data
docker compose up
```

---

## 🆘 **Getting Help**

### Before Asking for Help
1. **Check this guide** for your specific issue
2. **Review logs** for error messages
3. **Try basic troubleshooting** steps
4. **Document the problem** with screenshots/logs

### Where to Get Support
- **GitHub Issues**: Bug reports and technical problems
- **GitHub Discussions**: General questions and community help
- **Documentation**: Check other guides in this documentation

### Providing Good Bug Reports
Include:
- **System Information**: OS, Docker version, hardware
- **Steps to Reproduce**: Exact commands/actions taken
- **Error Messages**: Full error text and logs
- **Screenshots**: Visual evidence of the problem
- **Configuration**: Relevant config files (remove sensitive data)

---

**Need more technical details? Check our [Technical Documentation](../technical/)!** 🔧
