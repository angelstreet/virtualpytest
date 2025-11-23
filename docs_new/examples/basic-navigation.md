# Basic Navigation Examples

**Simple examples of using VirtualPyTest navigation features.**

---

## 🎯 **Quick Start Examples**

### Navigate to Home Screen
```bash
# Basic navigation to home
python test_scripts/goto.py --node home

# Navigate with specific device
python test_scripts/goto.py horizon_android_mobile --node home --device device1

# Navigate with specific host
python test_scripts/goto.py --node home --host sunri-pi2
```

### Navigate to Live TV
```bash
# Go to live TV
python test_scripts/goto.py --node live

# Go to live fullscreen
python test_scripts/goto.py --node live_fullscreen
```

### Navigate to Settings
```bash
# Basic settings navigation
python test_scripts/goto.py --node settings

# Navigate to specific settings section
python test_scripts/goto.py --node settings_audio
python test_scripts/goto.py --node settings_display
```

---

## 📱 **Device-Specific Examples**

### Android Mobile Navigation
```bash
# Android mobile interface
python test_scripts/goto.py horizon_android_mobile --node home
python test_scripts/goto.py horizon_android_mobile --node live --device device1
python test_scripts/goto.py horizon_android_mobile --node settings_network
```

### Android TV Navigation
```bash
# Android TV interface
python test_scripts/goto.py horizon_android_tv --node home
python test_scripts/goto.py horizon_android_tv --node live_guide
python test_scripts/goto.py horizon_android_tv --node apps
```

### iOS Navigation
```bash
# iOS interface
python test_scripts/goto.py horizon_ios --node home
python test_scripts/goto.py horizon_ios --node live --device ios_device1
```

---

## 🎮 **Interactive Examples**

### Debug Mode Navigation
```bash
# Run with debug mode to see each step
python test_scripts/goto.py --node live --debug

# This will:
# 1. Show current device state
# 2. Display navigation path
# 3. Pause at each step
# 4. Allow manual verification
```

### Verbose Output
```bash
# Get detailed execution information
python test_scripts/goto.py --node settings -v

# Output includes:
# - Device detection
# - Path calculation
# - Step-by-step execution
# - Screenshot capture info
# - Timing information
```

---

## 📊 **Understanding Navigation Output**

### Successful Navigation
```
🎯 [goto] Target node: live
📱 [goto] Device: Horizon Android Mobile (horizon_android_mobile)
🗺️ [goto] Finding path to live...
✅ [goto] Found path with 3 steps
📸 [goto] Screenshot captured: step_001.png
⏩ [goto] Executing step 1/3: press_key(home)
📸 [goto] Screenshot captured: step_002.png
⏩ [goto] Executing step 2/3: press_key(ok)
📸 [goto] Screenshot captured: step_003.png
⏩ [goto] Executing step 3/3: press_key(live)
📸 [goto] Screenshot captured: step_004.png
🎉 [goto] Successfully navigated to 'live'!
```

### Navigation Failure
```
🎯 [goto] Target node: invalid_node
📱 [goto] Device: Horizon Android Mobile (horizon_android_mobile)
🗺️ [goto] Finding path to invalid_node...
❌ [goto] No path found to 'invalid_node'

Available nodes:
- home
- live
- live_fullscreen
- settings
- settings_audio
- apps
```

---

## 🔧 **Advanced Examples**

### Custom Parameters
```bash
# Navigation with custom wait times
python test_scripts/goto.py --node live --wait_time 2000

# Navigation with retry on failure
python test_scripts/goto.py --node settings --retry_count 3

# Navigation with screenshot quality
python test_scripts/goto.py --node home --screenshot_quality 90
```

### Multiple Device Testing
```bash
# Test navigation on multiple devices
python test_scripts/goto.py --node live --devices device1,device2,device3

# Sequential navigation across devices
for device in device1 device2 device3; do
    python test_scripts/goto.py --node home --device $device
    python test_scripts/goto.py --node live --device $device
done
```

---

## 📝 **Python Script Examples**

