"""
Action Tools - Device action execution

Execute remote commands, ADB commands, web actions, and desktop actions.
"""

import json
import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ActionTools:
    """Device action execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def list_actions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available actions for a device
        
        REUSES existing /server/system/device-actions endpoint
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with categorized list of available actions
        """
        device_id = params.get('device_id')
        host_name = params.get('host_name')
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
        
        # Call EXISTING endpoint
        print(f"[@MCP:list_actions] Calling /server/system/getDeviceActions")
        result = self.api.get('/server/system/getDeviceActions', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list actions')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response - group actions by category
        device_action_types = result.get('device_action_types', {})
        device_model = result.get('device_model', 'unknown')
        
        if not device_action_types:
            return {"content": [{"type": "text", "text": f"No actions available for {device_model} device"}], "isError": False}
        
        response_text = f"Available actions for {device_model} ({device_id}):\n\n"
        
        if device_model in ['host_vnc', 'web']:
            response_text += "💡 WEB DEVICE - See execute_device_action tool description for detailed usage\n\n"
        
        for category, actions in device_action_types.items():
            if not actions:
                continue
            response_text += f"**{category.upper()}** ({len(actions)} actions):\n"
            for action in actions[:10]:  # Limit to first 10 per category
                label = action.get('label', action.get('command', 'unknown'))
                command = action.get('command', 'unknown')
                params_dict = action.get('params', {})
                description = action.get('description', '')
                
                response_text += f"  {label} (command: {command})\n"
                
                if params_dict:
                    response_text += f"    params: {params_dict}\n"
                if description:
                    response_text += f"    {description}\n"
            
            if len(actions) > 10:
                response_text += f"  ... and {len(actions) - 10} more\n"
            response_text += "\n"
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,
            "device_action_types": device_action_types  # Include full data for programmatic use
        }
    
    def execute_device_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute batch of actions on a device
        
        Supports: remote commands (IR, CEC, etc.), ADB commands, web actions, desktop automation.
        
        REUSES existing /server/action/executeBatch endpoint (same as frontend)
        
        ⚠️ CRITICAL - COMMAND VALIDATION:
        - ALWAYS call list_actions() FIRST to get valid commands for your device
        - ONLY use commands returned by list_actions() - invalid commands will FAIL
        - For android_mobile/android_tv: Use 'click_element' with text (NOT 'click_element_by_index')
        - For web: Use 'click_element' with text/selector
        - Example: {"command": "click_element", "params": {"element_id": "Home Tab"}}
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (OPTIONAL),
                'team_id': str (REQUIRED),
                'actions': List[Dict] (REQUIRED) - [{
                    'command': str (MUST be from list_actions() output),
                    'params': dict (structure depends on command),
                    'delay': int (ms, optional)
                }],
                'retry_actions': List[Dict] (OPTIONAL),
                'failure_actions': List[Dict] (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with execution results
        """
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        actions = params.get('actions', [])
        retry_actions = params.get('retry_actions', [])
        failure_actions = params.get('failure_actions', [])
        
        # Validate required parameters
        if not actions:
            return {"content": [{"type": "text", "text": "Error: actions array is required"}], "isError": True}
        
        # Build request - SAME format as frontend (useAction.ts line 166-172)
        data = {
            'device_id': device_id,
            'host_name': host_name,
            'actions': actions,
            'retry_actions': retry_actions,
            'failure_actions': failure_actions
        }
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useAction.ts line 163)
        print(f"[@MCP:execute_device_action] Calling /server/action/executeBatch")
        result = self.api.post('/server/action/executeBatch', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Action execution failed')
            return {"content": [{"type": "text", "text": f"Action execution failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id) - SAME as frontend (useAction.ts line 188)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:execute_device_action] Async execution started: {execution_id}")
            
            # POLL for completion - SAME pattern as frontend (useAction.ts line 200-246)
            return self._poll_action_completion(execution_id, device_id, host_name, team_id)
        
        # Sync result - strip verbose fields and return concise response
        print(f"[@MCP:execute_device_action] Sync execution completed")
        passed = result.get('passed_count', 0)
        total = result.get('total_count', 0)
        failed = result.get('failed_count', 0)
        execution_time = result.get('execution_time_ms', 0)
        
        concise_result = {
            'success': result.get('success', False),
            'message': f"✅ {passed}/{total} passed ({execution_time}ms)" if passed == total else f"❌ {passed}/{total} passed, {failed} failed",
            'passed_count': passed,
            'total_count': total,
            'failed_count': failed,
            'execution_time_ms': execution_time
        }
        
        return {"content": [{"type": "text", "text": json.dumps(concise_result)}], "isError": failed > 0}
    
    def _poll_action_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, max_wait: int = 180) -> Dict[str, Any]:
        """
        Poll action execution until complete
        
        REUSES existing /server/action/execution/<id>/status API (same as frontend)
        Pattern from useAction.ts lines 200-246
        """
        poll_interval = 1  # 1 second (same as frontend line 206)
        elapsed = 0
        
        print(f"[@MCP:poll_action] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (useAction.ts line 195)
            status = self.api.get(
                f'/server/action/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_action] Action execution completed after {elapsed}s")
                result = status.get('result', {})
                passed = result.get('passed_count', 0)
                total = result.get('total_count', 0)
                failed = result.get('failed_count', 0)
                execution_time = result.get('execution_time_ms', 0)
                
                # Build concise result (strip verbose logs/screenshots)
                concise_result = {
                    'passed_count': passed,
                    'total_count': total,
                    'failed_count': failed,
                    'execution_time_ms': execution_time
                }
                
                # Check if any actions failed
                if failed > 0 or passed < total:
                    message = f"❌ {passed}/{total} passed, {failed} failed"
                    print(f"[@MCP:poll_action] {message}")
                    error_details = result.get('error', '') or result.get('message', '')
                    if error_details:
                        concise_result['error'] = error_details[:200]  # Truncate error
                    return {
                        "content": [{"type": "text", "text": json.dumps({"success": False, "message": message, **concise_result})}],
                        "isError": True
                    }
                
                message = f"✅ {passed}/{total} passed ({execution_time}ms)"
                print(f"[@MCP:poll_action] {message}")
                return {"content": [{"type": "text", "text": json.dumps({"success": True, "message": message, **concise_result})}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_action] Action execution failed after {elapsed}s")
                error = status.get('error', 'Action execution failed')
                return {"content": [{"type": "text", "text": f"❌ Action execution failed: {error}"}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                print(f"[@MCP:poll_action] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_action] Action execution timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Action execution timed out after {max_wait}s"}], "isError": True}
