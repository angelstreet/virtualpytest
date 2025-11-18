"""Screenshot tool definitions for capturing device screenshots"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get screenshot-related tool definitions"""
    return [
        {
            "name": "capture_screenshot",
            "description": "Capture screenshot from device for AI vision analysis. Returns base64 image.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "include_ui_dump": {"type": "boolean", "description": "Include UI hierarchy dump for element detection"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"}
                },
                "required": []
            }
        }
    ]

