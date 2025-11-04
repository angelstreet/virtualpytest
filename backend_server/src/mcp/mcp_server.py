#!/usr/bin/env python3
"""
MCP Server for VirtualPyTest

Model Context Protocol server that exposes VirtualPyTest device control
functionality to external LLMs (Claude, ChatGPT, etc.)

This server provides 13 core tools for device automation:
1. take_control - Lock device and generate navigation cache (REQUIRED FIRST)
2. release_control - Release device lock
3. execute_device_action - Execute remote/ADB/web/desktop commands
4. navigate_to_node - Navigate through UI trees
5. verify_device_state - Verify UI elements and device states
6. execute_testcase - Run complete test cases
7. generate_test_graph - AI-powered test generation
8. capture_screenshot - Capture screenshots for vision analysis
9. get_transcript - Fetch audio transcripts
10. get_device_info - Get device capabilities and info
11. get_execution_status - Poll async execution status
12. view_logs - View systemd service logs
13. list_services - List VirtualPyTest services
"""

import logging
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
        
        # Tool registry mapping
        self.tool_handlers = {
            # Control tools (CRITICAL - must be first)
            'take_control': self.control_tools.take_control,
            'release_control': self.control_tools.release_control,
            
            # Action tools
            'execute_device_action': self.action_tools.execute_device_action,
            
            # Navigation tools
            'navigate_to_node': self.navigation_tools.navigate_to_node,
            
            # Verification tools
            'verify_device_state': self.verification_tools.verify_device_state,
            
            # TestCase tools
            'execute_testcase': self.testcase_tools.execute_testcase,
            
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
                "description": "Take control of a device (REQUIRED before any operations). Locks device and generates navigation cache.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "tree_id": {"type": "string", "description": "Navigation tree ID (triggers cache generation if provided)"}
                    },
                    "required": []
                }
            },
            {
                "name": "release_control",
                "description": "Release control of a device. Unlocks device when operations are complete.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"}
                    },
                    "required": []
                }
            },
            {
                "name": "execute_device_action",
                "description": "Execute batch of actions on device (remote commands, ADB, web, desktop). Returns execution_id for polling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "actions": {
                            "type": "array",
                            "description": "Array of action objects with command, params, and optional delay",
                            "items": {"type": "object"}
                        },
                        "retry_actions": {"type": "array", "description": "Actions to retry on failure", "items": {"type": "object"}},
                        "failure_actions": {"type": "array", "description": "Actions to execute on failure", "items": {"type": "object"}}
                    },
                    "required": ["actions"]
                }
            },
            {
                "name": "navigate_to_node",
                "description": "Navigate to target node in UI tree using pathfinding. Requires take_control first.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tree_id": {"type": "string", "description": "Navigation tree ID"},
                        "userinterface_name": {"type": "string", "description": "User interface name (e.g., 'horizon_android_tv')"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
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
                "name": "verify_device_state",
                "description": "Verify device state with batch verifications (image, text, video, ADB).",
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
                "description": "Execute complete test case from graph JSON. Returns execution_id for polling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "host_name": {"type": "string", "description": "Host name where device is connected (optional - defaults to 'sunri-pi1')"},
                        "graph_json": {"type": "object", "description": "Test case graph definition"},
                        "userinterface_name": {"type": "string", "description": "User interface name"},
                        "testcase_name": {"type": "string", "description": "Test case name"},
                        "async_execution": {"type": "boolean", "description": "Execute asynchronously (default: true)"}
                    },
                    "required": ["graph_json"]
                }
            },
            {
                "name": "generate_test_graph",
                "description": "Generate test case graph from natural language using AI.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Natural language test description"},
                        "device_id": {"type": "string", "description": "Device identifier (optional - defaults to 'device_1')"},
                        "team_id": {"type": "string", "description": "Team ID for security (optional - uses default if omitted)"},
                        "userinterface_name": {"type": "string", "description": "User interface name"},
                        "current_node_id": {"type": "string", "description": "Current node ID (optional)"}
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

