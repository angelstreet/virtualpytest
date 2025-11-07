#!/usr/bin/env python3
"""
MCP Server for VirtualPyTest

Model Context Protocol server that exposes VirtualPyTest device control
functionality to external LLMs (Claude, ChatGPT, etc.)

This server provides 17 core tools for device automation:
1. take_control - Lock device and generate navigation cache (ONLY for navigation)
2. execute_device_action - Execute remote/ADB/web/desktop commands
3. navigate_to_node - Navigate through UI trees
4. verify_device_state - Verify UI elements and device states
5. execute_testcase - Run complete test cases
6. execute_testcase_by_id - MCP convenience: Load and run saved testcase
7. save_testcase - Save test case graphs to database
8. list_testcases - List all saved test cases
9. load_testcase - Load a saved test case by ID
10. execute_script - Execute Python scripts with CLI parameters
11. generate_test_graph - AI-powered test generation
12. capture_screenshot - Capture screenshots for vision analysis
13. get_transcript - Fetch audio transcripts
14. get_device_info - Get device capabilities and info
15. get_execution_status - Poll async execution status
16. view_logs - View systemd service logs
17. list_services - List available systemd services
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import tool classes
from .tools.control_tools import ControlTools
from .tools.action_tools import ActionTools
from .tools.navigation_tools import NavigationTools
from .tools.verification_tools import VerificationTools
from .tools.testcase_tools import TestCaseTools
from .tools.ai_tools import AITools
from .tools.screenshot_tools import ScreenshotTools
from .tools.transcript_tools import TranscriptTools
from .tools.device_tools import DeviceTools
from .tools.logs_tools import LogsTools
from .tools.script_tools import ScriptTools
from .tools.tree_tools import TreeTools

# Import utilities
from .utils.api_client import MCPAPIClient
from .utils.mcp_formatter import MCPFormatter, ErrorCategory
from .utils.input_validator import InputValidator


class VirtualPyTestMCPServer:
    """MCP Server for VirtualPyTest device automation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_client = MCPAPIClient()
        self.formatter = MCPFormatter()
        self.validator = InputValidator()
        
        # Tool schemas cache (for validation)
        self._tool_schemas = None
        
        # Initialize all tool handlers
        self.control_tools = ControlTools(self.api_client)
        self.action_tools = ActionTools(self.api_client)
        self.navigation_tools = NavigationTools(self.api_client)
        self.verification_tools = VerificationTools(self.api_client)
        self.testcase_tools = TestCaseTools(self.api_client)
        self.ai_tools = AITools(self.api_client)
        self.screenshot_tools = ScreenshotTools(self.api_client)
        self.transcript_tools = TranscriptTools(self.api_client)
        self.device_tools = DeviceTools(self.api_client)
        self.logs_tools = LogsTools(self.api_client)
        self.script_tools = ScriptTools(self.api_client)
        self.tree_tools = TreeTools(self.api_client)
        
        # Tool registry mapping
        self.tool_handlers = {
            # Control tools (only for navigation)
            'take_control': self.control_tools.take_control,
            
            # Action tools
            'list_actions': self.action_tools.list_actions,
            'execute_device_action': self.action_tools.execute_device_action,
            
            # Navigation tools
            'list_navigation_nodes': self.navigation_tools.list_navigation_nodes,
            'navigate_to_node': self.navigation_tools.navigate_to_node,
            
            # Verification tools
            'list_verifications': self.verification_tools.list_verifications,
            'verify_device_state': self.verification_tools.verify_device_state,
            'dump_ui_elements': self.verification_tools.dump_ui_elements,
            
            # TestCase tools
            'execute_testcase': self.testcase_tools.execute_testcase,
            'execute_testcase_by_id': self.testcase_tools.execute_testcase_by_id,
            'save_testcase': self.testcase_tools.save_testcase,
            'list_testcases': self.testcase_tools.list_testcases,
            'load_testcase': self.testcase_tools.load_testcase,
            
            # Script tools
            'execute_script': self.script_tools.execute_script,
            
            # AI tools
            'generate_test_graph': self.ai_tools.generate_test_graph,
            
            # Screenshot tools
            'capture_screenshot': self.screenshot_tools.capture_screenshot,
            
            # Transcript tools
            'get_transcript': self.transcript_tools.get_transcript,
            
            # Device info tools
            'get_device_info': self.device_tools.get_device_info,
            'get_execution_status': self.device_tools.get_execution_status,
            
            # Logs tools
            'view_logs': self.logs_tools.view_logs,
            'list_services': self.logs_tools.list_services,
            
            # Tree CRUD tools (NEW - Primitives)
            'create_node': self.tree_tools.create_node,
            'update_node': self.tree_tools.update_node,
            'delete_node': self.tree_tools.delete_node,
            'create_edge': self.tree_tools.create_edge,
            'update_edge': self.tree_tools.update_edge,
            'delete_edge': self.tree_tools.delete_edge,
            'create_subtree': self.tree_tools.create_subtree,
        }
        
        self.logger.info(f"VirtualPyTest MCP Server initialized with {len(self.tool_handlers)} tools")
    
    def handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP tool call (synchronous) with input validation
        
        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            
        Returns:
            MCP-formatted response
        """
        try:
            self.logger.info(f"Handling tool call: {tool_name}")
            self.logger.debug(f"Parameters: {params}")
            
            # Check if tool exists
            if tool_name not in self.tool_handlers:
                error_msg = f"Unknown tool: {tool_name}. Available tools: {list(self.tool_handlers.keys())}"
                return self.formatter.format_error(error_msg, ErrorCategory.NOT_FOUND)
            
            # Validate input parameters against tool schema
            tool_schema = self._get_tool_schema(tool_name)
            if tool_schema:
                is_valid, validation_error = self.validator.validate_arguments(
                    tool_name,
                    params,
                    tool_schema['inputSchema']
                )
                
                if not is_valid:
                    self.logger.warning(f"Validation failed for {tool_name}: {validation_error}")
                    return self.formatter.format_validation_error(tool_name, validation_error)
            
            # Execute tool (synchronous)
            handler = self.tool_handlers[tool_name]
            result = handler(params)
            
            self.logger.info(f"Tool {tool_name} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Tool call error for {tool_name}: {e}", exc_info=True)
            return self.formatter.format_error(
                f"Tool execution error: {str(e)}",
                ErrorCategory.BACKEND
            )
    
    def _get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool schema dict or None if not found
        """
        # Cache tool schemas on first access
        if self._tool_schemas is None:
            tools = self.get_available_tools()
            self._tool_schemas = {tool['name']: tool for tool in tools}
        
        return self._tool_schemas.get(tool_name)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available MCP tools in proper MCP format with JSON Schema
        
        Returns:
            List of MCP-formatted tool definitions
        """
        tools = [
            {
                "name": "take_control",
                "description": """🔒 ONLY FOR NAVIGATION: Take control of a device for UI tree navigation

