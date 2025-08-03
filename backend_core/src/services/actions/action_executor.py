"""
Standardized Action Executor

This module provides a standardized way to execute actions that can be used by:
- Python code directly (navigation execution, scripts, etc.)
- API endpoints (maintaining consistency)
- Frontend hooks (via API calls)

The core logic is the same as /server/action/executeBatch but available as a reusable class.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from shared.lib.utils.route_utils import proxy_to_host_direct


class ActionExecutor:
    """
    Standardized action executor that provides consistent action execution
    across Python code and API endpoints.
    """
    
    def __init__(self, host: Dict[str, Any], device_id: Optional[str] = None, tree_id: str = None, edge_id: str = None, team_id: str = None):
        """
        Initialize ActionExecutor
        
        Args:
            host: Host configuration dict with host_name, devices, etc.
            device_id: Optional device ID for multi-device hosts
            tree_id: Tree ID for navigation context
            edge_id: Edge ID for navigation context
            team_id: Team ID for database context
        """
        self.host = host
        self.device_id = device_id
        self.tree_id = tree_id
        self.edge_id = edge_id
        
        # team_id is required
        self.team_id = team_id
        
        # Validate host configuration
        if not host or not host.get('host_name'):
            raise ValueError("Host configuration with host_name is required")
    
    def execute_actions(self, 
                       actions: List[Dict[str, Any]], 
                       retry_actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute batch of actions with retry logic
        
        Args:
            actions: List of action dictionaries with command, params, etc.
            retry_actions: Optional list of retry actions to execute if main actions fail
            
        Returns:
            Dict with success status, results, and execution statistics
        """
        print(f"[@lib:action_executor:execute_actions] Starting batch action execution")
        print(f"[@lib:action_executor:execute_actions] Processing {len(actions)} main actions, {len(retry_actions or [])} retry actions")
        print(f"[@lib:action_executor:execute_actions] Host: {self.host.get('host_name')}")
        
        # Validate inputs
        if not actions:
            return {
                'success': True,
                'message': 'No actions to execute',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        # Filter valid actions
        valid_actions = self._filter_valid_actions(actions)
        valid_retry_actions = self._filter_valid_actions(retry_actions or [])
        
        if not valid_actions:
            return {
                'success': False,
                'error': 'All actions were invalid and filtered out',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        results = []
        passed_count = 0
        execution_order = 1
        
        # Execute main actions - stop on first failure
        print(f"[@lib:action_executor:execute_actions] Executing {len(valid_actions)} main actions")
        main_actions_failed = False
        
        for i, action in enumerate(valid_actions):
            result = self._execute_single_action(action, execution_order, i+1, 'main')
            results.append(result)
            
            if result.get('success'):
                passed_count += 1
            else:
                # First action failed - stop executing remaining main actions
                print(f"[@lib:action_executor:execute_actions] Main action {i+1} failed, stopping main action execution")
                main_actions_failed = True
                break
                
            execution_order += 1
        
        # Execute retry actions if any main action failed
        if main_actions_failed and valid_retry_actions:
            print(f"[@lib:action_executor:execute_actions] Main actions failed, executing {len(valid_retry_actions)} retry actions")
            for i, retry_action in enumerate(valid_retry_actions):
                result = self._execute_single_action(retry_action, execution_order, i+1, 'retry')
                results.append(result)
                if result.get('success'):
                    passed_count += 1
                execution_order += 1

        # Calculate overall success (main actions must pass)
        overall_success = passed_count >= len(valid_actions)
        
        print(f"[@lib:action_executor:execute_actions] Batch completed: {passed_count}/{len(valid_actions)} main actions passed, overall success: {overall_success}")
        
        # Build simple error message showing which actions failed
        failed_actions = [r for r in results if not r.get('success')]
        
        if failed_actions:
            failed_names = [f.get('message', 'Unknown action') for f in failed_actions]
            error_message = f"Actions failed: {', '.join(failed_names)}"
        else:
            error_message = None
        
        return {
            'success': overall_success,
            'total_count': len(valid_actions),
            'passed_count': passed_count,
            'failed_count': len(valid_actions) - passed_count,
            'results': results,
            'message': f'Batch action execution completed: {passed_count}/{len(valid_actions)} passed',
            'error': error_message
        }
    
    def _filter_valid_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out invalid actions"""
        valid_actions = []
        
        for i, action in enumerate(actions):
            if not action.get('command') or action.get('command', '').strip() == '':
                print(f"[@lib:action_executor:_filter_valid_actions] Removing action {i}: No command specified")
                continue
            
            # Check if action requires input and has it
            if action.get('requiresInput') and not action.get('inputValue'):
                print(f"[@lib:action_executor:_filter_valid_actions] Removing action {i}: No input value for required input")
                continue
            
            valid_actions.append(action)
        
        return valid_actions
    
    def _execute_single_action(self, action: Dict[str, Any], execution_order: int, action_number: int, action_category: str) -> Dict[str, Any]:
        """Execute a single action and return standardized result"""
        start_time = time.time()
        
        try:
            print(f"[@lib:action_executor:_execute_single_action] Executing {action_category} action {action_number}: {action.get('command')} with params {action.get('params', {})}")
            
            # Use action params directly - wait_time is already in params from database
            params = action.get('params', {})
            
            # Proxy to host remote command endpoint using direct host info (no Flask context needed)
            response_data, status_code = proxy_to_host_direct(self.host, '/host/remote/executeCommand', 'POST', {
                'command': action.get('command'),
                'params': params,
                'device_id': self.device_id or 'device1'  # Include device_id in request
            })
            
            execution_time = int((time.time() - start_time) * 1000)
            success = status_code == 200 and response_data.get('success', False)
            
            print(f"[@lib:action_executor:_execute_single_action] Action {action_number} result: success={success}, time={execution_time}ms")
            
            # Record execution directly to database
            self._record_execution_to_database(
                success=success,
                execution_time_ms=execution_time,
                message=response_data.get('message') if success else response_data.get('error'),
                error_details=None if success else {'error': response_data.get('error')}
            )
            
            # Return standardized result (same format as API)
            return {
                'success': success,
                'message': f"{action.get('label', action.get('command'))}",
                'error': response_data.get('error') if not success else None,
                'resultType': 'PASS' if success else 'FAIL',
                'execution_time_ms': execution_time,
                'action_category': action_category,
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            print(f"[@lib:action_executor:_execute_single_action] Action {action_number} error: {str(e)}")
            
            # Record failed execution directly to database
            self._record_execution_to_database(
                success=False,
                execution_time_ms=execution_time,
                message=str(e),
                error_details={'error': str(e)}
            )
            
            action_label = action.get('label', action.get('command'))
            return {
                'success': False,
                'message': action_label,
                'error': str(e),
                'resultType': 'FAIL',
                'execution_time_ms': execution_time,
                'action_category': action_category,
                'action_details': f"{action_label} ({action.get('command')})" if action.get('label') != action.get('command') else action_label
            }
    
    def _record_execution_to_database(self, success: bool, execution_time_ms: int, message: str, error_details: Optional[Dict] = None):
        """Record single execution directly to database"""
        try:
            from shared.lib.supabase.execution_results_db import record_edge_execution
            
            record_edge_execution(
                team_id=self.team_id,
                tree_id=self.tree_id,
                edge_id=self.edge_id,
                host_name=self.host.get('host_name'),
                success=success,
                execution_time_ms=execution_time_ms,
                message=message,
                error_details=error_details,
                script_result_id=getattr(self, 'script_result_id', None),
                script_context=getattr(self, 'script_context', 'direct')
            )
            
        except Exception as e:
            print(f"[@lib:action_executor:_record_execution_to_database] Database recording error: {e}") 