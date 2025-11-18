"""
Device Tools - Device information and status

Get device information, capabilities, and execution status.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class DeviceTools:
    """Device information and status tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def get_device_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get device information and capabilities
        
        Returns device list with capabilities, controllers, and status.
        
        Args:
            params: {
                'device_id': str (OPTIONAL) - Specific device, or omit for all devices,
                'host_name': str (OPTIONAL) - Filter by host
            }
            
        Returns:
            MCP-formatted response with device information
        """
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        
        # Build request
        query_params = {}
        if device_id:
            query_params['device_id'] = device_id
        if host_name:
            query_params['host_name'] = host_name
        
        # Call API (auto-proxied from /server/devices to /host/devices)
        result = self.api.get('/server/devices', params=query_params)
        
        return self.formatter.format_api_response(result)
    
    def get_compatible_hosts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get hosts and devices compatible with a userinterface
        
        ⚠️ CRITICAL: Use this tool BEFORE execute_edge, navigate_to_node, 
        execute_testcase, or generate_test_graph to find compatible hosts/devices.
        
        This tool automatically filters hosts based on the userinterface's device models
        and returns the first compatible host/device for immediate use.
        
        Args:
            params: {
                'userinterface_name': str (REQUIRED) - Interface name (e.g., 'sauce-demo')
            }
            
        Returns:
            MCP-formatted response with:
            - compatible_hosts: List of hosts with compatible devices
            - recommended: Auto-selected first host and device
            - models: Device models required by the interface
            
        Example:
            get_compatible_hosts(userinterface_name='sauce-demo')
            # Returns: recommended_host='your-mac', recommended_device='device1'
        """
        userinterface_name = params.get('userinterface_name')
        
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "❌ Error: userinterface_name is required"}], "isError": True}
        
        # Get userinterface by name to extract models
        ui_result = self.api.get(f'/server/userinterface/getUserInterfaceByName/{userinterface_name}', params={'team_id': APP_CONFIG['DEFAULT_TEAM_ID']})
        
        # Check if userinterface exists
        if not ui_result or 'error' in ui_result:
            return {"content": [{"type": "text", "text": f"❌ Error: Userinterface '{userinterface_name}' not found"}], "isError": True}
        
        models = ui_result.get('models', [])
        
        if not models:
            return {"content": [{"type": "text", "text": f"❌ Error: Userinterface '{userinterface_name}' has no device models defined"}], "isError": True}
        
        # Get all hosts
        hosts_result = self.api.get('/server/system/getAllHosts')
        
        if not hosts_result.get('success'):
            return {"content": [{"type": "text", "text": "❌ Error: Failed to get hosts"}], "isError": True}
        
        all_hosts = hosts_result.get('hosts', [])
        
        # Filter hosts to only those with compatible devices
        compatible_hosts = []
        for host in all_hosts:
            compatible_devices = []
            for device in host.get('devices', []):
                device_model = device.get('device_model')
                device_capabilities = device.get('device_capabilities', {})
                
                # Check exact model match
                if device_model in models:
                    compatible_devices.append(device)
                # Check capability match (e.g., device with 'web' capability matches 'web' model)
                elif any(device_capabilities.get(model) for model in models):
                    compatible_devices.append(device)
            
            if compatible_devices:
                compatible_hosts.append({
                    'host_name': host.get('host_name'),
                    'host_url': host.get('host_url'),
                    'status': host.get('status', 'online'),
                    'devices': compatible_devices
                })
        
        # Check if any compatible hosts found
        if not compatible_hosts:
            return {"content": [{
                "type": "text",
                "text": f"❌ No compatible hosts found for userinterface '{userinterface_name}'\n\n"
                        f"Required device models: {', '.join(models)}\n\n"
                        f"💡 Make sure at least one host is running with a compatible device:\n"
                        f"   1. Start backend_host: ./scripts/launch_virtualhost.sh\n"
                        f"   2. Verify with: get_device_info()\n"
                        f"   3. Check host has device matching one of: {models}"
            }], "isError": True}
        
        # Auto-select first compatible host and device
        first_host = compatible_hosts[0]
        first_device = first_host['devices'][0]
        
        # Build response
        response_text = f"✅ Found {len(compatible_hosts)} compatible host(s) for '{userinterface_name}'\n\n"
        response_text += f"🎯 RECOMMENDED (Auto-selected):\n"
        response_text += f"   Host: {first_host['host_name']}\n"
        response_text += f"   Device: {first_device.get('device_name', 'Unknown')} ({first_device.get('device_model')})\n"
        response_text += f"   Device ID: {first_device.get('device_id')}\n\n"
        response_text += f"📋 Use these values in your next operation:\n"
        response_text += f"   host_name='{first_host['host_name']}'\n"
        response_text += f"   device_id='{first_device.get('device_id')}'\n\n"
        
        if len(compatible_hosts) > 1:
            response_text += f"📌 Other compatible hosts:\n"
            for host in compatible_hosts[1:]:
                response_text += f"   • {host['host_name']} ({len(host['devices'])} device(s))\n"
        
        response_text += f"\n💡 Interface requires models: {', '.join(models)}"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False}
    
    def get_execution_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Poll execution status for async operations
        
        Check status of actions, testcases, or other async operations.
        
        Args:
            params: {
                'execution_id': str (REQUIRED) - Execution ID from async operation,
                'operation_type': str (OPTIONAL) - 'action', 'testcase', 'ai' for specific endpoints
            }
            
        Returns:
            MCP-formatted response with execution status and results
        """
        execution_id = params.get('execution_id')
        operation_type = params.get('operation_type', 'action')
        
        # Validate required parameters
        if not execution_id:
            return {"content": [{"type": "text", "text": "Error: execution_id is required"}], "isError": True}
        
        # Call appropriate endpoint based on operation type
        if operation_type == 'action':
            endpoint = f'/host/action/getStatus/{execution_id}'
        elif operation_type == 'testcase':
            endpoint = f'/host/testcase/getStatus/{execution_id}'
        elif operation_type == 'ai':
            endpoint = f'/host/ai/getExecutionStatus/{execution_id}'
        else:
            return format_tool_result({'success': False, 'error': f'Unknown operation_type: {operation_type}'})
        
        # Call API
        result = self.api.get(endpoint)
        
        return self.formatter.format_api_response(result)

