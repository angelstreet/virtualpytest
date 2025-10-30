"""
TestCase Executor

Executes visual test cases created in TestCase Builder.
Integrates with existing executors and ScriptExecutionContext.
Supports async execution with real-time progress tracking.
"""

import time
import threading
import uuid
import sys
import io
from typing import Dict, List, Any, Optional
from shared.src.lib.executors.script_executor import ScriptExecutionContext
from shared.src.lib.database.testcase_db import get_testcase_by_name, get_testcase
from shared.src.lib.database.script_results_db import record_script_execution_start, update_script_execution_result
from .testcase_validator import TestCaseValidator


class TestCaseExecutor:
    """
    Executes test case graphs by traversing nodes and delegating to existing executors.
    Supports async execution with real-time progress tracking.
    """
    
    def __init__(self):
        self.validator = TestCaseValidator()
        self.context = None
        self.device = None
        self.current_block_id = None
        
        # Async execution tracking
        self._executions: Dict[str, Dict[str, Any]] = {}  # execution_id -> execution state
        self._lock = threading.Lock()
    
    def execute_testcase_from_graph(
        self,
        graph: Dict[str, Any],
        team_id: str,
        host_name: str,
        device_id: str,
        device_name: str,
        device_model: str,
        userinterface_name: str = ''
    ) -> Dict[str, Any]:
        """
        Execute a test case directly from graph JSON (no save required).
        
        Args:
            graph: Graph JSON definition
            team_id: Team ID
            host_name: Host name
            device_id: Device ID
            device_name: Device name
            device_model: Device model
            userinterface_name: Userinterface name (optional)
        
        Returns:
            Execution result with success, report_url, etc.
        """
        start_time = time.time()
        
        try:
            # Validate graph structure
            print(f"[@testcase_executor] Validating graph...")
            is_valid, errors, warnings = self.validator.validate_graph(
                graph,
                userinterface_name=userinterface_name,
                team_id=team_id
            )
            
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
                script_name='unsaved_testcase',
                script_type='testcase',
                userinterface_name=userinterface_name,
                host_name=host_name,
                device_name=device_name,
                metadata={
                    'device_id': device_id,
                    'device_model': device_model,
                    'unsaved': True
                }
            )
            
            print(f"[@testcase_executor] Script result ID: {script_result_id}")
            
            # Create execution context
            context = ScriptExecutionContext('unsaved_testcase')
            context.script_result_id = script_result_id
            context.team_id = team_id
            context.userinterface_name = userinterface_name
            
            # Start stdout capture for logs
            context.start_stdout_capture()
            
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
            nav_context['script_name'] = 'unsaved_testcase'
            nav_context['script_context'] = 'testcase'
            
            # Execute the graph
            print(f"[@testcase_executor] Executing test case from graph...")
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
            
            # Use ScriptExecutor's cleanup to generate report (same as @script decorator does)
            print(f"[@testcase_executor] Generating execution report using ScriptExecutor cleanup...")
            report_url = ""
            logs_url = ""
            report_path = ""
            logs_path = ""
            
            try:
                from shared.src.lib.executors.script_executor import ScriptExecutor
                executor = ScriptExecutor('unsaved_testcase')
                
                # Set overall_success in context before cleanup
                context.overall_success = execution_result['success']
                
                # Capture final screenshot before report generation (like cleanup_and_exit does)
                if context.host and context.selected_device:
                    print(f"📸 [{executor.script_name}] Capturing final state screenshot...")
                    from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                    screenshot_id = capture_screenshot_for_script(context.selected_device, context, "final_state")
                    if screenshot_id:
                        print(f"✅ [{executor.script_name}] Final screenshot captured: {screenshot_id}")
                
                # Use the same report generation flow as @script decorator
                device_info = executor.get_device_info_for_report_context(context)
                host_info = executor.get_host_info_for_report_context(context)
                
                report_result = executor.generate_report_for_context(context, device_info, host_info, userinterface_name)
                
                if report_result.get('success'):
                    report_url = report_result.get('report_url', '')
                    logs_url = report_result.get('logs_url', '')
                    report_path = report_result.get('report_path', '')
                    logs_path = report_result.get('logs_path', '')
                    
            except Exception as e:
                print(f"[@testcase_executor] Error generating report: {e}")
                import traceback
                traceback.print_exc()
            
            # Update script_results with final result including report URLs
            update_script_execution_result(
                script_result_id=script_result_id,
                success=execution_result['success'],
                execution_time_ms=execution_time_ms,
                html_report_r2_path=report_path,
                html_report_r2_url=report_url,
                logs_r2_path=logs_path,
                logs_r2_url=logs_url,
                error_msg=execution_result.get('error')
            )
            
            return {
                'success': execution_result['success'],
                'result_type': result_type,
                'execution_time_ms': execution_time_ms,
                'step_count': len(context.step_results),
                'error': execution_result.get('error'),
                'script_result_id': script_result_id,
                'step_results': context.step_results,
                'report_url': report_url,
                'logs_url': logs_url,
                'script_outputs': getattr(context, 'script_outputs', {})  # NEW: For campaign chaining
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
            is_valid, errors, warnings = self.validator.validate_graph(
                graph,
                userinterface_name=userinterface_name,
                team_id=team_id
            )
            
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
            
            # Use ScriptExecutor's cleanup to generate report (same as @script decorator does)
            print(f"[@testcase_executor] Generating execution report using ScriptExecutor cleanup...")
            report_url = ""
            logs_url = ""
            report_path = ""
            logs_path = ""
            
            try:
                from shared.src.lib.executors.script_executor import ScriptExecutor
                executor = ScriptExecutor('unsaved_testcase')
                
                # Set overall_success in context before cleanup
                context.overall_success = execution_result['success']
                
                # Capture final screenshot before report generation (like cleanup_and_exit does)
                if context.host and context.selected_device:
                    print(f"📸 [{executor.script_name}] Capturing final state screenshot...")
                    from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                    screenshot_id = capture_screenshot_for_script(context.selected_device, context, "final_state")
                    if screenshot_id:
                        print(f"✅ [{executor.script_name}] Final screenshot captured: {screenshot_id}")
                
                # Use the same report generation flow as @script decorator
                device_info = executor.get_device_info_for_report_context(context)
                host_info = executor.get_host_info_for_report_context(context)
                
                report_result = executor.generate_report_for_context(context, device_info, host_info, userinterface_name)
                
                if report_result.get('success'):
                    report_url = report_result.get('report_url', '')
                    logs_url = report_result.get('logs_url', '')
                    report_path = report_result.get('report_path', '')
                    logs_path = report_result.get('logs_path', '')
                    
            except Exception as e:
                print(f"[@testcase_executor] Error generating report: {e}")
                import traceback
                traceback.print_exc()
            
            # Update script_results with final result including report URLs
            update_script_execution_result(
                script_result_id=script_result_id,
                success=execution_result['success'],
                execution_time_ms=execution_time_ms,
                html_report_r2_path=report_path,
                html_report_r2_url=report_url,
                logs_r2_path=logs_path,
                logs_r2_url=logs_url,
                error_msg=execution_result.get('error')
            )
            
            return {
                'success': execution_result['success'],
                'result_type': result_type,
                'execution_time_ms': execution_time_ms,
                'step_count': len(context.step_results),
                'error': execution_result.get('error'),
                'script_result_id': script_result_id,
                'step_results': context.step_results,
                'report_url': report_url,
                'logs_url': logs_url,
                'script_outputs': getattr(context, 'script_outputs', {})  # NEW: For campaign chaining
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
    
    def execute_testcase_from_graph_async(
        self,
        graph: Dict[str, Any],
        team_id: str,
        host_name: str,
        device_id: str,
        device_name: str,
        device_model: str,
        userinterface_name: str = ''
    ) -> Dict[str, Any]:
        """
        Start async execution of test case from graph.
        Returns immediately with execution_id for polling.
        
        Returns:
            {
                'success': True,
                'execution_id': str,
                'message': 'Execution started'
            }
        """
        execution_id = str(uuid.uuid4())
        
        # Initialize execution state
        with self._lock:
            self._executions[execution_id] = {
                'execution_id': execution_id,
                'status': 'running',
                'start_time': time.time(),
                'current_block_id': None,
                'block_states': {},  # block_id -> {status, duration, error, message}
                'result': None,
                'error': None
            }
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_testcase_async_worker,
            args=(execution_id, graph, team_id, host_name, device_id, device_name, device_model, userinterface_name)
        )
        thread.daemon = True
        thread.start()
        
        print(f"[@testcase_executor] Started async execution: {execution_id}")
        
        return {
            'success': True,
            'execution_id': execution_id,
            'message': 'Execution started asynchronously'
        }
    
    def _execute_testcase_async_worker(
        self,
        execution_id: str,
        graph: Dict[str, Any],
        team_id: str,
        host_name: str,
        device_id: str,
        device_name: str,
        device_model: str,
        userinterface_name: str
    ):
        """Background worker for async execution"""
        start_time = time.time()
        
        try:
            # Validate graph
            print(f"[@testcase_executor:{execution_id}] Validating graph...")
            is_valid, errors, warnings = self.validator.validate_graph(
                graph,
                userinterface_name=userinterface_name,
                team_id=team_id
            )
            
            if not is_valid:
                error_msg = '; '.join(errors)
                print(f"[@testcase_executor:{execution_id}] Validation failed: {error_msg}")
                with self._lock:
                    self._executions[execution_id]['status'] = 'failed'
                    self._executions[execution_id]['error'] = f'Invalid graph: {error_msg}'
                    self._executions[execution_id]['result'] = {
                        'success': False,
                        'error': f'Invalid graph: {error_msg}',
                        'validation_errors': errors,
                        'execution_time_ms': 0
                    }
                return
            
            # Record execution start
            script_result_id = record_script_execution_start(
                team_id=team_id,
                script_name='unsaved_testcase',
                script_type='testcase',
                userinterface_name=userinterface_name,
                host_name=host_name,
                device_name=device_name,
                metadata={
                    'device_id': device_id,
                    'device_model': device_model,
                    'unsaved': True,
                    'execution_id': execution_id
                }
            )
            
            print(f"[@testcase_executor:{execution_id}] Script result ID: {script_result_id}")
            
            # Create execution context
            context = ScriptExecutionContext('unsaved_testcase')
            context.script_result_id = script_result_id
            context.team_id = team_id
            context.userinterface_name = userinterface_name
            
            # Start stdout capture for logs (CRITICAL for log upload)
            context.start_stdout_capture()
            print(f"[@testcase_executor:{execution_id}] Started stdout capture for logs")
            
            # Get device
            from backend_host.src.controllers.controller_manager import get_host
            host = get_host(device_ids=[device_id])
            device = next((d for d in host.get_devices() if d.device_id == device_id), None)
            
            if not device:
                raise ValueError(f"Device not found: {device_id}")
            
            context.selected_device = device
            context.host = host
            
            # Populate device navigation_context
            nav_context = device.navigation_context
            nav_context['script_id'] = script_result_id
            nav_context['script_name'] = 'unsaved_testcase'
            nav_context['script_context'] = 'testcase'
            
            # Store context for block execution callbacks
            self.context = context
            self.device = device
            
            # Execute graph with progress tracking
            print(f"[@testcase_executor:{execution_id}] Executing test case...")
            execution_result = self._execute_graph_with_tracking(graph, context, execution_id)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Generate report (same as synchronous path)
            print(f"[@testcase_executor:{execution_id}] Generating execution report...")
            report_url = ""
            logs_url = ""
            report_path = ""
            logs_path = ""
            
            try:
                from shared.src.lib.executors.script_executor import ScriptExecutor
                executor = ScriptExecutor('unsaved_testcase')
                
                # Set overall_success in context
                context.overall_success = execution_result['success']
                
                # Capture final screenshot
                if context.host and context.selected_device:
                    print(f"📸 [{executor.script_name}] Capturing final state screenshot...")
                    from shared.src.lib.utils.device_utils import capture_screenshot_for_script
                    screenshot_id = capture_screenshot_for_script(context.selected_device, context, "final_state")
                    if screenshot_id:
                        print(f"✅ [{executor.script_name}] Final screenshot captured: {screenshot_id}")
                
                # Generate report
                device_info = executor.get_device_info_for_report_context(context)
                host_info = executor.get_host_info_for_report_context(context)
                
                report_result = executor.generate_report_for_context(context, device_info, host_info, userinterface_name)
                
                if report_result.get('success'):
                    report_url = report_result.get('report_url', '')
                    logs_url = report_result.get('logs_url', '')
                    report_path = report_result.get('report_path', '')
                    logs_path = report_result.get('logs_path', '')
                    print(f"[@testcase_executor:{execution_id}] Report URL: {report_url}")
                    print(f"[@testcase_executor:{execution_id}] Logs URL: {logs_url}")
                    
            except Exception as e:
                print(f"[@testcase_executor:{execution_id}] Error generating report: {e}")
                import traceback
                traceback.print_exc()
            
            # Update script_results with report URLs
            update_script_execution_result(
                script_result_id=script_result_id,
                success=execution_result['success'],
                execution_time_ms=execution_time_ms,
                html_report_r2_path=report_path,
                html_report_r2_url=report_url,
                logs_r2_path=logs_path,
                logs_r2_url=logs_url,
                error_msg=execution_result.get('error')
            )
            
            # Update execution state
            with self._lock:
                self._executions[execution_id]['status'] = 'completed'
                self._executions[execution_id]['result'] = {
                    'success': execution_result['success'],
                    'result_type': execution_result.get('result_type', 'error'),
                    'execution_time_ms': execution_time_ms,
                    'step_count': len(context.step_results),
                    'error': execution_result.get('error'),
                    'script_result_id': script_result_id,
                    'step_results': context.step_results,
                    'report_url': report_url,
                    'logs_url': logs_url
                }
            
            print(f"[@testcase_executor:{execution_id}] Execution completed: {execution_result.get('result_type')}")
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Execution error: {str(e)}"
            print(f"[@testcase_executor:{execution_id}] ERROR: {error_msg}")
            
            import traceback
            traceback.print_exc()
            
            with self._lock:
                self._executions[execution_id]['status'] = 'failed'
                self._executions[execution_id]['error'] = error_msg
                self._executions[execution_id]['result'] = {
                    'success': False,
                    'error': error_msg,
                    'execution_time_ms': execution_time_ms
                }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of async execution.
        
        Returns:
            {
                'execution_id': str,
                'status': 'running' | 'completed' | 'failed',
                'current_block_id': str | None,
                'block_states': {},
                'result': {} | None,
                'error': str | None,
                'elapsed_time_ms': int
            }
        """
        with self._lock:
            if execution_id not in self._executions:
                return None
            
            execution = self._executions[execution_id].copy()
            
            # Calculate elapsed time
            start_time = execution.get('start_time', time.time())
            execution['elapsed_time_ms'] = int((time.time() - start_time) * 1000)
            
            # Don't include start_time in response
            execution.pop('start_time', None)
            
            return execution
    
    def _execute_graph_with_tracking(self, graph: Dict[str, Any], context: ScriptExecutionContext, execution_id: str) -> Dict[str, Any]:
        """
        Execute graph with real-time progress tracking for async execution.
        Updates execution state as blocks are processed.
        """
        nodes = {node['id']: node for node in graph['nodes']}
        edges = graph['edges']
        
        # Find START block
        start_node = next((node for node in graph['nodes'] if node['type'] == 'start'), None)
        if not start_node:
            return {'success': False, 'error': 'No START block found'}
        
        start_node_id = start_node['id']
        current_node_id = self._find_next_node(start_node_id, 'success', edges)
        
        if not current_node_id:
            executable_blocks = [n for n in graph['nodes'] if n['type'] not in ['start', 'success', 'failure']]
            if executable_blocks:
                return {'success': False, 'error': 'START block is not connected to any executable block'}
            else:
                context.overall_success = True
                return {'success': True, 'result_type': 'success'}
        
        max_iterations = 1000
        iteration_count = 0
        
        while current_node_id and iteration_count < max_iterations:
            iteration_count += 1
            
            # Update current block ID in execution state
            with self._lock:
                if execution_id in self._executions:
                    self._executions[execution_id]['current_block_id'] = current_node_id
            
            current_node = nodes.get(current_node_id)
            if not current_node:
                return {'success': False, 'error': f'Node not found: {current_node_id}'}
            
            node_type = current_node['type']
            
            # Terminal blocks
            if node_type == 'success':
                context.overall_success = True
                return {'success': True, 'result_type': 'success'}
            
            if node_type == 'failure':
                context.overall_success = False
                return {'success': False, 'result_type': 'failure', 'error': 'Test case reached FAILURE block'}
            
            # Execute block
            block_start_time = time.time()
            try:
                block_result = self._execute_block(current_node, context)
            except Exception as e:
                error_msg = f"Block {current_node_id} execution error: {str(e)}"
                return {'success': False, 'result_type': 'error', 'error': error_msg}
            
            block_duration_ms = int((time.time() - block_start_time) * 1000)
            
            # Update block state in execution tracking
            with self._lock:
                if execution_id in self._executions:
                    self._executions[execution_id]['block_states'][current_node_id] = {
                        'status': 'success' if block_result['success'] else 'failure',
                        'duration': block_duration_ms,
                        'error': block_result.get('error'),
                        'message': block_result.get('message')
                    }
            
            # Record step
            context.record_step_immediately({
                'block_id': current_node_id,
                'block_type': node_type,
                'success': block_result['success'],
                'execution_time_ms': block_result.get('execution_time_ms', 0),
                'message': block_result.get('message', ''),
                'error': block_result.get('error'),
                'logs': block_result.get('logs', ''),  # Include captured logs
                'step_category': 'testcase_block'
            })
            
            # Find next node
            edge_type = 'success' if block_result['success'] else 'failure'
            next_node_id = self._find_next_node(current_node_id, edge_type, edges)
            
            if not next_node_id:
                if edge_type == 'failure':
                    context.overall_success = False
                    return {'success': False, 'result_type': 'failure', 'error': f'Block {current_node_id} failed with no failure handler'}
                else:
                    context.overall_success = False
                    return {'success': False, 'result_type': 'error', 'error': f'No {edge_type} connection from block {current_node_id}'}
            
            current_node_id = next_node_id
        
        if iteration_count >= max_iterations:
            return {'success': False, 'result_type': 'error', 'error': 'Max iterations reached (possible infinite loop)'}
        
        return {'success': False, 'result_type': 'error', 'error': 'Graph execution ended unexpectedly'}
    
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
                
                # Resolve scriptConfig outputs and metadata before returning
                self._resolve_script_outputs_and_metadata(graph, context)
                
                return {'success': True, 'result_type': 'success'}
            
            if node_type == 'failure':
                context.overall_success = False
                print(f"[@testcase_executor] Reached FAILURE terminal block - test failed")
                return {'success': False, 'result_type': 'failure', 'error': 'Test case reached FAILURE block'}
            
            # Execute block
            self.current_block_id = current_node_id  # Set for output storage
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
                'logs': block_result.get('logs', ''),  # Include captured logs
                'step_category': 'testcase_block'
            })
            
            # Find next node based on success/failure result
            edge_type = 'success' if block_result['success'] else 'failure'
            print(f"[@testcase_executor] Looking for {edge_type} edge from block {current_node_id}...")
            next_node_id = self._find_next_node(current_node_id, edge_type, edges)
            
            if not next_node_id:
                # Block executed but has no outgoing connection for this result
                if edge_type == 'failure':
                    # IMPLICIT FAILURE ROUTING: Unconnected failure edges automatically route to FAILURE terminal
                    print(f"[@testcase_executor] No failure edge found from block {current_node_id} - implicitly routing to FAILURE terminal")
                    context.overall_success = False
                    return {'success': False, 'result_type': 'failure', 'error': f'Block {current_node_id} failed with no failure handler (implicit FAILURE terminal)'}
                else:
                    # Success edge must be connected - this is an error in graph structure
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
        Captures all stdout/stderr logs during execution.
        
        Returns:
            {success: bool, execution_time_ms: int, message: str, error: str, logs: str}
        """
        # Capture logs during block execution
        log_buffer = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to buffer
            sys.stdout = log_buffer
            sys.stderr = log_buffer
            
            node_type = node['type']
            data = node.get('data', {})
            
            # START block should never reach here - it's skipped in _execute_graph
            if node_type == 'start':
                raise Exception('START block should not be executed - it is only an entry point marker')
            
            # Execute based on type
            if node_type == 'action':
                result = self._execute_action_block(data, context)
            elif node_type == 'verification':
                result = self._execute_verification_block(data, context)
            elif node_type == 'navigation':
                result = self._execute_navigation_block(data, context)
            elif node_type == 'loop':
                result = self._execute_loop_block(node, context)
            else:
                result = {'success': False, 'error': f'Unknown block type: {node_type}'}
            
            # Add captured logs to result
            result['logs'] = log_buffer.getvalue()
            return result
            
        finally:
            # Always restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _execute_action_block(self, data: Dict, context: ScriptExecutionContext) -> Dict[str, Any]:
        """Execute action block using Orchestrator"""
        start_time = time.time()
        
        try:
            command = data.get('command')
            params = data.get('params', {})
            retry_actions = data.get('retry_actions', [])
            failure_actions = data.get('failure_actions', [])
            
            # Build actions array from single action
            actions = [{
                'command': command,
                'params': params
            }]
            
            # Use orchestrator for unified logging
            from backend_host.src.orchestrator import ExecutionOrchestrator
            result = ExecutionOrchestrator.execute_actions(
                device=self.device,
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
            
            # Store block output_data for scriptConfig resolution
            if result.get('output_data'):
                if not hasattr(context, 'block_outputs'):
                    context.block_outputs = {}
                # Store with current block ID
                if self.current_block_id:
                    context.block_outputs[self.current_block_id] = result['output_data']
                    print(f"[@testcase_executor] Stored block outputs for {self.current_block_id}: {list(result['output_data'].keys())}")
            
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
            
            # DEBUG: Check navigation context before execution
            nav_context = self.device.navigation_context
            print(f"[@testcase_executor:_execute_navigation_block] 🔍 NAVIGATION CONTEXT CHECK:")
            print(f"[@testcase_executor:_execute_navigation_block]   → current_node_id: {nav_context.get('current_node_id')}")
            print(f"[@testcase_executor:_execute_navigation_block]   → current_node_label: {nav_context.get('current_node_label')}")
            print(f"[@testcase_executor:_execute_navigation_block]   → target_node_label: {data.get('target_node_label')}")
            print(f"[@testcase_executor:_execute_navigation_block]   → target_node_id: {data.get('target_node_id')}")
            
            # Call navigation_executor with resilient parameter selection
            # PRIORITY: Use label if available (more human-readable), fallback to ID
            # Backend validation requires EXACTLY ONE parameter, not both
            target_label = data.get('target_node_label') or data.get('target_node')
            target_id = data.get('target_node_id')
            
            # Prefer label over ID - only pass ID if no label exists
            if target_label:
                print(f"[@testcase_executor:_execute_navigation_block] Using target_node_label: {target_label}")
                result = navigation_executor.execute_navigation(
                    tree_id=context.tree_id,
                    userinterface_name=context.userinterface_name,
                    target_node_id=None,  # Explicitly set to None when using label
                    target_node_label=target_label,
                    team_id=context.team_id,
                    context=context
                )
            elif target_id:
                print(f"[@testcase_executor:_execute_navigation_block] Using target_node_id: {target_id}")
                result = navigation_executor.execute_navigation(
                    tree_id=context.tree_id,
                    userinterface_name=context.userinterface_name,
                    target_node_id=target_id,
                    target_node_label=None,  # Explicitly set to None when using ID
                    team_id=context.team_id,
                    context=context
                )
            else:
                return {
                    'success': False,
                    'execution_time_ms': int((time.time() - start_time) * 1000),
                    'error': 'Navigation block missing both target_node_label and target_node_id'
                }
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Get the target for the message
            target = data.get('target_node_label') or data.get('target_node') or data.get('target_node_id') or 'unknown'
            
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
    
    def _resolve_script_outputs_and_metadata(self, graph: Dict[str, Any], context: ScriptExecutionContext):
        """
        Resolve scriptConfig outputs and metadata from block outputs.
        Populates context.script_outputs and context.metadata based on links.
        
        Args:
            graph: Graph JSON with scriptConfig
            context: Execution context with block_outputs
        """
        script_config = graph.get('scriptConfig')
        if not script_config:
            print(f"[@testcase_executor] No scriptConfig found - skipping output/metadata resolution")
            return
        
        print(f"[@testcase_executor] ========== RESOLVING SCRIPT OUTPUTS & METADATA ==========")
        
        # Resolve Script Outputs
        script_outputs_config = script_config.get('outputs', [])
        if script_outputs_config:
            print(f"[@testcase_executor] Resolving {len(script_outputs_config)} script outputs...")
            
            for output_config in script_outputs_config:
                output_name = output_config.get('name')
                source_block_id = output_config.get('sourceBlockId')
                source_output_name = output_config.get('sourceOutputName')
                source_output_path = output_config.get('sourceOutputPath')  # JSONPath for nested access
                
                if not output_name:
                    print(f"[@testcase_executor] Warning: Output config missing 'name', skipping")
                    continue
                
                if not source_block_id or not source_output_name:
                    print(f"[@testcase_executor] Warning: Output '{output_name}' has no source link, skipping")
                    continue
                
                # Get block output from context
                block_outputs = getattr(context, 'block_outputs', {})
                block_data = block_outputs.get(source_block_id, {})
                output_value = block_data.get(source_output_name)
                
                if output_value is None:
                    print(f"[@testcase_executor] Warning: Block '{source_block_id}' has no output '{source_output_name}'")
                    continue
                
                # Apply JSONPath if specified (for nested access like parsed_data.serial)
                if source_output_path and isinstance(output_value, dict):
                    try:
                        # Simple dot-notation path (e.g., "serial" or "device.serial")
                        for key in source_output_path.split('.'):
                            output_value = output_value.get(key)
                            if output_value is None:
                                break
                    except Exception as e:
                        print(f"[@testcase_executor] Error accessing path '{source_output_path}': {e}")
                        output_value = None
                
                if output_value is not None:
                    # Store in context.script_outputs (for campaign chaining)
                    if not hasattr(context, 'script_outputs'):
                        context.script_outputs = {}
                    context.script_outputs[output_name] = output_value
                    print(f"[@testcase_executor]   ✓ {output_name} = {output_value}")
                else:
                    print(f"[@testcase_executor]   ✗ {output_name} = None (path not found)")
        
        # Resolve Metadata
        metadata_config = script_config.get('metadata', {})
        metadata_mode = metadata_config.get('mode', 'append')
        metadata_fields = metadata_config.get('fields', [])
        
        if metadata_fields:
            print(f"[@testcase_executor] Resolving {len(metadata_fields)} metadata fields (mode: {metadata_mode})...")
            
            resolved_metadata = {}
            
            for field_config in metadata_fields:
                field_name = field_config.get('name')
                source_block_id = field_config.get('sourceBlockId')
                source_output_name = field_config.get('sourceOutputName')
                
                if not field_name:
                    print(f"[@testcase_executor] Warning: Metadata field missing 'name', skipping")
                    continue
                
                if not source_block_id or not source_output_name:
                    print(f"[@testcase_executor] Warning: Metadata field '{field_name}' has no source link, skipping")
                    continue
                
                # Get block output from context
                block_outputs = getattr(context, 'block_outputs', {})
                block_data = block_outputs.get(source_block_id, {})
                field_value = block_data.get(source_output_name)
                
                if field_value is not None:
                    resolved_metadata[field_name] = field_value
                    print(f"[@testcase_executor]   ✓ {field_name} = {field_value if not isinstance(field_value, dict) else '{...}'}")
                else:
                    print(f"[@testcase_executor]   ✗ {field_name} = None (not found)")
            
            # Apply to context.metadata based on mode
            if metadata_mode == 'set':
                # Replace entire metadata
                context.metadata = resolved_metadata
                print(f"[@testcase_executor] Metadata mode 'set': replaced with {len(resolved_metadata)} fields")
            else:  # append (default)
                # Merge into existing metadata
                if not hasattr(context, 'metadata'):
                    context.metadata = {}
                context.metadata.update(resolved_metadata)
                print(f"[@testcase_executor] Metadata mode 'append': added {len(resolved_metadata)} fields")
        
        print(f"[@testcase_executor] ========== RESOLUTION COMPLETE ==========")
        print(f"[@testcase_executor] Script Outputs: {getattr(context, 'script_outputs', {})}")
        print(f"[@testcase_executor] Metadata: {context.metadata}")
    
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

