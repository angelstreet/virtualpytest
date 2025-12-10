import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class ScriptTools:
    """Script execution and listing tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def _filter_result_for_mcp(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter script execution result to only include essential fields.
        Reduces token usage by ~99% (22k -> 200 tokens) by excluding verbose stdout/stderr.
        
        Full logs are available via logs_url if needed for debugging.
        """
        if not result:
            return {}
        
        # Essential fields only - exclude stdout/stderr (thousands of tokens)
        return {
            'script_name': result.get('script_name'),
            'device_id': result.get('device_id'),
            'exit_code': result.get('exit_code'),
            'script_success': result.get('script_success'),
            'execution_time_ms': result.get('execution_time_ms'),
            'report_url': result.get('report_url'),
            'logs_url': result.get('logs_url'),
            'parameters': result.get('parameters'),
        }
    
    def list_scripts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all available Python scripts
        
        REUSES existing /server/script/list endpoint (same as frontend)
        Pattern from server_script_routes.py line 284
        
        Args:
            params: {
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with list of scripts
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (RunTests.tsx line 331)
        print(f"[@MCP:list_scripts] Calling /server/script/list")
        result = self.api.get('/server/script/list', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list scripts')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response
        scripts = result.get('scripts', [])
        if not scripts:
            return {"content": [{"type": "text", "text": "No scripts found"}], "isError": False}
        
        scripts_dir = result.get('scripts_directory', 'unknown')
        response_text = f"📋 Found {len(scripts)} script(s) in {scripts_dir}:\n\n"
        
        for script in scripts[:30]:  # Limit to first 30
            response_text += f"- {script}\n"
        
        if len(scripts) > 30:
            response_text += f"\n... and {len(scripts) - 30} more"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False, "scripts": scripts}
    
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
        device_id = params.get('device_id')
        parameters = params.get('parameters', '')
        userinterface_name = params.get('userinterface_name', '')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not script_name:
            return {"content": [{"type": "text", "text": "Error: script_name is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
        # Build parameters string (SAME as RunTests.tsx lines 427-470)
        # The frontend always appends --host and --device at the end
        param_parts = []
        
        # Add user-provided parameters first
        if parameters and parameters.strip():
            param_parts.append(parameters.strip())
        
        # Add userinterface_name if provided (SAME as RunTests.tsx line 440-441)
        if userinterface_name:
            param_parts.append(f'--userinterface {userinterface_name}')
        
        # Always add --host and --device at the end (SAME as RunTests.tsx lines 461-467)
        param_parts.append(f'--host {host_name}')
        param_parts.append(f'--device {device_id}')
        
        final_parameters = ' '.join(param_parts)
        
        # Build request - SAME format as frontend (useScript.ts lines 247-255)
        data = {
            'script_name': script_name,
            'host_name': host_name,
            'device_id': device_id,
            'parameters': final_parameters  # Send the complete parameter string
        }
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as frontend (useScript.ts line 257)
        print(f"[@MCP:execute_script] Calling /server/script/execute for '{script_name}'")
        print(f"[@MCP:execute_script] Parameters: {final_parameters}")
        result = self.api.post('/server/script/execute', data=data, params=query_params)
        
        # Check if async execution (returns task_id) - SAME as frontend (useScript.ts line 265)
        if result.get('task_id'):
            task_id = result['task_id']
            print(f"[@MCP:execute_script] Async execution started with task_id: {task_id}")
            
            # POLL for completion - SAME pattern as frontend (useScript.ts lines 269-279)
            return self._poll_script_completion(task_id, host_name, script_name)
        
        # Check for errors - use exit_code since 'success' is not returned by script executor
        exit_code = result.get('exit_code', 0)
        if exit_code != 0:
            error_msg = result.get('stderr') or result.get('error') or f'Script execution failed with exit code {exit_code}'
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
        
        # Format response (use HTML color tags)
        response_text = f"✅ Script '{script_name}' completed\n"
        response_text += f"Exit code: {exit_code}\n"
        if script_success is not None:
            if script_success:
                status = '<span style="color: #22c55e; font-weight: 600;">PASSED</span>'
            else:
                status = '<span style="color: #ef4444; font-weight: 600;">FAILED</span>'
            response_text += f"Test result: {status}\n"
        if result.get('report_url'):
            response_text += f"\n📄 Report: {result['report_url']}"
        
        # Return filtered result (no stdout/stderr) to reduce token usage
        return {
            "content": [{"type": "text", "text": response_text}],
            "isError": False,  # exit_code 0 = tool execution successful
            "result": self._filter_result_for_mcp(result)
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
                    # Determine success: exit_code 0 = process ran successfully
                    # Note: script_success indicates test pass/fail, NOT tool execution success
                    exit_code = task_result.get('exit_code', 0)
                    script_success = task_result.get('script_success')
                    report_url = task_result.get('report_url', '')
                    
                    # Tool execution is successful if process exited cleanly (exit_code 0)
                    is_tool_error = exit_code != 0
                    
                    response_text = f"✅ Script '{script_name}' completed\n"
                    response_text += f"Exit code: {exit_code}\n"
                    if script_success is not None:
                        if script_success:
                            status = '<span style="color: #22c55e; font-weight: 600;">PASSED</span>'
                        else:
                            status = '<span style="color: #ef4444; font-weight: 600;">FAILED</span>'
                        response_text += f"Test result: {status}\n"
                    if report_url:
                        response_text += f"\n📄 Report: {report_url}"
                    
                    # Return filtered result (no stdout/stderr) to reduce token usage
                    return {
                        "content": [{"type": "text", "text": response_text}],
                        "isError": is_tool_error,
                        "result": self._filter_result_for_mcp(task_result)
                    }
                
                elif current_status == 'failed':
                    print(f"[@MCP:poll_script] Script failed after {elapsed}s")
                    error = task.get('error', 'Script execution failed')
                    return {"content": [{"type": "text", "text": f"❌ Script failed: {error}"}], "isError": True}
                
                elif current_status in ['pending', 'running']:
                    print(f"[@MCP:poll_script] Status: {current_status} - {elapsed}s elapsed")
        
        print(f"[@MCP:poll_script] Script execution timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Script execution timed out after {max_wait}s"}], "isError": True}

