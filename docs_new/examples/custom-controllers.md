# Custom Controllers Examples

**How to add support for new devices and extend VirtualPyTest capabilities.**

---

## 🎯 **What are Custom Controllers?**

Custom controllers allow you to:
- **Add new device types** (Smart TVs, gaming consoles, etc.)
- **Implement custom protocols** (proprietary APIs, serial communication)
- **Extend verification capabilities** (custom image recognition, audio analysis)
- **Create specialized automation** (device-specific workflows)

---

## 🏗️ **Controller Architecture**

### Controller Types
VirtualPyTest supports these controller categories:

```python
CONTROLLER_TYPES = {
    'remote': 'Device control (buttons, navigation)',
    'av': 'Audio/Video capture and streaming',
    'verification': 'Content verification and validation',
    'power': 'Power management and control',
    'desktop': 'Desktop/computer automation',
    'web': 'Web browser automation',
    'ai': 'AI-powered automation'
}
```

---

## 🎮 **Creating a Remote Controller**

### Basic Remote Controller Template
```python
# backend_host/src/controllers/remote/custom_device.py
"""
Custom Device Remote Controller
"""
import time
import requests
from typing import Dict, Any, Optional
from ..base_controller import RemoteControllerInterface

class CustomDeviceRemoteController(RemoteControllerInterface):
    """
    Remote controller for CustomDevice using HTTP API
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.device_ip = config.get('device_ip', '192.168.1.100')
        self.device_port = config.get('device_port', 8080)
        self.api_key = config.get('api_key', '')
        self.base_url = f"http://{self.device_ip}:{self.device_port}"
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize connection to device"""
        try:
            self.session = requests.Session()
            if self.api_key:
                self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
            
            # Test connection
            response = self.session.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                self.logger.info("CustomDevice controller initialized successfully")
                return True
            else:
                self.logger.error(f"Failed to connect to device: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize CustomDevice controller: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources"""
        if self.session:
            self.session.close()
        return True
    
    def press_key(self, key: str) -> bool:
        """Press a key on the remote"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/remote/key",
                json={'key': key},
                timeout=5
            )
            
            success = response.status_code == 200
            if success:
                self.logger.debug(f"Successfully pressed key: {key}")
            else:
                self.logger.error(f"Failed to press key {key}: HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error pressing key {key}: {e}")
            return False
    
    def navigate(self, direction: str) -> bool:
        """Navigate in a direction (up, down, left, right)"""
        direction_map = {
            'up': 'UP',
            'down': 'DOWN', 
            'left': 'LEFT',
            'right': 'RIGHT'
        }
        
        if direction.lower() not in direction_map:
            self.logger.error(f"Invalid direction: {direction}")
            return False
        
        return self.press_key(direction_map[direction.lower()])
    
    def send_text(self, text: str) -> bool:
        """Send text input to device"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/remote/text",
                json={'text': text},
                timeout=10
            )
            
            success = response.status_code == 200
            if success:
                self.logger.debug(f"Successfully sent text: {text}")
            else:
                self.logger.error(f"Failed to send text: HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending text: {e}")
            return False
    
    def get_device_status(self) -> Optional[Dict[str, Any]]:
        """Get current device status"""
        try:
            response = self.session.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get status: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting device status: {e}")
            return None
    
    # Custom methods specific to this device
    def launch_app(self, app_name: str) -> bool:
        """Launch a specific app on the device"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/apps/launch",
                json={'app_name': app_name},
                timeout=15
            )
            
            success = response.status_code == 200
            if success:
                self.logger.info(f"Successfully launched app: {app_name}")
            else:
                self.logger.error(f"Failed to launch app {app_name}: HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error launching app {app_name}: {e}")
            return False
    
    def set_volume(self, volume: int) -> bool:
        """Set device volume (0-100)"""
        if not 0 <= volume <= 100:
            self.logger.error(f"Invalid volume level: {volume}")
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/audio/volume",
                json={'volume': volume},
                timeout=5
            )
            
            success = response.status_code == 200
            if success:
                self.logger.debug(f"Successfully set volume to: {volume}")
            else:
                self.logger.error(f"Failed to set volume: HTTP {response.status_code}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error setting volume: {e}")
            return False
```

---

## 📹 **Creating an AV Controller**