### Basic Navigation Script
```python
#!/usr/bin/env python3
"""
Custom navigation script example
"""
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from shared.lib.utils.script_framework import ScriptExecutor
from backend_host.src.services.navigation.navigation_pathfinding import find_shortest_path

def navigate_to_live_and_back():
    """Navigate to live TV and return to home"""
    script_name = "navigate_live_and_back"
    executor = ScriptExecutor(script_name, "Navigate to live and back to home")
    
    # Setup
    args = executor.create_argument_parser().parse_args()
    context = executor.setup_execution_context(args)
    
    if not executor.load_navigation_tree(context, args.userinterface_name):
        return False
    
    try:
        # Navigate to live
        print("🎯 Navigating to live...")
        live_path = find_shortest_path(context.tree_id, 'live', context.team_id)
        if not executor.execute_navigation_sequence(context, live_path):
            return False
        
        # Wait 5 seconds
        print("⏱️ Waiting 5 seconds...")
        time.sleep(5)
        
        # Navigate back to home
        print("🏠 Navigating back to home...")
        home_path = find_shortest_path(context.tree_id, 'home', context.team_id)
        return executor.execute_navigation_sequence(context, home_path)
        
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)

if __name__ == "__main__":
    navigate_to_live_and_back()
```

### Navigation with Verification
```python
#!/usr/bin/env python3
"""
Navigation with content verification
"""
from shared.lib.utils.script_framework import ScriptExecutor
from backend_host.src.controllers.verification.text import TextVerificationController

def navigate_with_verification():
    """Navigate and verify expected content"""
    executor = ScriptExecutor("navigate_verify", "Navigate with verification")
    
    # Setup
    args = executor.create_argument_parser().parse_args()
    context = executor.setup_execution_context(args)
    
    if not executor.load_navigation_tree(context, args.userinterface_name):
        return False
    
    try:
        # Navigate to settings
        settings_path = find_shortest_path(context.tree_id, 'settings', context.team_id)
        if not executor.execute_navigation_sequence(context, settings_path):
            return False
        
        # Verify we're on settings page
        verifier = TextVerificationController()
        screenshot_path = context.capture_screenshot("settings_verification")
        
        if verifier.verify_text_present("Settings", screenshot_path):
            print("✅ Successfully verified settings page")
            return True
        else:
            print("❌ Failed to verify settings page")
            return False
            
    finally:
        executor.cleanup_and_exit(context, args.userinterface_name)

if __name__ == "__main__":
    navigate_with_verification()
```

---

## 🎯 **Best Practices**

### Navigation Strategy
1. **Start Simple**: Begin with basic home/live navigation
2. **Verify Paths**: Use `--debug` mode to verify navigation paths
3. **Handle Failures**: Always check return values and handle errors
4. **Use Screenshots**: Visual evidence helps debug navigation issues

### Error Handling
```bash
# Check if navigation succeeded
if python test_scripts/goto.py --node live; then
    echo "Navigation successful"
    # Continue with next steps
else
    echo "Navigation failed"
    # Handle failure
    exit 1
fi
```

### Timing Considerations
```bash
# Allow extra time for slow devices
python test_scripts/goto.py --node settings --wait_time 3000

# Use shorter waits for fast devices
python test_scripts/goto.py --node home --wait_time 500
```

---

## 🔍 **Troubleshooting Navigation**

### Common Issues

**"No path found"**:
```bash
# List available nodes
python test_scripts/goto.py --list_nodes

# Check navigation tree
python -c "
from backend_host.src.services.navigation.navigation_pathfinding import get_navigation_tree
tree = get_navigation_tree('horizon_android_mobile')
print('Available nodes:', list(tree.nodes()))
"
```

**"Device not responding"**:
```bash
# Test device connectivity first
python test_scripts/validation.py --quick_check

# Check device status
adb devices  # For Android devices
```

**"Navigation too slow"**:
```bash
# Reduce wait times
python test_scripts/goto.py --node live --wait_time 1000

# Use faster navigation paths
python test_scripts/goto.py --node live_direct  # If available
```

---

## 📚 **Related Examples**

- **[Channel Zapping](../user/running-tests.md#channel-zapping-tests)**: Test channel changing
- **[Campaign Setup](campaign-setup.md)**: Batch navigation tests
- **[Custom Controllers](custom-controllers.md)**: Add new device support

---

**Ready for more complex automation? Check [Campaign Setup Examples](campaign-setup.md)!** 🚀
