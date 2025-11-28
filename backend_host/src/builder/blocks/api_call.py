"""
API Call Block

Execute Postman API requests with context variable substitution.

Features:
- Select from configured Postman workspaces/collections/endpoints
- Auto-substitute variables from execution context (server_url, team_id, device_id, etc.)
- Store response in context for next blocks
- Clean UX with cascading dropdowns
"""

import requests
import json
import re
from typing import Dict, Any


def get_block_info() -> Dict[str, Any]:
    """
    Get API call block metadata with typed parameters.
    
    Returns:
        Dict with block metadata including cascading dropdown parameters
    """
    return {
        'command': 'api_call',
        'name': 'API Call',
        'category': 'api',
        'description': 'Execute Postman API request with context variables',
        'icon': '🌐',
        'params': [
            {
                'name': 'workspace_id',
                'type': 'select',
                'label': 'Workspace',
                'options_source': 'postman_workspaces',  # Dynamic from config
                'required': True,
                'description': 'Postman workspace'
            },
            {
                'name': 'collection_id',
                'type': 'select',
                'label': 'Collection',
                'options_source': 'postman_collections',  # Dynamic via API
                'required': True,
                'depends_on': 'workspace_id',
                'description': 'API collection'
            },
            {
                'name': 'request_id',
                'type': 'select',
                'label': 'Request',
                'options_source': 'postman_requests',  # Dynamic via API
                'required': True,
                'depends_on': 'collection_id',
                'description': 'API endpoint to call'
            },
            {
                'name': 'environment_id',
                'type': 'select',
                'label': 'Environment',
                'options_source': 'postman_environments',  # Dynamic via API
                'required': False,
                'depends_on': 'workspace_id',
                'description': 'Environment (defines variable templates)'
            },
            {
                'name': 'store_response_as',
                'type': 'string',
                'label': 'Store Response As',
                'description': 'Variable name to store response (optional)',
                'required': False,
                'default': 'api_response'
            },
            {
                'name': 'fail_on_error',
                'type': 'boolean',
                'label': 'Fail on Error',
                'description': 'Fail block if HTTP status >= 400',
                'required': False,
                'default': True
            },
            {
                'name': 'timeout_ms',
                'type': 'number',
                'label': 'Timeout (ms)',
                'description': 'Request timeout in milliseconds',
                'required': False,
                'default': 5000
            }
        ],
        'outputs': [
            {
                'name': 'response',
                'type': 'object',
                'description': 'API response data'
            },
            {
                'name': 'status_code',
                'type': 'number',
                'description': 'HTTP status code'
            },
            {
                'name': 'headers',
                'type': 'object',
                'description': 'Response headers'
            }
        ]
    }


def execute(workspace_id: str = None,
            collection_id: str = None,
            request_id: str = None,
            environment_id: str = None,
            store_response_as: str = 'api_response',
            fail_on_error: bool = True,
            timeout_ms: int = 5000,
            context: Dict[str, Any] = None,
            **kwargs) -> Dict[str, Any]:
    """
    Execute Postman API request with context variable substitution.
    
    Args:
        workspace_id: Postman workspace ID
        collection_id: Collection ID
        request_id: Request ID
        environment_id: Optional environment ID (for variable templates)
        store_response_as: Variable name to store response in context
        fail_on_error: Fail if status >= 400
        timeout_ms: Request timeout
        context: Execution context with variables
        **kwargs: Additional parameters
        
    Returns:
        Dict with success status and response data
    """
    print(f"[@api_call] Executing API request: {request_id}")
    
    if not context:
        context = {}
    
    try:
        # 1. Fetch request definition from Postman
        request_def = _fetch_request_definition(workspace_id, collection_id, request_id)
        if not request_def:
            return {
                'success': False,
                'message': f'Failed to fetch request definition: {request_id}',
                'error': 'Request not found'
            }
        
        # 2. Get environment variable templates
        env_variables = _get_environment_variables(workspace_id, environment_id) if environment_id else {}
        
        # 3. Build variable map from context (context overrides env defaults)
        variables = _build_variable_map(env_variables, context)
        
        # 4. Substitute variables in request
        url = _substitute_variables(request_def.get('url', ''), variables)
        body = _substitute_variables(request_def.get('body'), variables)
        headers = _substitute_variables(request_def.get('headers', {}), variables)
        
        # 5. Execute HTTP request
        method = request_def.get('method', 'GET').upper()
        timeout_sec = timeout_ms / 1000.0
        
        print(f"[@api_call] {method} {url}")
        
        response = requests.request(
            method=method,
            url=url,
            json=body if body else None,
            headers=headers,
            timeout=timeout_sec
        )
        
        # 6. Parse response
        try:
            response_data = response.json()
        except:
            response_data = response.text
        
        # 7. Store response in context
        if store_response_as:
            context[store_response_as] = response_data
            context[f'{store_response_as}_status'] = response.status_code
            context[f'{store_response_as}_headers'] = dict(response.headers)
        
        # 8. Determine success
        is_success = response.status_code < 400 or not fail_on_error
        
        return {
            'success': is_success,
            'result_success': 0 if is_success else 1,  # Legacy format
            'status_code': response.status_code,
            'response': response_data,
            'headers': dict(response.headers),
            'message': f'{method} {url} → {response.status_code}',
            'output_data': {
                'response': response_data,
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
        }
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'result_success': 1,
            'error': 'Request timeout',
            'message': f'Request timed out after {timeout_ms}ms'
        }
    except Exception as e:
        print(f"[@api_call] Error: {str(e)}")
        return {
            'success': False,
            'result_success': 1,
            'error': str(e),
            'message': f'API call failed: {str(e)}'
        }


def _fetch_request_definition(workspace_id: str, collection_id: str, request_id: str) -> Dict[str, Any]:
    """
    Fetch request definition from backend server Postman cache.
    
    Args:
        workspace_id: Workspace ID
        collection_id: Collection ID
        request_id: Request ID
        
    Returns:
        Request definition dict or None
    """
    try:
        # Call backend server to get request definition
        # This endpoint should be created to fetch and cache request details from Postman
        import os
        server_url = os.getenv('BACKEND_SERVER_URL', 'http://localhost:5109')
        
        response = requests.get(
            f'{server_url}/server/postman/requests/{request_id}/definition',
            params={
                'workspace_id': workspace_id,
                'collection_id': collection_id
            },
            timeout=5.0
        )
        
        if response.ok:
            data = response.json()
            return data.get('request')
        
        print(f"[@api_call] Failed to fetch request definition: {response.status_code}")
        return None
        
    except Exception as e:
        print(f"[@api_call] Error fetching request definition: {str(e)}")
        return None


def _get_environment_variables(workspace_id: str, environment_id: str) -> Dict[str, Any]:
    """
    Get environment variable templates from backend server.
    
    Args:
        workspace_id: Workspace ID
        environment_id: Environment ID
        
    Returns:
        Dict of variable key-value pairs
    """
    try:
        import os
        server_url = os.getenv('BACKEND_SERVER_URL', 'http://localhost:5109')
        
        response = requests.get(
            f'{server_url}/server/postman/environments/{environment_id}',
            params={'workspace_id': workspace_id},
            timeout=5.0
        )
        
        if response.ok:
            data = response.json()
            env = data.get('environment', {})
            variables = env.get('variables', [])
            
            # Convert to dict
            return {var['key']: var['value'] for var in variables if 'key' in var}
        
        return {}
        
    except Exception as e:
        print(f"[@api_call] Error fetching environment variables: {str(e)}")
        return {}


def _build_variable_map(env_variables: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build variable map with context overriding environment defaults.
    
    Priority: context > environment template
    
    Args:
        env_variables: Environment variable templates
        context: Execution context
        
    Returns:
        Merged variable map
    """
    variables = env_variables.copy()
    
    # Common variable names that come from context
    context_var_names = [
        'server_url', 'host_url', 'api_key',
        'team_id', 'user_id',
        'device_id', 'device_name',
        'host_name',
        'userinterface', 'userinterface_name'
    ]
    
    # Override with context values
    for var_name in context_var_names:
        if var_name in context:
            variables[var_name] = context[var_name]
    
    return variables


def _substitute_variables(template: Any, variables: Dict[str, Any]) -> Any:
    """
    Substitute {{variable}} placeholders with actual values.
    
    Supports:
    - Strings: "{{server_url}}/path"
    - Dicts: {"key": "{{value}}"}
    - Lists: ["{{item1}}", "{{item2}}"]
    
    Args:
        template: Template with {{variable}} placeholders
        variables: Variable map
        
    Returns:
        Template with substituted values
    """
    if template is None:
        return None
    
    # String substitution
    if isinstance(template, str):
        # Replace {{variable}} with value
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))
        
        return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
    
    # Dict substitution (recursive)
    if isinstance(template, dict):
        return {
            key: _substitute_variables(value, variables)
            for key, value in template.items()
        }
    
    # List substitution (recursive)
    if isinstance(template, list):
        return [_substitute_variables(item, variables) for item in template]
    
    # Other types - return as-is
    return template

