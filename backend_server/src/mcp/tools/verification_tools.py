"""
Verification Tools - Device state verification

Verify UI elements, video playback, text, and other device states.
"""

from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from shared.src.lib.config.constants import APP_CONFIG


class VerificationTools:
    """Device state verification tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
    
    def verify_device_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify device state with batch verifications
        
        Supports: image verification, text verification, ADB verification, video analysis.
        Returns evidence screenshots and verification results.
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'team_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED),
                'verifications': List[Dict] (REQUIRED) - [{
                    'type': str (image/text/adb/video),
                    'method': str (command name),
                    'params': dict,
                    'expected': any
                }],
                'tree_id': str (OPTIONAL),
                'node_id': str (OPTIONAL),
                'host_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with verification results and evidence
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name = params.get('userinterface_name')
        verifications = params.get('verifications', [])
        tree_id = params.get('tree_id')
        node_id = params.get('node_id')
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        
        # Validate required parameters
        if not userinterface_name:
            return {"content": [{"type": "text", "text": "Error: userinterface_name is required"}], "isError": True}
        if not verifications:
            return {"content": [{"type": "text", "text": "Error: verifications array is required"}], "isError": True}
        
        # Build request
        data = {
            'device_id': device_id,
            'userinterface_name': userinterface_name,
            'verifications': verifications
        }
        
        if tree_id:
            data['tree_id'] = tree_id
        if node_id:
            data['node_id'] = node_id
        if host_name:
            data['host_name'] = host_name
        
        query_params = {'team_id': team_id}
        
        # Call API
        result = self.api.post('/server/verification/executeBatch', data=data, params=query_params)
        
        return result

