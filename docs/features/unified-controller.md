# 🎮 Unified Device Controller

**One script. All devices.**

Write test scripts once and run them across Android TV, iOS, mobile, set-top boxes, and smart TVs without changing your code.

---

## The Problem

Traditional testing tools require different scripts for each device type:
- ❌ Separate Android and iOS automation frameworks
- ❌ Different APIs for TV vs. mobile
- ❌ Rewriting tests for each platform
- ❌ Maintaining multiple codebases

---

## The VirtualPyTest Solution

✅ **Unified API** - Same commands work across all devices  
✅ **Hardware abstraction** - Code to user journeys, not device specifics  
✅ **Automatic adaptation** - Controller picks the right method for each device  
✅ **Extensible** - Add new device types easily  

---

## Supported Devices

### Android Devices
- **Android TV** (Fire TV, Google TV, etc.)
- **Android Mobile** phones and tablets
- **Control via**: ADB, Appium, Web interface

### iOS Devices
- **iPhone** and **iPad**
- **Control via**: Appium, WebDriver

### Set-Top Boxes (STB)
- **IR-controlled** boxes
- **Bluetooth** remotes
- **Control via**: IR transmitter, GPIO, USB-UIRT

### Smart TVs
- **Samsung Tizen**
- **LG webOS**
- **Control via**: Network API, IR

### Desktop/Web
- **Browser automation**
- **Control via**: Selenium, Playwright

---

## How It Works

### 1. Define Your Test Once

```python
from shared.src.controller_factory import ControllerFactory

# Get controller for any device
controller = ControllerFactory.get_controller(
    model="horizon_android_mobile",  # or "appletv_ios", "stb_ir", etc.
    device_name="my_device"
)

# Navigate using the same commands
controller.navigate_to("home")
controller.press_key("DOWN")
controller.press_key("SELECT")
controller.verify_text("Settings")
```

### 2. Run on Any Device

The controller automatically adapts based on the device model:

```python
# On Android TV: Uses ADB commands
# On iOS: Uses Appium touch actions
# On STB: Sends IR signals
# On Web: Uses Selenium clicks
```

---

## Supported Actions

### Navigation
- `navigate_to(node)` - Go to any screen in your navigation tree
- `go_home()` - Return to home screen
- `go_back()` - Navigate backwards

### Remote Control
- `press_key(key)` - Press any button (UP, DOWN, SELECT, BACK, etc.)
- `enter_text(text)` - Type text into fields
- `swipe(direction)` - Swipe gestures on touch devices

### Verification
- `verify_text(text)` - Check if text appears on screen
- `verify_image(image_path)` - Compare visual elements
- `capture_screenshot()` - Take evidence screenshots

### Power Management
- `power_on()` - Turn device on
- `power_off()` - Turn device off
- `reboot()` - Restart device

---

## Example: Multi-Device Test

```python
# Test the same app on all platforms
devices = [
    "android_tv_living_room",
    "iphone_12_test",
    "samsung_stb_lab1"
]

for device in devices:
    controller = ControllerFactory.get_controller(device=device)
    
    # Same test code works for all
    controller.navigate_to("netflix")
    controller.enter_text("Stranger Things")
    controller.press_key("SELECT")
    controller.verify_text("Play")
    
    print(f"✅ {device} test passed!")
```

---

## Controller Configuration

Configure devices through the web interface or YAML:

```yaml
models:
  - name: "my_android_tv"
    type: "android_tv"
    connection:
      method: "adb"
      ip: "192.168.1.100"
      port: 5555
    
  - name: "my_stb"
    type: "stb"
    connection:
      method: "ir"
      gpio_pin: 17
      remote_profile: "humax_ir_codes.json"
```

---

## Benefits

### 🚀 Faster Development
Write tests once, deploy everywhere. No need to learn different frameworks for each platform.

### 💰 Cost Savings
One test suite instead of N different suites. Reduce maintenance overhead dramatically.

### 🎯 Better Coverage
Easy to test across all platforms means better multi-device compatibility.

### 🔧 Easy Maintenance
Update test logic once, all devices benefit. Fix once, deploy everywhere.

---

## Under the Hood

VirtualPyTest uses the **Factory Pattern** to create the right controller:

```
User Code
    ↓
ControllerFactory
    ↓
   ┌────────────────┬──────────────┬─────────────┐
   ▼                ▼              ▼             ▼
ADB Controller  Appium Controller  IR Controller  ...
   ↓                ↓              ↓             ↓
Android Device   iOS Device      STB Device    etc.
```

Each controller implements the same interface but uses device-specific methods internally.

---

## Add Your Own Device Type

Extending VirtualPyTest is simple:

1. Create a new controller class
2. Implement the standard interface
3. Register in ControllerFactory
4. Use immediately in your tests!

See [Technical Docs - Controller Creation](../technical/architecture/CONTROLLER_CREATION_GUIDE.md) for details.

---

## Next Steps

- 📖 [Visual Capture](./visual-capture.md) - Monitor what your devices display
- 📖 [AI Validation](./ai-validation.md) - Verify content automatically
- 📚 [User Guide - Running Tests](../user-guide/running-tests.md) - Execute your first test
- 🔧 [Technical Docs - Architecture](../technical/README.md) - Deep dive into controllers

---

**Ready to control all your devices from one script?**  
➡️ [Get Started](../get-started/quickstart.md)