### Custom AV Controller Template
```python
# backend_host/src/controllers/audiovideo/custom_capture.py
"""
Custom Video Capture Controller
"""
import subprocess
import os
from typing import Optional
from ..base_controller import AVControllerInterface

class CustomCaptureController(AVControllerInterface):
    """
    Custom video capture controller using specialized hardware
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.device_path = config.get('device_path', '/dev/video0')
        self.resolution = config.get('resolution', '1920x1080')
        self.fps = config.get('fps', 30)
        self.quality = config.get('quality', 80)
        self.stream_port = config.get('stream_port', 8554)
        self.stream_process = None
        
    def initialize(self) -> bool:
        """Initialize capture device"""
        try:
            # Check if device exists
            if not os.path.exists(self.device_path):
                self.logger.error(f"Capture device not found: {self.device_path}")
                return False
            
            # Test capture capability
            test_cmd = [
                'ffprobe', '-v', 'quiet', '-f', 'v4l2',
                '-i', self.device_path
            ]
            
            result = subprocess.run(test_cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("Custom capture controller initialized successfully")
                return True
            else:
                self.logger.error("Failed to initialize capture device")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize capture controller: {e}")
            return False
    
    def get_stream_url(self) -> str:
        """Get live stream URL"""
        return f"rtmp://localhost:{self.stream_port}/live/stream"
    
    def capture_screenshot(self, path: str) -> bool:
        """Capture screenshot to file"""
        try:
            cmd = [
                'ffmpeg', '-f', 'v4l2', '-i', self.device_path,
                '-vframes', '1', '-s', self.resolution,
                '-q:v', str(self.quality), '-y', path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            success = result.returncode == 0 and os.path.exists(path)
            if success:
                self.logger.debug(f"Successfully captured screenshot: {path}")
            else:
                self.logger.error(f"Failed to capture screenshot: {result.stderr}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {e}")
            return False
    
    def start_stream(self) -> bool:
        """Start live video stream"""
        try:
            if self.stream_process and self.stream_process.poll() is None:
                self.logger.warning("Stream already running")
                return True
            
            cmd = [
                'ffmpeg', '-f', 'v4l2', '-i', self.device_path,
                '-c:v', 'libx264', '-preset', 'ultrafast',
                '-tune', 'zerolatency', '-s', self.resolution,
                '-r', str(self.fps), '-f', 'flv',
                f"rtmp://localhost:{self.stream_port}/live/stream"
            ]
            
            self.stream_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            if self.stream_process.poll() is None:
                self.logger.info("Live stream started successfully")
                return True
            else:
                self.logger.error("Failed to start live stream")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting stream: {e}")
            return False
    
    def stop_stream(self) -> bool:
        """Stop live video stream"""
        try:
            if self.stream_process and self.stream_process.poll() is None:
                self.stream_process.terminate()
                self.stream_process.wait(timeout=10)
                self.logger.info("Live stream stopped")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping stream: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources"""
        return self.stop_stream()
```

---

## 🔍 **Creating a Verification Controller**

