"""Testcase tool definitions for test case management and execution"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get testcase-related tool definitions"""
    return [
        {
            "name": "execute_testcase",
            "description": """Execute a test case by name (or graph for unsaved testcases)

Executes saved test cases by name or unsaved testcases by graph.
Polls automatically until completion (up to 5 minutes).

Usage:
  # Execute saved testcase by name
  execute_testcase(
    testcase_name='Login Flow Test',
    host_name='sunri-pi1',
    device_id='device1',
    userinterface_name='horizon_android_mobile'
  )
  
  # Execute unsaved testcase with graph
  execute_testcase(
    testcase_name='temp_test',
    graph_json=graph_from_generate_test_graph,
    host_name='sunri-pi1',
    device_id='device1',
    userinterface_name='horizon_android_mobile'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_name": {"type": "string", "description": "Test case name like 'Login Flow Test' (REQUIRED)"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (REQUIRED)"},
                    "device_id": {"type": "string", "description": "Device identifier (REQUIRED)"},
                    "userinterface_name": {"type": "string", "description": "User interface name (REQUIRED)"},
                    "graph_json": {"type": "object", "description": "Test case graph from generate_test_graph() - only for unsaved testcases (OPTIONAL)"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["testcase_name", "host_name", "device_id", "userinterface_name"]
            }
        },
        {
            "name": "execute_testcase_by_id",
            "description": """⚠️ DEPRECATED: Load and execute a saved test case by ID

DEPRECATED: Use execute_testcase(testcase_name='...') instead.
This wrapper is kept for backward compatibility only.

Example:
  # OLD WAY (deprecated)
  execute_testcase_by_id(testcase_id='abc-123-def-456', ...)
  
  # NEW WAY (preferred)
  execute_testcase(testcase_name='Login Flow Test', ...)

Polls automatically until completion (up to 5 minutes).""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Test case ID from list_testcases()"},
                    "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
                    "host_name": {"type": "string", "description": "Host name where device is connected (required)"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "userinterface_name": {"type": "string", "description": "Override interface name (optional - uses testcase's interface if omitted)"}
                },
                "required": ["testcase_id", "host_name"]
            }
        },
        {
            "name": "save_testcase",
            "description": """Save a test case graph to database

Saves graph from generate_test_graph() for later reuse.
Can organize with folders and tags.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_name": {"type": "string", "description": "Name for the test case"},
                    "graph_json": {"type": "object", "description": "Test case graph from generate_test_graph()"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "description": {"type": "string", "description": "Description of what this test case does"},
                    "userinterface_name": {"type": "string", "description": "User interface name"},
                    "folder": {"type": "string", "description": "Folder path like 'smoke_tests' (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags like ['regression', 'critical'] (optional)"}
                },
                "required": ["testcase_name", "graph_json"]
            }
        },
        {
            "name": "list_testcases",
            "description": """List all saved test cases

Returns list of saved test cases with names, descriptions, and IDs.""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                    "include_inactive": {"type": "boolean", "description": "Include deleted test cases (optional, default: false)"}
                },
                "required": []
            }
        },
        {
            "name": "load_testcase",
            "description": """Load a saved test case by ID

Loads test case graph that can be passed to execute_testcase().""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Test case ID from list_testcases()"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["testcase_id"]
            }
        },
        {
            "name": "rename_testcase",
            "description": """Rename an existing test case

Updates the testcase_name field while preserving all other data.

Example:
  rename_testcase(
    testcase_id='abc-123-def-456',
    new_name='TC_PLAY_01_BasicPlayback'
  )""",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "testcase_id": {"type": "string", "description": "Test case UUID to rename (from list_testcases)"},
                    "new_name": {"type": "string", "description": "New name for the testcase"},
                    "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                },
                "required": ["testcase_id", "new_name"]
            }
        }
    ]

