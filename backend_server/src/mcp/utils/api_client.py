"""
API Client for MCP Server

Provides HTTP client to communicate with backend_server routes.
Returns responses in MCP format directly.
"""

import json
import requests
from typing import Dict, Any, Optional
import os


class MCPAPIClient:
    """HTTP client for backend_server API calls - returns MCP format"""
    
    def __init__(self):
        # MCP server runs inside backend_server, so it calls itself
        # Default to localhost:5109 (backend_server port)
        # Set SERVER_BASE_URL env var to override (e.g., for remote backend_server)
        self.base_url = os.getenv('SERVER_BASE_URL', 'http://localhost:5109')
        self.timeout = 30
    
    def _to_mcp_format(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert backend API response to MCP format"""
        success = api_response.get('success', False)
        
        if success:
            # Remove success flag and return clean data in MCP format
            clean_result = {k: v for k, v in api_response.items() if k != 'success'}
            return {
                "content": [{"type": "text", "text": json.dumps(clean_result, indent=2)}],
                "isError": False
            }
        else:
            # Error response
            error_msg = api_response.get('error', 'Operation failed')
            return {
                "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                "isError": True
            }
    
    def post(self, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        POST request to backend_server API
        
        Args:
            endpoint: API endpoint (e.g., '/server/control/takeControl')
            data: JSON body
            params: Query parameters (e.g., {'team_id': 'xxx'})
            
        Returns:
            Response in MCP format
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(
                url,
                json=data or {},
                params=params or {},
                timeout=self.timeout
            )
            
            # Return JSON response in MCP format
            if response.status_code == 200:
                return self._to_mcp_format(response.json())
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: HTTP {response.status_code}: {response.text}"}],
                    "isError": True
                }
                
        except requests.exceptions.Timeout:
            return {
                "content": [{"type": "text", "text": f"Error: Request timeout ({self.timeout}s)"}],
                "isError": True
            }
        except requests.exceptions.RequestException as e:
            return {
                "content": [{"type": "text", "text": f"Error: Network error: {str(e)}"}],
                "isError": True
            }
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        GET request to backend_server API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response in MCP format
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(
                url,
                params=params or {},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return self._to_mcp_format(response.json())
            else:
                return {
                    "content": [{"type": "text", "text": f"Error: HTTP {response.status_code}: {response.text}"}],
                    "isError": True
                }
                
        except requests.exceptions.Timeout:
            return {
                "content": [{"type": "text", "text": f"Error: Request timeout ({self.timeout}s)"}],
                "isError": True
            }
        except requests.exceptions.RequestException as e:
            return {
                "content": [{"type": "text", "text": f"Error: Network error: {str(e)}"}],
                "isError": True
            }

