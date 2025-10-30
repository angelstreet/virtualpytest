"""
Standard Block Executor
Executes standard blocks like sleep, set_variable, condition, loop, etc.
"""

import time
from typing import Dict, List, Any
from datetime import datetime


class StandardBlockExecutor:
    """
    Executor for standard blocks (sleep, set_variable, condition, etc.)
    PURE - no log capture (handled by orchestrator)
    """
    
    def __init__(self, device=None):
        """
        Initialize standard block executor
        
        Args:
            device: Optional device instance (for device-specific operations)
        """
        self.device = device
        
        # Registry of standard block handlers
        self.block_registry = {
            'sleep': self._execute_sleep,
            'set_variable': self._execute_set_variable,
            'get_current_time': self._execute_get_current_time,
            'condition': self._execute_condition,
            'loop': self._execute_loop,
            'custom_code': self._execute_custom_code,
            'evaluate_condition': self._execute_evaluate_condition,
            'set_metadata': self._execute_set_metadata,
            'common_operation': self._execute_common_operation
        }
    
    def execute_blocks(self, blocks: List[Dict[str, Any]], context=None) -> Dict[str, Any]:
        """
        Execute batch of standard blocks (PURE - no log capture)
        
        Args:
            blocks: List of block dictionaries
            context: Optional execution context
            
        Returns:
            Dict with success status, results, and execution statistics
        """
        print(f"[@StandardBlockExecutor] Executing {len(blocks)} standard block(s)")
        
        # Validate inputs
        if not blocks:
            return {
                'success': True,
                'message': 'No blocks to execute',
                'results': [],
                'passed_count': 0,
                'total_count': 0
            }
        
        results = []
        passed_count = 0
        
        # Execute each block
        for i, block in enumerate(blocks):
            block_type = block.get('type') or block.get('command')
            
            start_time = time.time()
            result = self._execute_single_block(block, context)
            execution_time = int((time.time() - start_time) * 1000)
            
            # Add execution time to result
            result['execution_time_ms'] = execution_time
            result['block_type'] = block_type
            results.append(result)
            
            # Count successful blocks
            if result.get('success'):
                passed_count += 1
        
        overall_success = passed_count == len(blocks)
        
        return {
            'success': overall_success,
            'total_count': len(blocks),
            'passed_count': passed_count,
            'failed_count': len(blocks) - passed_count,
            'results': results,
            'message': f'Batch block execution completed: {passed_count}/{len(blocks)} passed'
        }
    
    def _execute_single_block(self, block: Dict[str, Any], context=None) -> Dict[str, Any]:
        """
        Execute a single standard block
        
        Args:
            block: Block dictionary with type/command and params
            context: Optional execution context
            
        Returns:
            Dict with success status, message, and optional output_data
        """
        block_type = block.get('type') or block.get('command')
        params = block.get('params', {}) or block.get('data', {})
        
        print(f"[@StandardBlockExecutor] Executing block: {block_type}")
        
        # Get handler from registry
        handler = self.block_registry.get(block_type)
        
        if not handler:
            return {
                'success': False,
                'error': f'Unknown standard block type: {block_type}'
            }
        
        try:
            return handler(params, context)
        except Exception as e:
            return {
                'success': False,
                'error': f'Block execution failed: {str(e)}'
            }
    
    # Block Handlers
    
    def _execute_sleep(self, params: Dict, context=None) -> Dict[str, Any]:
        """Sleep for specified duration"""
        duration = params.get('duration', 1)  # seconds
        
        print(f"[@StandardBlockExecutor:sleep] Sleeping for {duration} seconds...")
        time.sleep(duration)
        
        return {
            'success': True,
            'message': f'Slept for {duration} seconds'
        }
    
    def _execute_set_variable(self, params: Dict, context=None) -> Dict[str, Any]:
        """Set a variable in context"""
        variable_name = params.get('variable_name') or params.get('name')
        variable_value = params.get('variable_value') or params.get('value')
        
        if not variable_name:
            return {
                'success': False,
                'error': 'variable_name is required'
            }
        
        # Set in context if available
        if context and hasattr(context, 'variables'):
            context.variables[variable_name] = variable_value
            print(f"[@StandardBlockExecutor:set_variable] Set {variable_name} = {variable_value}")
        else:
            print(f"[@StandardBlockExecutor:set_variable] No context available - variable not persisted")
        
        return {
            'success': True,
            'message': f'Set variable {variable_name} = {variable_value}',
            'output_data': {
                'variable_name': variable_name,
                'variable_value': variable_value
            }
        }
    
    def _execute_get_current_time(self, params: Dict, context=None) -> Dict[str, Any]:
        """Get current time"""
        format_string = params.get('format', '%Y-%m-%d %H:%M:%S')
        
        current_time = datetime.now().strftime(format_string)
        
        # Store in context if variable name provided
        variable_name = params.get('variable_name')
        if variable_name and context and hasattr(context, 'variables'):
            context.variables[variable_name] = current_time
        
        print(f"[@StandardBlockExecutor:get_current_time] Current time: {current_time}")
        
        return {
            'success': True,
            'message': f'Current time: {current_time}',
            'output_data': {
                'current_time': current_time
            }
        }
    
    def _execute_condition(self, params: Dict, context=None) -> Dict[str, Any]:
        """Evaluate a condition"""
        condition = params.get('condition')
        
        if not condition:
            return {
                'success': False,
                'error': 'condition is required'
            }
        
        try:
            # Evaluate condition in context
            if context and hasattr(context, 'variables'):
                result = eval(condition, {"__builtins__": {}}, context.variables)
            else:
                result = eval(condition, {"__builtins__": {}}, {})
            
            print(f"[@StandardBlockExecutor:condition] Condition '{condition}' evaluated to: {result}")
            
            return {
                'success': True,
                'message': f'Condition evaluated to: {result}',
                'output_data': {
                    'condition_result': result
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to evaluate condition: {str(e)}'
            }
    
    def _execute_loop(self, params: Dict, context=None) -> Dict[str, Any]:
        """Execute loop (handled by graph executor)"""
        iterations = params.get('iterations', 1)
        
        return {
            'success': True,
            'message': f'Loop configured for {iterations} iterations',
            'output_data': {
                'iterations': iterations
            }
        }
    
    def _execute_custom_code(self, params: Dict, context=None) -> Dict[str, Any]:
        """Execute custom Python code"""
        code = params.get('code')
        
        if not code:
            return {
                'success': False,
                'error': 'code is required'
            }
        
        try:
            # Execute code in context
            if context and hasattr(context, 'variables'):
                exec(code, {"__builtins__": {}}, context.variables)
            else:
                exec(code, {"__builtins__": {}}, {})
            
            print(f"[@StandardBlockExecutor:custom_code] Executed custom code")
            
            return {
                'success': True,
                'message': 'Custom code executed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to execute custom code: {str(e)}'
            }
    
    def _execute_evaluate_condition(self, params: Dict, context=None) -> Dict[str, Any]:
        """Evaluate condition (alias for condition)"""
        return self._execute_condition(params, context)
    
    def _execute_set_metadata(self, params: Dict, context=None) -> Dict[str, Any]:
        """Set metadata"""
        key = params.get('key')
        value = params.get('value')
        
        if not key:
            return {
                'success': False,
                'error': 'key is required'
            }
        
        # Store in context metadata
        if context and hasattr(context, 'metadata'):
            context.metadata[key] = value
            print(f"[@StandardBlockExecutor:set_metadata] Set metadata {key} = {value}")
        else:
            print(f"[@StandardBlockExecutor:set_metadata] No context available - metadata not persisted")
        
        return {
            'success': True,
            'message': f'Set metadata {key} = {value}',
            'output_data': {
                'key': key,
                'value': value
            }
        }
    
    def _execute_common_operation(self, params: Dict, context=None) -> Dict[str, Any]:
        """Execute common operation"""
        operation = params.get('operation')
        
        if not operation:
            return {
                'success': False,
                'error': 'operation is required'
            }
        
        # Delegate to specific operation handler
        operation_handlers = {
            'sleep': self._execute_sleep,
            'set_variable': self._execute_set_variable,
            'get_time': self._execute_get_current_time
        }
        
        handler = operation_handlers.get(operation)
        if handler:
            return handler(params, context)
        
        return {
            'success': False,
            'error': f'Unknown common operation: {operation}'
        }
    
    def get_available_blocks(self) -> List[str]:
        """Get list of available standard blocks"""
        return list(self.block_registry.keys())