### Custom Verification Controller Template
```python
# backend_host/src/controllers/verification/custom_verify.py
"""
Custom Content Verification Controller
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from ..base_controller import VerificationControllerInterface

class CustomVerificationController(VerificationControllerInterface):
    """
    Custom verification controller with specialized image analysis
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.confidence_threshold = config.get('confidence_threshold', 0.8)
        self.template_path = config.get('template_path', 'templates/')
        
    def initialize(self) -> bool:
        """Initialize verification resources"""
        try:
            # Load custom models, templates, etc.
            self.logger.info("Custom verification controller initialized")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize verification controller: {e}")
            return False
    
    def verify_element_present(self, element_name: str, screenshot_path: str) -> bool:
        """Verify if a UI element is present in screenshot"""
        try:
            # Load screenshot
            screenshot = cv2.imread(screenshot_path)
            if screenshot is None:
                self.logger.error(f"Failed to load screenshot: {screenshot_path}")
                return False
            
            # Load template
            template_file = f"{self.template_path}/{element_name}.png"
            template = cv2.imread(template_file)
            if template is None:
                self.logger.error(f"Template not found: {template_file}")
                return False
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            found = max_val >= self.confidence_threshold
            
            if found:
                self.logger.debug(f"Element '{element_name}' found with confidence {max_val:.2f}")
            else:
                self.logger.debug(f"Element '{element_name}' not found (confidence {max_val:.2f})")
            
            return found
            
        except Exception as e:
            self.logger.error(f"Error verifying element {element_name}: {e}")
            return False
    
    def verify_text_present(self, expected_text: str, screenshot_path: str) -> bool:
        """Verify if text is present in screenshot using OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            # Load and process image
            image = Image.open(screenshot_path)
            
            # Extract text using OCR
            detected_text = pytesseract.image_to_string(image)
            
            # Check if expected text is present
            found = expected_text.lower() in detected_text.lower()
            
            if found:
                self.logger.debug(f"Text '{expected_text}' found in screenshot")
            else:
                self.logger.debug(f"Text '{expected_text}' not found in screenshot")
            
            return found
            
        except Exception as e:
            self.logger.error(f"Error verifying text '{expected_text}': {e}")
            return False
    
    def verify_color_present(self, color_rgb: tuple, screenshot_path: str, 
                           tolerance: int = 10) -> bool:
        """Verify if a specific color is present in screenshot"""
        try:
            # Load screenshot
            image = cv2.imread(screenshot_path)
            if image is None:
                return False
            
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Create color range
            target_color = np.array(color_rgb)
            lower_bound = np.clip(target_color - tolerance, 0, 255)
            upper_bound = np.clip(target_color + tolerance, 0, 255)
            
            # Create mask for color range
            mask = cv2.inRange(image_rgb, lower_bound, upper_bound)
            
            # Check if color is present
            found = np.any(mask > 0)
            
            if found:
                pixel_count = np.count_nonzero(mask)
                self.logger.debug(f"Color {color_rgb} found ({pixel_count} pixels)")
            else:
                self.logger.debug(f"Color {color_rgb} not found")
            
            return found
            
        except Exception as e:
            self.logger.error(f"Error verifying color {color_rgb}: {e}")
            return False
    
    def detect_motion(self, screenshot1_path: str, screenshot2_path: str,
                     threshold: float = 0.1) -> bool:
        """Detect motion between two screenshots"""
        try:
            # Load images
            img1 = cv2.imread(screenshot1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(screenshot2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return False
            
            # Calculate difference
            diff = cv2.absdiff(img1, img2)
            
            # Calculate motion percentage
            motion_pixels = np.count_nonzero(diff > 30)  # Threshold for significant change
            total_pixels = diff.shape[0] * diff.shape[1]
            motion_percentage = motion_pixels / total_pixels
            
            motion_detected = motion_percentage > threshold
            
            if motion_detected:
                self.logger.debug(f"Motion detected: {motion_percentage:.2%}")
            else:
                self.logger.debug(f"No motion detected: {motion_percentage:.2%}")
            
            return motion_detected
            
        except Exception as e:
            self.logger.error(f"Error detecting motion: {e}")
            return False
```

---

## 📝 **Registering Custom Controllers**

### Update Controller Registry
```python
# backend_host/src/controllers/__init__.py
# Add your custom controllers to the registry

# Import your custom controllers
from .remote.custom_device import CustomDeviceRemoteController
from .audiovideo.custom_capture import CustomCaptureController
from .verification.custom_verify import CustomVerificationController

# Update the controller registry
CONTROLLER_REGISTRY = {
    'remote': {
        # ... existing controllers ...
        'custom_device': CustomDeviceRemoteController,
    },
    'av': {
        # ... existing controllers ...
        'custom_capture': CustomCaptureController,
    },
    'verification': {
        # ... existing controllers ...
        'custom_verify': CustomVerificationController,
    },
    # ... other controller types ...
}
```

### Update Device Controller Mapping
```python
# backend_host/src/controllers/controller_config_factory.py
# Add your device to the mapping

DEVICE_CONTROLLER_MAP = {
    # ... existing device mappings ...
    'custom_smart_tv': {
        'av': ['custom_capture'],
        'remote': ['custom_device'],
        'verification': ['custom_verify'],
        'power': ['tapo'],  # Reuse existing power controller
        'ai': ['ai_agent']
    },
}
```

---

## 🔧 **Configuration Examples**

### Device Configuration File
```json
{
  "custom_smart_tv": {
    "name": "Custom Smart TV",
    "description": "Custom smart TV with HTTP API",
    "remote_config": {
      "device_ip": "192.168.1.100",
      "device_port": 8080,
      "api_key": "your-api-key-here",
      "timeout": 10
    },
    "av_config": {
      "device_path": "/dev/video0",
      "resolution": "1920x1080",
      "fps": 30,
      "quality": 85,
      "stream_port": 8554
    },
    "verification_config": {
      "confidence_threshold": 0.8,
      "template_path": "templates/custom_tv/",
      "ocr_language": "eng"
    }
  }
}
```

### Environment Configuration
```bash
# Custom device configuration
CUSTOM_TV_IP=192.168.1.100
CUSTOM_TV_PORT=8080
CUSTOM_TV_API_KEY=your-api-key

# Custom capture configuration
CUSTOM_CAPTURE_DEVICE=/dev/video0
CUSTOM_CAPTURE_RESOLUTION=1920x1080
CUSTOM_CAPTURE_FPS=30
```

---

## 🧪 **Testing Custom Controllers**

