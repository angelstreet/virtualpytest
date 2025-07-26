# VirtualPyTest Backend Core

Pure Python business logic and device controllers for VirtualPyTest framework.

## 🎯 **Purpose**

Backend-core contains the core automation logic and device controllers without any web framework dependencies. It's designed to be imported by other services that need device control capabilities.

## 📦 **What's Included**

- **Device Controllers**: Hardware-specific automation (mobile, desktop, A/V, power)
- **Business Services**: Test execution, navigation, verification logic  
- **Interfaces**: Abstract base classes for controllers
- **Examples**: Sample scripts and usage examples

## 🔧 **Installation**

```bash
# Install dependencies
pip install -r requirements.txt

# Install as editable package
pip install -e .

# Install shared library dependency
pip install -e ../shared
```

## 📁 **Structure**

```
backend-core/src/
├── controllers/             # Device controllers
│   ├── desktop/            # Desktop automation
│   ├── remote/             # Mobile device control
│   ├── audiovideo/         # A/V capture and control
│   ├── power/              # Power management
│   ├── web/                # Web automation
│   └── verification/       # Verification controllers
├── services/               # Business services
│   ├── actions/            # Action execution
│   ├── navigation/         # Navigation pathfinding
│   └── verifications/      # Verification services
├── interfaces/             # Abstract interfaces
└── examples/               # Example scripts
```

## 🚀 **Usage**

### Device Controllers
```python
from backend_core.controllers.desktop.pyautogui import PyAutoGUIController
from backend_core.controllers.remote.android_mobile import AndroidMobileController

# Desktop automation
desktop = PyAutoGUIController()
desktop.click(100, 200)
desktop.type_text("Hello World")

# Mobile automation  
mobile = AndroidMobileController(device_id="device1")
mobile.tap(500, 300)
mobile.swipe(100, 100, 200, 200)
```

### Business Services
```python
from backend_core.services.actions.action_executor import ActionExecutor
from backend_core.services.navigation.navigation_execution import NavigationExecutor

# Execute test actions
executor = ActionExecutor()
result = executor.execute_action({
    "type": "click",
    "parameters": {"x": 100, "y": 200}
})

# Navigate through app
navigator = NavigationExecutor()
path = navigator.find_path(start_node, end_node)
```

## 🎮 **Controllers Available**

### Desktop Controllers
- **PyAutoGUI**: Cross-platform desktop automation
- **Bash**: Command-line automation

### Mobile Controllers  
- **Android Mobile**: Android phone/tablet control
- **Android TV**: Android TV automation
- **iOS**: iOS device control (via Appium)

### A/V Controllers
- **Camera Stream**: Video capture and streaming
- **HDMI Stream**: HDMI input capture
- **Audio Capture**: Audio recording and analysis

### Power Controllers
- **Tapo Power**: Smart plug control
- **UPS**: Uninterruptible power supply

### Web Controllers
- **Playwright**: Modern web automation
- **Browser-use**: AI-powered browser automation

### Verification Controllers
- **Image**: Visual verification
- **Text**: Text content verification  
- **Audio**: Audio verification
- **Video**: Video content verification
- **ADB**: Android debug bridge verification
- **Appium**: Mobile app verification

## 🔧 **Configuration**

Controllers are configured via the shared configuration system:

```python
from shared.lib.config.settings import shared_config

# Controllers automatically use shared config
controller = PyAutoGUIController()  # Uses shared config
```

Device-specific configuration:
```python
from shared.lib.config.devices import load_device_config

# Load device configuration
mobile_config = load_device_config('android_mobile.json')
controller = AndroidMobileController(config=mobile_config)
```

## 🧪 **Examples**

Check the `examples/` directory for sample scripts:

- `validation.py`: Complete validation workflow
- `goto_live_fullscreen.py`: Live streaming example
- `helloworld.py`: Simple automation example

```bash
# Run example
cd examples
python validation.py horizon_android_mobile
```

## 🔄 **Integration**

Backend-core is designed to be imported by:

- **Backend-Host**: Direct hardware control
- **Backend-Server**: Test orchestration
- **Custom Scripts**: Standalone automation

```python
# In backend-host
from backend_core.controllers import *
from backend_core.services import *

# In backend-server  
from backend_core.services.actions import ActionExecutor
```

## 🧪 **Testing**

```bash
# Run controller tests
python -m pytest tests/

# Test specific controller
python -m pytest tests/test_desktop_controllers.py

# Integration tests (requires hardware)
python -m pytest tests/integration/
```

## ⚡ **Performance**

- **Lightweight**: No web framework overhead
- **Direct Control**: Direct hardware access
- **Async Support**: Async/await patterns where beneficial
- **Resource Efficient**: Minimal memory footprint

## 🔧 **Hardware Requirements**

Different controllers have different requirements:

- **Desktop**: Local display server (X11, Wayland, Windows)
- **Mobile**: ADB access, Appium server
- **A/V**: Video capture devices, audio interfaces
- **Power**: Smart plug access, UPS connections

## 📋 **Dependencies**

See `requirements.txt` for full list. Key dependencies:

- **Hardware Control**: pyautogui, pynput, opencv-python
- **Mobile**: Appium-Python-Client, selenium
- **A/V**: ffmpeg-python, Pillow
- **Web**: playwright, beautifulsoup4
- **Power**: PyP100 (Tapo devices)

## 🤝 **Contributing**

1. Add new controllers to appropriate subdirectory
2. Inherit from base controller interface
3. Add configuration schema
4. Include example usage
5. Add tests for new functionality 