# Running Tests with VirtualPyTest

**How to execute test scripts and manage test campaigns.**

---

## 🎯 **Test Types**

### Navigation Tests
**Purpose**: Navigate to specific screens or menus
```bash
# Go to home screen
python test_scripts/goto.py --node home

# Navigate to live TV
python test_scripts/goto.py --node live

# Go to settings menu
python test_scripts/goto.py --node settings
```

**Use cases**:
- Verify app navigation works correctly
- Set up devices for other tests
- Check menu accessibility

### Channel Zapping Tests
**Purpose**: Test channel changing and content verification
```bash
# Basic channel zapping
python test_scripts/fullzap.py

# Extended zapping with specific parameters
python test_scripts/fullzap.py --action live_chup --max_iteration 20
```

**Use cases**:
- Test streaming stability
- Validate channel switching performance
- Check content loading times

### Validation Tests
**Purpose**: Comprehensive device and content validation
```bash
# Full validation suite
python test_scripts/validation.py horizon_android_mobile

# Specific device validation
python test_scripts/validation.py --device device2
```

**Use cases**:
- Complete device functionality check
- Content quality verification
- Performance benchmarking

---

## 📋 **Campaign Management**

### Creating Campaigns
**What it does**: Group multiple tests together for batch execution

**Through Web Interface**:
1. Go to **Campaigns** section
2. Click **"Create New Campaign"**
3. Add test scripts to the campaign
4. Configure execution parameters
5. Save and schedule

*[Image placeholder: Campaign creation interface]*

**Through Python**:
```python
# Campaign configuration example
campaign_config = {
    "name": "Nightly Regression",
    "tests": [
        {"script": "goto.py", "args": "--node home"},
        {"script": "fullzap.py", "args": "--max_iteration 10"},
        {"script": "validation.py", "args": ""}
    ],
    "schedule": "daily",
    "devices": ["device1", "device2"]
}
```

### Running Campaigns
```bash
# Execute campaign by name
python test_campaign/campaign_fullzap.py

# Run with specific parameters
python test_campaign/campaign_fullzap.py --devices device1,device2
```

---

## 🔧 **Test Configuration**

### Device Selection
**Choose your target device**:
```bash
# Test specific device interface
python goto.py horizon_android_mobile --device device1

# Test Android TV interface  
python goto.py horizon_android_tv --device device2

# Test iOS interface
python goto.py horizon_ios --device device3
```

### Host Selection
**Choose which host runs the test**:
```bash
# Run on specific host
python goto.py --host sunri-pi2

# Let system choose available host
python goto.py  # Uses default host selection
```

### Custom Parameters
**Modify test behavior**:
```bash
# Navigation with custom target
python goto.py --node live_fullscreen --device device1

# Zapping with specific iteration count
python fullzap.py --max_iteration 50 --action live_chdown

# Validation with specific checks
python validation.py --skip_audio_check --focus_video_validation
```

---

## 📊 **Test Execution Monitoring**

### Real-Time Progress
**Watch tests execute live**:
- **Terminal Output**: Detailed step-by-step logs
- **Web Dashboard**: Visual progress indicators
- **Screenshots**: Automatic capture at each step

*[Image placeholder: Split screen showing terminal logs and web progress]*

### Execution Logs
**Understanding test output**:
```
🎯 [goto] Target node: live
📱 [goto] Device: Horizon Android Mobile (horizon_android_mobile)
🗺️ [goto] Finding path to live...
✅ [goto] Found path with 3 steps
📸 [goto] Screenshot captured: step_001.png
🎉 [goto] Successfully navigated to 'live'!
```

**Log symbols meaning**:
- 🎯 Test objective
- 📱 Device information  
- 🗺️ Navigation planning
- ✅ Success confirmation
- 📸 Screenshot capture
- 🎉 Test completion
- ❌ Error indication

---

## 📈 **Results Analysis**

### Screenshot Review
**Visual test evidence**:
- **Location**: `/captures/[timestamp]/`
- **Naming**: `step_001.png`, `step_002.png`, etc.
- **Content**: Before/after each action

**Review process**:
1. Check screenshot sequence for test flow
2. Verify expected screens appeared
3. Identify failure points visually

*[Image placeholder: Screenshot gallery showing test execution sequence]*

### Performance Metrics
**Test execution data**:
- **Duration**: Total test execution time
- **Steps**: Number of actions performed
- **Success Rate**: Percentage of successful actions
- **Response Times**: Device reaction speeds

### Error Analysis
**When tests fail**:
```
❌ [goto] Navigation failed at step 2
📸 Error screenshot: error_step_002.png
🔍 Reason: Target element not found
💡 Suggestion: Check device state or navigation tree
```

**Troubleshooting steps**:
1. Review error screenshot
2. Check device connectivity
3. Verify navigation tree accuracy
4. Retry with different parameters

---

## 🔄 **Test Scheduling**

### Manual Execution
**Run tests on demand**:
```bash
# Immediate execution
python test_scripts/goto.py --node home

# Run and save results
python test_scripts/goto.py --node home --save_results
```

### Automated Scheduling
**Set up recurring tests**:

**Through Web Interface**:
1. Go to **Campaigns** → **Schedule**
2. Select campaign to schedule
3. Set frequency (hourly, daily, weekly)
4. Choose execution time
5. Save schedule

**Through System Cron**:
```bash
# Add to crontab for daily execution
0 2 * * * cd /path/to/virtualpytest && python test_scripts/validation.py
```

---

## 🎮 **Interactive Testing**

### Manual Device Control
**Control devices through web interface**:
1. Go to **Device Control** section
2. Select target device
3. Use virtual remote control
4. Send commands in real-time

*[Image placeholder: Web-based device remote control interface]*

### Live Debugging
**Debug tests interactively**:
1. Run test with `--debug` flag
2. Test pauses at each step
3. Review current state
4. Continue or modify execution

```bash
# Interactive debugging mode
python test_scripts/goto.py --node live --debug
```

---

## 📝 **Best Practices**

### Test Design
- **Start Simple**: Begin with basic navigation tests
- **Build Incrementally**: Add complexity gradually
- **Use Screenshots**: Visual verification is powerful
- **Handle Errors**: Plan for device state variations

### Execution Strategy
- **Test Order**: Run setup tests before complex scenarios
- **Device State**: Ensure known starting conditions
- **Resource Management**: Don't overload devices with parallel tests
- **Result Preservation**: Save important test artifacts

### Monitoring
- **Watch First Runs**: Monitor new tests closely
- **Check Dashboards**: Use Grafana for trend analysis
- **Review Failures**: Investigate failed tests promptly
- **Optimize Performance**: Adjust timing based on device speed

---

## 🚀 **Advanced Features**

### Parallel Execution
**Run tests on multiple devices simultaneously**:
```bash
# Execute on multiple devices
python test_scripts/goto.py --devices device1,device2,device3
```

### Custom Verification
**Add your own validation logic**:
```python
# Custom verification in test scripts
def verify_custom_condition(screenshot_path):
    # Your validation logic here
    return True  # or False
```

### Integration with CI/CD
**Automated testing in build pipelines**:
```bash
# Jenkins/GitHub Actions integration
python test_scripts/validation.py --output_junit results.xml
```

---

**Ready to set up monitoring? Check out our [Monitoring Guide](monitoring.md)!** 📊