⚠️ This is ONLY required if you plan to use navigate_to_node.
DO NOT call this for simple actions like execute_device_action.

This locks the device and builds navigation cache for the specified tree_id.

WORKFLOW (for navigation only):
1. Call take_control(device_id='device1', tree_id='<tree-id>') ONCE
2. Call navigate_to_node multiple times
3. Done - no need to release

For simple actions (swipe, click, type), just call execute_device_action directly.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "tree_id": {"type": "string", "description": "Navigation tree ID - REQUIRED for navigation"}
                    },
                    "required": []
                }
            },
            {
                "name": "list_actions",
                "description": """List available actions for a device

Returns categorized list of actions with commands and parameters.
Useful for discovering what actions can be executed on a device.

PREREQUISITE: Device must be registered with the host.

Device Model Specific:
- android_mobile/android_tv: Returns ADB/Remote commands (swipe_up, click_element, type_text, key, etc)
- web/desktop: Returns web automation commands (web_click, web_type, etc)

Example:
  list_actions(
    device_id='device1',
    host_name='sunri-pi1'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "host_name": {"type": "string", "description": "Host name where device is connected"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                    },
                    "required": ["host_name"]
                }
            },
            {
                "name": "execute_device_action",
                "description": """Execute batch of actions on device (remote commands, ADB, web, desktop)

✅ NO PREREQUISITES - Just call this directly for any device actions.

Executes commands like swipe, click, type, etc.
Returns execution_id for async operations - polls automatically until completion.

Device Model Specific:
- android_mobile/android_tv: Use ADB/Remote commands
  Examples: swipe_up, swipe_down, click_element, click_element_by_id, type_text, key
- web/desktop: Use web automation commands
  Examples: web_click, web_type, web_navigate

Examples:
- Swipe: execute_device_action(actions=[{"command": "swipe_up"}])
- Click: execute_device_action(actions=[{"command": "click_element", "params": {"text": "Home"}}])
- Type: execute_device_action(actions=[{"command": "type_text", "params": {"text": "Hello"}}])

If you're unsure about available commands, call list_actions() first.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "actions": {
                            "type": "array",
                            "description": "Array of action objects. Each action must have a 'command' field. Use list_actions() to discover available commands and their required parameters.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "Action command to execute (e.g., 'click_element', 'swipe', 'type_text'). Call list_actions() first to see all available commands."
                                    },
                                    "params": {
                                        "type": "object",
                                        "description": "Parameters for the command. Structure varies by command - use list_actions() to see required params."
                                    },
                                    "delay": {
                                        "type": "number",
                                        "description": "Optional delay in seconds after executing this action"
                                    }
                                },
                                "required": ["command"]
                            }
                        },
                        "retry_actions": {
                            "type": "array",
                            "description": "Actions to retry on failure",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string"},
                                    "params": {"type": "object"},
                                    "delay": {"type": "number"}
                                },
                                "required": ["command"]
                            }
                        },
                        "failure_actions": {
                            "type": "array",
                            "description": "Actions to execute on failure",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string"},
                                    "params": {"type": "object"},
                                    "delay": {"type": "number"}
                                },
                                "required": ["command"]
                            }
                        }
                    },
                    "required": ["actions"]
                }
            },
            {
                "name": "list_navigation_nodes",
                "description": """List navigation nodes available in a tree

Returns list of nodes with labels, IDs, types, and positions.
Useful for discovering what nodes are available for navigation.

Can accept EITHER tree_id OR userinterface_name (recommended).

Example:
  list_navigation_nodes(
    userinterface_name='horizon_android_mobile'
  )
  OR
  list_navigation_nodes(
    tree_id='abc-123'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID (optional - provide this OR userinterface_name)"},
                        "userinterface_name": {"type": "string", "description": "User interface name (optional - provide this OR tree_id). Recommended approach."},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "page": {"type": "integer", "description": "Page number (optional, default: 0)"},
                        "limit": {"type": "integer", "description": "Results per page (optional, default: 100)"}
                    },
                    "required": []
                }
            },
            {
                "name": "navigate_to_node",
                "description": """Navigate to target node in UI tree using pathfinding

⚠️ PREREQUISITE: take_control(tree_id='<tree>') must be called ONCE first with the SAME tree_id.

Can be called MULTIPLE times in the same session to navigate to different nodes.
All parameters (device_id, tree_id, userinterface_name) MUST match the take_control call.

The tool polls automatically until navigation completes (up to 3 minutes).

Example workflow:
1. take_control(device_id='device1', tree_id='abc-123')
2. navigate_to_node(device_id='device1', tree_id='abc-123', userinterface_name='horizon_android_tv', target_node_label='home')
3. navigate_to_node(device_id='device1', tree_id='abc-123', userinterface_name='horizon_android_tv', target_node_label='settings')
4. release_control(device_id='device1')""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID - MUST match the tree_id used in take_control"},
                        "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'horizon_android_tv', 'horizon_android_mobile')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "target_node_id": {"type": "string", "description": "Target node ID (provide either this or target_node_label)"},
                        "target_node_label": {"type": "string", "description": "Target node label (provide either this or target_node_id)"},
                        "current_node_id": {"type": "string", "description": "Current node ID (optional)"},
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"}
                    },
                    "required": ["tree_id", "userinterface_name"]
                }
            },
            {
                "name": "list_verifications",
                "description": """List available verification types for a device

Returns categorized list of verification methods with parameters.
Useful for discovering what verifications can be performed on a device.

PREREQUISITE: Device must be registered with the host.

Device Model Specific:
- android_mobile/android_tv: Returns ADB/Remote verifications (check_element_exists, check_text_on_screen, getMenuInfo, etc)
- web/desktop: Returns web verification methods

Example:
  list_verifications(
    device_id='device1',
    host_name='sunri-pi1'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "host_name": {"type": "string", "description": "Host name where device is connected"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                    },
                    "required": ["host_name"]
                }
            },
            {
                "name": "verify_device_state",
                "description": """Verify device state with batch verifications (image, text, video, ADB)

✅ NO PREREQUISITES - Just call this directly.

Can be called MULTIPLE times in the same session.

Device Model Specific:
- android_mobile/android_tv: Use ADB/Remote verification commands discovered via list_verifications()
  Must match command structure returned by list_verifications (type, method, params, expected)
- web/desktop: Use web verification methods

IMPORTANT: Call list_verifications() first to see exact command structure for the device model.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "userinterface_name": {"type": "string", "description": "User interface name"},
                        "verifications": {
                            "type": "array",
                            "description": "Array of verification objects with type, method, params, expected",
                            "items": {"type": "object"}
                        },
                        "tree_id": {"type": "string", "description": "Navigation tree ID (optional)"},
                        "node_id": {"type": "string", "description": "Node ID to verify (optional)"},
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"}
                    },
                    "required": ["userinterface_name", "verifications"]
                }
            },
            {
                "name": "execute_testcase",
                "description": """Execute a test case graph on device

Executes graph from generate_test_graph() or loaded testcase.
Polls automatically until completion (up to 5 minutes).""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1') - MUST match take_control"},
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "graph_json": {"type": "object", "description": "Test case graph from generate_test_graph()"},
                        "testcase_name": {"type": "string", "description": "Name for execution logs (optional)"},
                        "userinterface_name": {"type": "string", "description": "User interface name (optional)"}
                    },
                    "required": ["graph_json"]
                }
            },
            {
                "name": "execute_testcase_by_id",
                "description": """MCP CONVENIENCE: Load and execute a saved test case by ID

This combines load + execute for MCP convenience.
Use this when you want to run a saved testcase without manually passing graph_json.

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
                "name": "execute_script",
                "description": """Execute a Python script on device

PREREQUISITE: take_control() should be called first if script uses device controls.

Executes a Python script with optional CLI parameters.
Polls automatically until completion (up to 2 hours for long scripts).

Example:
  execute_script(
    script_name='my_validation.py',
    host_name='sunri-pi1',
    device_id='device1',
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
            },
            {
                "name": "generate_test_graph",
                "description": """Generate test case graph from natural language using AI

Takes a prompt like "Navigate to settings and verify WiFi is enabled"
Returns executable graph that can be:
1. Passed to execute_testcase() to run immediately
2. Passed to save_testcase() to save for later

Example workflow:
1. graph = generate_test_graph(prompt="Check home screen")
2. execute_testcase(graph_json=graph['graph'])
   OR
   save_testcase(testcase_name="Home Check", graph_json=graph['graph'])""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Natural language test description"},
                        "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'horizon_android_tv', 'horizon_android_mobile')"},
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "current_node_id": {"type": "string", "description": "Current node ID for context (optional)"}
                    },
                    "required": ["prompt", "userinterface_name"]
                }
            },
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
            },
            {
                "name": "get_transcript",
                "description": "Get audio transcript from device with optional translation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "chunk_url": {"type": "string", "description": "Chunk URL (provide this OR hour+chunk_index)"},
                        "hour": {"type": "integer", "description": "Hour number (use with chunk_index)"},
                        "chunk_index": {"type": "integer", "description": "Chunk index (use with hour)"},
                        "target_language": {"type": "string", "description": "Language code for translation (e.g., 'fr', 'es', 'de')"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_device_info",
                "description": "Get device information, capabilities, and controller status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Specific device ID, or omit for all devices"},
                        "host_name": {"type": "string", "description": "Host name to query (optional - defaults to 'sunri-pi1')"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_execution_status",
                "description": "Poll async execution status for actions, testcases, or AI operations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {"type": "string", "description": "Execution ID from async operation"},
                        "operation_type": {
                            "type": "string",
                            "description": "Operation type (action, testcase, ai)",
                            "enum": ["action", "testcase", "ai"]
                        }
                    },
                    "required": ["execution_id"]
                }
            },
            {
                "name": "view_logs",
                "description": "View systemd service logs via journalctl. Access backend_server, backend_host, or other service logs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Service name (e.g., 'backend_server', 'backend_host')"},
                        "lines": {"type": "integer", "description": "Number of lines to show"},
                        "since": {"type": "string", "description": "Show logs since time (e.g., '1 hour ago', '2024-01-01')"},
                        "level": {"type": "string", "description": "Log level filter (e.g., 'error', 'warning')"},
                        "grep": {"type": "string", "description": "Search pattern to filter logs"}
                    },
                    "required": ["service"]
                }
            },
            {
                "name": "list_services",
                "description": "List available VirtualPyTest systemd services and their status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # ═══════════════════════════════════════════════════
            # PRIMITIVE TOOLS - Tree CRUD & UI Inspection
            # ═══════════════════════════════════════════════════
            {
                "name": "create_node",
                "description": """Create a node in navigation tree

Atomic primitive for building navigation structures.
Can be composed for AI exploration, manual tree building, or tree refactoring.

Example:
  create_node(
    tree_id="main_tree",
    label="settings",
    type="screen",
    position={"x": 100, "y": 200}
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "label": {"type": "string", "description": "Node label/name"},
                        "node_id": {"type": "string", "description": "Node identifier (optional - auto-generated if omitted)"},
                        "type": {"type": "string", "description": "Node type (default: 'screen')"},
                        "position": {"type": "object", "description": "Position {x, y} coordinates (optional)"},
                        "data": {"type": "object", "description": "Custom metadata (optional)"}
                    },
                    "required": ["tree_id", "label"]
                }
            },
            {
                "name": "update_node",
                "description": """Update an existing node

Modify node properties like label, position, type, or custom data.

Example:
  update_node(
    tree_id="main_tree",
    node_id="settings",
    updates={"label": "settings_main", "position": {"x": 150, "y": 200}}
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "node_id": {"type": "string", "description": "Node identifier to update"},
                        "updates": {"type": "object", "description": "Fields to update (label, position, type, data)"}
                    },
                    "required": ["tree_id", "node_id", "updates"]
                }
            },
            {
                "name": "delete_node",
                "description": """Delete a node from navigation tree

Removes node and all connected edges.

Example:
  delete_node(
    tree_id="main_tree",
    node_id="old_node"
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "node_id": {"type": "string", "description": "Node identifier to delete"}
                    },
                    "required": ["tree_id", "node_id"]
                }
            },
            {
                "name": "create_edge",
                "description": """Create an edge between two nodes

Defines navigation path with forward and backward actions.

Example:
  create_edge(
    tree_id="main_tree",
    source_node_id="home",
    target_node_id="settings",
    action_sets=[
      {
        "id": "home_to_settings",
        "actions": [{"command": "click_element", "params": {"text": "Settings"}, "delay": 2000}]
      },
      {
        "id": "settings_to_home",
        "actions": [{"command": "press_key", "params": {"key": "BACK"}, "delay": 2000}]
      }
    ]
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "source_node_id": {"type": "string", "description": "Source node ID"},
                        "target_node_id": {"type": "string", "description": "Target node ID"},
                        "action_sets": {"type": "array", "description": "Array of action sets (forward/backward)"},
                        "edge_id": {"type": "string", "description": "Edge identifier (optional - auto-generated if omitted)"},
                        "label": {"type": "string", "description": "Edge label in format 'source→target' (optional - auto-generated from action_sets if omitted)"},
                        "final_wait_time": {"type": "number", "description": "Wait time after edge execution in ms - default: 2000"},
                        "sourceHandle": {"type": "string", "description": "Source handle ID (optional): bottom-source (default), top-left-menu-source, bottom-right-menu-source, left-source, right-source"},
                        "targetHandle": {"type": "string", "description": "Target handle ID (optional): top-target (default), top-right-menu-target, bottom-left-menu-target, left-target, right-target"},
                        "priority": {"type": "string", "description": "Edge priority: p1 (high), p2 (medium), p3 (low) - default: p3"},
                        "is_conditional": {"type": "boolean", "description": "Whether edge has conditions - default: false"},
                        "is_conditional_primary": {"type": "boolean", "description": "If conditional, is this primary path - default: false"}
                    },
                    "required": ["tree_id", "source_node_id", "target_node_id"]
                }
            },
            {
                "name": "update_edge",
                "description": """Update edge actions

Fix or modify navigation actions after testing.

Example:
  update_edge(
    tree_id="main_tree",
    edge_id="edge_home_settings",
    action_sets=[...new actions...]
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "edge_id": {"type": "string", "description": "Edge identifier to update"},
                        "action_sets": {"type": "array", "description": "New action sets (replaces existing)"}
                    },
                    "required": ["tree_id", "edge_id", "action_sets"]
                }
            },
            {
                "name": "delete_edge",
                "description": """Delete an edge from navigation tree

Example:
  delete_edge(
    tree_id="main_tree",
    edge_id="edge_old"
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "edge_id": {"type": "string", "description": "Edge identifier to delete"}
                    },
                    "required": ["tree_id", "edge_id"]
                }
            },
            {
                "name": "create_subtree",
                "description": """Create a subtree for a parent node

Required for recursive tree exploration - allows exploring deeper levels.

Example workflow:
  1. create_node(id="settings") in main tree
  2. create_subtree(parent_node_id="settings", subtree_name="settings_subtree")
     → Returns: {"subtree_tree_id": "subtree-123"}
  3. navigate_to_node(target="settings")
  4. create_node(tree_id="subtree-123", ...) in subtree
  5. Repeat for deeper levels

Example:
  create_subtree(
    parent_tree_id="main_tree",
    parent_node_id="settings",
    subtree_name="settings_subtree"
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "parent_tree_id": {"type": "string", "description": "Parent tree ID"},
                        "parent_node_id": {"type": "string", "description": "Parent node ID to attach subtree to"},
                        "subtree_name": {"type": "string", "description": "Name for the subtree (e.g., 'settings_subtree')"}
                    },
                    "required": ["parent_tree_id", "parent_node_id", "subtree_name"]
                }
            },
            {
                "name": "dump_ui_elements",
                "description": """Dump UI elements from current device screen

⚠️ **DEVICE MODEL COMPATIBILITY:**
- ✅ **android_mobile**: Use this tool (gets UI hierarchy via ADB)
- ✅ **web**: Use this tool (gets DOM elements)
- ❌ **android_tv / other**: Use capture_screenshot + AI vision instead (no UI dump support)

**How to choose:**
1. Call get_device_info() first to check device_model
2. If device_model is "android_mobile" or "web" → use dump_ui_elements()
3. If device_model is "android_tv" or other → use capture_screenshot() + AI vision

CRITICAL for debugging failed navigation or verification.
Returns all UI elements with text, resource-id, clickable status, bounds.

Use cases:
- Debug failed edge: "Element not found" → dump to see actual element names
- Verify screen: Check if expected elements are present
- Discover navigation targets: See what's clickable on current screen
- AI exploration: Identify clickable elements to create nodes/edges

Example:
  # Step 1: Check device model
  device_info = get_device_info(device_id="device1")
  device_model = device_info['device_model']  # e.g., "android_mobile"
  
  # Step 2: Choose inspection method
  if device_model in ["android_mobile", "web"]:
      elements = dump_ui_elements(device_id="device1", platform="mobile")
      # Returns: [{"text": "Settings Tab", "clickable": true, "resource-id": "tab_settings"}, ...]
  else:
      screenshot = capture_screenshot(device_id="device1")
      # Use AI vision to analyze screenshot
  
  # LLM analyzes: "Ah! It's 'Settings Tab', not 'Settings'"
  # Fix edge with correct element name
  update_edge(edge_id="...", actions=[...click "Settings Tab"...])""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "host_name": {"type": "string", "description": "Host name (optional - defaults to 'sunri-pi1')"},
                        "platform": {"type": "string", "description": "Platform type (optional: 'mobile', 'web', 'tv')"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": []
                }
            }
        ]
        
        return tools


async def main():
    """Main MCP server entry point"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting VirtualPyTest MCP Server")
    
    # Initialize server
    server = VirtualPyTestMCPServer()
    
    # Print available tools
    tools = server.get_available_tools()
    logger.info(f"Available tools ({len(tools)}):")
    for tool in tools:
        logger.info(f"  - {tool['name']}: {tool['description']}")
    
    # Keep server running
    try:
        logger.info("MCP Server ready and listening...")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server")


if __name__ == "__main__":
    asyncio.run(main())

