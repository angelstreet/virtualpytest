"""Control tool definitions for device control and locking"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get control-related tool definitions"""
    return [
        {
            "name": "take_control",
            "description": """Take exclusive control of a device.

Locks the device for exclusive use to prevent conflicts.
Required before executing any device operations.

Example:
  take_control(host_name='sunri-pi1', device_id='device1')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier (e.g. 'device1')"}
                },
                "required": ["host_name", "device_id"]
            }
        },
        {
            "name": "release_control",
            "description": """Release device control when done.

Unlocks the device so others can use it.

Example:
  release_control(host_name='sunri-pi1', device_id='device1')""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "host_name": {"type": "string", "description": "Host name where device is connected"},
                    "device_id": {"type": "string", "description": "Device identifier (e.g. 'device1')"}
                },
                "required": ["host_name", "device_id"]
            }
        }
    ]

