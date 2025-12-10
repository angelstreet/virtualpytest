"""
TestCase Tools - Test case operations

Execute, save, load, and list test cases.
"""

import time
from typing import Dict, Any
from ..utils.api_client import MCPAPIClient
from ..utils.mcp_formatter import MCPFormatter
from shared.src.lib.config.constants import APP_CONFIG


class TestCaseTools:
    """Test case execution and management tools"""
    
    def __init__(self, api_client: MCPAPIClient):
        self.api = api_client
        self.formatter = MCPFormatter()
    
    def execute_testcase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test case by name (or graph for unsaved testcases)
        
        ⚠️ CRITICAL: Host/Device Selection
        - If user explicitly specifies host_name/device_id: Use those values directly
        - Otherwise: Call get_compatible_hosts(userinterface_name='...') FIRST to find compatible hosts
        - DO NOT use default values blindly without checking compatibility
        
        REUSES existing /server/testcase/execute endpoint (same as frontend)
        Pattern from server_testcase_routes.py line 167
        
        Workflow (when host NOT specified by user):
            1. Call get_compatible_hosts(userinterface_name='your_ui')
            2. Use recommended host_name and device_id from response
            3. Call execute_testcase with those values
        
        Workflow (when user specifies host):
            1. User says "use host X with device Y"
            2. Call execute_testcase directly with host_name='X', device_id='Y'
        
        Args:
            params: {
                'testcase_name': str (REQUIRED) - Test case name like 'Login Flow Test',
                'host_name': str (REQUIRED),
                'device_id': str (REQUIRED),
                'userinterface_name': str (REQUIRED),
                'graph_json': Dict (OPTIONAL) - For unsaved/temporary testcases only,
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with execution results
        """
        testcase_name = params.get('testcase_name')
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        graph_json = params.get('graph_json')
        userinterface_name = params.get('userinterface_name', '')
        
        # Validate required parameters
        if not testcase_name:
            return {"content": [{"type": "text", "text": "Error: testcase_name is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
        # If no graph_json provided, load by name
        if not graph_json:
            print(f"[@MCP:execute_testcase] Loading testcase '{testcase_name}' by name")
            
            # Step 1: List all testcases
            list_result = self.api.get('/server/testcase/list', params={'team_id': team_id})
            
            if not list_result.get('success'):
                error_msg = list_result.get('error', 'Failed to list test cases')
                return {"content": [{"type": "text", "text": f"❌ Failed to lookup testcase: {error_msg}"}], "isError": True}
            
            # Step 2: Find testcase by name
            testcases = list_result.get('testcases', [])
            matching_testcase = None
            for tc in testcases:
                if tc.get('testcase_name') == testcase_name:
                    matching_testcase = tc
                    break
            
            if not matching_testcase:
                return {"content": [{"type": "text", "text": f"❌ Test case '{testcase_name}' not found. Use list_testcases() to see available testcases."}], "isError": True}
            
            testcase_id = matching_testcase.get('testcase_id')
            print(f"[@MCP:execute_testcase] Found testcase with ID: {testcase_id}")
            
            # Step 3: Load the graph
            load_result = self.api.get(f'/server/testcase/{testcase_id}', params={'team_id': team_id})
            
            if not load_result.get('success'):
                error_msg = load_result.get('error', 'Failed to load test case')
                return {"content": [{"type": "text", "text": f"❌ Failed to load testcase: {error_msg}"}], "isError": True}
            
            testcase = load_result.get('testcase', {})
            graph_json = testcase.get('graph_json')
            testcase_interface = testcase.get('userinterface_name', '')
            
            if not graph_json:
                return {"content": [{"type": "text", "text": "Error: Testcase has no graph_json"}], "isError": True}
            
            # Use testcase's interface if not overridden
            if not userinterface_name:
                userinterface_name = testcase_interface
            
            print(f"[@MCP:execute_testcase] Loaded graph for '{testcase_name}' with interface '{userinterface_name}'")
            
            # Prepare inputValues with runtime values (SAME as execute_testcase_by_id)
            if 'scriptConfig' in graph_json and 'inputs' in graph_json['scriptConfig']:
                print(f"[@MCP:execute_testcase] Preparing inputValues with runtime values")
                
                for input_def in graph_json['scriptConfig']['inputs']:
                    value = input_def.get('default', '')
                    if input_def['name'] == 'host_name':
                        value = host_name
                    elif input_def['name'] == 'device_name':
                        value = device_id
                    elif input_def['name'] == 'userinterface_name':
                        value = userinterface_name
                    
                    input_def['value'] = value
                    print(f"[@MCP:execute_testcase]   Set input '{input_def['name']}' = {value}")
        
        # Build request - SAME format as frontend
        data = {
            'device_id': device_id,
            'host_name': host_name,
            'graph_json': graph_json,
            'userinterface_name': userinterface_name,
            'testcase_name': testcase_name
        }
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as server_testcase_routes.py line 167
        print(f"[@MCP:execute_testcase] Calling /server/testcase/execute for '{testcase_name}'")
        result = self.api.post('/server/testcase/execute', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Test case execution failed')
            return {"content": [{"type": "text", "text": f"❌ Execution failed: {error_msg}"}], "isError": True}
        
        # Check if async (returns execution_id)
        if result.get('execution_id'):
            execution_id = result['execution_id']
            print(f"[@MCP:execute_testcase] Async execution started: {execution_id}")
            
            # POLL for completion - same pattern as navigation/actions
            return self._poll_testcase_completion(execution_id, device_id, host_name, team_id, testcase_name)
        
        # Sync result - format similar to async completion for consistency
        print(f"[@MCP:execute_testcase] Sync execution completed")
        
        # Extract execution details
        result_success = result.get('success', False)
        result_type = result.get('result_type', 'error')
        execution_time_ms = result.get('execution_time_ms', 0)
        execution_time_s = execution_time_ms / 1000
        report_url = result.get('report_url', '')
        logs_url = result.get('logs_url', '')
        error_msg = result.get('error', '')
        
        # Format response similar to execute_script for consistency
        if result_success:
            response = f"✅ Test case '{testcase_name}' completed\n"
            response += f"Result: PASSED ({execution_time_s:.1f}s)\n"
            if report_url:
                response += f"\n📄 Report: {report_url}"
            if logs_url:
                response += f"\n📋 Logs: {logs_url}"
            return {"content": [{"type": "text", "text": response}], "isError": False}
        else:
            response = f"✅ Test case '{testcase_name}' completed\n"
            response += f"Result: FAILED ({execution_time_s:.1f}s)\n"
            if error_msg:
                response += f"Error: {error_msg}\n"
            if report_url:
                response += f"\n📄 Report: {report_url}"
            if logs_url:
                response += f"\n📋 Logs: {logs_url}"
            return {"content": [{"type": "text", "text": response}], "isError": True}
    
    def execute_testcase_by_id(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        LEGACY WRAPPER: Load and execute a saved test case by ID
        
        ⚠️ DEPRECATED: Use execute_testcase(testcase_name=...) instead
        This wrapper is kept for backward compatibility with existing MCP clients.
        
        Args:
            params: {
                'testcase_id': str (REQUIRED),
                'device_id': str (OPTIONAL),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL),
                'userinterface_name': str (OPTIONAL) - Override interface (if empty, uses testcase's interface)
            }
            
        Returns:
            MCP-formatted response with execution results
        """
        testcase_id = params.get('testcase_id')
        device_id = params.get('device_id')
        host_name = params.get('host_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        userinterface_name_override = params.get('userinterface_name', '')
        
        # Validate required parameters
        if not testcase_id:
            return {"content": [{"type": "text", "text": "Error: testcase_id is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
        # Step 1: Load testcase to get graph_json
        print(f"[@MCP:execute_testcase_by_id] Loading testcase {testcase_id}")
        load_result = self.api.get(f'/server/testcase/{testcase_id}', params={'team_id': team_id})
        
        if not load_result.get('success'):
            error_msg = load_result.get('error', 'Failed to load test case')
            return {"content": [{"type": "text", "text": f"❌ Load failed: {error_msg}"}], "isError": True}
        
        testcase = load_result.get('testcase', {})
        graph_json = testcase.get('graph_json')
        testcase_name = testcase.get('testcase_name', 'unknown')
        testcase_interface = testcase.get('userinterface_name', '')
        
        if not graph_json:
            return {"content": [{"type": "text", "text": "Error: Testcase has no graph_json"}], "isError": True}
        
        # Use override interface if provided, otherwise use testcase's interface
        userinterface_name = userinterface_name_override or testcase_interface
        
        print(f"[@MCP:execute_testcase_by_id] Executing testcase '{testcase_name}' with interface '{userinterface_name}'")
        
        # ✅ Prepare inputValues with actual runtime values (EXACT SAME as RunTests.tsx lines 666-673)
        # Note: device_model_name will be automatically populated by the backend from device registry
        # (see host_testcase_routes.py lines 247-253)
        if 'scriptConfig' in graph_json and 'inputs' in graph_json['scriptConfig']:
            print(f"[@MCP:execute_testcase_by_id] Preparing inputValues with runtime values")
            
            # Map over inputs and set values (SAME as frontend)
            for input_def in graph_json['scriptConfig']['inputs']:
                value = input_def.get('default', '')
                # Set the runtime values we know - backend will add device_model from registry
                if input_def['name'] == 'host_name':
                    value = host_name
                elif input_def['name'] == 'device_name':
                    value = device_id
                elif input_def['name'] == 'userinterface_name':
                    value = userinterface_name
                # Note: device_model_name is intentionally NOT set here - 
                # the backend host will populate it from device registry during execution
                
                # Set the value in the input definition
                input_def['value'] = value
                print(f"[@MCP:execute_testcase_by_id]   Set input '{input_def['name']}' = {value}")
        
        # Step 2: Call the new execute_testcase with name instead of graph_json
        # (graph_json is already loaded and passed as optional parameter)
        return self.execute_testcase({
            'testcase_name': testcase_name,
            'device_id': device_id,
            'host_name': host_name,
            'team_id': team_id,
            'graph_json': graph_json,  # Pass pre-loaded graph to skip lookup
            'userinterface_name': userinterface_name
        })
    
    def _poll_testcase_completion(self, execution_id: str, device_id: str, host_name: str, team_id: str, testcase_name: str, max_wait: int = 300) -> Dict[str, Any]:
        """
        Poll testcase execution until complete
        
        REUSES existing /server/testcase/execution/<id>/status API
        """
        poll_interval = 2  # 2 seconds for testcases (can be longer)
        elapsed = 0
        
        print(f"[@MCP:poll_testcase] Polling for execution {execution_id} (max {max_wait}s)")
        
        while elapsed < max_wait:
            # Poll status endpoint
            status = self.api.get(
                f'/server/testcase/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            # Check for API errors (execution not found, etc.)
            if not status.get('success'):
                error_msg = status.get('error', 'Unknown error')
                print(f"[@MCP:poll_testcase] API error: {error_msg}")
                return {"content": [{"type": "text", "text": f"❌ Status check failed: {error_msg}"}], "isError": True}
            
            # The response is: {'success': True, 'status': {nested execution object}}
            # We need to extract the nested status object, then get its 'status' field
            execution_status_obj = status.get('status', {})
            current_status = execution_status_obj.get('status') if isinstance(execution_status_obj, dict) else None
            
            print(f"[@MCP:poll_testcase] current_status: {current_status}")
            
            if current_status == 'completed':
                # Get result from the nested execution_status_obj, not top-level status
                result = execution_status_obj.get('result', {})
                result_success = result.get('success', True)  # Check if testcase execution succeeded
                result_type = result.get('result_type', 'error')
                execution_time_ms = result.get('execution_time_ms', 0)
                execution_time_s = execution_time_ms / 1000
                report_url = result.get('report_url', '')
                logs_url = result.get('logs_url', '')
                
                # Format response similar to execute_script for consistency
                if result_success:
                    print(f"[@MCP:poll_testcase] Test case completed successfully after {elapsed}s")
                    response = f"✅ Test case '{testcase_name}' completed\n"
                    response += f"Result: PASSED ({execution_time_s:.1f}s)\n"
                    if report_url:
                        response += f"\n📄 Report: {report_url}"
                    if logs_url:
                        response += f"\n📋 Logs: {logs_url}"
                    return {"content": [{"type": "text", "text": response}], "isError": False}
                else:
                    # Execution completed but testcase FAILED
                    print(f"[@MCP:poll_testcase] Test case completed with FAILURES after {elapsed}s")
                    error_msg = result.get('error', 'Test case execution failed')
                    response = f"✅ Test case '{testcase_name}' completed\n"
                    response += f"Result: FAILED ({execution_time_s:.1f}s)\n"
                    if error_msg:
                        response += f"Error: {error_msg}\n"
                    if report_url:
                        response += f"\n📄 Report: {report_url}"
                    if logs_url:
                        response += f"\n📋 Logs: {logs_url}"
                    return {"content": [{"type": "text", "text": response}], "isError": True}
            
            elif current_status in ['error', 'failed']:  # Check for BOTH 'error' and 'failed'
                print(f"[@MCP:poll_testcase] Test case failed after {elapsed}s")
                error = execution_status_obj.get('error', 'Test case execution failed')
                result = execution_status_obj.get('result', {})
                report_url = result.get('report_url', '')
                logs_url = result.get('logs_url', '')
                response = f"❌ Test case failed: {error}"
                if report_url:
                    response += f"\n📄 Report: {report_url}"
                if logs_url:
                    response += f"\n📋 Logs: {logs_url}"
                return {"content": [{"type": "text", "text": response}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                progress = status.get('progress', {})
                current_block = progress.get('current_block')
                if current_block:
                    print(f"[@MCP:poll_testcase] Status: {current_status}, block: {current_block} - {elapsed}s elapsed")
                else:
                    print(f"[@MCP:poll_testcase] Status: {current_status} - {elapsed}s elapsed")
            
            # Sleep AFTER checking status
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        print(f"[@MCP:poll_testcase] Test case timed out after {max_wait}s")
        return {"content": [{"type": "text", "text": f"⏱️ Test case execution timed out after {max_wait}s"}], "isError": True}
    
    def save_testcase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a test case graph to the database
        
        REUSES existing /server/testcase/save endpoint (same as frontend)
        Pattern from server_testcase_routes.py line 28
        
        Args:
            params: {
                'testcase_name': str (REQUIRED) - Name for the test case,
                'graph_json': Dict (REQUIRED) - Graph from generate_test_graph,
                'team_id': str (OPTIONAL),
                'description': str (OPTIONAL),
                'userinterface_name': str (OPTIONAL),
                'folder': str (OPTIONAL) - Folder path like 'smoke_tests',
                'tags': List[str] (OPTIONAL) - Tags like ['regression', 'critical']
            }
            
        Returns:
            MCP-formatted response with saved testcase info
        """
        testcase_name = params.get('testcase_name')
        graph_json = params.get('graph_json')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        description = params.get('description', '')
        userinterface_name = params.get('userinterface_name', '')
        folder = params.get('folder', '(Root)')
        tags = params.get('tags', [])
        
        # Validate required parameters
        if not testcase_name:
            return {"content": [{"type": "text", "text": "Error: testcase_name is required"}], "isError": True}
        if not graph_json:
            return {"content": [{"type": "text", "text": "Error: graph_json is required"}], "isError": True}
        
        # ==================== VALIDATE GRAPH STRUCTURE ====================
        # Validate before saving to catch errors early
        validation_errors = []
        
        nodes = graph_json.get('nodes', [])
        edges = graph_json.get('edges', [])
        
        # Check navigation blocks - MUST use target_node_id (not target_node)
        for node in nodes:
            if node.get('type') == 'navigation':
                data = node.get('data', {})
                node_id = node.get('id')
                
                # Check for target_node_id (REQUIRED)
                if not data.get('target_node_id'):
                    validation_errors.append(
                        f"❌ Navigation node '{node_id}' missing 'target_node_id' (UUID from navigation tree)."
                    )
                
                # Check for target_node_label (REQUIRED for executor)
                if not data.get('target_node_label'):
                    validation_errors.append(
                        f"❌ Navigation node '{node_id}' missing 'target_node_label' (string like 'home', 'player')."
                    )
                
                # Warn if using deprecated 'target_node' field
                if data.get('target_node') and not data.get('target_node_id'):
                    validation_errors.append(
                        f"❌ Navigation node '{node_id}' uses deprecated 'target_node'. Use 'target_node_id' instead."
                    )
        
        # Check edge types
        for edge in edges:
            edge_type = edge.get('type')
            if edge_type and edge_type not in ['success', 'failure']:
                validation_errors.append(
                    f"❌ Edge '{edge.get('id')}' has invalid type '{edge_type}'. "
                    f"Must be 'success' or 'failure'."
                )
        
        # Return validation errors if any
        if validation_errors:
            error_msg = "Graph validation failed:\n" + "\n".join(validation_errors)
            error_msg += "\n\n💡 Correct format:"
            error_msg += "\n  Navigation: {\"target_node_id\": \"<UUID>\", \"target_node_label\": \"home\"}"
            error_msg += "\n  Edge: {\"type\": \"success\"} or {\"type\": \"failure\"}"
            error_msg += "\n\n📖 See docs/mcp/mcp_tools_testcase.md#graph-validation-rules"
            return {
                "content": [{"type": "text", "text": error_msg}],
                "isError": True
            }
        
        # Build request - SAME format as frontend
        data = {
            'testcase_name': testcase_name,
            'graph_json': graph_json,
            'description': description,
            'userinterface_name': userinterface_name,
            'folder': folder,
            'tags': tags
            # creation_method defaults to 'visual' in database
        }
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as server_testcase_routes.py line 28
        print(f"[@MCP:save_testcase] Calling /server/testcase/save for '{testcase_name}'")
        result = self.api.post('/server/testcase/save', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to save test case')
            return {"content": [{"type": "text", "text": f"❌ Save failed: {error_msg}"}], "isError": True}
        
        # Success
        testcase = result.get('testcase', {})
        testcase_id = testcase.get('testcase_id', 'unknown')
        return {"content": [{"type": "text", "text": f"✅ Test case '{testcase_name}' saved successfully (ID: {testcase_id})"}], "isError": False}
    
    def list_testcases(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all saved test cases"""
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        result = self.api.get('/server/testcase/list', params={'team_id': team_id})
        
        if not result.get('success'):
            return {"content": [{"type": "text", "text": f"Error: {result.get('error')}"}], "isError": True}
        
        testcases = result.get('testcases', [])
        
        if not testcases:
            return {"content": [{"type": "text", "text": "No test cases found"}], "isError": False}
        
        # Minimal output
        lines = [f"{len(testcases)} testcases:"]
        for tc in testcases:
            lines.append(f"- {tc.get('testcase_name')} ({tc.get('userinterface_name', '?')})")
        
        return {
            "content": [{"type": "text", "text": "\n".join(lines)}],
            "isError": False,
            "testcases": [{"id": tc.get('testcase_id'), "name": tc.get('testcase_name'), "interface": tc.get('userinterface_name')} for tc in testcases]
        }
    
    def load_testcase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load a saved test case by ID
        
        REUSES existing /server/testcase/<id> endpoint (same as frontend)
        Pattern from server_testcase_routes.py line 127
        
        Args:
            params: {
                'testcase_id': str (REQUIRED),
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with test case graph
        """
        testcase_id = params.get('testcase_id')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not testcase_id:
            return {"content": [{"type": "text", "text": "Error: testcase_id is required"}], "isError": True}
        
        query_params = {'team_id': team_id}
        
        # Call EXISTING endpoint - SAME as server_testcase_routes.py line 127
        print(f"[@MCP:load_testcase] Calling /server/testcase/{testcase_id}")
        result = self.api.get(f'/server/testcase/{testcase_id}', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to load test case')
            return {"content": [{"type": "text", "text": f"❌ Load failed: {error_msg}"}], "isError": True}
        
        # Success
        testcase = result.get('testcase', {})
        name = testcase.get('testcase_name', 'unknown')
        desc = testcase.get('description', 'No description')
        ui = testcase.get('userinterface_name', 'unknown')
        
        return {
            "content": [{"type": "text", "text": f"✅ Test case '{name}' loaded\nInterface: {ui}\nDescription: {desc}\n\nUse execute_testcase_by_id(testcase_id='{testcase_id}') to run it."}],
            "isError": False,
            "testcase": testcase,
            "graph_json": testcase.get('graph_json')
        }
    
    def rename_testcase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rename an existing test case
        
        USES /server/testcase/save endpoint with testcase_id for update
        Pattern from server_testcase_routes.py line 28 (update path)
        
        Args:
            params: {
                'testcase_id': str (REQUIRED) - Test case UUID to rename,
                'new_name': str (REQUIRED) - New testcase name,
                'team_id': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with rename result
        """
        testcase_id = params.get('testcase_id')
        new_name = params.get('new_name')
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        
        # Validate required parameters
        if not testcase_id:
            return {"content": [{"type": "text", "text": "Error: testcase_id is required"}], "isError": True}
        if not new_name:
            return {"content": [{"type": "text", "text": "Error: new_name is required"}], "isError": True}
        
        # Get the current testcase to preserve its data
        query_params = {'team_id': team_id}
        load_result = self.api.get(f'/server/testcase/{testcase_id}', params=query_params)
        
        if not load_result.get('success'):
            error_msg = load_result.get('error', 'Failed to load test case')
            return {"content": [{"type": "text", "text": f"❌ Failed to load testcase: {error_msg}"}], "isError": True}
        
        testcase = load_result.get('testcase', {})
        old_name = testcase.get('testcase_name', 'unknown')
        
        # Build update request with only the name change
        data = {
            'testcase_id': testcase_id,
            'testcase_name': new_name
        }
        
        # Call update endpoint
        print(f"[@MCP:rename_testcase] Renaming '{old_name}' -> '{new_name}' (ID: {testcase_id})")
        result = self.api.post('/server/testcase/save', data=data, params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to rename test case')
            return {"content": [{"type": "text", "text": f"❌ Rename failed: {error_msg}"}], "isError": True}
        
        # Success
        return {"content": [{"type": "text", "text": f"✅ Test case renamed: '{old_name}' → '{new_name}' (ID: {testcase_id})"}], "isError": False}

