"""
Tool Bridge

Connects Claude Agent SDK to existing MCP tools and UI interaction tools.
"""

import logging
from typing import Dict, Any, List

from mcp.mcp_server import VirtualPyTestMCPServer
from ..tools.page_interaction import (
    get_available_pages,
    get_page_schema,
    navigate_to_page,
    interact_with_element,
    highlight_element,
    show_toast,
    get_alerts,
    PAGE_INTERACTION_TOOLS,
)


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
            # UI Interaction tools - manual definitions
            if name == "get_available_pages":
                result.append({
                    "name": "get_available_pages",
                    "description": "Returns a list of all navigable pages in the application with their descriptions. Use this to understand what pages exist.",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })
                continue
                
            if name == "get_page_schema":
                result.append({
                    "name": "get_page_schema",
                    "description": "Returns the interactive elements available on a specific page. Use this to understand what actions can be performed on a page.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "page_path": {
                                "type": "string",
                                "description": "The page path (e.g., '/device-control', '/test-results/reports')"
                            }
                        },
                        "required": ["page_path"]
                    }
                })
                continue
                
            if name == "navigate_to_page":
                result.append({
                    "name": "navigate_to_page",
                    "description": "Navigates the user's browser to a specific page. Available pages: dashboard, device control, run tests, campaigns, test cases, incidents, heatmap, reports, test builder, settings, ai agent",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "page_name": {
                                "type": "string",
                                "description": "Page name or path (e.g., 'dashboard', 'device control', 'reports', 'heatmap', 'incidents')"
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional parameters (e.g., {'device_id': 's21'})"
                            }
                        },
                        "required": ["page_name"]
                    }
                })
                continue
                
            if name == "interact_with_element":
                result.append({
                    "name": "interact_with_element",
                    "description": "Interact with a specific element on the current page. Actions: click, select, filter, open, close, type, scroll_to",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "string",
                                "description": "The element ID from the page schema (e.g., 'reports-table', 'run-btn')"
                            },
                            "action": {
                                "type": "string",
                                "description": "The action to perform (click, select, filter, open, close, type, scroll_to)"
                            },
                            "params": {
                                "type": "object",
                                "description": "Optional parameters for the action (e.g., {'value': 'failed'})"
                            }
                        },
                        "required": ["element_id", "action"]
                    }
                })
                continue
                
            if name == "highlight_element":
                result.append({
                    "name": "highlight_element",
                    "description": "Highlight an element on the page to draw user's attention",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "element_id": {
                                "type": "string",
                                "description": "The element ID to highlight"
                            },
                            "duration_ms": {
                                "type": "integer",
                                "description": "How long to show the highlight (default 2000ms)"
                            }
                        },
                        "required": ["element_id"]
                    }
                })
                continue
                
            if name == "show_toast":
                result.append({
                    "name": "show_toast",
                    "description": "Show a toast notification to the user",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to display"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["info", "success", "warning", "error"],
                                "description": "Toast severity level"
                            }
                        },
                        "required": ["message"]
                    }
                })
                continue
            
            if name == "get_alerts":
                result.append({
                    "name": "get_alerts",
                    "description": "Fetch alerts from the monitoring system. Returns count and details of active and resolved alerts. Use this to answer questions about alerts/incidents.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["active", "resolved"],
                                "description": "Filter by alert status. Omit to get both active and resolved."
                            },
                            "host_name": {
                                "type": "string",
                                "description": "Filter by host name"
                            },
                            "device_id": {
                                "type": "string",
                                "description": "Filter by device ID"
                            },
                            "incident_type": {
                                "type": "string",
                                "description": "Filter by incident type (e.g., 'freeze', 'blackscreen')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max alerts to return (default 20)"
                            }
                        },
                        "required": []
                    }
                })
                continue

            # MCP tools
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
        Execute an MCP tool or UI interaction tool
        
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
        
        # UI Interaction tools
        if tool_name == "get_available_pages":
            result = get_available_pages()
            return {"result": result}
            
        if tool_name == "get_page_schema":
            result = get_page_schema(params.get("page_path", ""))
            return {"result": result}
            
        if tool_name == "navigate_to_page":
            result = navigate_to_page(
                page_name=params.get("page_name", ""), 
                context=params.get("context")
            )
            return {"result": result}
            
        if tool_name == "interact_with_element":
            result = interact_with_element(
                element_id=params.get("element_id", ""),
                action=params.get("action", ""),
                params=params.get("params")
            )
            return {"result": result}
            
        if tool_name == "highlight_element":
            result = highlight_element(
                element_id=params.get("element_id", ""),
                duration_ms=params.get("duration_ms", 2000)
            )
            return {"result": result}
            
        if tool_name == "show_toast":
            result = show_toast(
                message=params.get("message", ""),
                severity=params.get("severity", "info")
            )
            return {"result": result}
        
        if tool_name == "get_alerts":
            result = get_alerts(
                status=params.get("status"),
                host_name=params.get("host_name"),
                device_id=params.get("device_id"),
                incident_type=params.get("incident_type"),
                limit=params.get("limit", 20)
            )
            return {"result": result}

        # MCP tools
        result = self.mcp_server.handle_tool_call(tool_name, params)
        
        self.logger.info(f"Tool {tool_name} completed")
        return result
    
    def get_available_tool_names(self) -> List[str]:
        """Get list of all available tool names"""
        base_tools = [t['name'] for t in self._get_all_tools()]
        return base_tools + PAGE_INTERACTION_TOOLS
