"""
API Client for MCP Server

Provides HTTP client to communicate with backend_server routes.
"""

import requests
from typing import Dict, Any, Optional
import os


class MCPAPIClient:
    """HTTP client for backend_server API calls"""
    
    def __init__(self):
        # MCP server runs inside backend_server, so it calls itself
        # Default to localhost:5109 (backend_server port)
        # Set SERVER_BASE_URL env var to override (e.g., for remote backend_server)
        self.base_url = os.getenv('SERVER_BASE_URL', 'http://localhost:5109')
        self.timeout = 30
    
    def post(self, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        POST request to backend_server API
        
        Args:
            endpoint: API endpoint (e.g., '/server/control/takeControl')
            data: JSON body
            params: Query parameters (e.g., {'team_id': 'xxx'})
            
        Returns:
            Response JSON as dict
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(
                url,
                json=data or {},
                params=params or {},
                timeout=self.timeout
            )
            
            # Return JSON response
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'timeout': self.timeout
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        GET request to backend_server API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Response JSON as dict
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(
                url,
                params=params or {},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }

