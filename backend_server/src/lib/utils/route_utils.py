"""
Route Utilities

Shared utilities for server routes including host proxying and request handling.
"""

from flask import request
import requests
import json
import urllib3
import os

# Disable InsecureRequestWarning for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_host_from_request():
    """Get host information from request data using host_name lookup"""
    try:
        # Check both JSON body (for POST requests) and query parameters (for GET requests)
        try:
            data = request.get_json() or {}
        except:
            # GET requests don't have JSON body, that's fine
            data = {}
        host_name = data.get('host_name') or request.args.get('host_name')
        
        if not host_name:
            return None, 'host_name required in request body or query parameters'
            
        from  backend_server.src.lib.utils.server_utils import get_host_manager
        host_manager = get_host_manager()
        host_info = host_manager.get_host(host_name)
        
        if not host_info:
            return None, f'Host "{host_name}" not found'
            
        return host_info, None
                
    except Exception as e:
        return None, f'Error getting host from request: {str(e)}'


def proxy_to_host(endpoint, method='GET', data=None, timeout=30, headers=None):
    """
    Proxy a request to the specified host's endpoint using buildHostUrl
    
    Args:
        endpoint: The host endpoint to call (e.g., '/host/av/get-stream-url')
        method: HTTP method ('GET', 'POST', etc.)
        data: Request data for POST requests (should include host info)
        timeout: Request timeout in seconds (default: 30)
        headers: Additional headers to include in the request (dict)
    
    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        # Get host information from request
        host_info, error = get_host_from_request()
        if not host_info:
            return {
                'success': False,
                'error': error or 'Host information required'
            }, 400
        
        # Use centralized API URL builder to construct the proper URL
        from shared.src.lib.utils.build_url_utils import buildHostUrl
        full_url = buildHostUrl(host_info, endpoint)
        
        if not full_url:
            return {
                'success': False,
                'error': 'Failed to build host URL'
            }, 500
        
        print(f"[@utils:routeUtils:proxy_to_host] Proxying {method} {endpoint} to {full_url}")
        
        # Prepare request parameters
        # Use tuple format: (connect_timeout, read_timeout) to ensure read timeout is respected
        kwargs = {
            'timeout': (60, timeout),  # 60s connect, specified read timeout
            'verify': False  # For self-signed certificates
        }
        
        # Prepare headers - only set Content-Type if we have data
        request_headers = {}
        if data:
            request_headers['Content-Type'] = 'application/json'
            kwargs['json'] = data
        
        # Add API key for backend_host authentication
        api_key = os.getenv('API_KEY')
        if api_key:
            request_headers['X-API-Key'] = api_key
            print(f"[@utils:routeUtils:proxy_to_host] ✅ API key added (length: {len(api_key)})")
        else:
            print(f"[@utils:routeUtils:proxy_to_host] ⚠️ WARNING: API_KEY not found in environment")
        
        if headers:
            request_headers.update(headers)
        
        if request_headers:
            kwargs['headers'] = request_headers
        
        # Make the request to the host
        if method.upper() == 'GET':
            response = requests.get(full_url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(full_url, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(full_url, **kwargs)
        elif method.upper() == 'DELETE':
            response = requests.delete(full_url, **kwargs)
        else:
            return {
                'success': False,
                'error': f'Unsupported HTTP method: {method}'
            }, 400
        
        # Return the host's response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {
                'success': False,
                'error': 'Invalid JSON response from host',
                'raw_response': response.text[:500]  # First 500 chars for debugging
            }
        
        return response_data, response.status_code
        
    except requests.exceptions.Timeout as e:
        error_msg = f'Request to host timed out (timeout={timeout}s)'
        print(f"[@utils:routeUtils:proxy_to_host] ⚠️ TIMEOUT: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host] ⚠️ Error: {str(e)}")
        return {
            'success': False,
            'error': error_msg
        }, 504
    except requests.exceptions.ConnectionError as e:
        error_msg = f'Could not connect to host: {str(e)}'
        print(f"[@utils:routeUtils:proxy_to_host] ❌ CONNECTION ERROR: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host] ❌ Error details: {str(e)}")
        return {
            'success': False,
            'error': error_msg
        }, 503
    except Exception as e:
        error_msg = f'Proxy error: {str(e)}'
        print(f"[@utils:routeUtils:proxy_to_host] 💥 UNEXPECTED ERROR: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host] 💥 Error type: {type(e).__name__}")
        print(f"[@utils:routeUtils:proxy_to_host] 💥 Error details: {str(e)}")
        return {
            'success': False,
            'error': error_msg
        }, 500


def proxy_to_host_with_params(endpoint, method='GET', data=None, query_params=None, timeout=30, headers=None):
    """
    Proxy a request to the specified host's endpoint with query parameters (for device_id handling)
    
    Args:
        endpoint: The host endpoint to call (e.g., '/host/av/get-stream-url')
        method: HTTP method ('GET', 'POST', etc.)
        data: Request data for POST requests (should include host info)
        query_params: Query parameters to add to the URL (dict)
        timeout: Request timeout in seconds (default: 30)
        headers: Additional headers to include in the request (dict)
    
    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        # Get host information from request
        host_info, error = get_host_from_request()
        if not host_info:
            return {
                'success': False,
                'error': error or 'Host information required'
            }, 400
        
        # Use centralized API URL builder to construct the proper URL
        from shared.src.lib.utils.build_url_utils import buildHostUrl
        full_url = buildHostUrl(host_info, endpoint)
        
        if not full_url:
            return {
                'success': False,
                'error': 'Failed to build host URL'
            }, 500
        
        print(f"[@utils:routeUtils:proxy_to_host_with_params] Proxying {method} {endpoint} to {full_url}")
        if query_params:
            print(f"[@utils:routeUtils:proxy_to_host_with_params] Query params: {query_params}")
        
        # DEBUG: Check API key availability
        api_key_test = os.getenv('API_KEY')
        print(f"[@utils:routeUtils:proxy_to_host_with_params] 🔑 DEBUG: API_KEY from env: {('SET (len=' + str(len(api_key_test)) + ')') if api_key_test else 'NOT SET'}")
        
        # Prepare request parameters
        # Use tuple format: (connect_timeout, read_timeout) to ensure read timeout is respected
        kwargs = {
            'timeout': (60, timeout),  # 60s connect, specified read timeout
            'verify': False  # For self-signed certificates
        }
        
        # Add query parameters
        if query_params:
            kwargs['params'] = query_params
        
        # Prepare headers - only set Content-Type if we have data
        request_headers = {}
        if data:
            request_headers['Content-Type'] = 'application/json'
            kwargs['json'] = data
        
        # Add API key for backend_host authentication
        api_key = os.getenv('API_KEY')
        if api_key:
            request_headers['X-API-Key'] = api_key
            print(f"[@utils:routeUtils:proxy_to_host_with_params] ✅ API key added (length: {len(api_key)})")
        else:
            print(f"[@utils:routeUtils:proxy_to_host_with_params] ⚠️ WARNING: API_KEY not found in environment - requests will fail!")
        
        if headers:
            request_headers.update(headers)
        
        if request_headers:
            kwargs['headers'] = request_headers
        
        # Make the request to the host
        if method.upper() == 'GET':
            response = requests.get(full_url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(full_url, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(full_url, **kwargs)
        elif method.upper() == 'DELETE':
            response = requests.delete(full_url, **kwargs)
        else:
            return {
                'success': False,
                'error': f'Unsupported HTTP method: {method}'
            }, 400
        
        # Return the host's response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {
                'success': False,
                'error': 'Invalid JSON response from host',
                'raw_response': response.text[:500]  # First 500 chars for debugging
            }
        
        return response_data, response.status_code
        
    except requests.exceptions.Timeout as e:
        error_msg = f'Request to host timed out (timeout={timeout}s)'
        print(f"[@utils:routeUtils:proxy_to_host_with_params] ⚠️ TIMEOUT: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host_with_params] ⚠️ Error: {str(e)}")
        return {
            'success': False,
            'error': error_msg
        }, 504
    except requests.exceptions.ConnectionError as e:
        error_msg = f'Could not connect to host: {str(e)}'
        print(f"[@utils:routeUtils:proxy_to_host_with_params] ❌ CONNECTION ERROR: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host_with_params] ❌ Error details: {str(e)}")
        print(f"[@utils:routeUtils:proxy_to_host_with_params] ❌ Host info: {host_info.get('host_name', 'unknown')}")
        return {
            'success': False,
            'error': error_msg
        }, 503
    except Exception as e:
        error_msg = f'Proxy error: {str(e)}'
        print(f"[@utils:routeUtils:proxy_to_host_with_params] 💥 UNEXPECTED ERROR: {full_url}")
        print(f"[@utils:routeUtils:proxy_to_host_with_params] 💥 Error type: {type(e).__name__}")
        print(f"[@utils:routeUtils:proxy_to_host_with_params] 💥 Error details: {str(e)}")
        import traceback
        print(f"[@utils:routeUtils:proxy_to_host_with_params] 💥 Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': error_msg
        }, 500 


def proxy_to_host_direct(host_info, endpoint, method='GET', data=None, timeout=30, headers=None):
    """
    Proxy a request to the specified host's endpoint using provided host_info
    (for use in background threads where Flask request context is not available)
    
    Args:
        host_info: Host information dict (required)
        endpoint: The host endpoint to call (e.g., '/host/web/executeCommand')
        method: HTTP method ('GET', 'POST', etc.)
        data: Request data for POST requests
        timeout: Request timeout in seconds (default: 30)
        headers: Additional headers to include in the request (dict)
    
    Returns:
        Tuple of (response_data, status_code)
    """
    try:
        if not host_info:
            return {
                'success': False,
                'error': 'Host information required'
            }, 400
        
        # Use centralized API URL builder to construct the proper URL
        from shared.src.lib.utils.build_url_utils import buildHostUrl
        full_url = buildHostUrl(host_info, endpoint)
        
        if not full_url:
            return {
                'success': False,
                'error': 'Failed to build host URL'
            }, 500
        
        print(f"[@utils:routeUtils:proxy_to_host_direct] Proxying {method} {endpoint} to {full_url}")
        
        # Prepare request parameters
        # Use tuple format: (connect_timeout, read_timeout) to ensure read timeout is respected
        kwargs = {
            'timeout': (60, timeout),  # 60s connect, specified read timeout
            'verify': False  # For self-signed certificates
        }
        
        # Prepare headers
        request_headers = {'Content-Type': 'application/json'}
        
        # Add API key for backend_host authentication
        api_key = os.getenv('API_KEY')
        if api_key:
            request_headers['X-API-Key'] = api_key
        
        if headers:
            request_headers.update(headers)
        
        if data:
            kwargs['json'] = data
        
        kwargs['headers'] = request_headers
        
        # Make the request to the host
        if method.upper() == 'GET':
            response = requests.get(full_url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(full_url, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(full_url, **kwargs)
        elif method.upper() == 'DELETE':
            response = requests.delete(full_url, **kwargs)
        else:
            return {
                'success': False,
                'error': f'Unsupported HTTP method: {method}'
            }, 400
        
        # Return the host's response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {
                'success': False,
                'error': 'Invalid JSON response from host',
                'raw_response': response.text[:500]  # First 500 chars for debugging
            }
        
        return response_data, response.status_code
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': 'Request to host timed out'
        }, 504
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': 'Could not connect to host'
        }, 503
    except Exception as e:
        return {
            'success': False,
            'error': f'Proxy error: {str(e)}'
        }, 500 