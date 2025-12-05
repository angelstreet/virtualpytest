"""
Tool Bridge

Connects Claude Agent SDK to existing MCP tools.
"""

import logging
from typing import Dict, Any, List

from mcp.mcp_server import VirtualPyTestMCPServer
from ..tools.ui_control import navigate_to_page


class ToolBridge:
    """Bridge between agents and MCP tools"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mcp_server = VirtualPyTestMCPServer()
        self._tool_cache = None
        self.logger.info("ToolBridge initialized with MCP server")
    
    def _get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available MCP tools (cached)"""
        if self._tool_cache is None:
            self._tool_cache = self.mcp_server.get_available_tools()
            self.logger.info(f"Cached {len(self._tool_cache)} MCP tools")
        return self._tool_cache
    
    def get_tool_definitions(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """
        Get tool definitions for specified tools in Claude format
        
        Args:
            tool_names: List of tool names to get
            
        Returns:
            List of tool definitions in Claude's expected format
        """
        all_tools = self._get_all_tools()
        tools_by_name = {t['name']: t for t in all_tools}
        
        result = []
        for name in tool_names:
            if name == "navigate_to_page":
                # Manual definition for UI control tool
                result.append({
                    "name": "navigate_to_page",
                    "description": "Navigates the user's UI to a specific page.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "page_name": {
                                "type": "string",
                                "enum": ["dashboard", "device_control", "reports", "campaigns", "settings", "monitor"],
                                "description": "The identifier of the page to navigate to"
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional parameters context (e.g., device_id)"
                            }
                        },
                        "required": ["page_name"]
                    }
                })
                continue

            if name in tools_by_name:
                mcp_tool = tools_by_name[name]
                # Convert MCP format to Claude format
                claude_tool = {
                    "name": mcp_tool['name'],
                    "description": mcp_tool['description'],
                    "input_schema": mcp_tool['inputSchema'],
                }
                result.append(claude_tool)
            else:
                self.logger.warning(f"Tool not found: {name}")
        
        return result
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            Tool result
            
        Raises:
            ValueError: If tool fails
        """
        self.logger.info(f"Executing tool: {tool_name}")
        self.logger.debug(f"Params: {params}")
        
        if tool_name == "navigate_to_page":
            result = navigate_to_page(
                page_name=params.get("page_name"), 
                context=params.get("context")
            )
            return {"result": result}

        result = self.mcp_server.handle_tool_call(tool_name, params)
        
        self.logger.info(f"Tool {tool_name} completed")
        return result
    
    def get_available_tool_names(self) -> List[str]:
        """Get list of all available tool names"""
        base_tools = [t['name'] for t in self._get_all_tools()]
        return base_tools + ["navigate_to_page"]
