import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ScriptTools:
    """Script execution tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Python script on a device
        
        REUSES existing /server/script/execute endpoint (same as frontend)
        Pattern from useScript.ts lines 247-301
        
        Args:
            params: {
                'script_name': str (REQUIRED) - Script filename (e.g., 'my_script.py'),
                'host_name': str (REQUIRED) - Host where device is located,
                'device_id': str (REQUIRED) - Device identifier,
                'parameters': str (OPTIONAL) - CLI parameters as string (e.g., '--param1 value1 --param2 value2'),
                'team_id': str (OPTIONAL) - Team ID for security
            }
            
        Returns:
            MCP-formatted response with script execution results
        """
        script_name = params.get('script_name')
        host_name = params.get('host_name')
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        parameters = params.get('parameters', '')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not script_name:
            return {"content": [{"type": "text", "text": "Error: script_name is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
        # Build request - SAME format as frontend (useScript.ts lines 247-255)
        data = {
            'script_name': script_name,
            'host_name': host_name,
            'device_id': device_id
        }
        
        if parameters and parameters.strip():
            data['parameters'] = parameters.strip()
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useScript.ts line 257)
        print(f"[@MCP:execute_script] Calling /server/script/execute for '{script_name}'")
        result = self.api.post('/server/script/execute', data=data, params=query_params)
        
        # Check if async execution (returns task_id) - SAME as frontend (useScript.ts line 265)
        if result.get('task_id'):
            task_id = result['task_id']
            print(f"[@MCP:execute_script] Async execution started with task_id: {task_id}")
            
            # POLL for completion - SAME pattern as frontend (useScript.ts lines 269-279)
            return self._poll_script_completion(task_id, host_name, script_name)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('stderr') or result.get('error') or 'Script execution failed'
            return {"content": [{"type": "text", "text": f"❌ Script failed: {error_msg}"}], "isError": True}
        
        # Sync result - return directly (useScript.ts lines 283-300)
        print(f"[@MCP:execute_script] Sync execution completed")
        
        # Extract script_success marker (useScript.ts lines 288-293)
        script_success = result.get('script_success')
        if script_success is None and result.get('stdout'):
            if 'SCRIPT_SUCCESS:true' in result['stdout']:
                script_success = True
            elif 'SCRIPT_SUCCESS:false' in result['stdout']:
                script_success = False
        
        # Format response
        response_text = f"✅ Script '{script_name}' completed\n"
        response_text += f"Exit code: {result.get('exit_code', 0)}\n"
        if script_success is not None:
            response_text += f"Test result: {'PASSED' if script_success else 'FAILED'}\n"
        if result.get('report_url'):
            response_text += f"\n📄 Report: {result['report_url']}"
        
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": not result.get('success', False),
            "result": result
        }
    
    def _poll_script_completion(self, task_id: str, host_name: str, script_name: str, max_wait: int = 7200) -> Dict[str, Any]:
        """
        Poll script execution until complete
        
        REUSES existing /server/script/status/<task_id> endpoint (same as frontend)
        Pattern from useScript.ts lines 161-220
        """
        poll_interval = 10  # 10 seconds - less frequent for long scripts (useScript.ts line 166)
        elapsed = 0
        
        print(f"[@MCP:poll_script] Polling for task {task_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint - SAME as frontend (useScript.ts line 174)
            status = self.api.get(f'/server/script/status/{task_id}')
            
            # Check if we got a valid response (useScript.ts line 177)
            if status.get('success') and status.get('task'):
                task = status['task']
                current_status = task.get('status')
                
                if current_status == 'completed':
                    print(f"[@MCP:poll_script] Script completed after {elapsed}s")
                    task_result = task.get('result', {})
                    
                    # Extract results - SAME as frontend (useScript.ts lines 181-189)
                    success = task_result.get('success', False)
                    exit_code = task_result.get('exit_code', 0)
                    script_success = task_result.get('script_success')
                    report_url = task_result.get('report_url', '')
                    
                    response_text = f"✅ Script '{script_name}' completed\n"
                    response_text += f"Exit code: {exit_code}\n"
                    if script_success is not None:
                        response_text += f"Test result: {'PASSED' if script_success else 'FAILED'}\n"
                    if report_url:
                        response_text += f"\n📄 Report: {report_url}"
                    
                    return {
                        "content": [{"type": "text", "text": response_text}],
                        "isError": not success,
                        "result": task_result
                    }
                
                elif current_status == 'failed':
                    print(f"[@MCP:poll_script] Script failed after {elapsed}s")
                    error = task.get('error', 'Script execution failed')
                    return {"content": [{"type": "text", "text": f"❌ Script failed: {error}"}], "isError": True}
                
                elif current_status in ['pending', 'running']:
                    print(f"[@MCP:poll_script] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_script] Script execution timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Script execution timed out after {max_wait}s"}], "isError": True}

