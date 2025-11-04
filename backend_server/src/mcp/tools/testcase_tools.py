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
        Execute a test case graph on a device
        
        REUSES existing /server/testcase/execute endpoint (same as frontend)
        Pattern from server_testcase_routes.py line 167
        
        Args:
            params: {
                'device_id': str (REQUIRED),
                'host_name': str (REQUIRED),
                'team_id': str (OPTIONAL),
                'graph_json': Dict (REQUIRED) - Graph definition from generate_test_graph,
                'testcase_name': str (OPTIONAL) - Name for execution logs,
                'userinterface_name': str (OPTIONAL)
            }
            
        Returns:
            MCP-formatted response with execution results
        """
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        graph_json = params.get('graph_json')
        testcase_name = params.get('testcase_name', 'mcp_testcase')
        userinterface_name = params.get('userinterface_name', '')
        
        # Validate required parameters
        if not graph_json:
            return {"content": [{"type": "text", "text": "Error: graph_json is required"}], "isError": True}
        if not host_name:
            return {"content": [{"type": "text", "text": "Error: host_name is required"}], "isError": True}
        
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
        
        # Sync result - return directly
        print(f"[@MCP:execute_testcase] Sync execution completed")
        return self.formatter.format_api_response(result)
    
    def execute_testcase_by_id(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP CONVENIENCE WRAPPER: Load and execute a saved test case by ID
        
        This is a helper specifically for MCP that combines load + execute in one call.
        Frontend doesn't need this because it can pass graph_json between functions.
        
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
        device_id = params.get('device_id', APP_CONFIG['DEFAULT_DEVICE_ID'])
        host_name = params.get('host_name', APP_CONFIG['DEFAULT_HOST_NAME'])
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
        
        # Step 2: Execute the loaded graph
        return self.execute_testcase({
            'device_id': device_id,
            'host_name': host_name,
            'team_id': team_id,
            'graph_json': graph_json,
            'testcase_name': testcase_name,
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
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            # Poll status endpoint
            status = self.api.get(
                f'/server/testcase/execution/{execution_id}/status',
                params={'device_id': device_id, 'host_name': host_name, 'team_id': team_id}
            )
            
            current_status = status.get('status')
            
            if current_status == 'completed':
                print(f"[@MCP:poll_testcase] Test case completed successfully after {elapsed}s")
                result = status.get('result', {})
                message = result.get('message', f"Test case '{testcase_name}' completed")
                return {"content": [{"type": "text", "text": f"✅ {message}"}], "isError": False}
            
            elif current_status == 'error':
                print(f"[@MCP:poll_testcase] Test case failed after {elapsed}s")
                error = status.get('error', 'Test case execution failed')
                return {"content": [{"type": "text", "text": f"❌ Test case failed: {error}"}], "isError": True}
            
            elif current_status in ['pending', 'running']:
                progress = status.get('progress', {})
                current_block = progress.get('current_block', 'unknown')
                print(f"[@MCP:poll_testcase] Status: {current_status}, block: {current_block} - {elapsed}s elapsed")
        
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
        
        # Build request - SAME format as frontend
        data = {
            'testcase_name': testcase_name,
            'graph_json': graph_json,
            'description': description,
            'userinterface_name': userinterface_name,
            'folder': folder,
            'tags': tags,
            'creation_method': 'mcp_ai'
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
        """
        List all saved test cases
        
        REUSES existing /server/testcase/list endpoint (same as frontend)
        Pattern from server_testcase_routes.py line 108
        
        Args:
            params: {
                'team_id': str (OPTIONAL),
                'include_inactive': bool (OPTIONAL, default: False)
            }
            
        Returns:
            MCP-formatted response with list of test cases
        """
        team_id = params.get('team_id', APP_CONFIG['DEFAULT_TEAM_ID'])
        include_inactive = params.get('include_inactive', False)
        
        query_params = {'team_id': team_id, 'include_inactive': str(include_inactive).lower()}
        
        # Call EXISTING endpoint - SAME as server_testcase_routes.py line 108
        print(f"[@MCP:list_testcases] Calling /server/testcase/list")
        result = self.api.get('/server/testcase/list', params=query_params)
        
        # Check for errors
        if not result.get('success'):
            error_msg = result.get('error', 'Failed to list test cases')
            return {"content": [{"type": "text", "text": f"❌ List failed: {error_msg}"}], "isError": True}
        
        # Format response
        testcases = result.get('testcases', [])
        if not testcases:
            return {"content": [{"type": "text", "text": "No test cases found"}], "isError": False}
        
        response_text = f"📋 Found {len(testcases)} test case(s):\n\n"
        for tc in testcases[:20]:  # Limit to first 20
            name = tc.get('testcase_name', 'unknown')
            desc = tc.get('description', 'No description')
            ui = tc.get('userinterface_name', 'unknown')
            response_text += f"- {name} ({ui})\n  {desc}\n\n"
        
        if len(testcases) > 20:
            response_text += f"... and {len(testcases) - 20} more"
        
        return {"content": [{"type": "text", "text": response_text}], "isError": False, "testcases": testcases}
    
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
        
        return {
            "content": [{"type": "text", "text": f"✅ Test case '{name}' loaded\n{desc}"}],
            "isError": False,
            "testcase": testcase,
            "graph_json": testcase.get('graph_json')
        }

