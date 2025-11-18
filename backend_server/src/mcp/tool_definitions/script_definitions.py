"""Script tool definitions for Python script execution"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get script-related tool definitions"""
    return [
        {
            "name": "list_scripts",
            "description": """List all available Python scripts

Returns all scripts from the scripts directory.

Example:
  list_scripts()""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": []
            }
        },
        {
            "name": "execute_script",
            "description": """Execute a Python script on device

PREREQUISITE: take_control() should be called first if script uses device controls.

Executes a Python script with optional CLI parameters.
Polls automatically until completion (up to 2 hours for long scripts).

Example:
  # First get compatible host
  hosts = get_compatible_hosts(userinterface_name='your-interface')
  
  execute_script(
    script_name='my_validation.py',
    host_name=hosts['recommended_host'],
    device_id=hosts['recommended_device'],
    userinterface_name='horizon_android_mobile',
    parameters='--param1 value1 --param2 value2'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "script_name": {"type": "string", "description": "Script filename (e.g., 'my_script.py')"},
                    "host_name": {"type": "string", "description": "Host where device is located"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                    "userinterface_name": {"type": "string", "description": "Userinterface name (e.g., 'horizon_android_mobile', 'horizon_tv') - REQUIRED if script uses it"},
                    "parameters": {"type": "string", "description": "Additional CLI parameters as string (optional, e.g., '--param1 value1')"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["script_name", "host_name"]
            }
        }
    ]

