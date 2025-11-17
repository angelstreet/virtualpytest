#!/usr/bin/env python3
"""
MCP Server for VirtualPyTest

Model Context Protocol server that exposes VirtualPyTest device control
functionality to external LLMs (Claude, ChatGPT, etc.)

This server provides 52 core tools for device automation:
1. take_control - Lock device and generate navigation cache (ONLY for navigation)
2. list_actions - List available device actions
3. execute_device_action - Execute remote/ADB/web/desktop commands
4. list_navigation_nodes - List nodes in tree
5. navigate_to_node - Navigate through UI trees
6. preview_userinterface - Get compact text preview of navigation tree (NEW - "What do we test?")
7. list_verifications - List verification methods
8. verify_device_state - Verify UI elements and device states
9. dump_ui_elements - Dump UI hierarchy
10. execute_testcase - Run complete test cases
11. execute_testcase_by_id - MCP convenience: Load and run saved testcase
12. save_testcase - Save test case graphs to database
13. list_testcases - List all saved test cases
14. load_testcase - Load a saved test case by ID
15. rename_testcase - Rename an existing test case (NEW)
16. list_scripts - List all available Python scripts
17. execute_script - Execute Python scripts with CLI parameters
18. generate_test_graph - AI-powered test generation
19. capture_screenshot - Capture screenshots for vision analysis
20. get_transcript - Fetch audio transcripts
21. get_device_info - Get device capabilities and info
22. get_execution_status - Poll async execution status
23. view_logs - View systemd service logs
24. list_services - List available systemd services
25. create_node - Create navigation tree nodes
26. update_node - Update node properties
27. delete_node - Delete nodes from trees
28. create_edge - Create edges with actions
29. update_edge - Update edge actions
30. delete_edge - Delete edges
31. create_subtree - Create nested subtrees
32. get_node - Get node details
33. get_edge - Get edge details
34. execute_edge - Execute edge actions directly
35. save_node_screenshot - Save screenshot to node (NEW - wraps takeAndSaveScreenshot)
36. create_userinterface - Create new app models
37. list_userinterfaces - List all app models
38. get_userinterface_complete - Get complete tree data
39. list_nodes - List nodes with verifications
40. list_edges - List edges with actions
41. delete_userinterface - Delete userinterface models
42. verify_node - Verify node verifications directly
43. create_requirement - Create new requirement
44. list_requirements - List all requirements  
45. get_requirement - Get requirement by ID
46. update_requirement - Update requirement (NEW - app_type, device_model for reusability)
47. link_testcase_to_requirement - Link testcase for coverage
48. unlink_testcase_from_requirement - Unlink testcase
49. get_testcase_requirements - Get testcase requirements
50. get_requirement_coverage - Get requirement coverage details
51. get_coverage_summary - Get overall coverage metrics
52. get_uncovered_requirements - Get requirements without coverage
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
from .tools.userinterface_tools import UserInterfaceTools
from .tools.requirements_tools import RequirementsTools

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
        self.userinterface_tools = UserInterfaceTools(self.api_client)
        self.requirements_tools = RequirementsTools(self.api_client)
        
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
            'preview_userinterface': self.navigation_tools.preview_userinterface,
            
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
            'rename_testcase': self.testcase_tools.rename_testcase,
            
            # Script tools
            'list_scripts': self.script_tools.list_scripts,
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
            
            # Tree READ tools (NEW - Query primitives)
            'get_node': self.tree_tools.get_node,
            'get_edge': self.tree_tools.get_edge,
            'execute_edge': self.tree_tools.execute_edge,  # NEW - Execute edge actions
            'save_node_screenshot': self.tree_tools.save_node_screenshot,  # NEW - Save screenshot to node
            
            # UserInterface Management tools (NEW)
            'create_userinterface': self.userinterface_tools.create_userinterface,
            'list_userinterfaces': self.userinterface_tools.list_userinterfaces,
            'get_userinterface_complete': self.userinterface_tools.get_userinterface_complete,
            'list_nodes': self.userinterface_tools.list_nodes,
            'list_edges': self.userinterface_tools.list_edges,
            'delete_userinterface': self.userinterface_tools.delete_userinterface,
            
            # Verification tools (NEW - Node verification)
            'verify_node': self.verification_tools.verify_node,  # NEW - Verify node
            
            # Requirements Management tools (NEW)
            'create_requirement': self.requirements_tools.create_requirement,
            'list_requirements': self.requirements_tools.list_requirements,
            'get_requirement': self.requirements_tools.get_requirement,
            'update_requirement': self.requirements_tools.update_requirement,
            'link_testcase_to_requirement': self.requirements_tools.link_testcase_to_requirement,
            'unlink_testcase_from_requirement': self.requirements_tools.unlink_testcase_from_requirement,
            'get_testcase_requirements': self.requirements_tools.get_testcase_requirements,
            'get_requirement_coverage': self.requirements_tools.get_requirement_coverage,
            'get_coverage_summary': self.requirements_tools.get_coverage_summary,
            'get_uncovered_requirements': self.requirements_tools.get_uncovered_requirements,
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
            
        Raises:
            ValueError: If tool returns an error (isError: True)
        """
        try:
            self.logger.info(f"Handling tool call: {tool_name}")
            self.logger.debug(f"Parameters: {params}")
            
            # Check if tool exists
            if tool_name not in self.tool_handlers:
                error_msg = f"Unknown tool: {tool_name}. Available tools: {list(self.tool_handlers.keys())}"
                error_response = self.formatter.format_error(error_msg, ErrorCategory.NOT_FOUND)
                raise ValueError(error_response['content'][0]['text'])
            
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
                    error_response = self.formatter.format_validation_error(tool_name, validation_error)
                    raise ValueError(error_response['content'][0]['text'])
            
            # Execute tool (synchronous)
            handler = self.tool_handlers[tool_name]
            result = handler(params)
            
            # Check if result indicates an error
            if result.get('isError', False):
                error_text = result['content'][0]['text']
                self.logger.error(f"Tool {tool_name} returned error: {error_text}")
                raise ValueError(error_text)
            
            self.logger.info(f"Tool {tool_name} completed successfully")
            return result
            
        except ValueError:
            # Re-raise ValueError as-is (these are our formatted errors)
            raise
        except Exception as e:
            self.logger.error(f"Tool call error for {tool_name}: {e}", exc_info=True)
            error_response = self.formatter.format_error(
                f"Tool execution error: {str(e)}",
                ErrorCategory.BACKEND
            )
            raise ValueError(error_response['content'][0]['text'])
    
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

