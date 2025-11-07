"""
Verification Tools - Device state verification

Verify UI elements, video playback, text, and other device states.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class VerificationTools:
    """Device state verification tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def list_verifications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available verification types for a device
        
        REUSES existing /server/system/device-actions endpoint (returns both actions and verifications)
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with categorized list of available verifications
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        if not device_id:
            return {"content": [{"type": "text", "text": "Error: device_id is required"}], "isError": True}
        
        query_params = {
            'host_name': host_name,
            'device_id': device_id,
            'team_id': team_id
        }
        
        # Call EXISTING endpoint (same as list_actions - returns both)
        print(f"[@MCP:list_verifications] Calling /server/system/getDeviceActions")
        result = self.api.get('/server/system/getDeviceActions', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list verifications')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response - group verifications by type
        device_verification_types = result.get('device_verification_types', {})
        device_model = result.get('device_model', 'unknown')
        
        if not device_verification_types:
            return {"content": [{"type": "text", "text": f"No verifications available for {device_model} device"}], "isError": False}
        
        response_text = f"📋 Available verifications for {device_model} ({device_id}):\n\n"
        
        for category, verifications in device_verification_types.items():
            if not verifications:
                continue
            response_text += f"**{category.upper()}** ({len(verifications)} verifications):\n"
            
            # Handle both dict and list structures
            if isinstance(verifications, dict):
                items = list(verifications.items())[:10]
                for method_name, method_info in items:
                    description = method_info.get('description', '')
                    params_dict = method_info.get('params', {})
                    
                    response_text += f"  • {method_name}\n"
                    if description:
                        response_text += f"    {description}\n"
                    if params_dict:
                        response_text += f"    params: {params_dict}\n"
                
                if len(verifications) > 10:
                    response_text += f"  ... and {len(verifications) - 10} more\n"
            elif isinstance(verifications, list):
                for verification in verifications[:10]:
                    label = verification.get('label', verification.get('command', 'unknown'))
                    command = verification.get('command', 'unknown')
                    params_dict = verification.get('params', {})
                    description = verification.get('description', '')
                    
                    response_text += f"  • {label} (command: {command})\n"
                    if params_dict:
                        response_text += f"    params: {params_dict}\n"
                    if description:
                        response_text += f"    {description}\n"
                
                if len(verifications) > 10:
                    response_text += f"  ... and {len(verifications) - 10} more\n"
            
            response_text += "\n"
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
            "device_verification_types": device_verification_types  # Include full data for programmatic use
        }
    
    def verify_device_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify device state with batch verifications
        
        Supports: image verification, text verification, ADB verification, video analysis.
        
        REUSES existing /server/verification/executeBatch endpoint (same as frontend)
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (OPTIONAL),
                'team_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED),
                'verifications': List[Dict] (REQUIRED) - [{
                    'type': str (image/text/adb/video),
                    'method': str (command name),
                    'params': dict,
                    'expected': any
                }],
                'tree_id': str (OPTIONAL),
                'node_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with verification results and evidence
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name = params.get('userinterface_name')
        verifications = params.get('verifications', [])
        tree_id = params.get('tree_id')
        node_id = params.get('node_id')
        
        # Validate required parameters
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        if not verifications:
            return {"content": [{"type": "text", "text": "Error: verifications array is required"}], "isError": True}
        
        # Add userinterface_name to each verification for proper reference resolution (SAME as frontend line 226-229)
        verifications_with_userinterface = [
            {**v, 'userinterface_name': userinterface_name} for v in verifications
        ]
        
        # Build request - SAME format as frontend (useVerification.ts line 250-257)
        data = {
            'device_id': device_id,
            'host_name': host_name,
            'userinterface_name': userinterface_name,
            'verifications': verifications_with_userinterface
        }
        
        if tree_id:
            data['tree_id'] = tree_id
        if node_id:
            data['node_id'] = node_id
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useVerification.ts line 247)
        print(f"[@MCP:verify_device_state] Calling /server/verification/executeBatch")
        result = self.api.post('/server/verification/executeBatch', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Verification failed')
            return {"content": [{"type": "text", "text": f"Verification failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id) - SAME as frontend (useVerification.ts line 272)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:verify_device_state] Async execution started: {execution_id}")
            
            # POLL for completion - SAME pattern as frontend (useVerification.ts line 278-306)
            return self._poll_verification_completion(execution_id, device_id, host_name, team_id)
        
        # Sync result - return directly
        print(f"[@MCP:verify_device_state] Sync execution completed")
        return self.formatter.format_api_response(result)
    
    def dump_ui_elements(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dump UI elements from current device screen
        
        REUSES existing verification endpoints
        
        Args:
            params: {
                'device_id': str (OPTIONAL - defaults to 'device1'),
                'host_name': str (OPTIONAL - defaults to 'sunri-pi1'),
                'team_id': str (OPTIONAL),
                'platform': str (OPTIONAL - 'mobile', 'web', 'tv')
            }
            
        Returns:
            MCP-formatted response with UI elements array
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        platform = params.get('platform', 'mobile')
        
        query_params = {
            'device_id': device_id,
            'host_name': host_name,
            'team_id': team_id,
            'platform': platform
        }
        
        print(f"[@MCP:dump_ui_elements] Dumping UI for {device_id} on {host_name}")
        
        # Use /server/remote/dumpUi endpoint (proxies to backend_host)
        result = self.api.post('/server/remote/dumpUi', data=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to dump UI elements')
            return {"content": [{"type": "text", "text": f"❌ UI dump failed: {error_msg}"}], "isError": True}
        
        # Return raw output from API - backend already formats it correctly
        raw_output = result.get('output', '')
        
        return {
            "content": [{"type": "text", "text": raw_output}],
            "isError": False,
            "elements": result.get('elements', []),
            "raw_result": result
        }
    
    def _poll_verification_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, max_wait: int = 30) -> Dict[str, Any]:
        """
        Poll verification execution until complete
        
        REUSES existing /server/verification/execution/<id>/status API (same as frontend)
        Pattern from useVerification.ts lines 278-306
        """
        poll_interval = 1  # 1 second (same as frontend line 283)
        elapsed = 0
        
        print(f"[@MCP:poll_verification] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (useVerification.ts line 273)
            status = self.api.get(
                f'/server/verification/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_verification] Verification completed successfully after {elapsed}s")
                result = status.get('result', {})
                passed = result.get('passed_count', 0)
                total = result.get('total_count', 0)
                message = f"Verification completed: {passed}/{total} passed"
                return {"content": [{"type": "text", "text": f"✅ {message}"}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_verification] Verification failed after {elapsed}s")
                error = status.get('error', 'Verification failed')
                return {"content": [{"type": "text", "text": f"❌ Verification failed: {error}"}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                print(f"[@MCP:poll_verification] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_verification] Verification timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Verification timed out after {max_wait}s"}], "isError": True}

