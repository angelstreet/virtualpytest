#!/usr/bin/env python3
"""
MCP Server for VirtualPyTest

Model Context Protocol server that exposes VirtualPyTest device control
functionality to external LLMs (Claude, ChatGPT, etc.)

This server provides 11 core tools for device automation:
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
"""

import asyncio
import logging
from typing import Dict, Any, List
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

# Import utilities
from .utils.api_client import MCPAPIClient
from .utils.response_formatter import format_mcp_response


class VirtualPyTestMCPServer:
    """MCP Server for VirtualPyTest device automation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_client = MCPAPIClient()
        
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
        }
        
        self.logger.info(f"VirtualPyTest MCP Server initialized with {len(self.tool_handlers)} tools")
    
    async def handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP tool call
        
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
                return format_mcp_response(
                    success=False,
                    error=f"Unknown tool: {tool_name}. Available tools: {list(self.tool_handlers.keys())}"
                )
            
            # Execute tool
            handler = self.tool_handlers[tool_name]
            result = handler(params)
            
            self.logger.info(f"Tool {tool_name} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Tool call error for {tool_name}: {e}", exc_info=True)
            return format_mcp_response(
                success=False,
                error=f"Tool execution error: {str(e)}"
            )
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available MCP tools
        
        Returns:
            List of tool definitions with names and descriptions
        """
        tools = [
            {
                "name": "take_control",
                "description": "Take control of a device (REQUIRED before any operations). Locks device and generates navigation cache.",
                "category": "control",
                "required_params": ["host_name", "device_id", "team_id"],
                "optional_params": ["tree_id"]
            },
            {
                "name": "release_control",
                "description": "Release control of a device. Unlocks device when operations are complete.",
                "category": "control",
                "required_params": ["host_name", "device_id", "team_id"]
            },
            {
                "name": "execute_device_action",
                "description": "Execute batch of actions on device (remote commands, ADB, web, desktop). Returns execution_id for polling.",
                "category": "action",
                "required_params": ["device_id", "team_id", "actions"],
                "optional_params": ["retry_actions", "failure_actions"]
            },
            {
                "name": "navigate_to_node",
                "description": "Navigate to target node in UI tree using pathfinding. Requires take_control first.",
                "category": "navigation",
                "required_params": ["tree_id", "userinterface_name", "device_id", "team_id", "target_node_id or target_node_label"],
                "optional_params": ["current_node_id", "host_name"]
            },
            {
                "name": "verify_device_state",
                "description": "Verify device state with batch verifications (image, text, video, ADB).",
                "category": "verification",
                "required_params": ["device_id", "team_id", "userinterface_name", "verifications"],
                "optional_params": ["tree_id", "node_id", "host_name"]
            },
            {
                "name": "execute_testcase",
                "description": "Execute complete test case from graph JSON. Returns execution_id for polling.",
                "category": "testcase",
                "required_params": ["device_id", "team_id", "host_name", "graph_json"],
                "optional_params": ["userinterface_name", "testcase_name", "async_execution"]
            },
            {
                "name": "generate_test_graph",
                "description": "Generate test case graph from natural language using AI.",
                "category": "ai",
                "required_params": ["prompt", "device_id", "team_id", "userinterface_name"],
                "optional_params": ["current_node_id"]
            },
            {
                "name": "capture_screenshot",
                "description": "Capture screenshot from device for AI vision analysis. Returns base64 image.",
                "category": "screenshot",
                "required_params": ["device_id", "team_id"],
                "optional_params": ["include_ui_dump", "host_name"]
            },
            {
                "name": "get_transcript",
                "description": "Get audio transcript from device with optional translation.",
                "category": "transcript",
                "required_params": ["device_id", "team_id", "chunk_url or (hour + chunk_index)"],
                "optional_params": ["target_language"]
            },
            {
                "name": "get_device_info",
                "description": "Get device information, capabilities, and controller status.",
                "category": "device",
                "required_params": [],
                "optional_params": ["device_id", "host_name"]
            },
            {
                "name": "get_execution_status",
                "description": "Poll async execution status for actions, testcases, or AI operations.",
                "category": "device",
                "required_params": ["execution_id"],
                "optional_params": ["operation_type"]
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