Executes direct device commands including:
- Launch apps (launch_app)
- UI interactions (swipe, click, type)
- Key presses (press_key)
- And more...

Returns execution_id for async operations - polls automatically until completion.

ELEMENT SELECTION (selector MUST be unique on page):

1. #id (always unique)
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower)

Use dump_ui_elements() to verify selector appears only once on page.

⏱️ CRITICAL - ACTION WAIT TIMES:
Each action MUST include a 'wait_time' field (milliseconds) INSIDE params to wait AFTER execution.

✅ CORRECT: {"command": "launch_app", "params": {"package": "...", "wait_time": 8000}}
❌ WRONG: {"command": "launch_app", "params": {"package": "..."}, "delay": 8000}

Standard Wait Times (milliseconds) - INSIDE params:
- launch_app:     8000  (app initialization)
- click_element:  2000  (screen transition)
- tap_coordinates: 2000  (screen taps)
- press_key (BACK): 1500  (back navigation)
- press_key (other): 1000  (key response)
- type_text:      1000  (input processing)
- video playback: 5000  (player initialization)

Device Model Specific:
- android_mobile/android_tv: Use ADB/Remote commands
  Examples: launch_app, swipe_up, swipe_down, click_element_by_id (⭐ PREFERRED), click_element, type_text, press_key
- web/desktop: Use web automation commands
  Examples: web_click, web_type, web_navigate

Common Examples:

🚀 Launch App:
  execute_device_action({
    "device_id": "device1",
    "actions": [{
      "command": "launch_app",
      "params": {"package": "com.netflix.mediaclient", "wait_time": 8000}
    }]
  })

📱 Swipe:
  execute_device_action({
    "actions": [{"command": "swipe_up", "params": {"wait_time": 1000}}]
  })

👆 Click Element (⭐ PREFERRED - Use ID):
  execute_device_action({
    "actions": [{
      "command": "click_element_by_id",
      "params": {"element_id": "customer_login_link", "wait_time": 2000}
    }]
  })

