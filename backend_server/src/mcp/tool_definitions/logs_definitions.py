"""Logs tool definitions for systemd service log management"""

from typing import List, Dict, Any


def get_tools() -> List[Dict[str, Any]]:
    """Get logs-related tool definitions"""
    return [
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

