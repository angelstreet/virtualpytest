"""
API Client for MCP Server

Provides HTTP client to communicate with backend_server routes.
Returns raw API responses - formatting is handled by callers.
"""

import requests
from typing import Dict, Any, Optional
import os


class MCPAPIClient:
    """HTTP client for backend_server API calls - returns raw responses"""
    
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
            Raw API response dict with 'success', 'error', and data fields
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(
                url,
                json=data or {},
                params=params or {},
                timeout=self.timeout
            )
            
            # Return raw JSON response
            # Accept both 200 (success) and 202 (async started) as valid responses
            if response.status_code in [200, 202]:
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
                'error': f'Request timeout ({self.timeout}s)',
                'timeout': True
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'network_error': True
            }
    
    def put(self, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        PUT request to backend_server API
        
        Args:
            endpoint: API endpoint
            data: JSON body
            params: Query parameters
            
        Returns:
            Raw API response dict
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.put(
                url,
                json=data or {},
                params=params or {},
                timeout=self.timeout
            )
            
            if response.status_code in [200, 202]:
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
                'error': f'Request timeout ({self.timeout}s)',
                'timeout': True
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'network_error': True
            }
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        GET request to backend_server API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Raw API response dict
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
                'error': f'Request timeout ({self.timeout}s)',
                'timeout': True
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'network_error': True
            }