👆 Click Element (fallback - text when no ID available):
  execute_device_action({
    "actions": [{
      "command": "click_element",
      "params": {"text": "Home", "wait_time": 2000}
    }]
  })

⌨️ Type Text:
  execute_device_action({
    "actions": [{
      "command": "type_text",
      "params": {"text": "Hello", "wait_time": 1000}
    }]
  })

🔑 Press Key:
  execute_device_action({
    "actions": [{
      "command": "press_key",
      "params": {"key": "BACK", "wait_time": 1500}
    }]
  })

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
                                        "description": "Action command to execute (e.g., 'launch_app', 'click_element', 'swipe', 'type_text', 'press_key'). Call list_actions() first to see all available commands."
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
                "name": "preview_userinterface",
                "description": """Get compact text preview of userinterface navigation tree

Shows all nodes, edges, actions, and verifications in 8-10 lines.
Perfect for answering "What do we test and how?"

✅ NO PREREQUISITES - Just call with userinterface_name

Output format:
  netflix_mobile (7 nodes, 13 transitions)
  
  Entry→home: launch_app + tap(540,1645) [✓ Startseite]
  home⟷search: click(Suchen) ⟷ click(Nach oben navigieren) [✓ Suchen]
  home⟷content_detail: click(The Witcher) ⟷ BACK [✓ abspielen]
  ...

Use cases:
- Quick overview of test coverage
- Share navigation structure with stakeholders
- Understand what actions are tested
- Verify navigation completeness

Example:
  preview_userinterface(userinterface_name='netflix_mobile')""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'netflix_mobile', 'horizon_android_tv')"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default if omitted)"}
                    },
                    "required": ["userinterface_name"]
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
  Must use CORRECT field names: 'command' (not 'method') and 'verification_type' (not 'type')
- web/desktop: Use web verification methods

IMPORTANT: Call list_verifications() first to see exact command structure for the device model.

**CRITICAL - VERIFICATION FORMAT:**
Each verification object MUST use:
- 'command': The verification method name (e.g., 'waitForElementToAppear')
- 'verification_type': The category (e.g., 'adb', 'image', 'text', 'video')
- 'params': Method-specific parameters (e.g., 'search_term' for waitForElementToAppear)
- 'expected': Expected result (optional)

Example:
```json
{
  "command": "waitForElementToAppear",
  "verification_type": "adb",
  "params": {"search_term": "Home", "timeout": 5000}
}
```

**CRITICAL - PARAMETER NAMES:**
For waitForElementToAppear, use 'search_term' (NOT 'text'):
- CORRECT: {"search_term": "Home", "timeout": 10}
- WRONG: {"text": "Home", "timeout": 10}

search_term selector priority (MUST be unique on page):
1. #id (always unique)
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower)

Use 2-3 verifications per node if required for uniqueness
""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "userinterface_name": {"type": "string", "description": "User interface name"},
                        "verifications": {
                            "type": "array",
                            "description": "Array of verification objects. Each object MUST use 'command' (not 'method') and 'verification_type' (not 'type') to match frontend expectations.",
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
            },
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

⚠️ CRITICAL - NAVIGATION IS AUTONOMOUS:
The navigation tree (from Phase 1) already defines HOW to move between screens.
Test cases should use 'navigation' nodes that reference tree nodes by label.

**Architecture:**
- Navigation Tree = HOW to navigate (app-specific, built once)
- Test Case = WHAT to test (reusable across apps)

**Correct Usage:**
```json
{
  "type": "navigation",
  "data": {
    "target_node_id": "fb860f60-1f04-4b45-a952-5debf48f20c5",
    "target_node_label": "player"
  }
}
```
This automatically uses the pre-built navigation tree to go home→content_detail→player.

**REQUIRED FIELDS for Navigation Nodes:**
- `target_node_id`: UUID from navigation tree (REQUIRED)
- `target_node_label`: Human-readable label like "home", "player" (REQUIRED)

**DO NOT** create manual action sequences for navigation:
```json
❌ {"type": "action", "data": {"command": "click_element", "text": "Play"}}
```

**When to Use Actions:**
- Use 'action' nodes ONLY for non-navigation actions (pause, volume, text input)
- Use 'navigation' nodes to move between screens in the tree
- Use 'verification' nodes to check screen state

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

⚠️ IMPORTANT - NODE ID USAGE:
The tool returns the PERMANENT database UUID immediately. Use this ID for creating edges.
- create_node() → Returns permanent UUID (e.g., "60f8c86e-d0ec-4dd9-bbf5-88f7f74e016e")
- Use this UUID directly in create_edge(source_node_id=..., target_node_id=...)
- NO need to call list_navigation_nodes() to get IDs

Workflow for building navigation trees:
  # Step 1: Create nodes
  result1 = create_node(tree_id="main", label="home")
  # Returns: ✅ Node created: home (ID: abc-123-uuid)
  home_id = "abc-123-uuid"  # Extract from response
  
  result2 = create_node(tree_id="main", label="settings")
  # Returns: ✅ Node created: settings (ID: def-456-uuid)
  settings_id = "def-456-uuid"  # Extract from response
  
  # Step 2: Create edges with the returned permanent IDs
  create_edge(
    tree_id="main",
    source_node_id=home_id,      # ✅ Use permanent UUID from step 1
    target_node_id=settings_id,   # ✅ Use permanent UUID from step 1
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
  )

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

ELEMENT SELECTION (selector MUST be unique on page):

1. #id (always unique)
2. //xpath (e.g., //button[@name='login'])
3. [attr] or .class (verify uniqueness first)
4. plain text (fallback, slower)

Use dump_ui_elements() to verify selector appears only once on page.

⚠️ CRITICAL - NODE IDs MUST BE STRINGS (e.g., 'home'), NOT UUIDs!
- Use the 'node_id' field from list_navigation_nodes() or create_node() response.
- Examples: source_node_id='home' ✅ | source_node_id='ce97c317-...' ❌ (this is a database UUID and will error).
- If creating new nodes: create_node returns "node_id: 'home'" – use that string value.
- Validation will reject UUIDs with an error message.

⚠️ HANDLES - FIXED TO MENU HANDLES ONLY:
- sourceHandle: ALWAYS "bottom-right-menu-source" (auto-applied)
- targetHandle: ALWAYS "top-right-menu-target" (auto-applied)
- These create vertical connections between nodes.

Best Practice Workflow (From Scratch):
1. Inspect UI to find element IDs:
   dump_ui_elements() # Returns: {"element_id": "customer_login_link", "text": "Log In", ...}

2. (Optional) List existing nodes to get string node_ids:
   list_navigation_nodes(userinterface_name='your_ui')  # Returns: • home (node_id: 'home', ...) → Use 'home'

3. Create nodes if needed (returns string node_id):
   result1 = create_node(tree_id='your_tree_id', label='home')  # Returns: ✅ Node created: home (node_id: 'home')
   home_id = 'home'  # Extract the string 'home'

   result2 = create_node(tree_id='your_tree_id', label='login')  # Returns: ✅ Node created: login (node_id: 'login')
   login_id = 'login'  # Extract the string 'login'

4. Create the edge - FORMAT DEPENDS ON DEVICE TYPE:

   📱 MOBILE/ADB (Android) - ⭐ USE ELEMENT IDs:
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='login',
     source_label='home',
     target_label='login',
     action_sets=[
       {"id": "home_to_login", "label": "home → login",
        "actions": [{"command": "click_element_by_id", "params": {"element_id": "customer_login_link"}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "login_to_home", "label": "login → home",
        "actions": [{"command": "press_key", "params": {"key": "BACK"}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   🌐 WEB (Playwright) - ⭐ USE ELEMENT IDs or SELECTORS:
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='admin',
     source_label='home',
     target_label='admin',
     action_sets=[
       {"id": "home_to_admin", "label": "home → admin",
        "actions": [{"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "admin_nav_link", "wait_time": 1000}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "admin_to_home", "label": "admin → home",
        "actions": [{"command": "click_element_by_id", "action_type": "web", "params": {"element_id": "home_nav_link", "wait_time": 1000}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   🔴 REMOTE/IR (STB/TV):
   create_edge(
     tree_id='your_tree_id',
     source_node_id='home',
     target_node_id='settings',
     source_label='home',
     target_label='settings',
     action_sets=[
       {"id": "home_to_settings", "label": "home → settings",
        "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "RIGHT", "wait_time": 1500}}],
        "retry_actions": [], "failure_actions": []},
       {"id": "settings_to_home", "label": "settings → home",
        "actions": [{"command": "press_key", "action_type": "remote", "params": {"key": "LEFT", "wait_time": 1500}}],
        "retry_actions": [], "failure_actions": []}
     ]
   )

   ⚠️ KEY DIFFERENCES:
   - Mobile: NO action_type, NO wait_time, use element_id
   - Web: MUST have action_type="web", wait_time in params, use element_id
   - Remote: MUST have action_type="remote", wait_time in params, use key
   - All need: id, label, actions, retry_actions, failure_actions

4. Test the edge:
   take_control(tree_id='your_tree_id')  # Once per session
   navigate_to_node(tree_id='your_tree_id', target_node_id='settings')  # Uses the new edge

Tips:
- action_sets: Must include id, label, actions, retry_actions, failure_actions for each set
- Bidirectional nav: Provide 2 action_sets (forward + backward) for best results
- Device-specific format: Follow the examples above for your device type (Mobile/Web/Remote)
- If error: "must be the node_id string... not database UUID" – switch to string IDs from list_navigation_nodes
- For existing nodes: Always use list_navigation_nodes to get the correct string node_id
- Subtrees: Create via create_subtree, then use the new tree_id for edges within it.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "source_node_id": {"type": "string", "description": "Source node ID (string like 'home' from list_navigation_nodes or create_node – NOT a UUID!)"},
                        "target_node_id": {"type": "string", "description": "Target node ID (string like 'settings' from list_navigation_nodes or create_node – NOT a UUID!)"},
                        "source_label": {"type": "string", "description": "Source node label (REQUIRED - matches the label used in create_node)"},
                        "target_label": {"type": "string", "description": "Target node label (REQUIRED - matches the label used in create_node)"},
                        "action_sets": {"type": "array", "description": "Array of action sets with bidirectional navigation. Each action_set requires: id, label, actions[], retry_actions[], failure_actions[]. Format differs by device type: Mobile uses element_id (NO action_type/wait_time), Web uses element_id + action_type='web' + wait_time in params, Remote uses key + action_type='remote' + wait_time in params. See examples in description above."},
                        "edge_id": {"type": "string", "description": "Edge identifier (optional - auto-generated if omitted)"},
                        "label": {"type": "string", "description": "Edge label in format 'source→target' (optional - auto-generated from action_sets if omitted)"},
                        "final_wait_time": {"type": "number", "description": "Wait time after edge execution in ms - default: 2000"},
                        "priority": {"type": "string", "description": "Edge priority: p1 (high), p2 (medium), p3 (low) - default: p3"},
                        "is_conditional": {"type": "boolean", "description": "Whether edge has conditions - default: false"},
                        "is_conditional_primary": {"type": "boolean", "description": "If conditional, is this primary path - default: false"}
                    },
                    "required": ["tree_id", "source_node_id", "target_node_id", "source_label", "target_label"]
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
                "name": "get_node",
                "description": """Get a specific node by ID

