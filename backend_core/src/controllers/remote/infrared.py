"""
IR Remote Controller Implementation

This controller provides IR (Infrared) remote control functionality for TVs, STBs, and other devices.
Supports classic remote control buttons with standard IR keycodes.
"""

from typing import Dict, Any, List, Optional
import subprocess
import time
import json
import os
from pathlib import Path
from ..base_controller import RemoteControllerInterface


class IRRemoteController(RemoteControllerInterface):
    """IR remote controller using external script with JSON config files."""

    @staticmethod
    def get_remote_config() -> Dict[str, Any]:
        """Get the IR remote configuration including layout, buttons, and image."""
        # Return a generic IR remote configuration since actual keys depend on the config file
        return {
            "id": "ir_remote",
            "name": "IR Remote",
            "type": "ir_remote",
            "image": "infrared_remote.png",
            "buttons": [
                {"id": "POWER", "label": "Power", "x": 50, "y": 30},
                {"id": "VOLUME_UP", "label": "Vol+", "x": 20, "y": 60},
                {"id": "VOLUME_DOWN", "label": "Vol-", "x": 20, "y": 90},
                {"id": "UP", "label": "↑", "x": 50, "y": 120},
                {"id": "DOWN", "label": "↓", "x": 50, "y": 180},
                {"id": "LEFT", "label": "←", "x": 20, "y": 150},
                {"id": "RIGHT", "label": "→", "x": 80, "y": 150},
                {"id": "OK", "label": "OK", "x": 50, "y": 150}
            ]
        }
    
    def __init__(self, ir_path: str = None, ir_type: str = None, **kwargs):
        """
        Initialize the Infrared remote controller.
        
        Args:
            ir_path: Path to IR device (e.g., '/dev/lirc0')
            ir_type: Type of IR config file (e.g., 'samsung')
        """
        super().__init__("IR Remote", "infrared")
        
        # IR device parameters
        self.ir_path = ir_path
        self.ir_type = ir_type
        
        # Validate required parameters
        if not self.ir_path:
            raise ValueError("ir_path is required for IRRemoteController")
        if not self.ir_type:
            raise ValueError("ir_type is required for IRRemoteController")
            
        # IR config paths
        self.ir_config_path = os.path.join(
            os.path.dirname(__file__), 'ir_conf'
        )
        self.ir_config_file = f"{self.ir_type}.json"
        
        # IR connection state
        self.ir_available_keys = []
        self.ir_config_data = {}
        
        # Timing attributes
        self.last_command_time = 0
        
        print(f"[@controller:InfraredRemote] Initialized for device: {self.ir_path}")
        print(f"[@controller:InfraredRemote] Using config type: {self.ir_type}")
        
    def connect(self) -> bool:
        """Connect to IR transmitter device."""
        try:
            print(f"Remote[{self.device_type.upper()}]: Initializing IR device {self.ir_path}")
            
            # Load IR configuration first
            success, config_data = self._load_ir_config()
            if not success:
                return False
                
            self.ir_available_keys = list(config_data.keys())
            self.ir_config_data = config_data
            print(f"Remote[{self.device_type.upper()}]: Loaded {len(self.ir_available_keys)} keys from {self.ir_config_file}")
            
            # Check if IR device exists (warn but don't fail for testing)
            if not os.path.exists(self.ir_path):
                print(f"Remote[{self.device_type.upper()}]: WARNING - IR device not found: {self.ir_path}")
                print(f"Remote[{self.device_type.upper()}]: Continuing with config-only mode for testing")
                
            self.is_connected = True
            print(f"Remote[{self.device_type.upper()}]: Connected to {self.device_name}")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Connection failed: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Disconnect from IR transmitter."""
        try:
            self.ir_available_keys = []
            self.is_connected = False
            print(f"Remote[{self.device_type.upper()}]: Disconnected from {self.device_name}")
            return True
            
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Disconnect error: {e}")
            return False
            
    def press_key(self, key: str) -> bool:
        """Send IR key press command."""
        if not self.is_connected:
            print(f"Remote[{self.device_type.upper()}]: ERROR - Not connected")
            return False
            
        key_upper = key.upper()
        
        # Check if key is available in config
        if key_upper not in self.ir_available_keys:
            print(f"Remote[{self.device_type.upper()}]: Key '{key_upper}' not found")
            return False
            
        print(f"Remote[{self.device_type.upper()}]: Sending {key_upper}")
        return self._send_ir_command_integrated(key_upper)
            
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Execute IR remote command - only press_key supported."""
        if params is None:
            params = {}
        
        if command == 'press_key':
            key = params.get('key')
            return self.press_key(key) if key else False
        
        print(f"Remote[{self.device_type.upper()}]: Unknown command: {command}")
        return False
    

            
    def _load_ir_config(self) -> tuple[bool, dict]:
        """
        Load IR configuration from JSON file.
        
        Returns:
            tuple: (success, config_data)
        """
        ir_config_full_path = os.path.join(self.ir_config_path, self.ir_config_file)
        
        if not os.path.exists(ir_config_full_path):
            print(f"Remote[{self.device_type.upper()}]: IR config file not found: {ir_config_full_path}")
            return False, {}
            
        try:
            with open(ir_config_full_path, 'r') as f:
                config_data = json.load(f)
                return True, config_data
        except json.JSONDecodeError as e:
            print(f"Remote[{self.device_type.upper()}]: Invalid JSON in config file {ir_config_full_path}: {e}")
            return False, {}
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Error reading config file {ir_config_full_path}: {e}")
            return False, {}
    
    def _send_ir_command_integrated(self, key: str) -> bool:
        """
        Send IR command using integrated ir-ctl functionality.
        
        Args:
            key: Key name to send
            
        Returns:
            bool: True if command sent successfully
        """
        import tempfile
        
        try:
            # Get raw IR code from config
            raw_code = self.ir_config_data.get(key)
            if not raw_code:
                print(f"Remote[{self.device_type.upper()}]: Key {key} not found in {self.ir_config_file}")
                return False
            
            print(f"Remote[{self.device_type.upper()}]: Sending IR code for {key}")
            print(f"Remote[{self.device_type.upper()}]: Raw IR code: {raw_code[:100]}...")  # Debug: show first 100 chars
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(raw_code)
                temp_path = temp_file.name
            
            print(f"Remote[{self.device_type.upper()}]: Running command: sudo ir-ctl --device {self.ir_path} --send {temp_path}")
            
            result = subprocess.run(
                ["sudo", "ir-ctl", "--device", self.ir_path, "--send", temp_path], 
                check=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            print(f"Remote[{self.device_type.upper()}]: Successfully sent IR code for {key}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Remote[{self.device_type.upper()}]: Failed to send IR code: {e}")
            if e.stderr:
                print(f"Remote[{self.device_type.upper()}]: stderr: {e.stderr}")
            if e.stdout:
                print(f"Remote[{self.device_type.upper()}]: stdout: {e.stdout}")
            print(f"Remote[{self.device_type.upper()}]: Return code: {e.returncode}")
            return False
        except FileNotFoundError:
            print(f"Remote[{self.device_type.upper()}]: ir-ctl command not found. Please install lirc-tools.")
            return False
        except subprocess.TimeoutExpired:
            print(f"Remote[{self.device_type.upper()}]: IR command timed out")
            return False
        except Exception as e:
            print(f"Remote[{self.device_type.upper()}]: Unexpected error sending IR code: {e}")
            return False
        finally:
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f"Remote[{self.device_type.upper()}]: Failed to delete temp file: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status information."""
        return {
            'controller_type': self.controller_type,
            'device_type': self.device_type,
            'device_name': self.device_name,
            'ir_path': self.ir_path,
            'ir_type': self.ir_type,
            'ir_config_file': self.ir_config_file,
            'connection_timeout': self.connection_timeout,
            'command_delay': self.command_delay,
            'connected': self.is_connected,
            'last_command_time': self.last_command_time,
            'supported_keys': self.ir_available_keys,
            'capabilities': [
                'navigation', 'numeric_input', 'media_control', 
                'volume_control', 'channel_control', 'power_control',
                'color_buttons', 'function_buttons', 'tv_controls',
                'stb_controls'
            ]
        }
    
    def get_available_actions(self) -> Dict[str, Any]:
        """Get available actions from loaded IR config JSON."""
        if not self.ir_config_data:
            raise ValueError(f"No IR config loaded for {self.ir_type}")
        
        # Create actions for all keys in the config
        actions = []
        for key_name in self.ir_config_data.keys():
            # Skip empty keys
            if not self.ir_config_data[key_name]:
                continue
                
            actions.append({
                'id': f'ir_press_key_{key_name.lower()}',
                'label': f'IR {key_name}',
                'command': 'press_key',
                'action_type': 'remote',
                'params': {'key': key_name},
                'description': f'Press {key_name} key via infrared',
                'requiresInput': False
            })
        
        return {'remote': actions}
