"""
Response Formatter for MCP

Formats API responses into MCP-compatible format for LLMs.
"""

from typing import Dict, Any, List


def format_mcp_response(success: bool, content: Any = None, error: str = None) -> Dict[str, Any]:
    """
    Format response in MCP protocol format
    
    Args:
        success: Operation success status
        content: Content to return (text, JSON, etc.)
        error: Error message if failed
        
    Returns:
        MCP-formatted response
    """
    if success:
        # Format successful response
        if isinstance(content, str):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": content
                    }
                ]
            }
        elif isinstance(content, dict):
            # Pretty print JSON for LLM
            import json
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(content, indent=2)
                    }
                ]
            }
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(content)
                    }
                ]
            }
    else:
        # Format error response
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {error or 'Unknown error occurred'}"
                }
            ],
            "isError": True
        }


def format_tool_result(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert API response to MCP tool result
    
    Args:
        api_response: Raw API response from backend
        
    Returns:
        MCP-formatted tool result
    """
    success = api_response.get('success', False)
    
    if success:
        # Remove 'success' key for cleaner output
        filtered_response = {k: v for k, v in api_response.items() if k != 'success'}
        return format_mcp_response(True, filtered_response)
    else:
        error = api_response.get('error', 'Operation failed')
        return format_mcp_response(False, error=error)

