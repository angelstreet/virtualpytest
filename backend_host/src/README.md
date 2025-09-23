# VirtualPyTest Backend Core

**Shared library** containing pure Python business logic and device controllers for VirtualPyTest framework.

## 🎯 **Purpose**

backend_host is a **shared library component** that contains core automation logic and device controllers without any web framework dependencies. It's designed to be imported by other services (backend_server, backend_host) that need device control capabilities.

**⚠️ Note**: This is NOT a standalone service - it's a library that gets imported by other components.

## 📦 **What's Included**

- **Device Controllers**: Hardware-specific automation (mobile, desktop, A/V, power)
- **Business Services**: Test execution, navigation, verification logic  
- **Interfaces**: Abstract base classes for controllers
- **Examples**: Sample scripts and usage examples

## 🔧 **Installation**

**Note**: backend_host is a shared library component. Dependencies are managed by the services that import it.

For local development:
```bash
# Install as editable package (optional for development)
pip install -e .
```

For production, backend_host is included in service Docker containers via PYTHONPATH along with the `shared` library.

## 📁 **Structure**

```
backend_host/src/
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
from backend_host.src.controllers.desktop.pyautogui import PyAutoGUIController
from backend_host.src.controllers.remote.android_mobile import AndroidMobileController

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
from backend_host.services.actions.action_executor import ActionExecutor
from backend_host.services.navigation.navigation_execution import NavigationExecutor

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

backend_host is a **shared library** imported by:

- **backend_host**: Direct hardware control service
- **backend_server**: Test orchestration service  
- **Custom Scripts**: Standalone automation scripts

```python
# In backend_host service
from backend_host.controllers import *
from backend_host.services import *

# In backend_server service
from backend_host.services.actions import ActionExecutor

# In standalone scripts
from backend_host.src.controllers.desktop.pyautogui import PyAutoGUIController
```

### Docker Integration

backend_host is included in other services' Docker containers via PYTHONPATH:

```dockerfile
# In backend_server/Dockerfile and backend_host/Dockerfile
COPY backend_host/ backend_host/
ENV PYTHONPATH="/app/shared:/app/shared/lib:/app/backend_host/src"
```

## 🚀 **Deployment Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  backend_server │    │  backend_host   │    │  Custom Scripts │
│  (Docker)       │    │  (Docker)       │    │  (Local)        │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Flask API     │    │ • Hardware API  │    │ • Direct usage  │
│ • Orchestration │    │ • Device Control│    │ • Automation    │
│                 │    │                 │    │                 │
│ Imports:        │    │ Imports:        │    │ Imports:        │
│ backend_host ←──┼────┼─→ backend_host ←─┼────┼─→ backend_host  │
│ shared       ←──┼────┼─→ shared       ←─┼────┼─→ shared        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Key Points:**
- ✅ **backend_host**: Shared library (no Docker container)
- ✅ **shared**: Shared library (no Docker container)  
- 🐳 **backend_server**: Deployable service (has Docker container)
- 🐳 **backend_host**: Deployable service (has Docker container)

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

Dependencies are managed by the services that import backend_host. Key dependencies include:

- **Hardware Control**: pyautogui, pynput, opencv-python
- **Mobile**: Appium-Python-Client, selenium
- **A/V**: ffmpeg-python, Pillow
- **Web**: playwright, beautifulsoup4
- **Power**: PyP100 (Tapo devices)

These are installed by `backend_server/requirements.txt` and `backend_host/requirements.txt`.

## 🤝 **Contributing**

1. Add new controllers to appropriate subdirectory
2. Inherit from base controller interface
3. Add configuration schema
4. Include example usage
5. Add tests for new functionality 