Returns full node details including position, data, and verifications.
Use this to inspect node structure before updating or to verify node creation.

Example:
  get_node(
    tree_id="main_tree",
    node_id="settings"
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "node_id": {"type": "string", "description": "Node identifier"}
                    },
                    "required": ["tree_id", "node_id"]
                }
            },
            {
                "name": "get_edge",
                "description": """Get a specific edge by ID

Returns full edge details including action_sets, handles, and metadata.
Use this to inspect edge structure before updating or to verify edge creation.

Example:
  get_edge(
    tree_id="main_tree",
    edge_id="edge_home_settings"
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "edge_id": {"type": "string", "description": "Edge identifier"}
                    },
                    "required": ["tree_id", "edge_id"]
                }
            },
            {
                "name": "execute_edge",
                "description": """Execute a specific edge's action set (frontend: useEdge.ts executeActionSet)

This executes the actions in an edge's action set, useful for:
- Testing individual edges without full navigation
- Debugging edge actions
- Manual edge execution from UI

Args:
    edge_id: Edge identifier (REQUIRED)
    tree_id: Navigation tree ID (REQUIRED)
    action_set_id: Specific action set to execute (optional - uses default if omitted)
    device_id: Device identifier (optional - defaults to 'device1')
    host_name: Host name (optional - defaults to 'sunri-pi1')
    team_id: Team ID (optional - defaults to default)

Returns:
    Action execution results with success/failure status

Example:
    execute_edge({
        "edge_id": "edge-entry-node-to-home",
        "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
        "action_set_id": "actionset-1762771271791"  # optional
    })""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "edge_id": {"type": "string", "description": "Edge identifier"},
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "action_set_id": {"type": "string", "description": "Specific action set to execute (optional - uses default if omitted)"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "host_name": {"type": "string", "description": "Host name (optional - defaults to 'sunri-pi1')"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["tree_id", "edge_id"]
                }
            },
            {
                "name": "save_node_screenshot",
                "description": """Take screenshot and save it to a specific node (frontend: useNode.ts takeAndSaveScreenshot)

This wraps the screenshot capture and node update into a single operation:
1. Takes screenshot from device
2. Saves it to userinterface-specific path
3. Updates node with screenshot URL

Frontend equivalent: useNode.ts line 99-160

Use this after navigating to a node to automatically capture and attach screenshot.

Args:
    tree_id: Navigation tree ID (REQUIRED)
    node_id: Node identifier to attach screenshot to (REQUIRED)
    label: Node label used as filename (REQUIRED)
    host_name: Host where device is connected (REQUIRED)
    device_id: Device identifier (REQUIRED)
    userinterface_name: User interface name for organizing screenshots (REQUIRED)
    team_id: Team ID (optional - defaults to default)

Returns:
    {
        "success": true,
        "screenshot_url": "/screenshots/netflix_mobile/home_screen.png",
        "node_id": "home"
    }

Example:
    save_node_screenshot({
        "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
        "node_id": "home",
        "label": "Home Screen",
        "host_name": "sunri-pi1",
        "device_id": "device1",
        "userinterface_name": "netflix_mobile"
    })""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "node_id": {"type": "string", "description": "Node identifier to attach screenshot to"},
                        "label": {"type": "string", "description": "Node label used as filename"},
                        "host_name": {"type": "string", "description": "Host where device is connected"},
                        "device_id": {"type": "string", "description": "Device identifier"},
                        "userinterface_name": {"type": "string", "description": "User interface name for organizing screenshots"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["tree_id", "node_id", "label", "host_name", "device_id", "userinterface_name"]
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
            },
            # ═══════════════════════════════════════════════════
            # USERINTERFACE MANAGEMENT TOOLS
            # ═══════════════════════════════════════════════════
            {
                "name": "create_userinterface",
                "description": """Create a new userinterface (app model) like Netflix, YouTube, etc.

Automatically creates:
- Userinterface metadata
- Root navigation tree
- Entry node

Example:
  create_userinterface(
    name="netflix_android",
    device_model="android_mobile",
    description="Netflix Android TV app"
  )

Returns: userinterface_id and root tree_id""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Interface name (e.g., 'netflix_android', 'youtube_tv')"},
                        "device_model": {"type": "string", "description": "Device model: 'android_mobile', 'android_tv', 'web', 'host_vnc'"},
                        "description": {"type": "string", "description": "Optional description"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["name", "device_model"]
                }
            },
            {
                "name": "list_userinterfaces",
                "description": """List all userinterfaces (app models) for the team

Shows which apps have navigation trees ready.

Example:
  list_userinterfaces()

Returns: List of all interfaces with root tree info""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "force_refresh": {"type": "boolean", "description": "Force cache refresh (optional - default false)"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_userinterface_complete",
                "description": """Get COMPLETE userinterface with ALL nodes, edges, subtrees, and metrics

This is the RECOMMENDED way to get full tree data in ONE call.
Returns everything from root tree + all nested subtrees.

Example:
  complete_tree = get_userinterface_complete(
    userinterface_id="abc-123-def"
  )
  # Returns: {nodes: [...], edges: [...], metrics: {...}}

Replaces multiple calls:
  ❌ OLD: get_userinterface() → list_nodes() → list_edges() = 3 calls
  ✅ NEW: get_userinterface_complete() = 1 call""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "userinterface_id": {"type": "string", "description": "User interface UUID (from list_userinterfaces or create_userinterface)"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "include_metrics": {"type": "boolean", "description": "Include metrics data (optional - default true)"}
                    },
                    "required": ["userinterface_id"]
                }
            },
            {
                "name": "list_nodes",
                "description": """List all nodes in a navigation tree

Useful for checking what nodes exist after create/delete operations.

Example:
  list_nodes(tree_id="tree-abc-123")

Returns: List of nodes with verifications count""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "page": {"type": "integer", "description": "Page number (optional - default 0)"},
                        "limit": {"type": "integer", "description": "Results per page (optional - default 100)"}
                    },
                    "required": ["tree_id"]
                }
            },
            {
                "name": "list_edges",
                "description": """List all edges in a navigation tree

Useful for checking what navigation paths exist after create/delete operations.

Example:
  list_edges(tree_id="tree-abc-123")

Returns: List of edges with action sets""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "node_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional list of node IDs to filter edges"}
                    },
                    "required": ["tree_id"]
                }
            },
            {
                "name": "delete_userinterface",
                "description": """Delete a userinterface (soft delete)

⚠️ DESTRUCTIVE OPERATION - Requires explicit confirmation

Removes a user interface model from the system.
This operation is destructive and requires explicit confirmation.

Args:
    userinterface_id: User interface UUID to delete
    confirm: REQUIRED - Must be true to proceed (safety check)
    team_id: Team ID (optional - uses default)

Example:
  # Step 1: Attempt to delete (will ask for confirmation)
  delete_userinterface(
    userinterface_id="abc-123-def-456"
  )
  # Returns: ⚠️ DESTRUCTIVE OPERATION - Confirmation Required
  
  # Step 2: Confirm and delete
  delete_userinterface(
    userinterface_id="abc-123-def-456",
    confirm=true
  )
  # Returns: ✅ Userinterface deleted

Returns: Success confirmation or confirmation request""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "userinterface_id": {"type": "string", "description": "User interface UUID to delete"},
                        "confirm": {"type": "boolean", "description": "REQUIRED - Must be true to proceed (safety check)"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["userinterface_id"]
                }
            },
            {
                "name": "verify_node",
                "description": """Execute verifications for a specific node (frontend: useNode.ts line 403-411)

This runs the embedded verifications in a node, useful for:
- Testing node verifications without navigation
- Debugging verification logic
- Manual verification execution from UI

Args:
    node_id: Node identifier (REQUIRED)
    tree_id: Navigation tree ID (REQUIRED)
    device_id: Device identifier (optional - defaults to 'device1')
    host_name: Host name (optional - defaults to 'sunri-pi1')
    userinterface_name: User interface name (REQUIRED)
    team_id: Team ID (optional - defaults to default)

Returns:
    Verification results with pass/fail status

Example:
    verify_node({
        "node_id": "home",
        "tree_id": "ae9147a0-07eb-44d9-be71-aeffa3549ee0",
        "userinterface_name": "netflix_mobile"
    })""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "Node identifier"},
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "userinterface_name": {"type": "string", "description": "User interface name"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device1')"},
                        "host_name": {"type": "string", "description": "Host name (optional - defaults to 'sunri-pi1')"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["node_id", "tree_id", "userinterface_name"]
                }
            },
            # ═══════════════════════════════════════════════════
            # REQUIREMENTS MANAGEMENT TOOLS
            # ═══════════════════════════════════════════════════
            {
                "name": "create_requirement",
                "description": """Create a new requirement for requirements management
                
Creates a requirement with code, title, description, priority, and category.
Used for tracking test coverage and linking testcases to requirements.

Example:
  create_requirement(
    requirement_code='REQ_PLAYBACK_001',
    requirement_name='User can play video content',
    description='Users must be able to select and play video content from the catalog',
    priority='P1',
    category='playback'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_code": {"type": "string", "description": "Requirement code (e.g., 'REQ_PLAYBACK_001')"},
                        "requirement_name": {"type": "string", "description": "Requirement title"},
                        "description": {"type": "string", "description": "Detailed description (optional)"},
                        "priority": {"type": "string", "description": "Priority: P1, P2, P3 (optional - default: P2)"},
                        "category": {"type": "string", "description": "Category (e.g., 'playback', 'navigation', 'search')"},
                        "acceptance_criteria": {"type": "string", "description": "Acceptance criteria (optional)"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["requirement_code", "requirement_name"]
                }
            },
            {
                "name": "list_requirements",
                "description": """List all requirements with optional filters

Returns list of requirements with optional filtering by category, priority, or status.

Example:
  list_requirements(
    category='playback',
    priority='P1'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "category": {"type": "string", "description": "Filter by category (optional)"},
                        "priority": {"type": "string", "description": "Filter by priority: P1, P2, P3 (optional)"},
                        "status": {"type": "string", "description": "Filter by status (optional - default: 'active')"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_requirement",
                "description": """Get requirement details by ID

Returns full details for a specific requirement.

Example:
  get_requirement(
    requirement_id='abc-123-def'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_id": {"type": "string", "description": "Requirement ID"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["requirement_id"]
                }
            },
            {
                "name": "update_requirement",
                "description": """Update an existing requirement

Modify requirement fields including app_type and device_model for reusability.

Example:
  update_requirement(
    requirement_id='abc-123-def',
    app_type='streaming',
    device_model='all',
    description='Updated description'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_id": {"type": "string", "description": "Requirement ID (REQUIRED)"},
                        "requirement_name": {"type": "string", "description": "Requirement name (optional)"},
                        "requirement_code": {"type": "string", "description": "Requirement code (optional)"},
                        "description": {"type": "string", "description": "Description (optional)"},
                        "priority": {"type": "string", "description": "Priority: P1, P2, P3 (optional)"},
                        "category": {"type": "string", "description": "Category (optional)"},
                        "app_type": {"type": "string", "description": "App type: 'streaming', 'social', 'all' (optional)"},
                        "device_model": {"type": "string", "description": "Device model: 'android_mobile', 'android_tv', 'web', 'all' (optional)"},
                        "status": {"type": "string", "description": "Status: 'active', 'deprecated' (optional)"},
                        "acceptance_criteria": {"type": "string", "description": "Acceptance criteria (optional)"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["requirement_id"]
                }
            },
            {
                "name": "link_testcase_to_requirement",
                "description": """Link testcase to requirement for coverage tracking

Creates a link between a testcase and requirement to track test coverage.

Example:
  link_testcase_to_requirement(
    testcase_id='tc-abc-123',
    requirement_id='req-def-456',
    coverage_type='full'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "testcase_id": {"type": "string", "description": "Testcase ID"},
                        "requirement_id": {"type": "string", "description": "Requirement ID"},
                        "coverage_type": {"type": "string", "description": "Coverage type: 'full' or 'partial' (optional - default: 'full')"},
                        "coverage_notes": {"type": "string", "description": "Coverage notes (optional)"}
                    },
                    "required": ["testcase_id", "requirement_id"]
                }
            },
            {
                "name": "unlink_testcase_from_requirement",
                "description": """Unlink testcase from requirement

Removes the link between a testcase and requirement.

Example:
  unlink_testcase_from_requirement(
    testcase_id='tc-abc-123',
    requirement_id='req-def-456'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "testcase_id": {"type": "string", "description": "Testcase ID"},
                        "requirement_id": {"type": "string", "description": "Requirement ID"}
                    },
                    "required": ["testcase_id", "requirement_id"]
                }
            },
            {
                "name": "get_testcase_requirements",
                "description": """Get all requirements linked to a testcase

Returns list of requirements that are covered by a specific testcase.

Example:
  get_testcase_requirements(
    testcase_id='tc-abc-123'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "testcase_id": {"type": "string", "description": "Testcase ID"}
                    },
                    "required": ["testcase_id"]
                }
            },
            {
                "name": "get_requirement_coverage",
                "description": """Get detailed coverage for a requirement

Returns coverage details including linked testcases, scripts, and execution history.

Example:
  get_requirement_coverage(
    requirement_id='req-abc-123'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirement_id": {"type": "string", "description": "Requirement ID"},
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"}
                    },
                    "required": ["requirement_id"]
                }
            },
            {
                "name": "get_coverage_summary",
                "description": """Get coverage summary across all requirements

Returns overall coverage metrics including total requirements, covered/uncovered counts,
coverage percentage, and breakdowns by priority and category.

Example:
  get_coverage_summary()
  
  # With filters
  get_coverage_summary(
    category='playback',
    priority='P1'
  )""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string", "description": "Team ID (optional - uses default)"},
                        "category": {"type": "string", "description": "Filter by category (optional)"},
                        "priority": {"type": "string", "description": "Filter by priority (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "get_uncovered_requirements",
                "description": """Get all requirements without test coverage

Returns list of requirements that have no linked testcases or scripts.
Useful for identifying gaps in test coverage.

Example:
  get_uncovered_requirements()""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
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

