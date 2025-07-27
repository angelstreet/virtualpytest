"""
VirtualPyTest MCP (Model Context Protocol) Module

This module provides MCP server functionality for exposing VirtualPyTest 
capabilities as tools that can be used by external LLMs and AI agents.
"""

from .mcp_server import MockMCPServer

__all__ = ['MockMCPServer'] 