"""
Declarative Script Framework
Ultra-simple decorator-based script execution
"""

import functools
import argparse
from typing import Callable, Any
from .script_executor import ScriptExecutor, handle_keyboard_interrupt, handle_unexpected_error

# Global context for current script execution
_current_context = None
_current_executor = None

def script(name: str, description: str):
    """
    Decorator that handles all script infrastructure automatically
    
    @script("goto_live", "Navigate to live node")
    def main():
        navigate_to("live")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper():
            global _current_context, _current_executor
            
            # Setup everything automatically
            executor = ScriptExecutor(name, description)
            parser = executor.create_argument_parser()
            
            # Add script-specific arguments from function attribute
            # Check both the original function and the wrapper (since _script_args is set after decoration)
            script_args = None
            if hasattr(func, '_script_args'):
                script_args = func._script_args
            elif hasattr(wrapper, '_script_args'):
                script_args = wrapper._script_args
            
            if script_args:
                def str_to_bool(v):
                    if isinstance(v, bool):
                        return v
                    if v.lower() in ('yes', 'true', 't', 'y', '1'):
                        return True
                    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                        return False
                    else:
                        raise argparse.ArgumentTypeError('Boolean value expected.')
                
                for arg_spec in script_args:
                    # Parse format: '--name:type:default'
                    parts = arg_spec.split(':')
                    if len(parts) != 3:
                        continue
                    
                    arg_name, arg_type, default_value = parts
                    
                    # Convert type string to actual type
                    if arg_type == 'int':
                        parser.add_argument(arg_name, type=int, default=int(default_value),
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
                    elif arg_type == 'str':
                        parser.add_argument(arg_name, type=str, default=default_value,
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
                    elif arg_type == 'bool':
                        default_bool = default_value.lower() in ('true', 't', 'yes', 'y', '1')
                        parser.add_argument(arg_name, type=str_to_bool, default=default_bool,
                                           help=f'{arg_name.replace("--", "").replace("_", " ").title()} (default: {default_value})')
            
            args = parser.parse_args()
            context = executor.setup_execution_context(args, enable_db_tracking=True)
            
            if context.error_message:
                executor.cleanup_and_exit(context, args.userinterface_name)
                return
            
            # Set global context for helper functions
            _current_context = context
            _current_executor = executor
            
            # Store args in context for access
            context.args = args
            
            try:
                # Execute user's business logic
                result = func()
                
                # Auto-determine success
                if result is None or result is True:
                    executor.test_success(context)
                else:
                    executor.test_fail(context)
                    
            except KeyboardInterrupt:
                handle_keyboard_interrupt(name)
            except Exception as e:
                handle_unexpected_error(name, e)
            finally:
                executor.cleanup_and_exit(context, args.userinterface_name)
                _current_context = None
                _current_executor = None
        
        return wrapper
    return decorator

# PUBLIC: Helper functions for scripts
def get_device():
    """Get current device"""
    return _current_context.selected_device

def is_mobile_device() -> bool:
    """Check if current device is mobile"""
    return "mobile" in get_device().device_model.lower()

def navigate_to(target_node: str) -> bool:
    """Navigate to target node - direct call to NavigationExecutor"""
    context = _current_context
    device = context.selected_device
    args = context.args
    
    # Load navigation tree if not already loaded
    if not context.tree_id:
        nav_result = device.navigation_executor.load_navigation_tree(
            args.userinterface_name, 
            context.team_id,
            'navigation'
        )
        if not nav_result['success']:
            print(f"❌ [navigate_to] Navigation tree loading failed: {nav_result.get('error', 'Unknown error')}")
            return False
        
        context.tree_id = nav_result['tree_id']
        context.tree_data = nav_result
        context.nodes = nav_result.get('nodes', [])
        context.edges = nav_result.get('edges', [])
        print(f"✅ [navigate_to] Navigation tree loaded: {context.tree_id}")
    
    # Direct call to NavigationExecutor - no middle layer
    result = device.navigation_executor.execute_navigation(
        tree_id=context.tree_id,
        target_node_id=target_node,
        current_node_id=getattr(context, 'current_node_id', None),
        image_source_url=device.get_image_source_url(),
        team_id=context.team_id
    )
    
    return result.get('success', False)

def get_args():
    """Get parsed command line arguments"""
    return _current_context.args

# PRIVATE: Internal functions (scripts should not use these)
def _get_context():
    """PRIVATE: Get current execution context"""
    return _current_context

def _get_executor():
    """PRIVATE: Get current script executor"""
    return _current_executor


def _get_validation_plan():
    """PRIVATE: Get list of transitions to validate"""
    from backend_host.src.services.navigation.navigation_pathfinding import find_optimal_edge_validation_sequence
    
    context = _current_context
    
    # Ensure navigation tree is loaded
    if not context.tree_id:
        device = context.selected_device
        args = context.args
        nav_result = device.navigation_executor.load_navigation_tree(
            args.userinterface_name, 
            context.team_id,
            'validation'
        )
        if not nav_result['success']:
            print(f"❌ [_get_validation_plan] Navigation tree loading failed")
            return []
        
        context.tree_id = nav_result['tree_id']
        context.tree_data = nav_result
    
    return find_optimal_edge_validation_sequence(context.tree_id, context.team_id)