### Unit Tests
```python
# tests/test_custom_device_controller.py
import unittest
from unittest.mock import Mock, patch
from backend_host.src.controllers.remote.custom_device import CustomDeviceRemoteController

class TestCustomDeviceController(unittest.TestCase):
    
    def setUp(self):
        self.config = {
            'device_ip': '192.168.1.100',
            'device_port': 8080,
            'api_key': 'test-key'
        }
        self.controller = CustomDeviceRemoteController(self.config)
    
    @patch('requests.Session')
    def test_initialize_success(self, mock_session):
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        
        result = self.controller.initialize()
        
        self.assertTrue(result)
        mock_session.return_value.get.assert_called_once()
    
    @patch('requests.Session')
    def test_press_key_success(self, mock_session):
        # Setup
        self.controller.session = mock_session.return_value
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.post.return_value = mock_response
        
        result = self.controller.press_key('home')
        
        self.assertTrue(result)
        mock_session.return_value.post.assert_called_once()
    
    def test_navigate_invalid_direction(self):
        result = self.controller.navigate('invalid')
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests
```python
# tests/integration/test_custom_device_integration.py
import unittest
from backend_host.src.controllers.remote.custom_device import CustomDeviceRemoteController

class TestCustomDeviceIntegration(unittest.TestCase):
    """
    Integration tests for custom device controller
    Requires actual device for testing
    """
    
    @classmethod
    def setUpClass(cls):
        cls.config = {
            'device_ip': '192.168.1.100',  # Real device IP
            'device_port': 8080,
            'api_key': 'real-api-key'
        }
        cls.controller = CustomDeviceRemoteController(cls.config)
        cls.controller.initialize()
    
    def test_device_status(self):
        """Test getting device status"""
        status = self.controller.get_device_status()
        self.assertIsNotNone(status)
        self.assertIn('power_state', status)
    
    def test_key_press_sequence(self):
        """Test sequence of key presses"""
        # Test navigation sequence
        self.assertTrue(self.controller.press_key('home'))
        time.sleep(1)
        self.assertTrue(self.controller.navigate('down'))
        time.sleep(1)
        self.assertTrue(self.controller.press_key('ok'))
    
    @classmethod
    def tearDownClass(cls):
        cls.controller.cleanup()
```

---

## 🚀 **Using Custom Controllers**

### In Test Scripts
```python
#!/usr/bin/env python3
"""
Test script using custom controller
"""
from backend_host.controllers import get_controller

def test_custom_device():
    """Test custom device functionality"""
    
    # Get custom controller
    controller = get_controller('remote', 'custom_device')
    
    if not controller.initialize():
        print("❌ Failed to initialize custom device")
        return False
    
    try:
        # Test basic functionality
        print("🏠 Pressing home button...")
        controller.press_key('home')
        
        print("📱 Launching Netflix app...")
        controller.launch_app('Netflix')
        
        print("🔊 Setting volume to 50...")
        controller.set_volume(50)
        
        print("✅ Custom device test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        controller.cleanup()

if __name__ == "__main__":
    test_custom_device()
```

### In Navigation Trees
```python
# Add custom device to navigation configuration
custom_tv_navigation = {
    "device_model": "custom_smart_tv",
    "nodes": {
        "home": {
            "actions": [{"type": "press_key", "key": "home"}]
        },
        "netflix": {
            "actions": [
                {"type": "press_key", "key": "home"},
                {"type": "launch_app", "app_name": "Netflix"}
            ]
        },
        "settings": {
            "actions": [
                {"type": "press_key", "key": "menu"},
                {"type": "navigate", "direction": "down"},
                {"type": "press_key", "key": "ok"}
            ]
        }
    }
}
```

---

## 📊 **Best Practices**

### Controller Design
1. **Inherit from Base Interface**: Always extend the appropriate base controller
2. **Handle Errors Gracefully**: Implement proper error handling and logging
3. **Resource Management**: Always cleanup resources in `cleanup()` method
4. **Configuration Driven**: Use configuration for all customizable parameters
5. **Async Support**: Consider async operations for long-running tasks

### Testing Strategy
1. **Unit Tests**: Test individual methods with mocked dependencies
2. **Integration Tests**: Test with actual hardware when possible
3. **Error Scenarios**: Test failure conditions and error handling
4. **Performance Tests**: Verify controller performance under load

### Documentation
1. **Code Documentation**: Add docstrings to all methods
2. **Configuration Examples**: Provide sample configuration files
3. **Usage Examples**: Include practical usage examples
4. **Troubleshooting Guide**: Document common issues and solutions

---

**Ready to contribute back? Check our [Technical Architecture](../technical/architecture.md) for contribution guidelines!** 🤝
