# VirtualPyTest Examples

Sample scripts and usage examples for VirtualPyTest backend-core functionality.

## 📁 **Available Examples**

### `validation.py`
Complete validation workflow that demonstrates:
- Device control and automation
- Navigation tree traversal
- Screenshot capture and verification
- HTML report generation
- Database result recording

```bash
# Run validation example
python validation.py horizon_android_mobile --device device1
```

### `goto_live_fullscreen.py`
Live streaming and display example showing:
- Video capture and streaming
- Fullscreen display control
- Real-time media processing

```bash
# Run live streaming example
python goto_live_fullscreen.py
```

### `helloworld.py`
Simple automation example demonstrating:
- Basic controller usage
- Device interaction patterns

```bash
# Run hello world example
python helloworld.py
```

## 🔧 **Requirements**

Examples require backend-core and its dependencies:

```bash
# Install backend-core
cd ../
pip install -r requirements.txt
pip install -e .

# Install shared library
pip install -e ../shared
```

## 🎯 **Usage Patterns**

### Device Controller Usage
```python
from backend_core.controllers.remote.android_mobile import AndroidMobileController

# Initialize controller
controller = AndroidMobileController(device_id="device1")

# Basic interactions
controller.tap(500, 300)
controller.swipe(100, 100, 200, 200)
controller.type_text("Hello World")
```

### Service Integration
```python
from backend_core.services.actions.action_executor import ActionExecutor

# Execute actions
executor = ActionExecutor()
result = executor.execute_action({
    "type": "tap",
    "parameters": {"x": 500, "y": 300}
})
```

### Navigation and Verification
```python
from backend_core.services.navigation.navigation_execution import NavigationExecutor
from backend_core.services.verifications.verification_executor import VerificationExecutor

# Navigate through app
navigator = NavigationExecutor()
path = navigator.find_path("home", "settings")

# Verify results
verifier = VerificationExecutor()
result = verifier.verify_image("screenshot.png", "expected.png")
```

## 📝 **Creating New Examples**

1. **Follow naming convention**: `example_name.py`
2. **Add docstring**: Describe purpose and usage
3. **Include error handling**: Graceful failure modes
4. **Add to this README**: Document the new example

### Example Template
```python
#!/usr/bin/env python3
"""
Example Name - Brief Description

This example demonstrates:
- Feature 1
- Feature 2
- Feature 3

Usage:
    python example_name.py [options]
    
Example:
    python example_name.py --device device1
"""

import sys
import argparse
from backend_core.controllers import *

def main():
    """Main example function"""
    parser = argparse.ArgumentParser(description='Example Description')
    parser.add_argument('--device', default='device1', help='Device ID')
    args = parser.parse_args()
    
    try:
        # Example implementation
        print("Example running...")
        
    except Exception as e:
        print(f"Example failed: {e}")
        return 1
    
    print("Example completed successfully")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

## 🧪 **Testing Examples**

```bash
# Test all examples (dry run)
for example in *.py; do
    python "$example" --help
done

# Run specific example with test data
python validation.py test_interface --device mock_device
```

## 🔧 **Configuration**

Examples use shared configuration system:

```python
from shared.lib.config.settings import shared_config

# Access configuration in examples
device_config = shared_config.devices
timeout = shared_config.timeout
```

## 📊 **Common Patterns**

### Error Handling
```python
try:
    controller = AndroidMobileController(device_id=device_id)
    result = controller.tap(x, y)
except DeviceNotFoundError:
    print(f"Device {device_id} not found")
    return 1
except ControllerError as e:
    print(f"Controller error: {e}")
    return 1
```

### Logging
```python
import structlog
logger = structlog.get_logger()

logger.info("example_started", device_id=device_id)
logger.error("example_failed", error=str(e))
```

### Resource Cleanup
```python
import atexit

def cleanup():
    """Cleanup resources on exit"""
    if controller:
        controller.release()

atexit.register(cleanup)
```

## 🤝 **Contributing Examples**

1. **Real-world scenarios**: Examples should solve actual use cases
2. **Well documented**: Clear purpose and usage instructions
3. **Error handling**: Robust failure handling
4. **Reusable patterns**: Code that others can adapt
5. **Test data**: Include sample data where needed

Popular example topics:
- **Mobile app automation**: Login flows, navigation
- **Desktop automation**: File operations, UI interaction  
- **A/V testing**: Video quality, audio verification
- **Integration testing**: Multi-device scenarios
- **Performance testing**: Load testing, benchmarking 