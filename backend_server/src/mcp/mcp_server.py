#!/usr/bin/env python3
"""
MCP Server for VirtualPyTest

Model Context Protocol server that exposes VirtualPyTest device control
functionality to external LLMs (Claude, ChatGPT, etc.)

This server provides 70 core tools for device automation organized into domains:
- Control: device locking and session management
- Actions: device command execution
- Navigation: UI tree navigation and pathfinding
- Verification: state verification and UI inspection
- TestCase: test case execution and management
- Script: Python script execution
- Deployment: scheduled execution management
- AI: test generation
- Screenshot/Transcript: media capture
- Device: device info and compatibility
- Logs: systemd service logs
- Tree: navigation tree CRUD operations
- UserInterface: app model management
- Requirements: requirements and coverage tracking
- Screen Analysis: unified selector scoring
- Exploration: AI-powered tree building (NEW - RECOMMENDED)
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
from .tools.screen_analysis_tools import ScreenAnalysisTools
from .tools.exploration_tools import ExplorationTools  # NEW - AI-powered tree building
from .tools.deployment_tools import DeploymentTools  # NEW - Deployment management
from .tools.analysis_tools import AnalysisTools  # Analysis tools for analyzer agent

# Import tool definitions
from .tool_definitions import (
    get_control_tools,
    get_action_tools,
    get_navigation_tools,
    get_verification_tools,
    get_testcase_tools,
    get_script_tools,
    get_ai_tools,
    get_screenshot_tools,
    get_transcript_tools,
    get_device_tools,
    get_logs_tools,
    get_tree_tools,
    get_userinterface_tools,
    get_requirements_tools,
    get_screen_analysis_tools,
    get_exploration_tools,  # NEW - AI-powered tree building
    get_deployment_tools,  # NEW - Deployment management
    get_analysis_tools,  # Analysis tools for analyzer agent
)

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
        self.screen_analysis_tools = ScreenAnalysisTools()
        self.exploration_tools = ExplorationTools(self.api_client)  # NEW - AI-powered tree building
        self.deployment_tools = DeploymentTools(self.api_client)  # NEW - Deployment management
        self.analysis_tools = AnalysisTools()  # Analysis tools for analyzer agent
        
        # Tool registry mapping
        self.tool_handlers = {
            # Control tools
            'take_control': self.control_tools.take_control,
            'release_control': self.control_tools.release_control,
            
            # Action tools
            'list_actions': self.action_tools.list_actions,
            'execute_device_action': self.action_tools.execute_device_action,
            
            # Navigation tools
            'list_navigation_nodes': self.navigation_tools.list_navigation_nodes,
            'navigate_to_node': self.navigation_tools.navigate_to_node,
            'preview_userinterface': self.navigation_tools.preview_userinterface,
            
            # Verification tools
            'list_verifications': self.verification_tools.list_verifications,
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
            'generate_and_save_testcase': self.ai_tools.generate_and_save_testcase,  # NEW - Generate + save in one step
            
            # Screenshot tools
            'capture_screenshot': self.screenshot_tools.capture_screenshot,
            
            # Transcript tools
            'get_transcript': self.transcript_tools.get_transcript,
            
            # Device info tools
            'list_hosts': self.device_tools.list_hosts,  # NEW - List all registered hosts
            'get_device_info': self.device_tools.get_device_info,
            'get_compatible_hosts': self.device_tools.get_compatible_hosts,
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
            
            # Screen Analysis tools (NEW - Unified selector scoring)
            'analyze_screen_for_action': self.screen_analysis_tools.analyze_screen_for_action,
            'analyze_screen_for_verification': self.screen_analysis_tools.analyze_screen_for_verification,
            
            # AI Exploration tools (NEW - Automated tree building)
            'start_ai_exploration': self.exploration_tools.start_ai_exploration,
            'get_exploration_status': self.exploration_tools.get_exploration_status,
            'approve_exploration_plan': self.exploration_tools.approve_exploration_plan,
            'validate_exploration_edges': self.exploration_tools.validate_exploration_edges,
            'get_node_verification_suggestions': self.exploration_tools.get_node_verification_suggestions,
            'approve_node_verifications': self.exploration_tools.approve_node_verifications,
            'finalize_exploration': self.exploration_tools.finalize_exploration,
            
            # Deployment tools (NEW - Scheduled execution management)
            'create_deployment': self.deployment_tools.create_deployment,
            'list_deployments': self.deployment_tools.list_deployments,
            'pause_deployment': self.deployment_tools.pause_deployment,
            'resume_deployment': self.deployment_tools.resume_deployment,
            'update_deployment': self.deployment_tools.update_deployment,
            'delete_deployment': self.deployment_tools.delete_deployment,
            'get_deployment_history': self.deployment_tools.get_deployment_history,
            
            # Analysis tools (for analyzer agent)
            'get_last_execution_result': self.analysis_tools.get_last_execution_result,
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
            List of MCP-formatted tool definitions aggregated from all domains
        """
        tools: List[Dict[str, Any]] = []
        
        # Aggregate tool definitions from all domains
        tools.extend(get_control_tools())
        tools.extend(get_action_tools())
        tools.extend(get_navigation_tools())
        tools.extend(get_verification_tools())
        tools.extend(get_testcase_tools())
        tools.extend(get_script_tools())
        tools.extend(get_ai_tools())
        tools.extend(get_screenshot_tools())
        tools.extend(get_transcript_tools())
        tools.extend(get_device_tools())
        tools.extend(get_logs_tools())
        tools.extend(get_tree_tools())
        tools.extend(get_userinterface_tools())
        tools.extend(get_requirements_tools())
        tools.extend(get_screen_analysis_tools())
        tools.extend(get_exploration_tools())  # NEW - AI-powered tree building
        tools.extend(get_analysis_tools())  # Analysis tools for analyzer agent
        
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

