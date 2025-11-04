"""
MCP Response Formatter

Converts backend API responses to MCP protocol format.
Handles success/error responses, categorizes errors, and formats content.
"""

import json
from typing import Dict, Any, List
from enum import Enum


class ErrorCategory(Enum):
    """Error categories for better error handling"""
    VALIDATION = "validation_error"
    TIMEOUT = "timeout_error"
    NETWORK = "network_error"
    BACKEND = "backend_error"
    NOT_FOUND = "not_found_error"
    UNAUTHORIZED = "unauthorized_error"
    UNKNOWN = "unknown_error"


class MCPFormatter:
    """Utility for formatting responses in MCP protocol format"""
    
    @staticmethod
    def format_success(data: Any) -> Dict[str, Any]:
        """
        Format successful response in MCP format
        
        Args:
            data: Response data (dict, string, or other)
            
        Returns:
            MCP-formatted success response with content array and isError: False
        """
        if isinstance(data, str):
            text = data
        elif isinstance(data, dict):
            # Remove 'success' flag if present
            clean_data = {k: v for k, v in data.items() if k != 'success'}
            text = json.dumps(clean_data, indent=2)
        else:
            text = str(data)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": text
                }
            ],
            "isError": False
        }
    
    @staticmethod
    def format_error(error_msg: str, category: ErrorCategory = ErrorCategory.UNKNOWN) -> Dict[str, Any]:
        """
        Format error response in MCP format
        
        Args:
            error_msg: Error message
            category: Error category for better error handling
            
        Returns:
            MCP-formatted error response with content array and isError: True
        """
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error [{category.value}]: {error_msg}"
                }
            ],
            "isError": True,
            "errorCategory": category.value
        }
    
    @staticmethod
    def format_api_response(api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert backend API response to MCP format
        
        Automatically categorizes errors based on response fields.
        
        Args:
            api_response: Raw API response from backend
            
        Returns:
            MCP-formatted response
        """
        success = api_response.get('success', False)
        
        if success:
            return MCPFormatter.format_success(api_response)
        else:
            # Categorize error
            error_msg = api_response.get('error', 'Operation failed')
            
            # Determine error category from response
            if api_response.get('timeout'):
                category = ErrorCategory.TIMEOUT
            elif api_response.get('network_error'):
                category = ErrorCategory.NETWORK
            elif api_response.get('status_code') == 404:
                category = ErrorCategory.NOT_FOUND
            elif api_response.get('status_code') in [401, 403]:
                category = ErrorCategory.UNAUTHORIZED
            elif api_response.get('status_code'):
                category = ErrorCategory.BACKEND
            else:
                category = ErrorCategory.UNKNOWN
            
            return MCPFormatter.format_error(error_msg, category)
    
    @staticmethod
    def format_validation_error(field: str, message: str) -> Dict[str, Any]:
        """
        Format validation error for invalid inputs
        
        Args:
            field: Field that failed validation
            message: Validation error message
            
        Returns:
            MCP-formatted validation error
        """
        error_msg = f"Validation failed for '{field}': {message}"
        return MCPFormatter.format_error(error_msg, ErrorCategory.VALIDATION)

