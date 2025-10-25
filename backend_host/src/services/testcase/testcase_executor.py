"""
TestCase Executor

Executes visual test cases created in TestCase Builder.
Integrates with existing executors and ScriptExecutionContext.
"""

import time
from typing import Dict, List, Any, Optional
from shared.src.lib.executors.script_executor import ScriptExecutionContext
from shared.src.lib.database.testcase_db import get_testcase_by_name, get_testcase
from shared.src.lib.database.script_results_db import record_script_execution_start, update_script_execution_result
from .testcase_validator import TestCaseValidator


class TestCaseExecutor:
    """
    Executes test case graphs by traversing nodes and delegating to existing executors.
    """
    
    def __init__(self):
        self.validator = TestCaseValidator()
        self.context = None
        self.device = None
        self.current_block_id = None
    
    def execute_testcase(
        self,
        testcase_name: str,
        team_id: str,
        host_name: str,
        device_id: str,
        device_name: str,
        device_model: str
    ) -> Dict[str, Any]:
        """
        Execute a test case by name.
        
        Args:
            testcase_name: Name of the test case to execute
            team_id: Team ID
            host_name: Host name
            device_id: Device ID
            device_name: Device name
            device_model: Device model
        
        Returns:
            Execution result with success, report_url, etc.
        """
        start_time = time.time()
        
        try:
            # Load test case definition from database
            print(f"[@testcase_executor] Loading test case: {testcase_name}")
            testcase = get_testcase_by_name(testcase_name, team_id)
            
            if not testcase:
                return {
                    'success': False,
                    'error': f'Test case not found: {testcase_name}',
                    'execution_time_ms': 0
                }
            
            graph = testcase['graph_json']
            userinterface_name = testcase.get('userinterface_name')
            
            # Validate graph structure
            print(f"[@testcase_executor] Validating graph...")
            is_valid, errors, warnings = self.validator.validate_graph(graph)
            
            if not is_valid:
                error_msg = '; '.join(errors)
                print(f"[@testcase_executor] Validation failed: {error_msg}")
                return {
                    'success': False,
                    'error': f'Invalid graph: {error_msg}',
                    'validation_errors': errors,
                    'validation_warnings': warnings,
                    'execution_time_ms': 0
                }
            
            if warnings:
                print(f"[@testcase_executor] Validation warnings: {'; '.join(warnings)}")
            
            # Record execution start in script_results
            script_result_id = record_script_execution_start(
                team_id=team_id,
                script_name=testcase_name,
                script_type='testcase',  # Mark as test case execution
                userinterface_name=userinterface_name,
                host_name=host_name,
                device_name=device_name,
                metadata={
                    'testcase_id': str(testcase['testcase_id']),
                    'device_id': device_id,
                    'device_model': device_model
                }
            )
            
            print(f"[@testcase_executor] Script result ID: {script_result_id}")
            
            # Create execution context
            context = ScriptExecutionContext(testcase_name)
            context.script_result_id = script_result_id
            context.team_id = team_id
            context.userinterface_name = userinterface_name
            
            # Get device from controller manager
            from backend_host.src.controllers.controller_manager import get_host
            host = get_host(device_ids=[device_id])
            
            device = next((d for d in host.get_devices() if d.device_id == device_id), None)
            if not device:
                raise ValueError(f"Device not found: {device_id}")
            
            context.selected_device = device
            context.host = host
            
            # Populate device navigation_context for executor tracking
            nav_context = device.navigation_context
            nav_context['script_id'] = script_result_id
            nav_context['script_name'] = testcase_name
            nav_context['script_context'] = 'testcase'
            
            # Execute the graph
            print(f"[@testcase_executor] Executing test case...")
            self.context = context
            self.device = device
            
            execution_result = self._execute_graph(graph, context)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Determine result type for logging
            result_type = execution_result.get('result_type', 'error')
            if result_type == 'success':
                print(f"[@testcase_executor] Execution completed: SUCCESS (reached SUCCESS block)")
            elif result_type == 'failure':
                print(f"[@testcase_executor] Execution completed: FAILURE (reached FAILURE block)")
            else:
                print(f"[@testcase_executor] Execution completed: ERROR - {execution_result.get('error')}")
            
            # Update script_results with final result
            update_script_execution_result(
                script_result_id=script_result_id,
                success=execution_result['success'],
                execution_time_ms=execution_time_ms,
                error_msg=execution_result.get('error')
            )
            
            return {
                'success': execution_result['success'],
                'result_type': result_type,
                'execution_time_ms': execution_time_ms,
                'step_count': len(context.step_results),
                'error': execution_result.get('error'),
                'script_result_id': script_result_id,
                'step_results': context.step_results
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Execution error: {str(e)}"
            print(f"[@testcase_executor] ERROR: {error_msg}")
            
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': error_msg,
                'execution_time_ms': execution_time_ms
            }
    
    def _execute_graph(self, graph: Dict[str, Any], context: ScriptExecutionContext) -> Dict[str, Any]:
        """
        Execute a test case graph by traversing nodes.
        
        START block is never executed - it's only an entry point marker.
        SUCCESS/FAILURE blocks are terminal - they end execution immediately.
        Execution begins at the first executable block connected to START.
        
        Args:
            graph: {nodes: [...], edges: [...]}
            context: Execution context
        
        Returns:
            {
                success: bool (True only if reached SUCCESS terminal block),
                result_type: 'success' | 'failure' | 'error',
                error: str (if error occurred)
            }
        """
        nodes = {node['id']: node for node in graph['nodes']}
        edges = graph['edges']
        
        # Debug: Print raw graph structure
        print(f"[@testcase_executor] === RAW GRAPH DEBUG ===")
        print(f"[@testcase_executor] Total nodes: {len(graph['nodes'])}")
        for node in graph['nodes']:
            print(f"[@testcase_executor]   Node: {node['id']} (type: {node['type']})")
        
        print(f"[@testcase_executor] Total edges: {len(edges)}")
        for edge in edges:
            edge_type = edge.get('sourceHandle') or edge.get('type', 'unknown')
            print(f"[@testcase_executor]   Edge: {edge['source']} --[{edge_type}]--> {edge['target']}")
        print(f"[@testcase_executor] === END RAW GRAPH DEBUG ===")
        
        # Find START block - it's the entry point but never executed
        start_node = next((node for node in graph['nodes'] if node['type'] == 'start'), None)
        if not start_node:
            return {'success': False, 'error': 'No START block found'}
        
        # Skip START and find the first executable block
        # START is only a marker - execution begins at the first connected block
        start_node_id = start_node['id']
        print(f"[@testcase_executor] START node ID: {start_node_id}")
        print(f"[@testcase_executor] Looking for 'success' edge from START...")
        current_node_id = self._find_next_node(start_node_id, 'success', edges)
        
        if current_node_id:
            print(f"[@testcase_executor] Found first executable block: {current_node_id}")
        else:
            print(f"[@testcase_executor] No block connected to START via 'success' edge")
        
        # If START has no connection, check if graph has other blocks
        if not current_node_id:
            # Count executable blocks (exclude START, SUCCESS, FAILURE)
            executable_blocks = [n for n in graph['nodes'] if n['type'] not in ['start', 'success', 'failure']]
            
            if executable_blocks:
                # Graph has blocks but START is not connected - this is an error
                return {
                    'success': False,
                    'error': f'START block is not connected to any executable block. Found {len(executable_blocks)} disconnected block(s).'
                }
            else:
                # No executable blocks - minimal test case (just validates setup)
                print(f"[@testcase_executor] No executable blocks - minimal test case, treating as success")
                context.overall_success = True
                return {'success': True, 'result_type': 'success'}
        
        visited_blocks = set()
        max_iterations = 1000  # Prevent infinite loops
        iteration_count = 0
        
        print(f"[@testcase_executor] Skipping START block, beginning execution at first connected block: {current_node_id}")
        
        while current_node_id and iteration_count < max_iterations:
            iteration_count += 1
            
            # Get current node
            current_node = nodes.get(current_node_id)
            if not current_node:
                return {'success': False, 'error': f'Node not found: {current_node_id}'}
            
            node_type = current_node['type']
            
            print(f"[@testcase_executor] Processing block: {current_node_id} (type: {node_type})")
            
            # SUCCESS and FAILURE are terminal blocks - they end execution immediately
            # They are not executed, just signal the final test result
            if node_type == 'success':
                context.overall_success = True
                print(f"[@testcase_executor] Reached SUCCESS terminal block - test passed")
                return {'success': True, 'result_type': 'success'}
            
            if node_type == 'failure':
                context.overall_success = False
                print(f"[@testcase_executor] Reached FAILURE terminal block - test failed")
                return {'success': False, 'result_type': 'failure', 'error': 'Test case reached FAILURE block'}
            
            # Execute block
            try:
                block_result = self._execute_block(current_node, context)
            except Exception as e:
                error_msg = f"Block {current_node_id} execution error: {str(e)}"
                print(f"[@testcase_executor] ERROR: {error_msg}")
                return {'success': False, 'result_type': 'error', 'error': error_msg}
            
            # Show execution result
            result_status = "SUCCESS" if block_result['success'] else "FAILURE"
            print(f"[@testcase_executor] Block {current_node_id} executed: {result_status}")
            if block_result.get('message'):
                print(f"[@testcase_executor]   Message: {block_result['message']}")
            if block_result.get('error'):
                print(f"[@testcase_executor]   Error: {block_result['error']}")
            
            # Record step with block ID for frontend tracking
            context.record_step_immediately({
                'block_id': current_node_id,
                'block_type': node_type,
                'success': block_result['success'],
                'execution_time_ms': block_result.get('execution_time_ms', 0),
                'message': block_result.get('message', ''),
                'error': block_result.get('error'),
                'step_category': 'testcase_block'
            })
            
            # Find next node based on success/failure result
            edge_type = 'success' if block_result['success'] else 'failure'
            print(f"[@testcase_executor] Looking for {edge_type} edge from block {current_node_id}...")
            next_node_id = self._find_next_node(current_node_id, edge_type, edges)
            
            if not next_node_id:
                # Block executed but has no outgoing connection for this result
                error_msg = f"No {edge_type} connection found from block {current_node_id}"
                print(f"[@testcase_executor] ERROR: {error_msg}")
                context.overall_success = False
                return {'success': False, 'result_type': 'error', 'error': error_msg}
            
            print(f"[@testcase_executor] Following {edge_type} edge to block: {next_node_id}")
            
            current_node_id = next_node_id
        
        # Max iterations reached - treat as error
        if iteration_count >= max_iterations:
            return {'success': False, 'result_type': 'error', 'error': 'Max iterations reached (possible infinite loop)'}
        
        return {'success': False, 'result_type': 'error', 'error': 'Graph execution ended unexpectedly'}
    
    def _execute_block(self, node: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """
        Execute a single block by delegating to appropriate executor.
        
        Returns:
            {success: bool, execution_time_ms: int, message: str, error: str}
        """
        node_type = node['type']
        data = node.get('data', {})
        
        # START block should never reach here - it's skipped in _execute_graph
        if node_type == 'start':
            raise Exception('START block should not be executed - it is only an entry point marker')
        
        if node_type == 'action':
            return self._execute_action_block(data, context)
        
        elif node_type == 'verification':
            return self._execute_verification_block(data, context)
        
        elif node_type == 'navigation':
            return self._execute_navigation_block(data, context)
        
        elif node_type == 'loop':
            return self._execute_loop_block(node, context)
        
        else:
            return {'success': False, 'error': f'Unknown block type: {node_type}'}
    
    def _execute_action_block(self, data: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Execute action block using ActionExecutor"""
        start_time = time.time()
        
        try:
            action_executor = self.device.action_executor
            
            command = data.get('command')
            params = data.get('params', {})
            retry_actions = data.get('retry_actions', [])
            failure_actions = data.get('failure_actions', [])
            
            # Build actions array from single action
            actions = [{
                'command': command,
                'params': params
            }]
            
            # Execute actions using same method as single block execution
            result = action_executor.execute_actions(
                actions=actions,
                retry_actions=retry_actions,
                failure_actions=failure_actions,
                team_id=context.team_id,
                context=context
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': result['success'],
                'execution_time_ms': execution_time_ms,
                'message': f"Action: {command}",
                'error': result.get('error')
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'execution_time_ms': execution_time_ms,
                'error': f'Action execution error: {str(e)}'
            }
    
    def _execute_verification_block(self, data: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Execute verification block using VerificationExecutor"""
        start_time = time.time()
        
        try:
            verification_executor = self.device.verification_executor
            
            verification_type = data.get('verification_type')
            reference = data.get('reference')
            threshold = data.get('threshold', 0.8)
            
            # Execute verification
            result = verification_executor.execute_verification(
                verification_type=verification_type,
                reference=reference,
                threshold=threshold,
                context=context,
                userinterface_name=context.userinterface_name
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': result['success'],
                'execution_time_ms': execution_time_ms,
                'message': f"Verification: {verification_type}",
                'error': result.get('error')
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'execution_time_ms': execution_time_ms,
                'error': f'Verification execution error: {str(e)}'
            }
    
    def _execute_navigation_block(self, data: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Execute navigation block using NavigationExecutor"""
        start_time = time.time()
        
        try:
            navigation_executor = self.device.navigation_executor
            
            target_node = data.get('target_node')
            target_node_id = data.get('target_node_id')
            
            # Use target_node_id if available, otherwise use target_node label
            if target_node_id:
                target = target_node_id
            elif target_node:
                target = target_node
            else:
                return {
                    'success': False,
                    'execution_time_ms': 0,
                    'error': 'No target node specified'
                }
            
            # Load navigation tree if not already loaded
            if not context.tree_id:
                nav_result = navigation_executor.load_navigation_tree(
                    context.userinterface_name,
                    context.team_id
                )
                if not nav_result['success']:
                    return {
                        'success': False,
                        'execution_time_ms': int((time.time() - start_time) * 1000),
                        'error': f"Failed to load navigation tree: {nav_result.get('error')}"
                    }
                context.tree_id = nav_result['tree_id']
            
            # Execute navigation
            result = navigation_executor.execute_navigation(
                tree_id=context.tree_id,
                userinterface_name=context.userinterface_name,
                target_node_id=target,
                team_id=context.team_id,
                context=context
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': result['success'],
                'execution_time_ms': execution_time_ms,
                'message': f"Navigate to: {target}",
                'error': result.get('error')
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'execution_time_ms': execution_time_ms,
                'error': f'Navigation execution error: {str(e)}'
            }
    
    def _execute_loop_block(self, node: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Execute loop block with nested graph"""
        start_time = time.time()
        
        try:
            data = node.get('data', {})
            iterations = data.get('iterations', 1)
            nested_blocks = data.get('nested_blocks')
            
            if not nested_blocks:
                return {
                    'success': False,
                    'execution_time_ms': 0,
                    'error': 'Loop block has no nested blocks'
                }
            
            # Execute nested graph for specified iterations
            for i in range(iterations):
                print(f"[@testcase_executor] Loop iteration {i+1}/{iterations}")
                
                result = self._execute_graph(nested_blocks, context)
                
                # Check loop behavior (continue/break)
                if not result['success']:
                    # Nested graph failed - should we break or continue?
                    loop_behavior = data.get('on_failure', 'break')  # 'break' or 'continue'
                    
                    if loop_behavior == 'break':
                        execution_time_ms = int((time.time() - start_time) * 1000)
                        return {
                            'success': False,
                            'execution_time_ms': execution_time_ms,
                            'message': f'Loop failed at iteration {i+1}',
                            'error': result.get('error')
                        }
                    # else: continue to next iteration
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'execution_time_ms': execution_time_ms,
                'message': f'Loop completed {iterations} iterations'
            }
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'execution_time_ms': execution_time_ms,
                'error': f'Loop execution error: {str(e)}'
            }
    
    def _find_next_node(self, current_node_id: str, edge_type: str, edges: List[Dict]) -> Optional[str]:
        """
        Find the next node ID by following edges.
        
        Args:
            current_node_id: Current node ID
            edge_type: 'success' or 'failure'
            edges: List of edges
        
        Returns:
            Next node ID or None
        """
        for edge in edges:
            if edge['source'] == current_node_id:
                # Check edge type (can be in 'type' or 'sourceHandle')
                edge_handle = edge.get('sourceHandle') or edge.get('type')
                
                # React Flow adds suffixes like '-hitarea' to handle names
                # Match if edge_handle starts with the edge_type we're looking for
                if edge_handle and edge_handle.startswith(edge_type):
                    print(f"[@testcase_executor] Found edge: {current_node_id} --[{edge_handle}]--> {edge['target']}")
                    return edge['target']
        
        return None

